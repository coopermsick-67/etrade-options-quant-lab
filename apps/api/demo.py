"""Deterministic demo payloads used when no broker is connected."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

from data.providers.mock import MockMarketDataProvider
from quant.pricing.black_scholes import OptionType, bs_greeks, bs_price, implied_volatility
from quant.pricing.payoffs import long_call_profit
from quant.probability.bayesian import beta_binomial_update
from quant.simulation.monte_carlo import simulate_payoff
from quant.volatility.estimators import (
    expected_move,
    iv_percentile,
    iv_rank,
)
from strategies.spreads.bull_call import build_bull_call_spread


def build_candidate_rows(provider: MockMarketDataProvider) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for symbol, _strategy in (
        ("SPY", "Bull call spread"),
        ("AAPL", "Bull call spread"),
        ("IWM", "Bull call spread"),
    ):
        chain = provider.get_option_chain(symbol)
        calls = [row for row in chain if row.option_type.value == "CALL"]
        candidate = build_bull_call_spread(calls[2], calls[3], forecast_volatility=0.19)
        item = asdict(candidate)
        item["legs"] = [asdict(leg) for leg in candidate.legs]
        item["expiration"] = candidate.legs[0].expiration.isoformat()
        item["status"] = "Model watch" if symbol == "AAPL" else "Model signal"
        candidates.append(item)
    return candidates


def build_dashboard_payload() -> dict[str, Any]:
    provider = MockMarketDataProvider()
    candidates = build_candidate_rows(provider)
    equity_curve = [10_000 + x for x in (0, 42, 35, 88, 65, 121, 93, 168, 145, 214, 198, 342.56)]
    return {
        "mode": "PAPER",
        "demo": True,
        "broker_status": {"etrade": "disconnected", "robinhood": "live unavailable"},
        "live_enabled": False,
        "account": {
            "equity": equity_curve[-1],
            "daily_pnl": 121.18,
            "buying_power": 8451.22,
            "open_risk": 1213.0,
            "portfolio_delta": -18.4,
            "portfolio_vega": 312.7,
            "cash": 8451.22,
            "drawdown": -0.012,
        },
        "equity_curve": [
            {"label": f"T{i + 1}", "value": value} for i, value in enumerate(equity_curve)
        ],
        "risk_limits": [
            {"label": "Max position size", "value": 2000, "used": 0.61},
            {"label": "Max portfolio delta", "value": 500, "used": 0.04},
            {"label": "Max portfolio vega", "value": 1000, "used": 0.31},
            {"label": "Daily loss limit", "value": 500, "used": 0.25},
            {"label": "Total drawdown limit", "value": 2000, "used": 0.17},
        ],
        "candidates": candidates,
        "recent_activity": [
            {
                "time": "10:21 AM",
                "symbol": "AAPL",
                "action": "Close (Paper)",
                "details": "Sold 1x AAPL call spread",
                "status": "Filled",
            },
            {
                "time": "09:47 AM",
                "symbol": "SPY",
                "action": "Open (Paper)",
                "details": "Bought 1x SPY call spread",
                "status": "Filled",
            },
            {
                "time": "Apr 25, 1:03 PM",
                "symbol": "IWM",
                "action": "Open (Paper)",
                "details": "Bought 1x IWM call spread",
                "status": "Filled",
            },
        ],
        "model_health": {
            "status": "Research only",
            "signal_win_rate": 0.542,
            "average_trade_expectancy": 36.12,
            "sharpe": 1.08,
            "max_drawdown": -0.124,
            "trades_analyzed": 2381,
            "note": "Demo sample data. No live or out-of-sample profitability claim.",
        },
    }


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
