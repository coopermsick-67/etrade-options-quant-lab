"""Small event-driven backtester that makes point-in-time access explicit."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from quant.statistics.metrics import PerformanceMetrics, calculate_performance


@dataclass(frozen=True)
class HistoricalBar:
    timestamp: datetime
    close: float
    option_mid: float
    option_bid: float
    option_ask: float
    multiplier: float = 100.0


@dataclass(frozen=True)
class BacktestTrade:
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl: float
    reason: str


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: tuple[float, ...]
    trades: tuple[BacktestTrade, ...]
    metrics: PerformanceMetrics
    fill_model: str
    lookahead_safe: bool


def _fill(bar: HistoricalBar, side: str, fill_model: str, slippage_bps: float) -> float:
    if fill_model == "optimistic":
        price = bar.option_mid
    elif fill_model == "realistic":
        price = (
            bar.option_mid + (bar.option_ask - bar.option_mid) * 0.45
            if side == "buy"
            else bar.option_mid - (bar.option_mid - bar.option_bid) * 0.45
        )
    elif fill_model == "conservative":
        price = bar.option_ask if side == "buy" else bar.option_bid
    else:
        raise ValueError("unknown fill model")
    adjustment = price * slippage_bps / 10_000
    return price + adjustment if side == "buy" else max(0.0, price - adjustment)


def _contract_value(
    bar: HistoricalBar, side: str, fill_model: str, slippage_bps: float, fee: float
) -> float:
    price = _fill(bar, side, fill_model, slippage_bps)
    fee_per_share = fee / bar.multiplier
    return (
        price + fee_per_share if side == "buy" else max(0.0, price - fee_per_share)
    ) * bar.multiplier


def run_simple_event_backtest(
    bars: Sequence[HistoricalBar],
    signal: Callable[[Sequence[HistoricalBar], int], bool],
    initial_equity: float = 10_000.0,
    fill_model: str = "realistic",
    slippage_bps: float = 15.0,
    fee_per_contract: float = 0.65,
) -> BacktestResult:
    if len(bars) < 2:
        raise ValueError("at least two bars are required")
    trades: list[BacktestTrade] = []
    equity = [initial_equity]
    open_trade: tuple[int, float] | None = None
    for index, bar in enumerate(bars):
        history = bars[: index + 1]  # point-in-time view: current bar only
        if open_trade is None and signal(history, index):
            open_trade = (
                index,
                _contract_value(bar, "buy", fill_model, slippage_bps, fee_per_contract),
            )
        elif open_trade is not None and not signal(history, index):
            entry_index, entry_price = open_trade
            exit_price = _contract_value(bar, "sell", fill_model, slippage_bps, fee_per_contract)
            pnl = exit_price - entry_price
            trades.append(
                BacktestTrade(
                    bars[entry_index].timestamp,
                    bar.timestamp,
                    entry_price,
                    exit_price,
                    pnl,
                    "signal exit",
                )
            )
            equity.append(equity[-1] + pnl)
            open_trade = None
    if open_trade is not None:
        entry_index, entry_price = open_trade
        bar = bars[-1]
        exit_price = _contract_value(bar, "sell", fill_model, slippage_bps, fee_per_contract)
        pnl = exit_price - entry_price
        trades.append(
            BacktestTrade(
                bars[entry_index].timestamp,
                bar.timestamp,
                entry_price,
                exit_price,
                pnl,
                "end of test",
            )
        )
        equity.append(equity[-1] + pnl)
    pnl_values = [trade.pnl for trade in trades]
    metrics = calculate_performance(equity, pnl_values)
    return BacktestResult(tuple(equity), tuple(trades), metrics, fill_model, True)
