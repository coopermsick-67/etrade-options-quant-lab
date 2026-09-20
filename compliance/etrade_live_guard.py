"""Human approval and immutable-ticket guard for live E*TRADE actions."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any


class ComplianceError(PermissionError):
    """Raised when a live action lacks valid human approval."""


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
        except (ValueError, json.JSONDecodeError, binascii.Error) as exc:
            raise ComplianceError("malformed approval token") from exc
        nonce = str(payload.get("nonce", ""))
        if not nonce or nonce in self._used:
            raise ComplianceError("approval token is missing or already used")
        if payload.get("actor") != "user":
            raise ComplianceError("approval actor is not user")
        if int(payload.get("expires_at", 0)) < int(time.time()):
            raise ComplianceError("approval token expired")
        if payload.get("ticket_hash") != ticket.sha256():
            raise ComplianceError("approval does not match immutable trade ticket")
        self._used.add(nonce)
        return payload
