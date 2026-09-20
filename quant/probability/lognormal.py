"""Explicit real-world and risk-neutral lognormal probabilities."""

from __future__ import annotations

from math import exp, isfinite, log, sqrt

from scipy.stats import norm


def _validate(spot: float, strike: float, volatility: float, time: float) -> None:
    if any(not isfinite(value) for value in (spot, strike, volatility, time)):
        raise ValueError("probability inputs must be finite")
    if spot <= 0 or strike <= 0 or volatility < 0 or time < 0:
        raise ValueError("spot must be positive, volatility non-negative, and time non-negative")


def probability_above(
    spot: float, strike: float, time: float, volatility: float, drift: float
) -> float:
    """P(S_T > strike) under a real-world/model lognormal process."""

    _validate(spot, strike, volatility, time)
    if not isfinite(drift):
        raise ValueError("drift must be finite")
    if time == 0 or volatility == 0:
        terminal = spot if time == 0 else spot * exp(drift * time)
        return float(terminal > strike)
    d2 = (log(spot / strike) + (drift - 0.5 * volatility**2) * time) / (volatility * sqrt(time))
    return float(norm.cdf(d2))


def probability_below(
    spot: float, strike: float, time: float, volatility: float, drift: float
) -> float:
    _validate(spot, strike, volatility, time)
    if not isfinite(drift):
        raise ValueError("drift must be finite")
    if time == 0 or volatility == 0:
        terminal = spot if time == 0 else spot * exp(drift * time)
        return float(terminal < strike)
    d2 = (log(spot / strike) + (drift - 0.5 * volatility**2) * time) / (volatility * sqrt(time))
    return float(norm.cdf(-d2))


def probability_between(
    spot: float,
    lower: float,
    upper: float,
    time: float,
    volatility: float,
    drift: float,
) -> float:
    _validate(spot, lower, volatility, time)
    if upper <= lower:
        raise ValueError("lower must be less than upper")
    if not isfinite(drift):
        raise ValueError("drift must be finite")
    if time == 0 or volatility == 0:
        terminal = spot if time == 0 else spot * exp(drift * time)
        return float(lower < terminal < upper)
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
