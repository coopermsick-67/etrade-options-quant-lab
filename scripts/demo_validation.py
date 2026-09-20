"""Run the deterministic validation demonstrations used in the delivery checklist."""

from __future__ import annotations

import json

from apps.api.demo import build_math_demo
from brokers.base import OrderAction, OrderRequest
from brokers.paper.broker import PaperBroker
from quant.risk.engine import RiskLimits, pretrade_check


def main() -> None:
    broker = PaperBroker(initial_equity=10_000, slippage_bps=15)
    request = OrderRequest(
        symbol="SPY240621C00500000",
        action=OrderAction.BUY,
        quantity=1,
        limit_price=1.20,
        bid=1.00,
        ask=1.10,
        client_order_id="demo-validation-order",
    )
    first = broker.submit(request)
    duplicate = broker.submit(request)
    risk_rejection = pretrade_check(
        account_equity=10_000,
        max_loss_per_contract=500,
        contracts=1,
        total_open_risk=0,
        spread_pct=0.20,
        volume=0,
        open_interest=0,
        quote_age_seconds=999,
        stale_seconds=120,
        current_positions=0,
        limits=RiskLimits(),
    )
    print(
        json.dumps(
            {
                "math": build_math_demo(),
                "paper_order_status": first.status,
                "duplicate_order_id_same": first.order_id == duplicate.order_id,
                "risk_rejection": {
                    "passed": risk_rejection.passed,
                    "reasons": risk_rejection.reasons,
                },
                "live_default": False,
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
