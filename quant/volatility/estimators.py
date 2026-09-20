"""Historical, realized, and implied-volatility analytics."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt

import numpy as np


def log_returns(prices: Sequence[float]) -> np.ndarray:
    values = np.asarray(prices, dtype=float)
    if values.ndim != 1 or len(values) < 2 or np.any(values <= 0):
        raise ValueError(
            "prices must be a one-dimensional sequence of at least two positive values"
        )
    return np.diff(np.log(values))


def arithmetic_returns(prices: Sequence[float]) -> np.ndarray:
    values = np.asarray(prices, dtype=float)
    if values.ndim != 1 or len(values) < 2 or np.any(values <= 0):
        raise ValueError(
            "prices must be a one-dimensional sequence of at least two positive values"
        )
    return np.diff(values) / values[:-1]


def annualized_volatility(returns: Sequence[float], periods_per_year: float = 252.0) -> float:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) < 2 or periods_per_year <= 0:
        raise ValueError("at least two returns and a positive annualization factor are required")
    return float(np.std(values, ddof=1) * sqrt(periods_per_year))


def close_to_close_volatility(prices: Sequence[float], periods_per_year: float = 252.0) -> float:
    return annualized_volatility(log_returns(prices).tolist(), periods_per_year)


def rolling_volatility(
    prices: Sequence[float], window: int, periods_per_year: float = 252.0
) -> np.ndarray:
    returns = log_returns(prices)
    if window < 2 or len(returns) < window:
        raise ValueError("window must be at least two and fit inside the return history")
    return np.asarray(
        [
            annualized_volatility(returns[i - window : i].tolist(), periods_per_year)
            for i in range(window, len(returns) + 1)
        ]
    )


def ewma_volatility(
    returns: Sequence[float], decay: float = 0.94, periods_per_year: float = 252.0
) -> float:
    values = np.asarray(returns, dtype=float)
    if len(values) < 2 or not 0 < decay < 1:
        raise ValueError("EWMA needs at least two returns and decay in (0, 1)")
    variance = float(values[0] ** 2)
    for value in values[1:]:
        variance = decay * variance + (1 - decay) * float(value**2)
    return sqrt(max(variance, 0.0) * periods_per_year)


def parkinson_volatility(
    highs: Sequence[float], lows: Sequence[float], periods_per_year: float = 252.0
) -> float:
    high_values = np.asarray(highs, dtype=float)
    low_values = np.asarray(lows, dtype=float)
    if (
        len(high_values) != len(low_values)
        or len(high_values) < 2
        or np.any(low_values <= 0)
        or np.any(high_values < low_values)
    ):
        raise ValueError("high/low series are invalid")
    variance = np.mean(np.log(high_values / low_values) ** 2) / (4 * np.log(2))
    return float(sqrt(max(variance, 0.0) * periods_per_year))


def garman_klass_volatility(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    periods_per_year: float = 252.0,
) -> float:
    open_values = np.asarray(opens, dtype=float)
    high_values = np.asarray(highs, dtype=float)
    low_values = np.asarray(lows, dtype=float)
    close_values = np.asarray(closes, dtype=float)
    if (
        not all(len(x) == len(open_values) for x in (high_values, low_values, close_values))
        or len(open_values) < 2
    ):
        raise ValueError("OHLC series must have equal length and at least two rows")
    if np.any(np.asarray([*open_values, *high_values, *low_values, *close_values]) <= 0):
        raise ValueError("OHLC values must be positive")
    term = (
        0.5 * np.log(high_values / low_values) ** 2
        - (2 * np.log(2) - 1) * np.log(close_values / open_values) ** 2
    )
    return float(sqrt(max(float(np.mean(term)), 0.0) * periods_per_year))


def expected_move(
    spot: float, implied_volatility: float, dte: float, days_per_year: float = 365.0
) -> float:
    if spot <= 0 or implied_volatility < 0 or dte < 0 or days_per_year <= 0:
        raise ValueError("invalid expected-move inputs")
    return float(spot * implied_volatility * sqrt(dte / days_per_year))


def iv_rank(current_iv: float, historical_ivs: Sequence[float]) -> float:
    values = np.asarray(historical_ivs, dtype=float)
    if len(values) == 0 or current_iv < 0 or np.any(values < 0):
        raise ValueError("IV history must be non-empty and non-negative")
    minimum, maximum = float(np.min(values)), float(np.max(values))
    if maximum == minimum:
        return 0.0
    return float((current_iv - minimum) / (maximum - minimum) * 100.0)


def iv_percentile(current_iv: float, historical_ivs: Sequence[float]) -> float:
    values = np.asarray(historical_ivs, dtype=float)
    if len(values) == 0 or current_iv < 0 or np.any(values < 0):
        raise ValueError("IV history must be non-empty and non-negative")
    return float(np.mean(values < current_iv) * 100.0)
