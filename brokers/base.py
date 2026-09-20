"""Broker-independent order contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
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
