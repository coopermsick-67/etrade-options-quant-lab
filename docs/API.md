# API

The local FastAPI application exposes:

| Route | Purpose |
| --- | --- |
| `GET /health` | Application status, mode, and live flag. |
| `GET /health/etrade` | Non-ordering E*TRADE connection status. |
| `GET /api/capabilities` | Explicit broker/mode capabilities. |
| `GET /api/dashboard` | Demo/research dashboard payload. |
| `GET /api/math/demo` | Deterministic pricing, Greeks, IV, EV/simulation, Bayesian, and XYZ validation payload. |
| `GET /api/paper/portfolio` | Current internal paper cash/equity/positions. |
| `POST /api/paper/orders` | Submit a validated paper order; client order IDs are idempotent. |
| `POST /api/live/approval` | Approval-token issuance; fail-closed with 403 until production broker support and an authenticated approval UI are configured. |
| `GET /api/paper/emergency-stop` | Current internal paper emergency-stop state. |
| `POST /api/paper/emergency-stop` | Enable or disable the internal paper emergency stop; it blocks new simulated orders. |

OpenAPI is available from FastAPI at `/docs` locally. The live order adapter intentionally is not exposed as a generic public endpoint; a production UI would implement preview and final-confirmation actions over authenticated server-side routes.
