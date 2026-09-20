from math import log, sqrt

import pytest

from quant.pricing.american import price_american_option
from quant.pricing.black_scholes import (
    OptionType,
    PricingError,
    bs_greeks,
    bs_price,
    implied_volatility,
)
from quant.pricing.payoffs import (
    call_debit_spread_profile,
    contract_cost,
    long_call_profile,
    long_call_profit,
    long_put_profit,
    put_debit_spread_profile,
)


def test_black_scholes_reference_values_and_put_call_parity() -> None:
    call = bs_price(100, 100, 1, 0.05, 0.20, OptionType.CALL)
    put = bs_price(100, 100, 1, 0.05, 0.20, OptionType.PUT)
    assert call == pytest.approx(10.45058357, rel=1e-8)
    assert put == pytest.approx(5.57352602, rel=1e-8)
    assert call - put == pytest.approx(100 - 100 * 2.718281828459045**-0.05, rel=1e-8)


def test_greeks_match_finite_differences() -> None:
    spot, strike, time, rate, vol = 100.0, 105.0, 0.75, 0.03, 0.24
    greeks = bs_greeks(spot, strike, time, rate, vol, OptionType.CALL)
    ds, dv, dr, dt = 0.01, 1e-5, 1e-5, 1e-5

    def price(s: float, t: float = time, v: float = vol, r: float = rate) -> float:
        return bs_price(s, strike, t, r, v, OptionType.CALL)

    delta_fd = (price(spot + ds) - price(spot - ds)) / (2 * ds)
    gamma_fd = (price(spot + ds) - 2 * price(spot) + price(spot - ds)) / ds**2
    vega_fd = (price(spot, v=vol + dv) - price(spot, v=vol - dv)) / (2 * dv)
    rho_fd = (price(spot, r=rate + dr) - price(spot, r=rate - dr)) / (2 * dr)
    theta_fd = (price(spot, t=time - dt) - price(spot, t=time + dt)) / (2 * dt)
    assert greeks.delta == pytest.approx(delta_fd, rel=1e-5)
    assert greeks.gamma == pytest.approx(gamma_fd, rel=1e-4)
    assert greeks.vega == pytest.approx(vega_fd, rel=1e-5)
    assert greeks.rho == pytest.approx(rho_fd, rel=1e-5)
    assert greeks.theta == pytest.approx(theta_fd, rel=1e-5)


def test_implied_volatility_inversion_is_diagnostic() -> None:
    price = bs_price(100, 105, 30 / 365, 0.04, 0.40, OptionType.CALL)
    result = implied_volatility(price, 100, 105, 30 / 365, 0.04, OptionType.CALL)
    assert result.converged is True
    assert result.implied_volatility == pytest.approx(0.40, rel=1e-8)
    assert result.pricing_error is not None and result.pricing_error < 1e-8
    with pytest.raises(PricingError):
        implied_volatility(1000, 100, 105, 30 / 365, 0.04, OptionType.CALL)
    lower_bound = implied_volatility(0.0, 100, 500, 30 / 365, 0.04, OptionType.CALL)
    assert lower_bound.converged is False
    assert lower_bound.implied_volatility is None


def test_american_put_is_at_least_european_put() -> None:
    european = bs_price(100, 100, 1, 0.05, 0.20, OptionType.PUT)
    american = price_american_option(100, 100, 1, 0.05, 0.20, OptionType.PUT, steps=300)
    assert american >= european
    assert american == pytest.approx(6.09, abs=0.03)


def test_xyz_long_call_validation_case() -> None:
    assert contract_cost(2.0) == 200.0
    profile = long_call_profile(105, 2.0)
    assert profile.max_loss_per_contract == 200.0
    assert profile.break_even == (107.0,)
    assert profile.max_profit_per_contract == float("inf")
    assert [long_call_profit(x, 105, 2.0) for x in (90, 100, 105, 107, 110, 120)] == [
        -200.0,
        -200.0,
        -200.0,
        0.0,
        300.0,
        1300.0,
    ]


def test_other_payoff_profiles_are_defined_risk() -> None:
    call_spread = call_debit_spread_profile(100, 110, 2.0)
    put_spread = put_debit_spread_profile(110, 100, 2.0)
    assert call_spread.max_loss_per_contract == 200.0
    assert call_spread.max_profit_per_contract == 800.0
    assert put_spread.max_loss_per_contract == 200.0
    assert put_spread.max_profit_per_contract == 800.0
    assert long_put_profit(90, 105, 2.0) == 1300.0
    assert log(105 / 100) == pytest.approx(0.048790164, rel=1e-7)
    assert 0.01 * sqrt(252) == pytest.approx(0.158745, rel=1e-5)
