"""Market-data quality gates. Suspicious rows are rejected with reasons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import isfinite

from data.normalization.models import OptionQuote, UnderlyingQuote


@dataclass(frozen=True)
class QualityResult:
    valid: bool
    reasons: tuple[str, ...]


def validate_underlying_quote(quote: UnderlyingQuote) -> QualityResult:
    reasons: list[str] = []
    if not quote.symbol.strip():
        reasons.append("missing symbol")
    if not isfinite(quote.price) or quote.price <= 0:
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
    if not isfinite(quote.strike) or not isfinite(quote.multiplier):
        reasons.append("non-finite contract field")
    comparison_date = now.date() if now else date.today()
    if quote.expiration < comparison_date:
        reasons.append("expired contract")
    if not isfinite(quote.bid) or not isfinite(quote.ask):
        reasons.append("non-finite quote")
    elif quote.bid < 0 or quote.ask < 0:
        reasons.append("negative quote")
    if quote.ask < quote.bid:
        reasons.append("crossed market")
    if quote.bid == 0 and quote.ask == 0:
        reasons.append("empty quote")
    if quote.volume < 0 or quote.open_interest < 0:
        reasons.append("negative liquidity field")
    if quote.last is not None and (not isfinite(quote.last) or quote.last < 0):
        reasons.append("invalid last price")
    for field_name, value in (
        ("implied volatility", quote.implied_volatility),
        ("delta", quote.delta),
        ("gamma", quote.gamma),
        ("theta", quote.theta),
        ("vega", quote.vega),
        ("rho", quote.rho),
        ("underlying price", quote.underlying_price),
    ):
        if value is not None and not isfinite(value):
            reasons.append(f"non-finite {field_name}")
    if quote.implied_volatility is not None and quote.implied_volatility < 0:
        reasons.append("negative implied volatility")
    if quote.underlying_price is not None and quote.underlying_price <= 0:
        reasons.append("non-positive underlying price")
    if quote.timestamp.tzinfo is None:
        reasons.append("timestamp must be timezone-aware")
    elif quote.timestamp > datetime.now(UTC):
        reasons.append("quote timestamp is in the future")
    if quote.age_seconds(now) > stale_seconds:
        reasons.append("stale quote")
    return QualityResult(not reasons, tuple(reasons))
