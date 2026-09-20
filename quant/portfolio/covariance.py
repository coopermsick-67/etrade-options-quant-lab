"""Correlation, covariance, and portfolio volatility helpers."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def covariance_matrix(return_series: Sequence[Sequence[float]]) -> np.ndarray:
    values = np.asarray(return_series, dtype=float)
    if (
        values.ndim != 2
        or values.shape[0] < 2
        or values.shape[1] < 2
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("return_series must contain at least two observations and two assets")
    return np.cov(values, rowvar=False, ddof=1)


def correlation_matrix(return_series: Sequence[Sequence[float]]) -> np.ndarray:
    values = np.asarray(return_series, dtype=float)
    if (
        values.ndim != 2
        or values.shape[0] < 2
        or values.shape[1] < 2
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("return_series must contain at least two observations and two assets")
    return np.corrcoef(values, rowvar=False)


def portfolio_volatility(weights: Sequence[float], covariance: np.ndarray) -> float:
    w = np.asarray(weights, dtype=float)
    sigma = np.asarray(covariance, dtype=float)
    if (
        w.ndim != 1
        or sigma.shape != (len(w), len(w))
        or not np.all(np.isfinite(w))
        or not np.all(np.isfinite(sigma))
    ):
        raise ValueError("weights and covariance dimensions do not match")
    variance = float(w.T @ sigma @ w)
    return float(np.sqrt(max(variance, 0.0)))
