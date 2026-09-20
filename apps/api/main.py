"""FastAPI entrypoint for the research and paper-trading platform."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from apps.api.demo import build_dashboard_payload, build_math_demo
from apps.api.settings import get_settings
from brokers.base import OrderAction, OrderRequest
from brokers.paper.broker import PaperBroker
from compliance.etrade_live_guard import ApprovalTokenService, TradeTicket

settings = get_settings()
app = FastAPI(title="E*TRADE Options Quant Lab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

paper_broker = PaperBroker(
    settings.paper_initial_equity,
    settings.paper_slippage_bps,
    settings.paper_partial_fill_rate,
    settings.paper_fee_per_contract,
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

    @model_validator(mode="after")
    def validate_quote(self) -> PaperOrderInput:
        if self.ask < self.bid:
            raise ValueError("ask must not be below bid")
        return self


class TicketInput(BaseModel):
    ticket: dict[str, Any]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": settings.trading_mode.upper(),
        "live_enabled": settings.effective_live_trading_enabled,
    }


@app.get("/health/database")
def database_health() -> dict[str, Any]:
    """Check database connectivity without mutating state."""

    from sqlalchemy import create_engine, text

    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:
        return {"status": "degraded", "detail": type(exc).__name__}
    return {"status": "ok"}


@app.get("/health/etrade")
def etrade_health() -> dict[str, Any]:
    return {"status": "disconnected", "environment": settings.etrade_env, "orders_created": False}


@app.get("/api/capabilities")
def capabilities() -> dict[str, Any]:
    return {
        "modes": ["analysis", "paper", "live"],
        "default_mode": "paper",
        "live_trading_enabled": settings.effective_live_trading_enabled,
        "etrade": {
            "adapter": True,
            "live_orders": settings.effective_live_trading_enabled,
            "human_approval_required": True,
        },
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
        "emergency_stop": paper_broker.emergency_stop,
    }


class EmergencyStopInput(BaseModel):
    enabled: bool


@app.get("/api/paper/emergency-stop")
def paper_emergency_stop() -> dict[str, bool]:
    return {"enabled": paper_broker.emergency_stop}


@app.post("/api/paper/emergency-stop")
def set_paper_emergency_stop(payload: EmergencyStopInput) -> dict[str, bool]:
    paper_broker.set_emergency_stop(payload.enabled)
    return {"enabled": paper_broker.emergency_stop}


@app.post("/api/paper/orders")
def paper_order(payload: PaperOrderInput) -> dict[str, Any]:
    try:
        action = OrderAction(payload.action.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="action must be BUY or SELL") from exc
    try:
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
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    order = paper_broker.submit(request)
    return asdict(order)


@app.post("/api/live/approval")
def issue_live_approval(payload: TicketInput) -> dict[str, Any]:
    if not settings.effective_live_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="live approval UI is disabled until production broker support and authenticated human review are configured",
        )
    try:
        ticket = TradeTicket(**payload.ticket)
        token = approval_service.issue_from_ui(ticket)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "ticket_hash": ticket.sha256(),
        "approval_token": token,
        "expires_in_seconds": approval_service.ttl_seconds,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
