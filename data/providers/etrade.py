"""E*TRADE market-data adapter using the documented REST client.

The adapter is intentionally small and defensive. E*TRADE responses contain
optional fields and the application must never turn a missing field into a
made-up quote. Unsupported history requests raise an explicit error so callers
can show an honest unavailable state.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from math import isfinite
from typing import Any

from brokers.etrade.client import ETradeClient
from data.normalization.models import ContractType, OptionQuote, QuoteStatus, UnderlyingQuote
from data.validation.quality import validate_option_quote, validate_underlying_quote


class ETradeMarketDataError(RuntimeError):
    """Raised when an E*TRADE response cannot be normalized safely."""


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _as_float(value: Any, field: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ETradeMarketDataError(f"E*TRADE field {field} is not numeric") from exc
    if not isfinite(result):
        raise ETradeMarketDataError(f"E*TRADE field {field} is not finite")
    return result


def _as_int(value: Any, field: str, default: int = 0) -> int:
    if value is None:
        return default
    try:
        result = int(float(value))
    except (TypeError, ValueError) as exc:
        raise ETradeMarketDataError(f"E*TRADE field {field} is not an integer") from exc
    return max(0, result)


def _timestamp(value: Any, fallback: datetime) -> datetime:
    if value is None:
        return fallback
    try:
        numeric = float(value)
        # E*TRADE commonly returns epoch milliseconds for quoteTimeAsLong.
        if numeric > 10_000_000_000:
            numeric /= 1000
        return datetime.fromtimestamp(numeric, tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return fallback


def _root(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name, payload)
    return value if isinstance(value, dict) else {}


class ETradeMarketDataProvider:
    source = "etrade"

    def __init__(self, client: ETradeClient, stale_seconds: float | None = 120.0) -> None:
        if stale_seconds is not None and (not isfinite(stale_seconds) or stale_seconds <= 0):
            raise ValueError("stale_seconds must be positive or None")
        self.client = client
        self.stale_seconds = stale_seconds

    def get_quote(self, symbol: str) -> UnderlyingQuote:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        retrieved_at = datetime.now(UTC)
        payload = self.client.get_quote(symbol)
        root = _root(payload, "QuoteResponse")
        rows = root.get("QuoteData", [])
        if not isinstance(rows, list) or not rows:
            raise ETradeMarketDataError("E*TRADE returned no quote rows")
        row = rows[0] if isinstance(rows[0], dict) else {}
        fields = row.get("All", {}) if isinstance(row.get("All", {}), dict) else {}
        product = row.get("Product", {}) if isinstance(row.get("Product", {}), dict) else {}
        price = _first(fields, "lastTrade", "lastTradePrice", "lastPrice")
        if price is None:
            price = _first(row, "lastTrade", "lastTradePrice", "lastPrice")
        numeric_price = _as_float(price, "lastTrade")
        if numeric_price is None or numeric_price <= 0:
            raise ETradeMarketDataError("E*TRADE returned an invalid underlying price")
        quote_time = _first(fields, "quoteTimeAsLong", "quoteTime")
        resolved_symbol = str(_first(product, "symbol") or symbol).upper()
        quote = UnderlyingQuote(
            resolved_symbol,
            numeric_price,
            _timestamp(quote_time, retrieved_at),
            self.source,
            QuoteStatus.REALTIME,
        )
        quality = validate_underlying_quote(quote)
        if not quality.valid:
            raise ETradeMarketDataError(
                f"E*TRADE underlying quote failed validation: {', '.join(quality.reasons)}"
            )
        return quote

    def get_option_chain(self, symbol: str, expiration: date | None = None) -> list[OptionQuote]:
        if expiration is None:
            raise ValueError("an expiration date is required for E*TRADE option chains")
        symbol = symbol.strip().upper()
        underlying = self.get_quote(symbol)
        payload = self.client.get_option_chain(
            symbol,
            expiration.year,
            expiration.month,
            expiryDay=expiration.day,
        )
        root = _root(payload, "OptionChainResponse")
        pairs = root.get("OptionPair", root.get("optionPairs", root.get("OptionPairs", [])))
        if not isinstance(pairs, list):
            raise ETradeMarketDataError("E*TRADE returned an invalid option-pair list")
        result: list[OptionQuote] = []
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            for option_type, field_names in (
                (ContractType.CALL, ("Call", "call", "optioncall", "OptionCall")),
                (ContractType.PUT, ("Put", "put", "optionPut", "OptionPut")),
            ):
                raw = next((pair.get(field) for field in field_names if field in pair), None)
                if not isinstance(raw, dict):
                    continue
                try:
                    strike_raw = _first(raw, "strikePrice", "strike")
                    if strike_raw is None:
                        strike_raw = _first(pair, "strikePrice", "strike")
                    strike = _as_float(strike_raw, "strikePrice", allow_none=True)
                    if strike is None or strike <= 0:
                        continue
                    bid = _as_float(_first(raw, "bid", "bidPrice"), "bid")
                    ask = _as_float(_first(raw, "ask", "askPrice"), "ask")
                    if bid is None or ask is None or bid < 0 or ask < bid:
                        continue
                    greeks = raw.get(
                        "OptionGreeks", raw.get("optionGreeks", raw.get("optionGreek", {}))
                    )
                    if not isinstance(greeks, dict):
                        greeks = {}
                    iv = _as_float(
                        _first(raw, "iv", "impliedVolatility")
                        if _first(raw, "iv", "impliedVolatility") is not None
                        else _first(greeks, "iv", "impliedVolatility"),
                        "iv",
                        allow_none=True,
                    )
                    if iv is not None and iv > 3:
                        iv /= 100
                    timestamp = _timestamp(
                        _first(raw, "quoteTimeAsLong", "quoteTime"), underlying.timestamp
                    )
                    option_symbol = str(
                        _first(raw, "symbol", "displaySymbol", "optionSymbol")
                        or f"{symbol}-{expiration.isoformat()}-{option_type.value}-{strike:.2f}"
                    )
                    option_quote = OptionQuote(
                        underlying_symbol=symbol,
                        option_symbol=option_symbol,
                        option_type=option_type,
                        strike=strike,
                        expiration=expiration,
                        timestamp=timestamp,
                        bid=bid,
                        ask=ask,
                        last=_as_float(_first(raw, "lastTrade", "lastPrice"), "last", allow_none=True),
                        volume=_as_int(_first(raw, "volume", "totalVolume"), "volume"),
                        open_interest=_as_int(
                            _first(raw, "openInterest", "openInterestAmount"), "openInterest"
                        ),
                        multiplier=100.0,
                        implied_volatility=iv,
                        delta=_as_float(_first(greeks, "delta"), "delta", allow_none=True),
                        gamma=_as_float(_first(greeks, "gamma"), "gamma", allow_none=True),
                        theta=_as_float(_first(greeks, "theta"), "theta", allow_none=True),
                        vega=_as_float(_first(greeks, "vega"), "vega", allow_none=True),
                        rho=_as_float(_first(greeks, "rho"), "rho", allow_none=True),
                        exercise_style="American",
                        source=self.source,
                        underlying_price=underlying.price,
                    )
                    quality = validate_option_quote(
                        option_quote, stale_seconds=self.stale_seconds
                    )
                    if quality.valid:
                        result.append(option_quote)
                except ETradeMarketDataError:
                    # A malformed contract must not poison the rest of a chain.
                    continue
        if pairs and not result:
            raise ETradeMarketDataError("E*TRADE option chain contained no valid current quotes")
        return result

    def get_expirations(self, symbol: str) -> list[date]:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        payload = self.client.get_option_expirations(symbol)
        root = _root(payload, "OptionExpireDateResponse")
        rows = root.get("ExpirationDate", root.get("expirationDates", []))
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise ETradeMarketDataError("E*TRADE returned an invalid expiration list")
        result: list[date] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                value = date(int(row["year"]), int(row["month"]), int(row["day"]))
            except (KeyError, TypeError, ValueError):
                continue
            if value >= date.today():
                result.append(value)
        return sorted(set(result))

    def get_history(self, symbol: str, limit: int = 252) -> list[float]:
        raise ETradeMarketDataError(
            "E*TRADE market-data adapter does not provide historical bars here; import a validated dataset"
        )
