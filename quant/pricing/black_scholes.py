"""Black-Scholes-Merton pricing, Greeks, and implied volatility.

The functions in this module use decimal prices and rates represented as floats
only at the numerical boundary.  Vega and rho are per 1.00 change in the
volatility/rate input; callers that want a one percentage-point change should
multiply them by 0.01.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import exp, log, sqrt

from scipy.optimize import brentq
from scipy.stats import norm


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class PricingError(ValueError):
    """Raised when an option input or price is mathematically invalid."""


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


@dataclass(frozen=True)
class IVResult:
    implied_volatility: float | None
    converged: bool
    iterations: int
    pricing_error: float | None
    method: str


def _validate(spot: float, strike: float, time: float, volatility: float) -> None:
    if spot <= 0 or strike <= 0:
        raise PricingError("spot and strike must be positive")
    if time < 0:
        raise PricingError("time to expiry cannot be negative")
    if volatility < 0:
        raise PricingError("volatility cannot be negative")


def _d1_d2(
    spot: float,
    strike: float,
    time: float,
    rate: float,
    volatility: float,
    dividend_yield: float,
) -> tuple[float, float]:
    if time <= 0 or volatility <= 0:
        raise PricingError("d1/d2 are undefined for zero time or volatility")
    sigma_sqrt_t = volatility * sqrt(time)
    d1 = (log(spot / strike) + (rate - dividend_yield + 0.5 * volatility**2) * time) / sigma_sqrt_t
    return d1, d1 - sigma_sqrt_t


def bs_price(
    spot: float,
    strike: float,
    time: float,
    rate: float,
    volatility: float,
    option_type: OptionType | str,
    dividend_yield: float = 0.0,
) -> float:
    """Return the European Black-Scholes-Merton value per underlying share."""

    option_type = OptionType(option_type)
    _validate(spot, strike, time, volatility)
    if time == 0:
        return (
            max(spot - strike, 0.0) if option_type is OptionType.CALL else max(strike - spot, 0.0)
        )
    if volatility == 0:
        forward = spot * exp((rate - dividend_yield) * time)
        payoff = (
            max(forward - strike, 0.0)
            if option_type is OptionType.CALL
            else max(strike - forward, 0.0)
        )
        return exp(-rate * time) * payoff
    d1, d2 = _d1_d2(spot, strike, time, rate, volatility, dividend_yield)
    discounted_spot = spot * exp(-dividend_yield * time)
    discounted_strike = strike * exp(-rate * time)
    if option_type is OptionType.CALL:
        return discounted_spot * norm.cdf(d1) - discounted_strike * norm.cdf(d2)
    return discounted_strike * norm.cdf(-d2) - discounted_spot * norm.cdf(-d1)


def bs_greeks(
    spot: float,
    strike: float,
    time: float,
    rate: float,
    volatility: float,
    option_type: OptionType | str,
    dividend_yield: float = 0.0,
) -> Greeks:
    """Return analytical BSM Greeks per underlying share."""

    option_type = OptionType(option_type)
    _validate(spot, strike, time, volatility)
    if time <= 0 or volatility <= 0:
        raise PricingError("analytical Greeks require positive time and volatility")
    d1, d2 = _d1_d2(spot, strike, time, rate, volatility, dividend_yield)
    discount_q = exp(-dividend_yield * time)
    discount_r = exp(-rate * time)
    pdf = norm.pdf(d1)
    gamma = discount_q * pdf / (spot * volatility * sqrt(time))
    vega = spot * discount_q * pdf * sqrt(time)
    if option_type is OptionType.CALL:
        delta = discount_q * norm.cdf(d1)
        theta = (
            -spot * discount_q * pdf * volatility / (2 * sqrt(time))
            - rate * strike * discount_r * norm.cdf(d2)
            + dividend_yield * spot * discount_q * norm.cdf(d1)
        )
        rho = strike * time * discount_r * norm.cdf(d2)
    else:
        delta = discount_q * (norm.cdf(d1) - 1)
        theta = (
            -spot * discount_q * pdf * volatility / (2 * sqrt(time))
            + rate * strike * discount_r * norm.cdf(-d2)
            - dividend_yield * spot * discount_q * norm.cdf(-d1)
        )
        rho = -strike * time * discount_r * norm.cdf(-d2)
    return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)


def no_arbitrage_bounds(
    spot: float,
    strike: float,
    time: float,
    rate: float,
    option_type: OptionType | str,
    dividend_yield: float = 0.0,
) -> tuple[float, float]:
    """Return European no-arbitrage lower/upper bounds per share."""

    option_type = OptionType(option_type)
    if spot <= 0 or strike <= 0 or time < 0:
        raise PricingError("invalid inputs for no-arbitrage bounds")
    spot_pv = spot * exp(-dividend_yield * time)
    strike_pv = strike * exp(-rate * time)
    if option_type is OptionType.CALL:
        return max(0.0, spot_pv - strike_pv), spot_pv
    return max(0.0, strike_pv - spot_pv), strike_pv


def implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    time: float,
    rate: float,
    option_type: OptionType | str,
    dividend_yield: float = 0.0,
    max_volatility: float = 8.0,
) -> IVResult:
    """Invert BSM with a bracketed Brent solver and explicit diagnostics."""

    option_type = OptionType(option_type)
    _validate(spot, strike, time, 0.0)
    if market_price < 0:
        raise PricingError("market price cannot be negative")
    if time <= 0:
        intrinsic = bs_price(spot, strike, 0.0, rate, 0.0, option_type, dividend_yield)
        if abs(market_price - intrinsic) <= 1e-8:
            return IVResult(0.0, True, 0, 0.0, "expiry-intrinsic")
        raise PricingError("IV is undefined at expiry unless price equals intrinsic value")
    lower, upper = no_arbitrage_bounds(spot, strike, time, rate, option_type, dividend_yield)
    tolerance = 1e-8 + 1e-6 * max(1.0, upper)
    if market_price < lower - tolerance or market_price > upper + tolerance:
        raise PricingError(
            f"market price {market_price} violates no-arbitrage bounds [{lower}, {upper}]"
        )
    if abs(market_price - lower) <= tolerance:
        return IVResult(0.0, True, 0, abs(market_price - lower), "lower-bound")

    def objective(volatility: float) -> float:
        return (
            bs_price(spot, strike, time, rate, volatility, option_type, dividend_yield)
            - market_price
        )

    low = 1e-10
    high = max_volatility
    high_value = objective(high)
    while high_value < 0 and high < 64:
        high *= 2
        high_value = objective(high)
    if high_value < 0:
        return IVResult(None, False, 0, None, "brentq-unbracketed")
    root, result = brentq(objective, low, high, xtol=1e-12, rtol=1e-12, full_output=True)
    residual = abs(objective(root))
    return IVResult(root, bool(result.converged), int(result.iterations), residual, "brentq")
