"""Canonical market-data models with provenance and freshness fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum


class QuoteStatus(StrEnum):
    REALTIME = "REALTIME"
    DELAYED = "DELAYED"
    CLOSING = "CLOSING"
    INVALID = "INVALID"


class ContractType(StrEnum):
    CALL = "CALL"
    PUT = "PUT"


@dataclass(frozen=True)
class UnderlyingQuote:
    symbol: str
    price: float
    timestamp: datetime
    source: str
    status: QuoteStatus = QuoteStatus.DELAYED

    def age_seconds(self, now: datetime | None = None) -> float:
        now = now or datetime.now(UTC)
        timestamp = self.timestamp if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=UTC)
        return max(0.0, (now - timestamp).total_seconds())


@dataclass(frozen=True)
class OptionQuote:
    underlying_symbol: str
    option_symbol: str
    option_type: ContractType
    strike: float
    expiration: date
    timestamp: datetime
    bid: float
    ask: float
    last: float | None
    volume: int
    open_interest: int
    multiplier: float = 100.0
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None
    exercise_style: str = "American"
    source: str = "unknown"
    underlying_price: float | None = None

    @property
    def midpoint(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def spread_pct(self) -> float:
        return self.spread / self.midpoint if self.midpoint > 0 else float("inf")

    def age_seconds(self, now: datetime | None = None) -> float:
        now = now or datetime.now(UTC)
        timestamp = self.timestamp if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=UTC)
        return max(0.0, (now - timestamp).total_seconds())

    def dte(self, as_of: date | None = None) -> int:
        as_of = as_of or date.today()
        return max(0, (self.expiration - as_of).days)
