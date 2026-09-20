"""FastAPI entrypoint for the research and paper-trading platform."""

from __future__ import annotations

import calendar
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from apps.api.connections import (
    BrokerConnectionManager,
    ETradeConnectionError,
)
from apps.api.demo import build_math_demo
from apps.api.runtime import build_runtime_dashboard, market_data_status
from apps.api.settings import get_settings
from backtest.datasets import (
    HistoricalDatasetError,
    inspect_dataset,
    list_datasets,
    load_bars,
    serialize_dataset,
)
from backtest.engine import HistoricalBar, run_simple_event_backtest
from brokers.base import OrderAction, OrderRequest
from brokers.etrade.client import ETradeAPIError, ETradeClient
from brokers.paper.broker import PaperBroker
from compliance.etrade_live_guard import ApprovalTokenService, TradeTicket
from data.providers.etrade import ETradeMarketDataError, ETradeMarketDataProvider

settings = get_settings()
connection_manager = BrokerConnectionManager(settings.etrade_oauth_pending_ttl_seconds)
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


class ETradeOAuthCompleteInput(BaseModel):
    connection_id: str = Field(min_length=1, max_length=200)
    verifier: str = Field(min_length=1, max_length=200)


class BacktestInput(BaseModel):
    dataset: str = Field(min_length=1, max_length=300)
    symbol: str | None = Field(default=None, max_length=32)
    period: str = "max"
    start_date: date | None = None
    end_date: date | None = None
    strategy: str = "moving_average"
    lookback: int = Field(default=20, ge=2, le=252)
    fill_model: str = "realistic"
    initial_equity: float = Field(default=10_000, gt=0)
    slippage_bps: float = Field(default=15, ge=0, le=10_000)
    fee_per_contract: float = Field(default=0.65, ge=0)

    @model_validator(mode="after")
    def validate_backtest(self) -> BacktestInput:
        if self.period not in {"30d", "3m", "6m", "1y", "3y", "max", "custom"}:
            raise ValueError("period must be 30d, 3m, 6m, 1y, 3y, max, or custom")
        if self.strategy not in {"moving_average", "hold"}:
            raise ValueError("strategy must be moving_average or hold")
        if self.fill_model not in {"optimistic", "realistic", "conservative"}:
            raise ValueError("fill_model must be optimistic, realistic, or conservative")
        if self.period == "custom" and (self.start_date is None or self.end_date is None):
            raise ValueError("custom period requires start_date and end_date")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self


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
    data_status = market_data_status(settings, connection_manager)
    return {
        "status": "configured" if data_status["configured"] else "disconnected",
        "environment": settings.etrade_env,
        "orders_created": False,
        "message": data_status["message"],
    }


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
            "connection_workflow": True,
        },
        "robinhood": {
            "adapter": False,
            "live_options": False,
            "reason": "No official public brokerage-options API verified",
            "documentation": "https://docs.robinhood.com/crypto/trading/",
        },
        "backtesting": {"file_import": True, "point_in_time_required": True},
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    return build_runtime_dashboard(paper_broker, settings, connection_manager)


def _etrade_provider() -> ETradeMarketDataProvider:
    connection_status = connection_manager.status(settings)
    if settings.market_data_provider != "etrade" and not connection_status["configured"]:
        raise HTTPException(
            status_code=503,
            detail="No market-data provider is connected. Open Connections, configure E*TRADE consumer credentials, and complete OAuth.",
        )
    try:
        client = connection_manager.client(settings)
    except ETradeConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ETradeMarketDataProvider(client, stale_seconds=settings.quote_stale_seconds)


@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    data_status = market_data_status(settings, connection_manager)
    return {
        "api": "ok",
        "mode": settings.trading_mode.upper(),
        "live_enabled": settings.effective_live_trading_enabled,
        "market_data": data_status,
        "paper": {
            "emergency_stop": paper_broker.emergency_stop,
            "orders": len(paper_broker.orders()),
            "positions": len(paper_broker.positions()),
        },
    }


@app.get("/api/settings/public")
def public_settings() -> dict[str, Any]:
    """Expose non-secret settings needed to render the configuration page."""

    return {
        "mode": settings.trading_mode.upper(),
        "market_data_provider": settings.market_data_provider,
        "etrade_environment": settings.etrade_env,
        "live_enabled": settings.effective_live_trading_enabled,
        "risk": {
            "risk_per_trade_pct": settings.risk_per_trade_pct,
            "max_open_risk_pct": settings.max_open_risk_pct,
            "daily_loss_limit_pct": settings.daily_loss_limit_pct,
            "weekly_loss_limit_pct": settings.weekly_loss_limit_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
        },
    }


@app.get("/api/data/status")
def data_status() -> dict[str, Any]:
    return market_data_status(settings, connection_manager)


@app.get("/api/connections")
def connections() -> dict[str, Any]:
    return {
        "etrade": connection_manager.status(settings),
        "robinhood": {
            "provider": "robinhood",
            "status": "unavailable",
            "configured": False,
            "live_options": False,
            "message": "No official public Robinhood brokerage/options API is verified. Unofficial endpoints and browser automation are not used.",
            "documentation": "https://docs.robinhood.com/crypto/trading/",
        },
    }


