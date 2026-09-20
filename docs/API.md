# API

The local FastAPI application exposes:

| Route | Purpose |
| --- | --- |
| `GET /health` | Application status, mode, and live flag. |
| `GET /health/etrade` | Non-ordering E*TRADE connection status. |
| `GET /api/capabilities` | Explicit broker/mode capabilities. |
| `GET /api/dashboard` | Runtime paper-account dashboard; market-data fields remain empty until a provider is configured. |
| `GET /api/system/status` | Non-secret runtime and broker capability status. |
| `GET /api/settings/public` | Non-secret configuration for the workspace UI. |
| `GET /api/data/status` | Market-data provider configuration and freshness status. |
| `GET /api/connections` | Non-secret E*TRADE and Robinhood capability/connection status. |
| `POST /api/connections/etrade/start` | Start documented E*TRADE OAuth; returns only a short-lived authorization URL and connection ID. |
| `POST /api/connections/etrade/complete` | Exchange a user-supplied E*TRADE verifier for an in-process access session. |
| `POST /api/connections/etrade/disconnect` | Clear the local E*TRADE session and attempt documented token revocation. |
| `GET /api/connections/etrade/accounts` | Verify the connected E*TRADE account surface and return masked account identifiers. |
| `GET /api/market/quote` | Authorized-provider quote lookup; unavailable when no provider is configured. |
| `GET /api/market/option-chain` | Authorized-provider option-chain lookup; unavailable when no provider is configured. |
| `GET /api/market/expirations` | Authorized-provider expiration discovery for a symbol. |
| `GET /api/scanner` | Data-backed scanner surface; returns no candidates when required inputs are unavailable. |
| `GET /api/paper/orders` | Current internal paper-order records. |
| `GET /api/risk` | Current deterministic risk limits and paper-account utilization. |
| `GET /api/journal` | Current paper-order journal. |
| `GET /api/backtests` | Validated historical dataset catalog, date presets, and current-session backtest runs. |
| `POST /api/backtests/datasets/import` | Validate and import a point-in-time option quote CSV into the configured local data directory. |
| `POST /api/backtests/run` | Run a point-in-time event backtest over a preset or custom date range with explicit fill/cost assumptions. |
| `GET /api/math/demo` | Deterministic pricing, Greeks, IV, EV/simulation, Bayesian, and XYZ validation payload. |
| `GET /api/paper/portfolio` | Current internal paper cash/equity/positions. |
| `POST /api/paper/orders` | Submit a validated paper order; client order IDs are idempotent. |
| `POST /api/live/approval` | Approval-token issuance; fail-closed with 403 until production broker support and an authenticated approval UI are configured. |
| `GET /api/paper/emergency-stop` | Current internal paper emergency-stop state. |
| `POST /api/paper/emergency-stop` | Enable or disable the internal paper emergency stop; it blocks new simulated orders. |

OpenAPI is available from FastAPI at `/docs` locally. The live order adapter intentionally is not exposed as a generic public endpoint; a production UI would implement preview and final-confirmation actions over authenticated server-side routes.
