"""Ephemeral, server-side broker connection state.

The browser never receives consumer secrets, OAuth token secrets, request-token
secrets, cookies, or login credentials.  This deliberately keeps the local
single-user OAuth session in process memory until a secure encrypted secret
store is configured for a deployment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from threading import RLock

from apps.api.settings import Settings
from brokers.etrade.client import ETradeClient
from brokers.etrade.oauth import ETradeOAuthClient, ETradeOAuthError, OAuthTokens


class ETradeConnectionError(RuntimeError):
    """Raised when an E*TRADE OAuth session cannot be created or completed."""


@dataclass(frozen=True)
class _PendingAuthorization:
    connection_id: str
    request_token: OAuthTokens
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class _ActiveSession:
    tokens: OAuthTokens
    environment: str
    connected_at: datetime


class BrokerConnectionManager:
    """Manage the minimum state needed for an explicit E*TRADE OAuth flow."""

    def __init__(self, pending_ttl_seconds: int = 600) -> None:
        if pending_ttl_seconds <= 0:
            raise ValueError("pending_ttl_seconds must be positive")
        self.pending_ttl_seconds = pending_ttl_seconds
        self._lock = RLock()
        self._pending: dict[str, _PendingAuthorization] = {}
        self._active: _ActiveSession | None = None

    @staticmethod
    def _oauth_client(settings: Settings) -> ETradeOAuthClient:
        try:
            return ETradeOAuthClient(
                settings.etrade_consumer_key,
                settings.etrade_consumer_secret,
                environment=settings.etrade_env,
            )
        except ETradeOAuthError as exc:
            raise ETradeConnectionError(str(exc)) from exc

    def _purge_expired(self, now: datetime) -> None:
        expired = [
            connection_id
            for connection_id, pending in self._pending.items()
            if pending.expires_at <= now
        ]
        for connection_id in expired:
            self._pending.pop(connection_id, None)

    def start(self, settings: Settings) -> dict[str, str | int]:
        """Request a temporary token and return only the authorization URL."""

        client = self._oauth_client(settings)
        try:
            request_token = client.get_request_token()
        except Exception as exc:
            raise ETradeConnectionError("E*TRADE request-token exchange failed") from exc
        now = datetime.now(UTC)
        connection_id = token_urlsafe(32)
        pending = _PendingAuthorization(
            connection_id=connection_id,
            request_token=request_token,
            created_at=now,
            expires_at=now + timedelta(seconds=self.pending_ttl_seconds),
        )
        with self._lock:
            self._purge_expired(now)
            self._pending[connection_id] = pending
        return {
            "connection_id": connection_id,
            "authorization_url": client.build_authorization_url(request_token),
            "expires_in_seconds": self.pending_ttl_seconds,
            "environment": settings.etrade_env,
        }

    def complete(self, settings: Settings, connection_id: str, verifier: str) -> dict[str, str]:
        if not connection_id.strip() or not verifier.strip():
            raise ETradeConnectionError("connection_id and verifier are required")
        now = datetime.now(UTC)
        with self._lock:
            self._purge_expired(now)
            pending = self._pending.get(connection_id)
        if pending is None:
            raise ETradeConnectionError("OAuth authorization is missing or expired; start again")
        client = self._oauth_client(settings)
        try:
            access_token = client.get_access_token(pending.request_token, verifier)
        except Exception as exc:
            raise ETradeConnectionError("E*TRADE access-token exchange failed") from exc
        with self._lock:
            self._pending.pop(connection_id, None)
            self._active = _ActiveSession(access_token, settings.etrade_env, now)
        return {
            "status": "connected",
            "environment": settings.etrade_env,
            "connected_at": now.isoformat(),
        }

    def disconnect(self, settings: Settings) -> str:
        """Clear local secrets even if remote revocation is unavailable."""

        with self._lock:
            active = self._active
            self._active = None
            self._pending.clear()
        if active is None:
            return "not_connected"
        if active.environment != settings.etrade_env:
            return "disconnected_local_environment_changed"
        try:
            self._oauth_client(settings).revoke_access_token(active.tokens)
        except Exception:
            return "disconnected_local_revocation_unverified"
        return "disconnected"

    def has_active_session(self, settings: Settings) -> bool:
        with self._lock:
            return self._active is not None and self._active.environment == settings.etrade_env

    def _tokens_for(self, settings: Settings) -> tuple[str, str, str] | None:
        with self._lock:
            active = self._active
        if active is not None and active.environment == settings.etrade_env:
            return active.tokens.token, active.tokens.token_secret, "oauth_session"
        if settings.etrade_access_token.strip() and settings.etrade_access_token_secret.strip():
            return settings.etrade_access_token, settings.etrade_access_token_secret, "environment"
        return None

    def client(self, settings: Settings) -> ETradeClient:
        tokens = self._tokens_for(settings)
        if tokens is None:
            raise ETradeConnectionError(
                "E*TRADE is not connected. Configure consumer credentials and complete OAuth."
            )
        try:
            return ETradeClient(
                settings.etrade_consumer_key,
                settings.etrade_consumer_secret,
                tokens[0],
                tokens[1],
                environment=settings.etrade_env,
            )
        except ValueError as exc:
            raise ETradeConnectionError(str(exc)) from exc

    def status(self, settings: Settings) -> dict[str, object]:
        with self._lock:
            active = self._active
            pending_count = len(self._pending)
        consumer_ready = bool(
            settings.etrade_consumer_key.strip() and settings.etrade_consumer_secret.strip()
        )
        token_info = self._tokens_for(settings)
        if token_info is not None and consumer_ready:
            status = "connected" if token_info[2] == "oauth_session" else "configured"
            message = (
                "OAuth session is active in this API process."
                if token_info[2] == "oauth_session"
                else "OAuth access tokens are configured in the server environment."
            )
            source = token_info[2]
            connected_at = active.connected_at.isoformat() if active is not None else None
        elif consumer_ready:
            status = "ready_to_connect"
            message = "Consumer credentials are present. Start OAuth to authorize this environment."
            source = None
            connected_at = None
        else:
            status = "credentials_missing"
            message = "Set ETRADE_CONSUMER_KEY and ETRADE_CONSUMER_SECRET on the server first."
            source = None
            connected_at = None
        return {
            "provider": "etrade",
            "environment": settings.etrade_env,
            "status": status,
            "configured": token_info is not None,
            "consumer_credentials_ready": consumer_ready,
            "source": source,
            "connected_at": connected_at,
            "pending_authorizations": pending_count,
            "message": message,
            "live_orders_enabled": settings.effective_live_trading_enabled,
        }


connection_manager = BrokerConnectionManager()