@app.post("/api/connections/etrade/start")
def start_etrade_connection() -> dict[str, Any]:
    try:
        return connection_manager.start(settings)
    except ETradeConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/connections/etrade/complete")
def complete_etrade_connection(payload: ETradeOAuthCompleteInput) -> dict[str, Any]:
    try:
        connection_manager.complete(settings, payload.connection_id, payload.verifier)
    except ETradeConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return connection_manager.status(settings)


@app.post("/api/connections/etrade/disconnect")
def disconnect_etrade_connection() -> dict[str, Any]:
    result = connection_manager.disconnect(settings)
    return {"status": result, "connection": connection_manager.status(settings)}


def _mask_identifier(value: object) -> str:
    text = str(value or "")
    return f"••••{text[-4:]}" if len(text) >= 4 else "••••"


@app.get("/api/connections/etrade/accounts")
def etrade_accounts() -> dict[str, Any]:
    client = _etrade_client()
    try:
        payload = client.list_accounts()
    except ETradeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    root = payload.get("AccountListResponse", payload)
    accounts_root = root.get("Accounts", root) if isinstance(root, dict) else {}
    raw_accounts = accounts_root.get("Account", []) if isinstance(accounts_root, dict) else []
    if isinstance(raw_accounts, dict):
        raw_accounts = [raw_accounts]
    accounts = []
    for account in raw_accounts if isinstance(raw_accounts, list) else []:
        if not isinstance(account, dict):
            continue
        accounts.append(
            {
                "account_id": _mask_identifier(account.get("accountId")),
                "account_mode": account.get("accountMode"),
                "account_type": account.get("accountType"),
                "account_status": account.get("accountStatus"),
                "description": account.get("accountDesc"),
            }
        )
    return {"environment": settings.etrade_env, "accounts": accounts, "source": "etrade"}


def _etrade_client() -> ETradeClient:
    try:
        return connection_manager.client(settings)
    except ETradeConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/market/quote")
