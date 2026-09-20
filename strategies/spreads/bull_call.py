"""Defined-risk bull call spread research candidate."""

from __future__ import annotations

from uuid import uuid4

from data.normalization.models import ContractType, OptionQuote
from quant.pricing.black_scholes import OptionType, bs_greeks, bs_price
from quant.pricing.payoffs import call_debit_spread_profile
from quant.probability.lognormal import probability_above
from quant.volatility.estimators import expected_move
from strategies.base import Candidate, TradeLeg


def build_bull_call_spread(
    long_call: OptionQuote,
    short_call: OptionQuote,
    risk_free_rate: float = 0.04,
    forecast_volatility: float | None = None,
    model_drift: float = 0.0,
    transaction_costs: float = 1.30,
) -> Candidate:
    if (
        long_call.option_type is not ContractType.CALL
        or short_call.option_type is not ContractType.CALL
    ):
        raise ValueError("both legs must be calls")
    if long_call.strike >= short_call.strike:
        raise ValueError("long strike must be below short strike")
    if (
        long_call.expiration != short_call.expiration
        or long_call.underlying_symbol != short_call.underlying_symbol
    ):
        raise ValueError("legs must share underlying and expiration")
    spot = long_call.underlying_price or 0.0
    if spot <= 0:
        raise ValueError("underlying price is required")
    dte = long_call.dte()
    time = max(dte, 1) / 365.0
    iv_long = long_call.implied_volatility or 0.25
    iv_short = short_call.implied_volatility or iv_long
    debit = long_call.ask - short_call.bid
    if debit <= 0:
        raise ValueError("spread debit must be positive")
    profile = call_debit_spread_profile(
        long_call.strike, short_call.strike, debit, long_call.multiplier
    )
    long_greeks = bs_greeks(spot, long_call.strike, time, risk_free_rate, iv_long, OptionType.CALL)
    short_greeks = bs_greeks(
        spot, short_call.strike, time, risk_free_rate, iv_short, OptionType.CALL
    )
    net_greeks = type(long_greeks)(
        long_greeks.delta - short_greeks.delta,
        long_greeks.gamma - short_greeks.gamma,
        long_greeks.theta - short_greeks.theta,
        long_greeks.vega - short_greeks.vega,
        long_greeks.rho - short_greeks.rho,
    )
    forecast_volatility = forecast_volatility or 0.20
    probability_profit = probability_above(
        spot, profile.break_even[0], time, forecast_volatility, model_drift
    )
    expected = bs_price(
        spot, long_call.strike, time, risk_free_rate, forecast_volatility, OptionType.CALL
    ) - bs_price(
        spot, short_call.strike, time, risk_free_rate, forecast_volatility, OptionType.CALL
    )
    gross_ev = (expected - debit) * long_call.multiplier
    net_ev = gross_ev - transaction_costs
    risk_adjusted = net_ev / profile.max_loss_per_contract if profile.max_loss_per_contract else 0.0
    return Candidate(
        candidate_id=str(uuid4()),
        underlying=long_call.underlying_symbol,
        underlying_price=spot,
        strategy="Bull call spread",
        legs=(
            TradeLeg(
                "BUY_OPEN",
                ContractType.CALL,
                long_call.strike,
                long_call.expiration,
                1,
                long_call.ask,
                long_call.option_symbol,
            ),
            TradeLeg(
                "SELL_OPEN",
                ContractType.CALL,
                short_call.strike,
                short_call.expiration,
                1,
                short_call.bid,
                short_call.option_symbol,
            ),
        ),
        dte=dte,
        bid=long_call.bid - short_call.ask,
        ask=debit,
        midpoint=(long_call.midpoint - short_call.midpoint),
        spread_pct=max(long_call.spread_pct, short_call.spread_pct),
        implied_volatility=(iv_long + iv_short) / 2,
        realized_volatility=forecast_volatility,
        forecast_volatility=forecast_volatility,
        expected_move=expected_move(spot, (iv_long + iv_short) / 2, dte),
        delta=net_greeks.delta,
        gamma=net_greeks.gamma,
        theta=net_greeks.theta,
        vega=net_greeks.vega,
        rho=net_greeks.rho,
        probability_profit=probability_profit,
        probability_interval=(
            max(0.0, probability_profit - 0.08),
            min(1.0, probability_profit + 0.08),
        ),
        gross_ev=gross_ev,
        estimated_costs=transaction_costs,
        net_ev=net_ev,
        max_loss=profile.max_loss_per_contract,
        max_profit=profile.max_profit_per_contract,
        break_even=profile.break_even[0],
        risk_adjusted_edge=risk_adjusted,
        assumptions=(
            "European BSM benchmark",
            "real-world drift is explicitly configured",
            "executable debit uses long ask and short bid",
            "research candidate only",
        ),
    )
