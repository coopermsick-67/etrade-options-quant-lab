"""FastAPI entrypoint for the research and paper-trading platform."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from apps.api.demo import build_dashboard_payload, build_math_demo
from apps.api.settings import get_settings
from brokers.base import OrderAction, OrderRequest
from brokers.paper.broker import PaperBroker
from compliance.etrade_live_guard import ApprovalTokenService, TradeTicket

settings = get_settings()
app = FastAPI(title="E*TRADE Options Quant Lab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

paper_broker = PaperBroker(
    settings.paper_initial_equity, settings.paper_slippage_bps, settings.paper_partial_fill_rate
)
approval_service = ApprovalTokenService(settings.approval_token_secret)


class PaperOrderInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    action: str
    quantity: int = Field(gt=0, le=100)
    limit_price: float = Field(gt=0)
    bid: float = Field(ge=0)
    ask: float = Field(gt=0)
    multiplier: float = Field(default=100, gt=0)
    client_order_id: str | None = None


class TicketInput(BaseModel):
    ticket: dict[str, Any]


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "mode": settings.trading_mode.upper(), "live_enabled": False}


@app.get("/health/etrade")
def etrade_health() -> dict[str, Any]:
    return {"status": "disconnected", "environment": settings.etrade_env, "orders_created": False}


@app.get("/api/capabilities")
def capabilities() -> dict[str, Any]:
    return {
        "modes": ["analysis", "paper", "live"],
        "default_mode": "paper",
        "live_trading_enabled": False,
        "etrade": {"adapter": True, "live_orders": False, "human_approval_required": True},
        "robinhood": {
            "adapter": False,
            "live_options": False,
            "reason": "No official public brokerage-options API verified",
        },
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    return build_dashboard_payload()


@app.get("/api/math/demo")
def math_demo() -> dict[str, Any]:
    return build_math_demo()


@app.get("/api/paper/portfolio")
def paper_portfolio() -> dict[str, Any]:
    return {
        "cash": paper_broker.cash,
        "equity": paper_broker.equity(),
        "positions": paper_broker.positions(),
    }


@app.post("/api/paper/orders")
def paper_order(payload: PaperOrderInput) -> dict[str, Any]:
    try:
        action = OrderAction(payload.action.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="action must be BUY or SELL") from exc
    request = OrderRequest(
        symbol=payload.symbol.upper(),
        action=action,
        quantity=payload.quantity,
        limit_price=payload.limit_price,
        bid=payload.bid,
        ask=payload.ask,
        multiplier=payload.multiplier,
        client_order_id=payload.client_order_id or str(uuid4()),
    )
    order = paper_broker.submit(request)
    return asdict(order)


@app.post("/api/live/approval")
def issue_live_approval(payload: TicketInput) -> dict[str, Any]:
    if not settings.live_trading_enabled:
        raise HTTPException(status_code=403, detail="LIVE_TRADING_ENABLED is false")
    try:
        ticket = TradeTicket(**payload.ticket)
        token = approval_service.issue_from_ui(ticket)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "ticket_hash": ticket.sha256(),
        "approval_token": token,
        "expires_in_seconds": approval_service.ttl_seconds,
    }
