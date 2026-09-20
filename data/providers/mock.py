"""Test-only deterministic fixture; never used by the operational runtime.

The production API defaults to ``MARKET_DATA_PROVIDER=none`` and only uses an
authorized provider. This fixture exists solely for deterministic unit tests.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import exp

import numpy as np

from data.normalization.models import ContractType, OptionQuote, QuoteStatus, UnderlyingQuote


class MockMarketDataProvider:
    """Synthetic fixture for tests, not a market-data source."""

    source = "mock-demo"

    def __init__(self, as_of: datetime | None = None) -> None:
        self.as_of = as_of or datetime.now(UTC).replace(microsecond=0)
        self.prices = {"SPY": 552.40, "AAPL": 226.15, "IWM": 215.72}

    def get_quote(self, symbol: str) -> UnderlyingQuote:
        symbol = symbol.upper()
        price = self.prices.get(symbol, 100.0)
        return UnderlyingQuote(symbol, price, self.as_of, self.source, QuoteStatus.DELAYED)

    def get_option_chain(self, symbol: str, expiration: date | None = None) -> list[OptionQuote]:
        underlying = self.get_quote(symbol)
        expiration = expiration or (self.as_of.date() + timedelta(days=30))
        strikes = [
            round(underlying.price * (1 + offset), 2) for offset in (-0.08, -0.04, 0.0, 0.04, 0.08)
        ]
        rows: list[OptionQuote] = []
        for strike in strikes:
            moneyness = np.log(strike / underlying.price)
            for option_type in (ContractType.CALL, ContractType.PUT):
                base = max(0.35, underlying.price * 0.04 - abs(moneyness) * underlying.price * 0.35)
                premium = base if option_type is ContractType.CALL else base * 0.95
                spread = max(0.04, premium * 0.04)
                delta = 0.5 - moneyness * 2.0
                if option_type is ContractType.PUT:
                    delta -= 1
                rows.append(
                    OptionQuote(
                        underlying_symbol=symbol,
                        option_symbol=f"{symbol}-{expiration.isoformat()}-{option_type.value}-{strike:.2f}",
                        option_type=option_type,
                        strike=strike,
                        expiration=expiration,
                        timestamp=self.as_of,
                        bid=round(premium - spread / 2, 2),
                        ask=round(premium + spread / 2, 2),
                        last=round(premium, 2),
                        volume=1250,
                        open_interest=8400,
                        implied_volatility=0.22 + abs(moneyness) * 0.18,
                        delta=max(-0.99, min(0.99, delta)),
                        gamma=0.02,
                        theta=-0.04,
                        vega=0.18,
                        rho=0.04 if option_type is ContractType.CALL else -0.04,
                        exercise_style="American",
                        source=self.source,
                        underlying_price=underlying.price,
                    )
                )
        return rows

    def get_history(self, symbol: str, limit: int = 252) -> list[float]:
        if limit < 2:
            raise ValueError("history limit must be at least two")
        base = self.get_quote(symbol).price
        rng = np.random.default_rng(sum(ord(ch) for ch in symbol.upper()))
        returns = rng.normal(0.0002, 0.012, limit - 1)
        prices = [base]
        for ret in reversed(returns):
            prices.insert(0, prices[0] / exp(ret))
        return prices
