from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.api.main as main_module
from apps.api.connections import BrokerConnectionManager
from apps.api.settings import Settings
from backtest.engine import HistoricalBar, run_simple_event_backtest
from brokers.etrade.oauth import OAuthTokens


def _csv_content() -> bytes:
    rows = [
        "timestamp,symbol,close,option_mid,option_bid,option_ask,multiplier",
        "2026-01-02T14:30:00+00:00,SPY,100,1.00,0.90,1.10,100",
        "2026-01-05T14:30:00+00:00,SPY,101,1.10,1.00,1.20,100",
        "2026-01-06T14:30:00+00:00,SPY,102,1.20,1.10,1.30,100",
        "2026-01-07T14:30:00+00:00,SPY,101,1.00,0.90,1.10,100",
    ]
    return ("\n".join(rows) + "\n").encode()


def test_no_trade_backtest_is_a_valid_flat_result() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        HistoricalBar(start + timedelta(days=index), 100, 1, 0.9, 1.1) for index in range(3)
    )
    result = run_simple_event_backtest(bars, lambda _history, _index: False)
    assert result.trades == ()
    assert result.equity_curve == (10_000.0, 10_000.0)
    assert result.metrics.total_return == 0


def test_backtest_dataset_upload_and_custom_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(historical_data_dir=str(tmp_path))
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(main_module, "connection_manager", BrokerConnectionManager())
    client = TestClient(main_module.app)

    upload = client.post(
        "/api/backtests/datasets/import",
        files={"file": ("spy.csv", _csv_content(), "text/csv")},
    )
    assert upload.status_code == 200
    assert upload.json()["dataset"]["rows"] == 4

    catalog = client.get("/api/backtests")
    assert catalog.status_code == 200
    assert catalog.json()["datasets"][0]["path"] == "spy.csv"

    run = client.post(
        "/api/backtests/run",
        json={
            "dataset": "spy.csv",
            "symbol": "SPY",
            "period": "custom",
            "start_date": "2026-01-05",
            "end_date": "2026-01-07",
            "strategy": "hold",
            "fill_model": "realistic",
        },
    )
    assert run.status_code == 200
    result = run.json()
    assert result["start_date"] == "2026-01-05"
    assert result["end_date"] == "2026-01-07"
    assert result["observations"] == 3
    assert result["lookahead_safe"] is True
    assert result["trades"] == 1


def test_backtest_rejects_timezone_naive_upload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(historical_data_dir=str(tmp_path))
    monkeypatch.setattr(main_module, "settings", settings)
    naive = _csv_content().replace(b"2026-01-02T14:30:00+00:00", b"2026-01-02T14:30:00")
    response = TestClient(main_module.app).post(
        "/api/backtests/datasets/import",
        files={"file": ("naive.csv", naive, "text/csv")},
    )
    assert response.status_code == 422
    assert not (tmp_path / "naive.csv").exists()


def test_connection_manager_keeps_oauth_secrets_server_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeOAuth:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_request_token(self) -> OAuthTokens:
            return OAuthTokens("request", "request-secret", True)

        def build_authorization_url(self, _token: OAuthTokens) -> str:
            return "https://us.etrade.com/authorize?token=request"

        def get_access_token(self, _token: OAuthTokens, _verifier: str) -> OAuthTokens:
            return OAuthTokens("access", "access-secret", True)

        def revoke_access_token(self, _token: OAuthTokens) -> str:
            return "revoked"

    monkeypatch.setattr("apps.api.connections.ETradeOAuthClient", FakeOAuth)
    manager = BrokerConnectionManager()
    settings = Settings(etrade_consumer_key="consumer", etrade_consumer_secret="secret")
    started = manager.start(settings)
    assert "access-secret" not in str(started)
    completed = manager.complete(settings, str(started["connection_id"]), "verifier")
    assert completed["status"] == "connected"
    status = manager.status(settings)
    assert status["configured"] is True
    assert status["source"] == "oauth_session"
    client = manager.client(settings)
    assert client.environment == "sandbox"
    assert manager.disconnect(settings) == "disconnected"


def test_option_chain_without_provider_explains_connection_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(main_module, "connection_manager", BrokerConnectionManager())
    response = TestClient(main_module.app).get(
        "/api/market/option-chain?symbol=VOO&expiration=2026-09-20"
    )
    assert response.status_code == 503
    assert "Open Connections" in response.json()["detail"]
