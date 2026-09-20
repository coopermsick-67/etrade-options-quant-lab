"""Research strategy contracts. Strategies return candidates, never orders."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from data.normalization.models import ContractType


@dataclass(frozen=True)
class TradeLeg:
    action: str
    option_type: ContractType
    strike: float
    expiration: date
    quantity: int
    price: float
    symbol: str


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    underlying: str
    underlying_price: float
    strategy: str
    legs: tuple[TradeLeg, ...]
    dte: int
    bid: float
    ask: float
    midpoint: float
    spread_pct: float
    implied_volatility: float
    realized_volatility: float | None
    forecast_volatility: float
    expected_move: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    probability_profit: float
    probability_interval: tuple[float, float]
    gross_ev: float
    estimated_costs: float
    net_ev: float
    max_loss: float
    max_profit: float
    break_even: float
    risk_adjusted_edge: float
    status: str = "RESEARCH"
    assumptions: tuple[str, ...] = field(default_factory=tuple)
