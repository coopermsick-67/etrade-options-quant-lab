"""Long call and long put research candidates."""

from __future__ import annotations

from uuid import uuid4

from data.normalization.models import ContractType, OptionQuote
from quant.pricing.black_scholes import OptionType, bs_greeks, bs_price
from quant.pricing.payoffs import long_call_profile, long_put_profile
from quant.probability.lognormal import probability_above, probability_below
from quant.volatility.estimators import expected_move
from strategies.base import Candidate, TradeLeg


def build_long_option_candidate(
    option: OptionQuote,
    risk_free_rate: float = 0.04,
    forecast_volatility: float | None = None,
    model_drift: float = 0.0,
    transaction_costs: float = 0.65,
) -> Candidate:
    if option.option_type not in {ContractType.CALL, ContractType.PUT}:
        raise ValueError("option type must be a call or put")
    spot = option.underlying_price or 0.0
    if spot <= 0:
        raise ValueError("underlying price is required")
    premium = option.ask
    if premium <= 0:
        raise ValueError("executable premium must be positive")
    dte = option.dte()
    time = max(dte, 1) / 365.0
    iv = option.implied_volatility or 0.25
    forecast_volatility = forecast_volatility or iv
    option_type = OptionType(option.option_type.value.lower())
    greeks = bs_greeks(spot, option.strike, time, risk_free_rate, iv, option_type)
    fair_value = bs_price(
        spot, option.strike, time, risk_free_rate, forecast_volatility, option_type
    )
    gross_ev = (fair_value - premium) * option.multiplier
    net_ev = gross_ev - transaction_costs
    if option_type is OptionType.CALL:
        profile = long_call_profile(option.strike, premium, option.multiplier)
        probability = probability_above(
            spot, profile.break_even[0], time, forecast_volatility, model_drift
        )
        strategy = "Long call"
    else:
        profile = long_put_profile(option.strike, premium, option.multiplier)
        probability = probability_below(
            spot, profile.break_even[0], time, forecast_volatility, model_drift
        )
        strategy = "Long put"
    return Candidate(
        candidate_id=str(uuid4()),
        underlying=option.underlying_symbol,
        underlying_price=spot,
        strategy=strategy,
        legs=(
            TradeLeg(
                "BUY_OPEN",
                option.option_type,
                option.strike,
                option.expiration,
                1,
                premium,
                option.option_symbol,
            ),
        ),
        dte=dte,
        bid=option.bid,
        ask=option.ask,
        midpoint=option.midpoint,
        spread_pct=option.spread_pct,
        implied_volatility=iv,
        realized_volatility=forecast_volatility,
        forecast_volatility=forecast_volatility,
        expected_move=expected_move(spot, iv, dte),
        delta=greeks.delta,
        gamma=greeks.gamma,
        theta=greeks.theta,
        vega=greeks.vega,
        rho=greeks.rho,
        probability_profit=probability,
        probability_interval=(max(0.0, probability - 0.08), min(1.0, probability + 0.08)),
        gross_ev=gross_ev,
        estimated_costs=transaction_costs,
        net_ev=net_ev,
        max_loss=profile.max_loss_per_contract,
        max_profit=profile.max_profit_per_contract,
        break_even=profile.break_even[0],
        risk_adjusted_edge=net_ev / profile.max_loss_per_contract,
        assumptions=(
            "European BSM benchmark",
            "long option uses ask as entry price",
            "probability is model-based, not delta",
            "research candidate only",
        ),
    )
