"""Human approval and immutable-ticket guard for live E*TRADE actions."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class ComplianceError(PermissionError):
    """Raised when a live action lacks valid human approval."""


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TradeTicket:
    account_id: str
    symbol: str
    action: str
    quantity: int
    limit_price: str
    order_type: str
    legs: tuple[dict[str, Any], ...]
    quote_timestamp: str
    risk_dollars: str
    model_version: str
    payload_hash: str | None = None

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str)
            for value in (
                self.account_id,
                self.symbol,
                self.action,
                self.limit_price,
                self.order_type,
                self.quote_timestamp,
                self.risk_dollars,
                self.model_version,
            )
        ):
            raise ValueError("ticket string fields have invalid types")
        if not self.account_id.strip() or not self.symbol.strip():
            raise ValueError("account and symbol are required")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 1:
            raise ValueError("ticket quantity must be positive")
        if not self.order_type.strip() or not self.action.strip():
            raise ValueError("ticket action and order type are required")
        if not isinstance(self.legs, (tuple, list)) or not self.legs or any(
            not isinstance(leg, dict) for leg in self.legs
        ):
            raise ValueError("ticket must contain at least one leg")
        if self.payload_hash is not None:
            if len(self.payload_hash) != 64 or any(
                character not in "0123456789abcdef" for character in self.payload_hash
            ):
                raise ValueError("ticket payload hash must be a lowercase SHA-256 hex digest")
        try:
            limit_price = Decimal(self.limit_price)
            risk_dollars = Decimal(self.risk_dollars)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("ticket prices and risk must be decimal strings") from exc
        if not limit_price.is_finite() or limit_price <= 0:
            raise ValueError("ticket limit price must be positive and finite")
        if not risk_dollars.is_finite() or risk_dollars < 0:
            raise ValueError("ticket risk must be non-negative and finite")

    def canonical_payload(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_payload().encode("utf-8")).hexdigest()


class ApprovalTokenService:
    """In-memory token store for the local single-user MVP.

    Production deployments should persist issued/consumed token IDs in a
    durable, encrypted store. The token remains single-use in this process and
    all token payloads are signed with HMAC-SHA256.
    """

    def __init__(self, secret: str, ttl_seconds: int = 90) -> None:
        if len(secret) < 32:
            raise ValueError("approval secret must contain at least 32 characters")
        if ttl_seconds < 1:
            raise ValueError("approval TTL must be positive")
        self._secret = secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds
        self._used: set[str] = set()
        self._lock = threading.Lock()

    def issue_from_ui(self, ticket: TradeTicket, actor: str = "user") -> str:
        if actor != "user":
            raise ComplianceError("approval tokens can only be issued by an explicit user action")
        now = int(time.time())
        payload = {
            "ticket_hash": ticket.sha256(),
            "issued_at": now,
            "expires_at": now + self.ttl_seconds,
            "nonce": secrets.token_urlsafe(16),
            "actor": actor,
        }
        encoded = (
            base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )
        signature = hmac.new(self._secret, encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def consume(self, ticket: TradeTicket, token: str) -> dict[str, Any]:
        try:
            encoded, signature = token.split(".", 1)
            expected = hmac.new(self._secret, encoded.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ComplianceError("invalid approval signature")
            padding = "=" * (-len(encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        except (ValueError, TypeError, json.JSONDecodeError, binascii.Error) as exc:
            raise ComplianceError("malformed approval token") from exc
        if not isinstance(payload, dict):
            raise ComplianceError("malformed approval payload")
        nonce = payload.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise ComplianceError("approval token is missing or already used")
        if payload.get("actor") != "user":
            raise ComplianceError("approval actor is not user")
        expires_at = payload.get("expires_at")
        if not isinstance(expires_at, int):
            raise ComplianceError("approval expiry is invalid")
        if expires_at <= int(time.time()):
            raise ComplianceError("approval token expired")
        if payload.get("ticket_hash") != ticket.sha256():
            raise ComplianceError("approval does not match immutable trade ticket")
        with self._lock:
            if nonce in self._used:
                raise ComplianceError("approval token is missing or already used")
            self._used.add(nonce)
        return payload
