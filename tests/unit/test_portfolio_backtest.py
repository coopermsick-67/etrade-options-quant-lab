from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from backtest.engine import HistoricalBar, run_simple_event_backtest
from quant.portfolio.greeks import GreekPosition, aggregate_greeks
from quant.pricing.black_scholes import Greeks
from quant.simulation.monte_carlo import simulate_payoff, simulate_terminal_prices
from quant.statistics.metrics import calculate_performance, max_drawdown, profit_factor


def test_portfolio_greek_aggregation_and_metrics() -> None:
    greeks = Greeks(0.5, 0.02, -0.1, 0.3, 0.05)
    portfolio = aggregate_greeks(
        [
            GreekPosition("A", 1, 100, greeks),
            GreekPosition("B", -2, 100, greeks),
        ]
    )
    assert portfolio.delta == pytest.approx(-50)
    assert portfolio.gamma == pytest.approx(-2)
    assert portfolio.theta == pytest.approx(10)
    assert max_drawdown([100, 110, 90, 95]) == pytest.approx((-2 / 11, -20))
    assert profit_factor([10, -5, 20, -10]) == pytest.approx(2.0)
    metrics = calculate_performance([100, 110, 105, 120], [10, -5, 15])
    assert metrics.total_return == pytest.approx(0.20)
    assert metrics.expectancy == pytest.approx(20 / 3)


def test_monte_carlo_is_reproducible_and_reports_tails() -> None:
    first = simulate_terminal_prices(100, 0, 0.2, 30 / 365, paths=500, seed=42)
    second = simulate_terminal_prices(100, 0, 0.2, 30 / 365, paths=500, seed=42)
    assert np.array_equal(first, second)
    result = simulate_payoff(
        100,
        0,
        0.2,
        30 / 365,
        lambda terminal: terminal - 100,
        paths=500,
        seed=42,
    )
    summary = result.summary()
    assert summary.percentiles[1] <= summary.percentiles[50] <= summary.percentiles[99]
    assert 0 <= summary.probability_profit <= 1
    assert summary.expected_shortfall >= summary.var


def test_event_backtest_uses_only_point_in_time_history_and_costs() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        HistoricalBar(
            timestamp=start + timedelta(days=index),
            close=100 + index,
            option_mid=1.0 + index * 0.1,
            option_bid=0.9 + index * 0.1,
            option_ask=1.1 + index * 0.1,
        )
        for index in range(4)
    )
    seen_lengths: list[int] = []

    def signal(history: Sequence[HistoricalBar], _index: int) -> bool:
        seen_lengths.append(len(history))
        return len(history) == 1

    result = run_simple_event_backtest(bars, signal, fee_per_contract=0.65)
    assert result.lookahead_safe is True
    assert seen_lengths == [1, 2, 3, 4]
    assert len(result.trades) == 1
    assert result.trades[0].pnl < 0
