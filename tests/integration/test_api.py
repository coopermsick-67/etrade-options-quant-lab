from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_capabilities_and_demo_math_endpoints() -> None:
    assert client.get("/health").json()["live_enabled"] is False
    capabilities = client.get("/api/capabilities").json()
    assert capabilities["default_mode"] == "paper"
    assert capabilities["robinhood"]["live_options"] is False
    math_demo = client.get("/api/math/demo").json()
    assert math_demo["iv_inversion"]["converged"] is True
    assert math_demo["xyz_payoffs"]["107"] == 0


def test_paper_orders_are_idempotent_at_api_boundary() -> None:
    payload = {
        "symbol": "SPY240621C00500000",
        "action": "BUY",
        "quantity": 1,
        "limit_price": 1.20,
        "bid": 1.00,
        "ask": 1.10,
        "client_order_id": "api-test-idempotent",
    }
    first = client.post("/api/paper/orders", json=payload)
    second = client.post("/api/paper/orders", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["order_id"] == second.json()["order_id"]


def test_live_approval_is_disabled_by_default() -> None:
    payload = {
        "ticket": {
            "account_id": "masked",
            "symbol": "SPY",
            "action": "BUY_TO_OPEN",
            "quantity": 1,
            "limit_price": "1.25",
            "order_type": "LIMIT",
            "legs": [{"strike": "500", "type": "CALL"}],
            "quote_timestamp": "2026-09-20T12:00:00Z",
            "risk_dollars": "125.00",
            "model_version": "demo-v1",
        }
    }
    assert client.post("/api/live/approval", json=payload).status_code == 403
