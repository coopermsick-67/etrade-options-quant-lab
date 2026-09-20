"""Runtime payloads for the operational dashboard.

This module deliberately returns empty, truthful states when no market-data
provider is configured. The UI must never substitute sample prices or paper
performance for a disconnected account.
"""

from __future__ import annotations

from typing import Any

from apps.api.settings import Settings
from brokers.paper.broker import PaperBroker


def market_data_status(settings: Settings) -> dict[str, Any]:
    required = (
        settings.etrade_consumer_key,
        settings.etrade_consumer_secret,
        settings.etrade_access_token,
        settings.etrade_access_token_secret,
    )
    credentials_ready = all(value.strip() for value in required)
    if settings.market_data_provider == "none":
        return {
            "provider": "none",
            "status": "not_configured",
            "configured": False,
            "source": None,
            "quote_timestamp": None,
            "message": "Configure an authorized market-data provider to load live or delayed quotes.",
        }
    if not credentials_ready:
        return {
            "provider": settings.market_data_provider,
            "status": "credentials_missing",
            "configured": False,
            "source": None,
            "quote_timestamp": None,
            "message": "E*TRADE credentials are not configured. No market data is being fabricated.",
        }
    return {
        "provider": settings.market_data_provider,
        "status": "configured",
        "configured": True,
        "source": settings.market_data_provider,
        "quote_timestamp": None,
        "message": "Provider configured. Request a quote or chain to verify connectivity.",
    }


def _position_risk(positions: list[dict[str, object]]) -> float:
    total = 0.0
    for position in positions:
        quantity = position.get("quantity")
        average_price = position.get("average_price")
        multiplier = position.get("multiplier")
        if not isinstance(quantity, (int, float)):
            continue
        if not isinstance(average_price, (int, float)):
            continue
        if not isinstance(multiplier, (int, float)):
            continue
        total += max(0.0, float(quantity)) * float(average_price) * float(multiplier)
    return total


def build_runtime_dashboard(paper_broker: PaperBroker, settings: Settings) -> dict[str, Any]:
    positions = list(paper_broker.positions())
    orders = list(paper_broker.orders())
    equity = paper_broker.equity()
    open_risk = _position_risk(positions)
    data_status = market_data_status(settings)
    initial_equity = paper_broker.initial_equity
    paper_pnl = equity - initial_equity
    loss_amount = max(0.0, -paper_pnl)

    def loss_utilization(limit_pct: float) -> float:
        limit = initial_equity * limit_pct
        return min(1.0, loss_amount / limit) if limit > 0 else 1.0

    drawdown_utilization = min(
        1.0,
        max(0.0, -paper_pnl) / (initial_equity * settings.max_drawdown_pct),
    )
    risk_limits = [
        {
            "label": "Max open risk",
            "value": initial_equity * settings.max_open_risk_pct,
            "used": min(1.0, open_risk / (initial_equity * settings.max_open_risk_pct)),
        },
        {
            "label": "Daily loss limit",
            "value": initial_equity * settings.daily_loss_limit_pct,
            "used": loss_utilization(settings.daily_loss_limit_pct),
        },
        {
            "label": "Weekly loss limit",
            "value": initial_equity * settings.weekly_loss_limit_pct,
            "used": loss_utilization(settings.weekly_loss_limit_pct),
        },
        {
            "label": "Maximum drawdown",
            "value": initial_equity * settings.max_drawdown_pct,
            "used": drawdown_utilization,
        },
    ]
    recent_activity = []
    for order in reversed(orders[-10:]):
        recent_activity.append(
            {
                "time": order["submitted_at"],
                "symbol": order["symbol"],
                "action": order["action"],
                "details": order.get("reason") or f"{order['status']} paper order",
                "status": order["status"],
            }
        )
    return {
        "mode": settings.trading_mode.upper(),
        "demo": False,
        "data_status": data_status,
        "broker_status": {
            "etrade": "configured" if data_status["configured"] else "disconnected",
            "robinhood": "live unavailable",
        },
        "live_enabled": settings.effective_live_trading_enabled,
        "account": {
            "equity": equity,
            "daily_pnl": paper_pnl,
            "buying_power": paper_broker.cash,
            "open_risk": open_risk,
            "portfolio_delta": 0.0,
            "portfolio_vega": 0.0,
            "cash": paper_broker.cash,
            "drawdown": min(0.0, paper_pnl / initial_equity),
        },
        "equity_curve": paper_broker.equity_history(),
        "risk_limits": risk_limits,
        "candidates": [],
        "recent_activity": recent_activity,
        "model_health": {
            "status": "No validated run",
            "signal_win_rate": None,
            "average_trade_expectancy": None,
            "sharpe": None,
            "max_drawdown": None,
            "trades_analyzed": 0,
            "note": "No validated backtest or paper-trading results have been recorded.",
        },
        "paper": {
            "emergency_stop": paper_broker.emergency_stop,
            "positions": positions,
            "orders": orders,
        },
    }
