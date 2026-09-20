from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.runtime import build_runtime_dashboard
from apps.api.settings import Settings
from brokers.base import OrderAction, OrderRequest
from brokers.paper.broker import PaperBroker
from data.providers.etrade import ETradeMarketDataProvider


class FakeETradeClient:
    environment = "sandbox"

    def get_quote(self, symbol: str) -> dict[str, object]:
        assert symbol == "SPY"
        return {
            "QuoteResponse": {
                "QuoteData": [
                    {
                        "Product": {"symbol": "SPY"},
                        "All": {
                            "lastTrade": 550.0,
                            "quoteTimeAsLong": int(datetime.now(UTC).timestamp() * 1000),
                        },
                    }
                ]
            }
        }

    def get_option_chain(
        self, symbol: str, expiry_year: int, expiry_month: int, **params: object
    ) -> dict[str, object]:
        assert (symbol, expiry_year, expiry_month, params["expiryDay"]) == ("SPY", 2026, 12, 18)
        greeks = {"delta": 0.5, "gamma": 0.02, "theta": -0.04, "vega": 0.18, "rho": 0.04}
        return {
            "OptionChainResponse": {
                "OptionPair": [
                    {
                        "strikePrice": 550,
                        "Call": {
                            "displaySymbol": "SPY C550",
                            "bid": 5.0,
                            "ask": 5.1,
                            "lastTrade": 5.05,
                            "volume": 100,
                            "openInterest": 1000,
                            "iv": 0.22,
                            "OptionGreeks": greeks,
                        },
                        "Put": {
                            "displaySymbol": "SPY P550",
                            "bid": 4.9,
                            "ask": 5.0,
                            "lastTrade": 4.95,
                            "volume": 90,
                            "openInterest": 900,
                            "iv": 22.0,
                            "OptionGreeks": {**greeks, "delta": -0.5, "rho": -0.04},
                        },
                    }
                ]
            }
        }


def test_dashboard_is_truthful_without_market_data() -> None:
    payload = TestClient(app).get("/api/dashboard").json()
    assert payload["demo"] is False
    assert payload["data_status"]["provider"] == "none"
    assert payload["candidates"] == []
    assert payload["model_health"]["trades_analyzed"] == 0


def test_quote_endpoint_refuses_unconfigured_provider() -> None:
    response = TestClient(app).get("/api/market/quote?symbol=SPY")
    assert response.status_code == 503


def test_paper_equity_history_and_runtime_snapshot_are_real_state() -> None:
    broker = PaperBroker(initial_equity=1_000)
    request = OrderRequest(
        symbol="SPY-TEST",
        action=OrderAction.BUY,
        quantity=1,
        limit_price=1.25,
        bid=1.0,
        ask=1.1,
        client_order_id="runtime-unit-1",
    )
    order = broker.submit(request)
    assert order.status.value == "FILLED"
    settings = Settings()
    payload = build_runtime_dashboard(broker, settings)
    assert len(payload["equity_curve"]) == 2
    assert payload["account"]["daily_pnl"] < 0
    assert payload["risk_limits"][1]["used"] > 0
    assert payload["paper"]["orders"][0]["client_order_id"] == "runtime-unit-1"


def test_etrade_market_data_adapter_normalizes_documented_shapes() -> None:
    provider = ETradeMarketDataProvider(FakeETradeClient())  # type: ignore[arg-type]
    quote = provider.get_quote("SPY")
    assert quote.symbol == "SPY"
    assert quote.price == 550.0
    chain = provider.get_option_chain("SPY", date(2026, 12, 18))
    assert len(chain) == 2
    assert chain[0].ask >= chain[0].bid
    put = next(contract for contract in chain if contract.option_type.value == "PUT")
    assert put.implied_volatility == 0.22
    assert put.delta == -0.5


def test_etrade_adapter_does_not_invent_historical_bars() -> None:
    provider = ETradeMarketDataProvider(FakeETradeClient())  # type: ignore[arg-type]
    try:
        provider.get_history("SPY")
    except RuntimeError as exc:
        assert "historical bars" in str(exc)
    else:
        raise AssertionError("historical data was fabricated")
