import pytest

from quant.probability.bayesian import bayes_binary_update, beta_binomial_update
from quant.probability.lognormal import probability_above, probability_below, probability_between
from quant.volatility.estimators import (
    arithmetic_returns,
    close_to_close_volatility,
    expected_move,
    iv_percentile,
    iv_rank,
    log_returns,
    rolling_volatility,
)


def test_returns_volatility_expected_move_and_iv_statistics() -> None:
    prices = [100, 105, 103, 106, 108, 107]
    assert arithmetic_returns(prices)[0] == pytest.approx(0.05)
    assert log_returns(prices)[0] == pytest.approx(0.048790164)
    assert close_to_close_volatility([100, 101, 99, 102, 100]) > 0
    assert len(rolling_volatility(prices, 3)) == 3
    assert expected_move(100, 0.40, 30) == pytest.approx(11.47, abs=0.01)
    history = [0.20, 0.25, 0.30, 0.35, 0.45]
    assert iv_rank(0.40, history) == pytest.approx(80.0)
    assert iv_percentile(0.40, history) == pytest.approx(80.0)


def test_lognormal_probabilities_partition_the_space() -> None:
    above = probability_above(100, 100, 30 / 365, 0.2, 0.0)
    below = probability_below(100, 100, 30 / 365, 0.2, 0.0)
    between = probability_between(100, 90, 110, 30 / 365, 0.2, 0.0)
    assert above + below == pytest.approx(1.0)
    assert 0 < between < 1


def test_beta_binomial_preserves_prior_uncertainty() -> None:
    posterior = beta_binomial_update(2, 2, 8, 2)
    assert (posterior.alpha, posterior.beta) == (10.0, 4.0)
    assert posterior.mean == pytest.approx(10 / 14)
    lower, upper = posterior.credible_interval()
    assert 0 < lower < posterior.mean < upper < 1
    bayes = bayes_binary_update(0.52, 0.75, 0.45)
    assert 0.52 < bayes < 1
