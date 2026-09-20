# etrade-options-quant-lab

`etrade-options-quant-lab` is a research-first options platform for deterministic pricing, volatility analysis, probabilistic scenario modeling, backtesting, paper trading, and carefully gated broker integration.

It is designed to answer **“Do I actually have a repeatable options-trading edge?”**, not to manufacture attractive backtests. No strategy is assumed profitable, and a positive backtest is never treated as proof of future performance.

## Current status

- Analysis and PAPER modes are implemented and enabled by default.
- LIVE mode is disabled by default.
- The quantitative core includes Black-Scholes-Merton, American CRR pricing, Greeks, IV inversion, volatility estimators, Bayesian updating, Monte Carlo, payoff math, risk sizing, portfolio Greeks, and performance metrics.
- E*TRADE integration is adapter-based and uses the documented OAuth 1.0a lifecycle plus REST account/market/order endpoints. The live adapter is additionally gated by a single-use, short-lived human approval token; the shipped API keeps live approval UI disabled until authenticated review is implemented.
- The Connections page now provides a server-side E*TRADE OAuth handoff, masked account verification, expiration discovery, and a truthful Robinhood capability boundary. OAuth access secrets remain in the API process and are never returned to the browser.
- Robinhood live options trading is disabled because no official public brokerage-options API was verified in the current official developer documentation. Unofficial endpoints and browser automation are intentionally excluded.
- The UI launches in PAPER mode without broker credentials, but it does not fabricate quotes, candidates, or performance. Without a configured provider it shows explicit empty states.
- The Backtests page accepts validated point-in-time option-quote CSVs and supports full-range, 30-day, 3-month, 6-month, 1-year, 3-year, and custom windows. It does not download or fabricate historical option data.

This is an implemented research MVP with explicit follow-on boundaries. It does not bundle point-in-time historical option chains, claim a trading edge, or present demo results as live performance.

## Run locally

### Backend

Using `uv` (recommended):

```bash
uv venv
uv pip install -e '.[dev]'
cp .env.example .env
uv run uvicorn apps.api.main:app --reload --port 8000
uv run python -m scripts.demo_validation
```

Using only Python and `pip`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
python -m apps.api.main
```

The final command is a real server entrypoint; `python -m apps.api.main` is not
equivalent to merely importing the module. If you use a system Python without
installing the project dependencies, FastAPI will not be available.

Windows PowerShell:

```powershell
uv venv
uv pip install -e '.[dev]'
Copy-Item .env.example .env
uv run uvicorn apps.api.main:app --reload --port 8000
```

PowerShell without `uv`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
Copy-Item .env.example .env
python -m apps.api.main
```

### Dashboard

```bash
# terminal 1, from the repository root
uv run uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

# terminal 2, from the repository root
npm --prefix apps/web ci
npm --prefix apps/web run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. Running `npm run dev` by itself only starts Vite; the proxy errors with `ECONNREFUSED 127.0.0.1:8000` when the FastAPI process is not also running. The dashboard displays PAPER mode with truthful empty states until a supported provider is configured.

For a single Linux/macOS command that starts both processes, use:

```bash
./scripts/dev.sh
```

### Docker

```bash
docker compose up --build
```

The Compose stack uses safe no-provider defaults and does not require a `.env`
file to start. Add a local `.env` only when overriding configuration; never
commit it.

SQLite is supported for local work. PostgreSQL is the recommended deployment database; the current core keeps persistence interfaces small so a PostgreSQL migration can be added without changing quantitative calculations.

## Modes

| Mode | Behavior |
| --- | --- |
| ANALYSIS | Calculations and candidates only. No simulated or live orders. |
| PAPER | Simulated fills, positions, P&L, risk, and audit records. Default. |
| LIVE | Disabled by default. Requires verified broker support, risk checks, reconciliation, preview, and fresh human approval. |

## Safety boundary

The strategy layer cannot submit orders. Any future live order must pass:

1. deterministic risk and data-freshness checks;
2. an immutable trade-ticket hash;
3. a short-lived single-use approval token created by an authenticated user interface (the current API intentionally returns 403 because that UI is not enabled);
4. broker preview;
5. a separate final user confirmation.

There is no `autotrade-live` command, no scheduler path to live submission, and no browser automation for brokerage actions.

## Documentation

Start with:

- [Robinhood capability report](docs/ROBINHOOD_CAPABILITY_REPORT.md)
- [E*TRADE integration](docs/ETRADE_INTEGRATION.md)
- [Broker connections](docs/ETRADE_INTEGRATION.md#local-connection-workflow)
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
uv run mypy quant compliance brokers data backtest paper apps/api tests
uv run python -m compileall -q apps backtest brokers compliance data quant strategies tests
(cd apps/web && npm run build)
python scripts/secret_scan.py --history
```

No broker credentials are needed for CI. Never commit `.env`, OAuth tokens, account identifiers, or private keys.

## Disclaimer

Options involve substantial risk and are not appropriate for all investors. This software is educational and research software, not investment, tax, or legal advice. It does not guarantee profitability, execution, data accuracy, or suitability. Use it only with accounts and permissions you are authorized to access.
