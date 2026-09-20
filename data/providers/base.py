"""Market-data provider interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from data.normalization.models import OptionQuote, UnderlyingQuote


class MarketDataProvider(Protocol):
    def get_quote(self, symbol: str) -> UnderlyingQuote: ...

    def get_option_chain(
        self, symbol: str, expiration: date | None = None
    ) -> Sequence[OptionQuote]: ...

    def get_history(self, symbol: str, limit: int = 252) -> Sequence[float]: ...
