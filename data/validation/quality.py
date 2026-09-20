"""Market-data quality gates. Suspicious rows are rejected with reasons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from data.normalization.models import OptionQuote, UnderlyingQuote


@dataclass(frozen=True)
class QualityResult:
    valid: bool
    reasons: tuple[str, ...]


def validate_underlying_quote(quote: UnderlyingQuote) -> QualityResult:
    reasons: list[str] = []
    if not quote.symbol.strip():
        reasons.append("missing symbol")
    if quote.price <= 0:
        reasons.append("non-positive price")
    if quote.timestamp.tzinfo is None:
        reasons.append("timestamp must be timezone-aware")
    return QualityResult(not reasons, tuple(reasons))


def validate_option_quote(
    quote: OptionQuote, stale_seconds: float = 120.0, now: datetime | None = None
) -> QualityResult:
    reasons: list[str] = []
    if not quote.underlying_symbol or not quote.option_symbol:
        reasons.append("missing symbol")
    if quote.strike <= 0 or quote.multiplier <= 0:
        reasons.append("invalid strike or multiplier")
    comparison_date = now.date() if now else date.today()
    if quote.expiration < comparison_date:
        reasons.append("expired contract")
    if quote.bid < 0 or quote.ask < 0:
        reasons.append("negative quote")
    if quote.ask < quote.bid:
        reasons.append("crossed market")
    if quote.bid == 0 and quote.ask == 0:
        reasons.append("empty quote")
    if quote.volume < 0 or quote.open_interest < 0:
        reasons.append("negative liquidity field")
    if quote.implied_volatility is not None and quote.implied_volatility < 0:
        reasons.append("negative implied volatility")
    if quote.timestamp.tzinfo is None:
        reasons.append("timestamp must be timezone-aware")
    elif quote.timestamp > datetime.now(UTC):
        reasons.append("quote timestamp is in the future")
    if quote.age_seconds(now) > stale_seconds:
        reasons.append("stale quote")
    return QualityResult(not reasons, tuple(reasons))
