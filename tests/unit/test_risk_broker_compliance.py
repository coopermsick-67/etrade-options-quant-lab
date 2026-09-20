from dataclasses import replace

import pytest

from brokers.base import OrderAction, OrderRequest, OrderStatus
from brokers.etrade.broker import BrokerCapabilityError, ETradeLiveBroker, RobinhoodOptionsBroker
from brokers.paper.broker import PaperBroker
from compliance.etrade_live_guard import ApprovalTokenService, ComplianceError, TradeTicket
from quant.risk.engine import RiskLimits, fixed_risk_contracts, pretrade_check


def order_request(client_id: str = "client-1", limit: float = 1.20) -> OrderRequest:
    return OrderRequest(
        symbol="SPY240621C00500000",
        action=OrderAction.BUY,
        quantity=2,
        limit_price=limit,
        bid=1.00,
        ask=1.10,
        client_order_id=client_id,
    )


def test_position_sizing_never_rounds_up() -> None:
    assert fixed_risk_contracts(10_000, 0.01, 75) == 1
    assert fixed_risk_contracts(10_000, 0.005, 75) == 0


def test_risk_engine_rejects_stale_and_wide_spread() -> None:
    result = pretrade_check(
        account_equity=10_000,
        max_loss_per_contract=100,
        contracts=1,
        total_open_risk=0,
        spread_pct=0.20,
        volume=10,
        open_interest=10,
        quote_age_seconds=200,
        stale_seconds=120,
        current_positions=0,
        limits=RiskLimits(),
    )
    assert result.passed is False
    assert "quote is stale" in result.reasons
    assert "spread exceeds configured maximum" in result.reasons


def test_paper_broker_models_slippage_partial_fills_and_idempotency() -> None:
    broker = PaperBroker(initial_equity=10_000, slippage_bps=100, partial_fill_rate=0.5)
    first = broker.submit(order_request())
    duplicate = broker.submit(order_request())
    assert first.order_id == duplicate.order_id
    assert first.status is OrderStatus.PARTIALLY_FILLED
    assert first.filled_quantity == 1
    assert first.fill is not None and first.fill.price == pytest.approx(1.111)
    assert len(broker.positions()) == 1

    broker.set_outage(True)
    unknown = broker.submit(order_request("client-2"))
    assert unknown.status is OrderStatus.UNKNOWN
    assert unknown.reason == "paper broker outage"

    broker.set_outage(False)
    short = broker.submit(
        replace(order_request("client-3"), action=OrderAction.SELL, quantity=4, limit_price=0.90)
    )
    assert short.status is OrderStatus.REJECTED
    assert short.reason == "uncovered short is disabled"


def ticket() -> TradeTicket:
    return TradeTicket(
        account_id="masked",
        symbol="SPY",
        action="BUY_TO_OPEN",
        quantity=1,
        limit_price="1.25",
        order_type="LIMIT",
        legs=({"strike": "500", "type": "CALL"},),
        quote_timestamp="2026-09-20T12:00:00Z",
        risk_dollars="125.00",
        model_version="demo-v1",
    )


def test_live_approval_is_short_lived_single_use_and_hash_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ApprovalTokenService("x" * 40, ttl_seconds=10)
    with pytest.raises(ComplianceError):
        service.issue_from_ui(ticket(), actor="scheduler")
    token = service.issue_from_ui(ticket())
    assert service.consume(ticket(), token)["actor"] == "user"
    with pytest.raises(ComplianceError):
        service.consume(ticket(), token)
    altered = replace(ticket(), limit_price="1.30")
    token_two = service.issue_from_ui(ticket())
    with pytest.raises(ComplianceError):
        service.consume(altered, token_two)

    now = 1_000
    monkeypatch.setattr("compliance.etrade_live_guard.time.time", lambda: now)
    expiring = ApprovalTokenService("y" * 40, ttl_seconds=1)
    token_three = expiring.issue_from_ui(ticket())
    monkeypatch.setattr("compliance.etrade_live_guard.time.time", lambda: now + 2)
    with pytest.raises(ComplianceError, match="expired"):
        expiring.consume(ticket(), token_three)


def test_live_broker_requires_approval_and_robinhood_is_disabled() -> None:
    class FakeClient:
        environment = "production"

        def __init__(self) -> None:
            self.placed = 0

        def place_order(self, _account: str, _payload: dict[str, object]) -> dict[str, object]:
            self.placed += 1
            return {"status": "accepted"}

        def preview_order(self, _account: str, _payload: dict[str, object]) -> dict[str, object]:
            return {"status": "previewed"}

    service = ApprovalTokenService("z" * 40)
    client = FakeClient()
    broker = ETradeLiveBroker(client, "masked", service, live_trading_enabled=True)
    with pytest.raises(ComplianceError):
        broker.submit(ticket(), {}, "not-a-token")
    token = service.issue_from_ui(ticket())
    assert broker.submit(ticket(), {}, token) == {"status": "accepted"}
    assert client.placed == 1
    with pytest.raises(BrokerCapabilityError):
        RobinhoodOptionsBroker().submit()
