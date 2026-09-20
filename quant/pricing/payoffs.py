"""Expiration payoff and defined-risk trade profiles."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True)
class PayoffProfile:
    break_even: tuple[float, ...]
    max_loss_per_contract: float
    max_profit_per_contract: float
    defined_risk: bool


def contract_cost(premium: float, multiplier: float = 100.0, contracts: int = 1) -> float:
    if premium < 0 or multiplier <= 0 or contracts < 0:
        raise ValueError("premium, multiplier, and contracts are invalid")
    return premium * multiplier * contracts


def long_call_profit(
    terminal_spot: float, strike: float, premium: float, multiplier: float = 100.0
) -> float:
    return (max(terminal_spot - strike, 0.0) - premium) * multiplier


def long_put_profit(
    terminal_spot: float, strike: float, premium: float, multiplier: float = 100.0
) -> float:
    return (max(strike - terminal_spot, 0.0) - premium) * multiplier


def call_debit_spread_profit(
    terminal_spot: float,
    long_strike: float,
    short_strike: float,
    debit: float,
    multiplier: float = 100.0,
) -> float:
    if short_strike <= long_strike:
        raise ValueError("short call strike must be above long call strike")
    value = max(terminal_spot - long_strike, 0.0) - max(terminal_spot - short_strike, 0.0)
    return (value - debit) * multiplier


def put_debit_spread_profit(
    terminal_spot: float,
    long_strike: float,
    short_strike: float,
    debit: float,
    multiplier: float = 100.0,
) -> float:
    if short_strike >= long_strike:
        raise ValueError("short put strike must be below long put strike")
    value = max(long_strike - terminal_spot, 0.0) - max(short_strike - terminal_spot, 0.0)
    return (value - debit) * multiplier


def covered_call_profit(
    terminal_spot: float,
    stock_entry: float,
    strike: float,
    premium: float,
    multiplier: float = 100.0,
) -> float:
    stock_pnl = terminal_spot - stock_entry
    call_obligation = max(terminal_spot - strike, 0.0)
    return (stock_pnl + premium - call_obligation) * multiplier


def cash_secured_put_profit(
    terminal_spot: float,
    strike: float,
    premium: float,
    multiplier: float = 100.0,
) -> float:
    return (premium - max(strike - terminal_spot, 0.0)) * multiplier


def long_call_profile(strike: float, premium: float, multiplier: float = 100.0) -> PayoffProfile:
    return PayoffProfile((strike + premium,), premium * multiplier, inf, True)


def long_put_profile(strike: float, premium: float, multiplier: float = 100.0) -> PayoffProfile:
    return PayoffProfile(
        (strike - premium,), premium * multiplier, (strike - premium) * multiplier, True
    )


def call_debit_spread_profile(
    long_strike: float, short_strike: float, debit: float, multiplier: float = 100.0
) -> PayoffProfile:
    if short_strike <= long_strike:
        raise ValueError("short call strike must be above long call strike")
    return PayoffProfile(
        (long_strike + debit,),
        debit * multiplier,
        (short_strike - long_strike - debit) * multiplier,
        True,
    )


def put_debit_spread_profile(
    long_strike: float, short_strike: float, debit: float, multiplier: float = 100.0
) -> PayoffProfile:
    if short_strike >= long_strike:
        raise ValueError("short put strike must be below long put strike")
    return PayoffProfile(
        (long_strike - debit,),
        debit * multiplier,
        (long_strike - short_strike - debit) * multiplier,
        True,
    )
