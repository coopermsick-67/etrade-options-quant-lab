"""Explicit real-world and risk-neutral lognormal probabilities."""

from __future__ import annotations

from math import log, sqrt

from scipy.stats import norm


def _validate(spot: float, volatility: float, time: float) -> None:
    if spot <= 0 or volatility < 0 or time < 0:
        raise ValueError("spot must be positive, volatility non-negative, and time non-negative")


def probability_above(
    spot: float, strike: float, time: float, volatility: float, drift: float
) -> float:
    """P(S_T > strike) under a real-world/model lognormal process."""

    _validate(spot, volatility, time)
    if strike <= 0:
        raise ValueError("strike must be positive")
    if time == 0:
        return float(spot > strike)
    if volatility == 0:
        return float(spot * __import__("math").exp(drift * time) > strike)
    d2 = (log(spot / strike) + (drift - 0.5 * volatility**2) * time) / (volatility * sqrt(time))
    return float(norm.cdf(d2))


def probability_below(
    spot: float, strike: float, time: float, volatility: float, drift: float
) -> float:
    return 1.0 - probability_above(spot, strike, time, volatility, drift)


def probability_between(
    spot: float,
    lower: float,
    upper: float,
    time: float,
    volatility: float,
    drift: float,
) -> float:
    if lower >= upper:
        raise ValueError("lower must be less than upper")
    return probability_above(spot, lower, time, volatility, drift) - probability_above(
        spot, upper, time, volatility, drift
    )


def probability_beyond_breakeven(
    spot: float,
    breakeven: float,
    time: float,
    volatility: float,
    drift: float,
    direction: str,
) -> float:
    if direction == "up":
        return probability_above(spot, breakeven, time, volatility, drift)
    if direction == "down":
        return probability_below(spot, breakeven, time, volatility, drift)
    raise ValueError("direction must be up or down")
