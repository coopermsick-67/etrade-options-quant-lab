from datetime import UTC, datetime
from math import nan
from threading import Barrier, Thread

import pytest

from apps.api.settings import Settings
from backtest.engine import HistoricalBar
from brokers.base import OrderAction, OrderRequest, OrderStatus
from brokers.paper.broker import PaperBroker
from compliance.etrade_live_guard import ApprovalTokenService, ComplianceError, TradeTicket
from quant.probability.lognormal import probability_above, probability_below, probability_between
from quant.risk.engine import RiskLimits, pretrade_check
from quant.simulation.monte_carlo import simulate_payoff


def request(client_order_id: str = "hardening") -> OrderRequest:
    return OrderRequest(
        symbol="SPY-TEST-CALL",
        action=OrderAction.BUY,
        quantity=1,
        limit_price=1.25,
        bid=1.00,
        ask=1.10,
        client_order_id=client_order_id,
    )


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
        model_version="hardening",
    )


def test_outage_is_idempotent_and_emergency_stop_is_fail_closed() -> None:
    broker = PaperBroker()
    broker.set_outage(True)
    first = broker.submit(request("outage-1"))
    duplicate = broker.submit(request("outage-1"))
    assert first.order_id == duplicate.order_id
    broker.set_outage(False)
    broker.set_emergency_stop(True)
    blocked = broker.submit(request("stop-1"))
    assert blocked.status is OrderStatus.REJECTED
    assert blocked.reason == "paper emergency stop is active"


def test_order_contract_rejects_invalid_market_data() -> None:
    with pytest.raises(ValueError, match="ask must not be below bid"):
        OrderRequest(
            symbol="SPY",
            action=OrderAction.BUY,
            quantity=1,
            limit_price=1.0,
            bid=1.1,
            ask=1.0,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        OrderRequest(
            symbol="SPY",
            action=OrderAction.BUY,
            quantity=1,
            limit_price=1.0,
            bid=0.9,
            ask=1.0,
            submitted_at=datetime(2026, 9, 20),
        )


def test_approval_token_expiry_is_exact_and_malformed_payloads_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 10_000
    monkeypatch.setattr("compliance.etrade_live_guard.time.time", lambda: now)
    service = ApprovalTokenService("h" * 40, ttl_seconds=10)
    token = service.issue_from_ui(ticket())
    monkeypatch.setattr("compliance.etrade_live_guard.time.time", lambda: now + 10)
    with pytest.raises(ComplianceError, match="expired"):
        service.consume(ticket(), token)
    with pytest.raises(ComplianceError, match="malformed"):
        service.consume(ticket(), "not-a-token")


def test_approval_token_is_single_use_under_concurrency() -> None:
    service = ApprovalTokenService("c" * 40)
    token = service.issue_from_ui(ticket())
    barrier = Barrier(2)
    results: list[object] = []

    def consume() -> None:
        barrier.wait()
        try:
            results.append(service.consume(ticket(), token))
        except ComplianceError as exc:
            results.append(exc)

    threads = [Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(isinstance(result, dict) for result in results) == 1
    assert sum(isinstance(result, ComplianceError) for result in results) == 1


def test_deterministic_lognormal_probabilities_do_not_partition_strict_inequalities_badly() -> None:
    assert probability_above(100, 100, 0, 0, 0) == 0.0
    assert probability_below(100, 100, 0, 0, 0) == 0.0
    assert probability_between(100, 90, 110, 0, 0, 0) == 1.0
    assert probability_above(100, 100, 1, 0, 0.0) == 0.0
    assert probability_below(100, 100, 1, 0, 0.0) == 0.0


def test_risk_engine_rejects_nonfinite_and_negative_inputs() -> None:
    result = pretrade_check(
        account_equity=10_000,
        max_loss_per_contract=nan,
        contracts=1,
        total_open_risk=0,
        spread_pct=0.01,
        volume=100,
        open_interest=100,
        quote_age_seconds=1,
        stale_seconds=120,
        current_positions=0,
        limits=RiskLimits(),
    )
    assert result.passed is False
    assert "maximum loss per contract must be positive" in result.reasons


def test_historical_bar_requires_timezone_and_valid_market() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        HistoricalBar(datetime(2026, 9, 20), 100, 1, 0.9, 1.1)
    with pytest.raises(ValueError, match="ask cannot be below bid"):
        HistoricalBar(datetime(2026, 9, 20, tzinfo=UTC), 100, 1, 1.1, 1.0)
    with pytest.raises(ValueError, match="midpoint"):
        HistoricalBar(datetime(2026, 9, 20, tzinfo=UTC), 100, 1.5, 0.9, 1.1)


def test_monte_carlo_rejects_nonfinite_payoff() -> None:
    with pytest.raises(ValueError, match="finite values"):
        simulate_payoff(100, 0, 0.2, 1, lambda terminals: terminals * nan, paths=10)


def test_unimplemented_live_approval_ui_cannot_be_enabled_by_environment() -> None:
    with pytest.raises(ValueError, match="authenticated human review"):
        Settings(live_approval_ui_enabled=True)
