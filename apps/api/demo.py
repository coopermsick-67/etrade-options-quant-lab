"""Explicit math-validation payloads.

These calculations are returned only from ``/api/math/demo`` or the validation
CLI. They are never used to populate the operational dashboard.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

from quant.pricing.black_scholes import OptionType, bs_greeks, bs_price, implied_volatility
from quant.pricing.payoffs import long_call_profit
from quant.probability.bayesian import beta_binomial_update
from quant.simulation.monte_carlo import simulate_payoff
from quant.volatility.estimators import expected_move, iv_percentile, iv_rank


def build_math_demo() -> dict[str, Any]:
    spot, strike, dte, iv, rate = 100.0, 105.0, 30, 0.40, 0.04
    time = dte / 365
    price = bs_price(spot, strike, time, rate, iv, OptionType.CALL)
    greeks = bs_greeks(spot, strike, time, rate, iv, OptionType.CALL)
    iv_result = implied_volatility(price, spot, strike, time, rate, OptionType.CALL)
    posterior = beta_binomial_update(2, 2, 8, 2)
    sim = simulate_payoff(
        spot,
        0.0,
        iv,
        time,
        lambda terminal: np.asarray([long_call_profit(x, strike, price) for x in terminal]),
        paths=2000,
        seed=11,
    )
    return {
        "black_scholes_price": price,
        "greeks": asdict(greeks),
        "iv_inversion": asdict(iv_result),
        "expected_move": expected_move(spot, iv, dte),
        "bayesian_posterior": {
            "alpha": posterior.alpha,
            "beta": posterior.beta,
            "mean": posterior.mean,
            "credible_interval": posterior.credible_interval(),
        },
        "monte_carlo": asdict(sim.summary()),
        "xyz_payoffs": {
            str(x): long_call_profit(x, strike, 2.0) for x in (90, 100, 105, 107, 110, 120)
        },
        "volatility_sample": {
            "iv_rank": iv_rank(0.40, [0.2, 0.25, 0.3, 0.35, 0.45]),
            "iv_percentile": iv_percentile(0.40, [0.2, 0.25, 0.3, 0.35, 0.45]),
        },
    }