def market_quote(symbol: str) -> dict[str, Any]:
    try:
        quote = _etrade_provider().get_quote(symbol)
    except (ETradeAPIError, ETradeMarketDataError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return asdict(quote)


@app.get("/api/market/option-chain")
def market_option_chain(symbol: str, expiration: date) -> dict[str, Any]:
    try:
        chain = _etrade_provider().get_option_chain(symbol, expiration)
    except (ETradeAPIError, ETradeMarketDataError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "symbol": symbol.upper(),
        "expiration": expiration.isoformat(),
        "source": "etrade",
        "contracts": [asdict(contract) for contract in chain],
    }


@app.get("/api/market/expirations")
def market_expirations(symbol: str) -> dict[str, Any]:
    if not symbol.strip():
        raise HTTPException(status_code=422, detail="symbol is required")
    try:
        expirations = _etrade_provider().get_expirations(symbol)
    except (ETradeAPIError, ETradeMarketDataError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "symbol": symbol.strip().upper(),
        "source": "etrade",
        "expirations": [value.isoformat() for value in expirations],
    }


@app.get("/api/scanner")
def scanner(symbol: str | None = None) -> dict[str, Any]:
    data = market_data_status(settings, connection_manager)
    if not data["configured"]:
        return {
            "status": "unavailable",
            "symbol": symbol.upper() if symbol else None,
            "candidates": [],
            "message": data["message"],
        }
    # Candidate construction is intentionally not guessed from an arbitrary
    # chain. A future scanner job must provide an expiration, liquidity policy,
    # and model version explicitly before it can emit a candidate.
    return {
        "status": "ready",
        "symbol": symbol.upper() if symbol else None,
        "candidates": [],
        "message": "Provider connected. Supply an explicit scanner configuration before ranking candidates.",
    }


@app.get("/api/math/demo")
def math_demo() -> dict[str, Any]:
    return build_math_demo()


@app.get("/api/paper/portfolio")
def paper_portfolio() -> dict[str, Any]:
    return {
        "cash": paper_broker.cash,
        "equity": paper_broker.equity(),
        "positions": paper_broker.positions(),
        "orders": paper_broker.orders(),
        "emergency_stop": paper_broker.emergency_stop,
    }


@app.get("/api/paper/orders")
def paper_orders() -> dict[str, Any]:
    return {"orders": paper_broker.orders(), "emergency_stop": paper_broker.emergency_stop}


@app.get("/api/risk")
def risk_snapshot() -> dict[str, Any]:
    payload = build_runtime_dashboard(paper_broker, settings, connection_manager)
    return {
        "limits": payload["risk_limits"],
        "account": payload["account"],
        "violations": [],
        "emergency_stop": paper_broker.emergency_stop,
        "message": "Risk is calculated from the current in-process paper account. Daily and weekly loss utilization is conservative since-reset utilization until a persistent timestamped ledger is enabled. No market Greeks are available without positions and quote marks.",
    }


@app.get("/api/journal")
def journal() -> dict[str, Any]:
    return {"entries": paper_broker.orders(), "source": "paper_broker"}


backtest_runs: list[dict[str, Any]] = []


def _historical_root() -> Path:
    return Path(settings.historical_data_dir)


def _subtract_months(value: date, months: int) -> date:
    total_months = value.year * 12 + (value.month - 1) - months
    year, month_index = divmod(total_months, 12)
    month = month_index + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _period_dates(payload: BacktestInput, info: dict[str, Any]) -> tuple[date, date]:
    available_start = date.fromisoformat(str(info["start"])[:10])
    available_end = date.fromisoformat(str(info["end"])[:10])
    end = payload.end_date or available_end
    if payload.period == "custom":
        assert payload.start_date is not None
        assert payload.end_date is not None
        return payload.start_date, payload.end_date
    if payload.start_date is not None:
        start = payload.start_date
    elif payload.period == "max":
        start = available_start
    elif payload.period == "30d":
        start = end - timedelta(days=29)
    elif payload.period == "3m":
        start = _subtract_months(end, 3) + timedelta(days=1)
    elif payload.period == "6m":
        start = _subtract_months(end, 6) + timedelta(days=1)
    elif payload.period == "1y":
        start = _subtract_months(end, 12) + timedelta(days=1)
    else:
        start = _subtract_months(end, 36) + timedelta(days=1)
    return max(start, available_start), min(end, available_end)


def _backtest_signal(
    strategy: str, lookback: int
) -> Callable[[Sequence[HistoricalBar], int], bool]:
    def signal(history: Sequence[HistoricalBar], _index: int) -> bool:
        if strategy == "hold":
            return True
        if len(history) < lookback:
            return False
        average = sum(bar.close for bar in history[-lookback:]) / lookback
        return history[-1].close > average

    return signal


@app.get("/api/backtests")
def backtests() -> dict[str, Any]:
    datasets = [serialize_dataset(info) for info in list_datasets(_historical_root())]
    return {
        "runs": list(reversed(backtest_runs)),
        "datasets": datasets,
        "period_presets": ["30d", "3m", "6m", "1y", "3y", "max", "custom"],
        "message": "Import a validated point-in-time option quote CSV to run research." if not datasets else "Select a dataset and date range; results include realistic fills and costs.",
        "schema": {
            "required_columns": ["timestamp", "close", "option_mid", "option_bid", "option_ask"],
            "optional_columns": ["symbol", "multiplier"],
            "timestamp": "timezone-aware ISO-8601 timestamp",
        },
    }


@app.post("/api/backtests/datasets/import")
async def import_backtest_dataset(
    file: Annotated[UploadFile, File(...)],
) -> dict[str, Any]:
    raw_filename = file.filename or ""
    filename = Path(raw_filename).name
    if (
        not filename
        or filename != raw_filename
        or "/" in raw_filename
        or "\\" in raw_filename
        or Path(filename).suffix.lower() != ".csv"
    ):
        raise HTTPException(status_code=422, detail="upload a .csv file with a safe filename")
    content = await file.read(settings.backtest_upload_max_bytes + 1)
    if len(content) > settings.backtest_upload_max_bytes:
        raise HTTPException(status_code=413, detail="historical dataset exceeds the configured upload limit")
    root = _historical_root()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / filename
    if destination.exists():
        raise HTTPException(status_code=409, detail="a dataset with that filename already exists")
    destination.write_bytes(content)
    try:
        info = inspect_dataset(root, filename)
    except HistoricalDatasetError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"dataset": serialize_dataset(info), "message": "dataset imported and validated"}


@app.post("/api/backtests/run")
def run_backtest(payload: BacktestInput) -> dict[str, Any]:
    root = _historical_root()
    try:
        info = serialize_dataset(inspect_dataset(root, payload.dataset))
        start_date, end_date = _period_dates(payload, info)
        bars = load_bars(
            root,
            payload.dataset,
            symbol=payload.symbol,
            start_date=start_date,
            end_date=end_date,
        )
        result = run_simple_event_backtest(
            bars,
            _backtest_signal(payload.strategy, payload.lookback),
            initial_equity=payload.initial_equity,
            fill_model=payload.fill_model,
            slippage_bps=payload.slippage_bps,
            fee_per_contract=payload.fee_per_contract,
        )
    except HistoricalDatasetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run_id = str(uuid4())
    run = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": payload.dataset,
        "symbol": payload.symbol.upper() if payload.symbol else None,
        "strategy": payload.strategy,
        "lookback": payload.lookback,
        "period": payload.period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "observations": len(bars),
        "fill_model": payload.fill_model,
        "slippage_bps": payload.slippage_bps,
        "fee_per_contract": payload.fee_per_contract,
        "lookahead_safe": result.lookahead_safe,
        "trades": len(result.trades),
        "metrics": asdict(result.metrics),
        "trade_log": [
            {
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat(),
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "reason": trade.reason,
            }
            for trade in result.trades
        ],
    }
    backtest_runs.append(run)
    del backtest_runs[:-50]
    return run


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
