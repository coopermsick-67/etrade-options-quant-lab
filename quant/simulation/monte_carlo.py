"""Reproducible vectorized Monte Carlo scenario analysis."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

import numpy as np


@dataclass(frozen=True)
class DistributionSummary:
    expected_value: float
    median: float
    standard_deviation: float
    probability_profit: float
    var: float
    expected_shortfall: float
    percentiles: dict[int, float]


@dataclass(frozen=True)
class MonteCarloResult:
    terminal_prices: np.ndarray
    pnl: np.ndarray
    seed: int
    model: str
    paths: int
    steps: int

    def summary(self, confidence: float = 0.95) -> DistributionSummary:
        return summarize_distribution(self.pnl, confidence)


def simulate_terminal_prices(
    spot: float,
    drift: float,
    volatility: float,
    time: float,
    paths: int = 10_000,
    steps: int = 1,
    seed: int = 7,
    model: str = "gbm",
    student_df: float = 5.0,
) -> np.ndarray:
    if any(not isfinite(value) for value in (spot, drift, volatility, time)):
        raise ValueError("spot, drift, volatility, and time must be finite")
    if spot <= 0 or volatility < 0 or time < 0 or paths < 1 or steps < 1:
        raise ValueError("invalid Monte Carlo inputs")
    if model not in {"gbm", "student_t"}:
        raise ValueError("model must be gbm or student_t")
    rng = np.random.default_rng(seed)
    dt = time / steps
    if time == 0:
        return np.full(paths, spot, dtype=float)
    if model == "gbm":
        shocks = rng.standard_normal((paths, steps))
    else:
        if student_df <= 2:
            raise ValueError("student-t degrees of freedom must exceed two for finite variance")
        shocks = rng.standard_t(student_df, (paths, steps))
        shocks = shocks / np.sqrt(student_df / (student_df - 2))
    increments = (drift - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * shocks
    return spot * np.exp(np.sum(increments, axis=1))


def simulate_payoff(
    spot: float,
    drift: float,
    volatility: float,
    time: float,
    payoff: Callable[[np.ndarray], np.ndarray],
    paths: int = 10_000,
    steps: int = 1,
    seed: int = 7,
    model: str = "gbm",
    student_df: float = 5.0,
) -> MonteCarloResult:
    terminals = simulate_terminal_prices(
        spot, drift, volatility, time, paths, steps, seed, model, student_df
    )
    pnl = np.asarray(payoff(terminals), dtype=float)
    if pnl.shape != terminals.shape:
        raise ValueError("payoff must return one value per terminal price")
    if not np.all(np.isfinite(pnl)):
        raise ValueError("payoff must return finite values")
    return MonteCarloResult(terminals, pnl, seed, model, paths, steps)


def summarize_distribution(pnl: np.ndarray, confidence: float = 0.95) -> DistributionSummary:
    values = np.asarray(pnl, dtype=float)
    if values.ndim != 1 or len(values) == 0 or not 0 < confidence < 1:
        raise ValueError("pnl must be a non-empty vector and confidence must be in (0, 1)")
    lower_tail = (1 - confidence) * 100
    cutoff = float(np.percentile(values, lower_tail))
    tail = values[values <= cutoff]
    return DistributionSummary(
        expected_value=float(np.mean(values)),
        median=float(np.median(values)),
        standard_deviation=float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        probability_profit=float(np.mean(values > 0)),
        var=float(max(0.0, -cutoff)),
        expected_shortfall=float(max(0.0, -np.mean(tail))) if len(tail) else 0.0,
        percentiles={p: float(np.percentile(values, p)) for p in (1, 5, 25, 50, 75, 95, 99)},
    )
