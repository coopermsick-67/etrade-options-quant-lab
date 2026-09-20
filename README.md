# etrade-options-quant-lab

`etrade-options-quant-lab` is a research-first options platform for deterministic pricing, volatility analysis, probabilistic scenario modeling, backtesting, paper trading, and carefully gated broker integration.

It is designed to answer **“Do I actually have a repeatable options-trading edge?”**, not to manufacture attractive backtests. No strategy is assumed profitable, and a positive backtest is never treated as proof of future performance.

## Current status

- Analysis and PAPER modes are implemented and enabled by default.
- LIVE mode is disabled by default.
- The quantitative core includes Black-Scholes-Merton, American CRR pricing, Greeks, IV inversion, volatility estimators, Bayesian updating, Monte Carlo, payoff math, risk sizing, portfolio Greeks, and performance metrics.
- E*TRADE integration is adapter-based and uses the documented OAuth 1.0a lifecycle plus REST account/market/order endpoints. Live order submission is additionally gated by a single-use, short-lived human approval token.
- Robinhood live options trading is disabled because no official public brokerage-options API was verified in the current official developer documentation. Unofficial endpoints and browser automation are intentionally excluded.
- The UI launches in DEMO/PAPER mode without broker credentials.

This is an implemented research MVP with explicit follow-on boundaries. It does not bundle point-in-time historical option chains, claim a trading edge, or present demo results as live performance.

## Run locally

### Backend

```bash
uv venv
uv pip install -e '.[dev]'
cp .env.example .env
uv run uvicorn apps.api.main:app --reload --port 8000
uv run python -m scripts.demo_validation
```

Windows PowerShell:

```powershell
uv venv
uv pip install -e '.[dev]'
Copy-Item .env.example .env
uv run uvicorn apps.api.main:app --reload --port 8000
```

### Dashboard

```bash
cd apps/web
npm install
npm run dev
```

Open <http://localhost:5173>. The dashboard displays PAPER mode and demo data until a supported provider is configured.

### Docker

```bash
docker compose up --build
```

SQLite is supported for local work. PostgreSQL is the recommended deployment database; the current core keeps persistence interfaces small so a PostgreSQL migration can be added without changing quantitative calculations.

## Modes

| Mode | Behavior |
| --- | --- |
| ANALYSIS | Calculations and candidates only. No simulated or live orders. |
| PAPER | Simulated fills, positions, P&L, risk, and audit records. Default. |
| LIVE | Disabled by default. Requires verified broker support, risk checks, reconciliation, preview, and fresh human approval. |

## Safety boundary

The strategy layer cannot submit orders. Any live order must pass:

1. deterministic risk and data-freshness checks;
2. an immutable trade-ticket hash;
3. a short-lived single-use approval token created by the user interface;
4. broker preview;
5. a separate final user confirmation.

There is no `autotrade-live` command, no scheduler path to live submission, and no browser automation for brokerage actions.

## Documentation

Start with:

- [Robinhood capability report](docs/ROBINHOOD_CAPABILITY_REPORT.md)
- [E*TRADE integration](docs/ETRADE_INTEGRATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Quantitative math](docs/QUANTITATIVE_MATH.md)
- [Risk policy](docs/RISK_POLICY.md)
- [Backtesting methodology](docs/BACKTESTING_METHODOLOGY.md)
- [Paper trading guide](docs/PAPER_TRADING_GUIDE.md)
- [Live trading checklist](docs/LIVE_TRADING_CHECKLIST.md)

## Test and quality checks

```bash
uv run pytest
uv run ruff check .
uv run mypy quant compliance brokers data backtest paper apps/api
(cd apps/web && npm run build)
python scripts/secret_scan.py
```

No broker credentials are needed for CI. Never commit `.env`, OAuth tokens, account identifiers, or private keys.

## Disclaimer

Options involve substantial risk and are not appropriate for all investors. This software is educational and research software, not investment, tax, or legal advice. It does not guarantee profitability, execution, data accuracy, or suitability. Use it only with accounts and permissions you are authorized to access.
