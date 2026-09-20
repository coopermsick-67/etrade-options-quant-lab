"""E*TRADE broker adapter with an explicit human-approved live path."""

from __future__ import annotations

from typing import Any

from brokers.base import BrokerOrder
from brokers.etrade.client import ETradeClient
from compliance.etrade_live_guard import ApprovalTokenService, ComplianceError, TradeTicket


class BrokerCapabilityError(RuntimeError):
    """Raised when a requested broker capability is not officially available."""


class ETradeLiveBroker:
    def __init__(
        self,
        client: ETradeClient,
        account_id_key: str,
        approval_service: ApprovalTokenService,
        live_trading_enabled: bool = False,
    ) -> None:
        self.client = client
        self.account_id_key = account_id_key
        self.approval_service = approval_service
        self.live_trading_enabled = live_trading_enabled

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.client.environment != "production":
            raise ComplianceError("live order preview requires ETRADE_ENV=production")
        return self.client.preview_order(self.account_id_key, payload)

    def submit(
        self, ticket: TradeTicket, payload: dict[str, Any], approval_token: str
    ) -> dict[str, Any]:
        if not self.live_trading_enabled:
            raise ComplianceError("live trading is disabled")
        if self.client.environment != "production":
            raise ComplianceError("live order submission requires production environment")
        self.approval_service.consume(ticket, approval_token)
        return self.client.place_order(self.account_id_key, payload)


class RobinhoodOptionsBroker:
    """Intentionally disabled until an official public options API is verified."""

    def __init__(self) -> None:
        self.enabled = False

    def submit(self, *_: Any, **__: Any) -> BrokerOrder:
        raise BrokerCapabilityError(
            "Robinhood live options execution is disabled; see docs/ROBINHOOD_CAPABILITY_REPORT.md"
        )
