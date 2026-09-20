"""Research VaR and expected-shortfall estimators."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt

import numpy as np
from scipy.stats import norm


def historical_var(returns: Sequence[float], confidence: float = 0.95) -> float:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) == 0 or not np.all(np.isfinite(values)) or not 0 < confidence < 1:
        raise ValueError("invalid historical VaR inputs")
    return float(max(0.0, -np.quantile(values, 1 - confidence)))


def expected_shortfall(returns: Sequence[float], confidence: float = 0.95) -> float:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) == 0 or not np.all(np.isfinite(values)) or not 0 < confidence < 1:
        raise ValueError("invalid expected-shortfall inputs")
    cutoff = np.quantile(values, 1 - confidence)
    return float(max(0.0, -np.mean(values[values <= cutoff])))


def parametric_var(
    returns: Sequence[float], confidence: float = 0.95, mean: float | None = None
) -> float:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values)) or not 0 < confidence < 1:
        raise ValueError("invalid parametric VaR inputs")
    mu = float(np.mean(values) if mean is None else mean)
    sigma = float(np.std(values, ddof=1))
    return float(max(0.0, -(mu + sigma * norm.ppf(1 - confidence))))


def annualized_volatility_from_returns(
    returns: Sequence[float], periods_per_year: float = 252
) -> float:
    values = np.asarray(returns, dtype=float)
    if len(values) < 2 or not np.all(np.isfinite(values)) or periods_per_year <= 0:
        raise ValueError("at least two returns and a positive annualization factor are required")
    return float(np.std(values, ddof=1) * sqrt(periods_per_year))
