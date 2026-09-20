"""Performance metrics with explicit edge-case behavior."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return: float
    annualized_return: float | None
    volatility: float
    max_drawdown: float
    max_drawdown_dollars: float
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float | None
    expectancy: float
    sharpe: float | None
    sortino: float | None


def max_drawdown(equity: Sequence[float]) -> tuple[float, float]:
    values = np.asarray(equity, dtype=float)
    if values.ndim != 1 or len(values) == 0 or not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("equity must be a non-empty positive series")
    peaks = np.maximum.accumulate(values)
    drawdowns = (values - peaks) / peaks
    index = int(np.argmin(drawdowns))
    return float(drawdowns[index]), float(values[index] - peaks[index])


def profit_factor(trade_pnls: Sequence[float]) -> float | None:
    values = np.asarray(trade_pnls, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("trade P&L must be a finite one-dimensional sequence")
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(abs(values[values < 0].sum()))
    if gross_loss == 0:
        return None if gross_profit == 0 else float("inf")
    return gross_profit / gross_loss


def expectancy(trade_pnls: Sequence[float]) -> float:
    values = np.asarray(trade_pnls, dtype=float)
    if len(values) == 0 or not np.all(np.isfinite(values)):
        raise ValueError("at least one trade is required")
    return float(np.mean(values))


def sharpe_ratio(
    returns: Sequence[float], risk_free_per_period: float = 0.0, annualization: float = 252.0
) -> float | None:
    values = np.asarray(returns, dtype=float) - risk_free_per_period
    if (
        len(values) < 2
        or not np.all(np.isfinite(values))
        or not np.isfinite(risk_free_per_period)
        or not np.isfinite(annualization)
        or annualization <= 0
        or np.std(values, ddof=1) == 0
    ):
        return None
    return float(np.mean(values) / np.std(values, ddof=1) * np.sqrt(annualization))


def sortino_ratio(
    returns: Sequence[float], target_per_period: float = 0.0, annualization: float = 252.0
) -> float | None:
    values = np.asarray(returns, dtype=float)
    if not np.all(np.isfinite(values)) or not np.isfinite(target_per_period) or not np.isfinite(annualization) or annualization <= 0:
        raise ValueError("returns, target, and annualization must be finite")
    downside = np.minimum(values - target_per_period, 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)))
    if len(values) == 0 or downside_deviation == 0:
        return None
    return float(
        (np.mean(values) - target_per_period) / downside_deviation * np.sqrt(annualization)
    )


def calculate_performance(
    equity: Sequence[float], trade_pnls: Sequence[float], periods_per_year: float = 252.0
) -> PerformanceMetrics:
    equity_values = np.asarray(equity, dtype=float)
    if len(equity_values) < 2 or not np.all(np.isfinite(equity_values)):
        raise ValueError("at least two equity observations are required")
    trade_values = np.asarray(trade_pnls, dtype=float)
    if trade_values.ndim != 1 or not np.all(np.isfinite(trade_values)):
        raise ValueError("trade P&L must be a finite one-dimensional sequence")
    if not np.isfinite(periods_per_year) or periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive and finite")
    returns = equity_values[1:] / equity_values[:-1] - 1
    wins, losses = trade_values[trade_values > 0], trade_values[trade_values < 0]
    dd_pct, dd_dollars = max_drawdown(equity_values.tolist())
    total_return = float(equity_values[-1] / equity_values[0] - 1)
    annualized_return = (
        float((1 + total_return) ** (periods_per_year / max(1, len(returns))) - 1)
        if 1 + total_return > 0
        else None
    )
    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))
        if len(returns) > 1
        else 0.0,
        max_drawdown=dd_pct,
        max_drawdown_dollars=dd_dollars,
        win_rate=float(np.mean(trade_values > 0)) if len(trade_values) else 0.0,
        average_win=float(np.mean(wins)) if len(wins) else 0.0,
        average_loss=float(np.mean(losses)) if len(losses) else 0.0,
        profit_factor=profit_factor(trade_values.tolist()),
        expectancy=expectancy(trade_values.tolist()) if len(trade_values) else 0.0,
        sharpe=sharpe_ratio(returns.tolist()),
        sortino=sortino_ratio(returns.tolist()),
    )
