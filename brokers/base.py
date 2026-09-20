"""Broker-independent order contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from typing import Protocol
from uuid import uuid4


class OrderAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    action: OrderAction
    quantity: int
    limit_price: float
    bid: float
    ask: float
    multiplier: float = 100.0
    client_order_id: str = field(default_factory=lambda: str(uuid4()))
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol is required")
        if not isinstance(self.action, OrderAction):
            raise ValueError("action must be an OrderAction")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 1:
            raise ValueError("quantity must be positive")
        for name, value in (
            ("limit_price", self.limit_price),
            ("bid", self.bid),
            ("ask", self.ask),
            ("multiplier", self.multiplier),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.limit_price <= 0 or self.multiplier <= 0:
            raise ValueError("limit price and multiplier must be positive")
        if self.bid < 0 or self.ask < 0 or self.ask < self.bid:
            raise ValueError("quote must be non-negative and ask must not be below bid")
        if not isinstance(self.client_order_id, str) or not self.client_order_id.strip():
            raise ValueError("client_order_id is required")
        if self.submitted_at.tzinfo is None or self.submitted_at.utcoffset() is None:
            raise ValueError("submitted_at must be timezone-aware")


@dataclass(frozen=True)
class Fill:
    order_id: str
    client_order_id: str
    symbol: str
    action: OrderAction
    quantity: int
    price: float
    fees: float
    timestamp: datetime


@dataclass(frozen=True)
class BrokerOrder:
    order_id: str
    request: OrderRequest
    status: OrderStatus
    filled_quantity: int = 0
    fill: Fill | None = None
    reason: str | None = None


class Broker(Protocol):
    def submit(self, request: OrderRequest) -> BrokerOrder: ...

    def cancel(self, order_id: str) -> BrokerOrder: ...

    def positions(self) -> Sequence[dict[str, object]]: ...
