"""Cox-Ross-Rubinstein American option pricing."""

from __future__ import annotations

from math import exp, isfinite, sqrt

import numpy as np

from .black_scholes import OptionType, PricingError


def price_american_option(
    spot: float,
    strike: float,
    time: float,
    rate: float,
    volatility: float,
    option_type: OptionType | str,
    dividend_yield: float = 0.0,
    steps: int = 200,
) -> float:
    """Price an American option with a CRR tree and early exercise."""

    option_type = OptionType(option_type)
    if any(not isfinite(value) for value in (spot, strike, time, rate, volatility, dividend_yield)):
        raise PricingError("CRR inputs must be finite")
    if spot <= 0 or strike <= 0 or time < 0 or volatility < 0 or steps < 1:
        raise PricingError("invalid CRR inputs")
    if time == 0:
        return (
            max(spot - strike, 0.0) if option_type is OptionType.CALL else max(strike - spot, 0.0)
        )
    if volatility == 0:
        raise PricingError("positive volatility is required when time remains")
    dt = time / steps
    up = exp(volatility * sqrt(dt))
    down = 1.0 / up
    growth = exp((rate - dividend_yield) * dt)
    probability = (growth - down) / (up - down)
    if not 0 <= probability <= 1:
        raise PricingError("CRR risk-neutral probability is outside [0, 1]")
    discount = exp(-rate * dt)
    terminal_spots = spot * up ** np.arange(steps, -1, -1) * down ** np.arange(0, steps + 1)
    if option_type is OptionType.CALL:
        values = np.maximum(terminal_spots - strike, 0.0)
    else:
        values = np.maximum(strike - terminal_spots, 0.0)
    for step in range(steps - 1, -1, -1):
        values = discount * (probability * values[:-1] + (1 - probability) * values[1:])
        node_spots = spot * up ** np.arange(step, -1, -1) * down ** np.arange(0, step + 1)
        if option_type is OptionType.CALL:
            exercise = np.maximum(node_spots - strike, 0.0)
        else:
            exercise = np.maximum(strike - node_spots, 0.0)
        values = np.maximum(values, exercise)
    return float(values[0])
