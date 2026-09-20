"""Portfolio Greek aggregation and simple stress scenarios."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite

from quant.pricing.black_scholes import Greeks


@dataclass(frozen=True)
class GreekPosition:
    symbol: str
    quantity: int
    multiplier: float
    greeks: Greeks

    def __post_init__(self) -> None:
        if self.quantity == 0 or not isfinite(self.multiplier) or self.multiplier <= 0:
            raise ValueError("Greek position quantity must be non-zero and multiplier positive")
        if not all(isfinite(value) for value in vars(self.greeks).values()):
            raise ValueError("Greek values must be finite")


@dataclass(frozen=True)
class PortfolioGreeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


def aggregate_greeks(positions: Iterable[GreekPosition]) -> PortfolioGreeks:
    totals = {name: 0.0 for name in ("delta", "gamma", "theta", "vega", "rho")}
    for position in positions:
        scale = position.quantity * position.multiplier
        for name in totals:
            totals[name] += getattr(position.greeks, name) * scale
    return PortfolioGreeks(**totals)


def greek_stress(
    positions: Iterable[GreekPosition], spot_moves: tuple[float, ...] = (-0.05, -0.02, 0.02, 0.05)
) -> dict[float, float]:
    portfolio = aggregate_greeks(positions)
    result: dict[float, float] = {}
    for move in spot_moves:
        result[move] = portfolio.delta * move + 0.5 * portfolio.gamma * move**2
    return result
