import numpy as np
import pytest

from data.providers.mock import MockMarketDataProvider
from quant.portfolio.covariance import correlation_matrix, portfolio_volatility
from quant.risk.tail import expected_shortfall, historical_var, parametric_var
from quant.statistics.calibration import brier_score, calibration_error, log_loss
from quant.statistics.uncertainty import bootstrap_interval
from strategies.directional.single_leg import build_long_option_candidate
from strategies.research.defined_income import scenario_payoffs


def test_single_leg_and_defined_income_strategies_have_explicit_payoffs() -> None:
    provider = MockMarketDataProvider()
    call = next(row for row in provider.get_option_chain("SPY") if row.option_type.value == "CALL")
    candidate = build_long_option_candidate(call, forecast_volatility=0.20)
    assert candidate.strategy == "Long call"
    assert candidate.max_loss == pytest.approx(call.ask * 100)
    assert candidate.legs[0].action == "BUY_OPEN"
    covered = scenario_payoffs(
        [90, 100, 110], "covered_call", stock_entry=100, strike=105, premium=2
    )
    secured_put = scenario_payoffs([90, 100, 110], "cash_secured_put", strike=100, premium=2)
    assert covered.tolist() == pytest.approx([-800, 200, 700])
    assert secured_put.tolist() == pytest.approx([-800, 200, 200])


def test_calibration_metrics_and_bootstrap_are_reproducible() -> None:
    probabilities = [0.2, 0.4, 0.6, 0.8]
    outcomes = [0, 0, 1, 1]
    assert brier_score(probabilities, outcomes) == pytest.approx(0.10)
    assert log_loss(probabilities, outcomes) > 0
    assert 0 <= calibration_error(probabilities, outcomes, bins=4) <= 1
    first = bootstrap_interval([1, 2, 3, 4, 5], iterations=500, seed=22)
    second = bootstrap_interval([1, 2, 3, 4, 5], iterations=500, seed=22)
    assert first == second
    assert first[0] <= 3 <= first[1]


def test_covariance_and_tail_risk_helpers() -> None:
    returns = np.array([[0.01, 0.02], [0.00, 0.01], [-0.02, -0.01], [0.03, 0.02]])
    corr = correlation_matrix(returns.tolist())
    assert corr.shape == (2, 2)
    assert corr[0, 0] == pytest.approx(1.0)
    covariance = np.cov(returns, rowvar=False, ddof=1)
    assert portfolio_volatility([0.5, 0.5], covariance) > 0
    losses = [-0.10, -0.04, -0.02, 0.01, 0.03]
    assert historical_var(losses, 0.8) >= 0
    assert expected_shortfall(losses, 0.8) >= historical_var(losses, 0.8)
    assert parametric_var(losses, 0.95) >= 0
