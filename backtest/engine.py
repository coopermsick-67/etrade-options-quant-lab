"""Small event-driven backtester that makes point-in-time access explicit."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from quant.statistics.metrics import PerformanceMetrics, calculate_performance


@dataclass(frozen=True)
class HistoricalBar:
    timestamp: datetime
    close: float
    option_mid: float
    option_bid: float
    option_ask: float
    multiplier: float = 100.0

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("historical bar timestamp must be timezone-aware")
        for name, value in (
            ("close", self.close),
            ("option_mid", self.option_mid),
            ("option_bid", self.option_bid),
            ("option_ask", self.option_ask),
            ("multiplier", self.multiplier),
        ):
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.close <= 0 or self.option_mid < 0 or self.option_bid < 0 or self.option_ask < 0:
            raise ValueError("prices must be non-negative and close must be positive")
        if self.option_ask < self.option_bid:
            raise ValueError("option ask cannot be below bid")
        if not self.option_bid <= self.option_mid <= self.option_ask:
            raise ValueError("option midpoint must lie within the bid/ask market")
        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")


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
    if any(
        previous.timestamp >= current.timestamp
        for previous, current in zip(bars[:-1], bars[1:], strict=True)
    ):
        raise ValueError("historical bars must be strictly time-ordered")
    if initial_equity <= 0 or not isfinite(initial_equity):
        raise ValueError("initial equity must be positive and finite")
    if slippage_bps < 0 or not isfinite(slippage_bps):
        raise ValueError("slippage must be non-negative and finite")
    if fee_per_contract < 0 or not isfinite(fee_per_contract):
        raise ValueError("fee must be non-negative and finite")
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
