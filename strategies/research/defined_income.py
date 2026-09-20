"""Expiration analysis helpers for covered calls and cash-secured puts."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from quant.pricing.payoffs import cash_secured_put_profit, covered_call_profit


def scenario_payoffs(
    terminal_prices: Iterable[float],
    strategy: str,
    *,
    stock_entry: float | None = None,
    strike: float,
    premium: float,
    multiplier: float = 100.0,
) -> np.ndarray:
    prices = np.asarray(list(terminal_prices), dtype=float)
    if prices.ndim != 1 or len(prices) == 0:
        raise ValueError("terminal_prices must be a non-empty one-dimensional sequence")
    if strategy == "covered_call":
        if stock_entry is None or stock_entry <= 0:
            raise ValueError("stock_entry is required for covered calls")
        return np.asarray(
            [
                covered_call_profit(price, stock_entry, strike, premium, multiplier)
                for price in prices
            ]
        )
    if strategy == "cash_secured_put":
        return np.asarray(
            [cash_secured_put_profit(price, strike, premium, multiplier) for price in prices]
        )
    raise ValueError("strategy must be covered_call or cash_secured_put")
