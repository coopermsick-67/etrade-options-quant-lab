"""Probability calibration metrics for binary forecasts."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def _validate(
    probabilities: Sequence[float], outcomes: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    if p.ndim != 1 or y.ndim != 1 or len(p) != len(y) or len(p) == 0:
        raise ValueError("probabilities and outcomes must be equally sized non-empty vectors")
    if np.any((p <= 0) | (p >= 1)) or np.any(~np.isin(y, (0, 1))):
        raise ValueError("probabilities must be in (0,1) and outcomes must be binary")
    return p, y


def brier_score(probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    p, y = _validate(probabilities, outcomes)
    return float(np.mean((p - y) ** 2))


def log_loss(probabilities: Sequence[float], outcomes: Sequence[int]) -> float:
    p, y = _validate(probabilities, outcomes)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calibration_error(
    probabilities: Sequence[float], outcomes: Sequence[int], bins: int = 10
) -> float:
    p, y = _validate(probabilities, outcomes)
    if bins < 2:
        raise ValueError("bins must be at least two")
    error = 0.0
    for lower, upper in zip(
        np.linspace(0, 1, bins, endpoint=False), np.linspace(0, 1, bins + 1)[1:], strict=True
    ):
        mask = (p >= lower) & (p < upper if upper < 1 else p <= upper)
        if np.any(mask):
            error += float(np.mean(mask)) * abs(float(np.mean(p[mask])) - float(np.mean(y[mask])))
    return error
