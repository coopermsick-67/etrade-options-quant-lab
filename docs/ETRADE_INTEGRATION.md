# E*TRADE integration audit

**Audit date:** 2026-09-20  
**Sources:** current public E*TRADE Developer Platform documentation and API Developer License Agreement pages reviewed on the audit date.

## Verified capabilities

E*TRADE publicly documents a REST API using OAuth 1.0a. The getting-started guide says a client application can authenticate customers, place/modify/cancel orders and check order status, retrieve balances and positions, and retrieve index, stock, and option information. The public API reference documents:

- OAuth request-token, authorization, access-token, renewal, and revocation flows;
- account listing, balances, transactions, and portfolio endpoints;
- stock and option quotes;
- option chains and expiration dates;
- quote fields including bid, ask, sizes, volume, open interest, option multiplier, OSI key, option style, and vendor-provided Greeks/IV when present;
- order listing, preview, placement, cancellation, and changed-order preview/placement;
- single-option orders and multi-leg spread order examples.

The sandbox is documented as a syntax/deserialization test environment using stored responses. It does not execute real transactions and does not provide current market data. The application therefore uses an internal `PaperBroker` for realistic simulation and treats E*TRADE sandbox as an integration test target, not as a performance simulator.

## Live execution policy in this repository

The public agreement reviewed here does document restrictions around confidentiality, market-data redistribution, API use, security, and E*TRADE’s right to reject orders. The accessible public text did not provide a definitive universal statement about algorithmic order generation. This repository therefore makes the safer product-policy choice required by the project specification: live actions are human-approved only, even if a particular account agreement might permit more automation.

Live submission is disabled unless all of the following hold:

1. `ETRADE_ENV=production`;
2. `LIVE_TRADING_ENABLED=true`;
3. current credentials are present server-side;
4. market data is fresh and account reconciliation is healthy;
5. deterministic risk checks pass;
6. the exact ticket has been previewed;
7. an authenticated UI created a short-lived, single-use approval token for the immutable ticket hash, including the canonical hash of the exact broker payload;
8. the user performs a separate final confirmation.

The shipped FastAPI approval route is intentionally disabled (`LIVE_APPROVAL_UI_ENABLED=false` and no local authentication layer exists). The adapter and guard are therefore mock/integration-testable, but production live execution is not enabled by this repository. No strategy, scheduler, LLM, or background task can create an approval token. There is no unattended live-order path.

## Authentication requirements

The documented workflow uses a consumer key and secret, a temporary request token, user authorization and verifier, then an access token and secret. Requests use OAuth 1.0a with HMAC-SHA1. Tokens may become inactive after two hours of API inactivity and are documented to expire at midnight U.S. Eastern Time by default; the app treats renewal and reauthorization as explicit states rather than guessing.

Separate sandbox and production keys are required. Secrets are server-side environment variables only. The app never asks for an E*TRADE username or password.

The current getting-started page also distinguishes individual and vendor keys,
requires the API agreement for production access, and notes that market-data
access requires the applicable market-data agreement. Those account and
entitlement checks remain operator responsibilities; this repository does not
pretend that sandbox credentials prove production access.

## Environment and endpoints

| Environment | Base URL |
| --- | --- |
| Sandbox | `https://apisb.etrade.com/v1` |
| Production | `https://api.etrade.com/v1` |

The app does not hardcode a rate limit. The reviewed public pages do not state a single universal numeric limit, so the provider uses a conservative configurable client limiter and honors HTTP rate-limit responses if returned.

## Data and order limitations

- Real-time quote access may require the E*TRADE market-data agreement; otherwise data may be delayed.
- The API docs expose option Greeks/IV as response fields, but the app recalculates core values where possible and records provenance and timestamps.
- E*TRADE data is not assumed synchronized with third-party data.
- A successful order submission response is not treated as a fill. Status is reconciled through the order endpoint.
- Order modification and cancellation require separate explicit user actions in the app.
- Actual option approval level, buying power, account restrictions, fee schedules, and supported order types are account-specific and must be verified through the live preview/account response.

## Official sources

- [E*TRADE Developer home](https://developer.etrade.com/home)
- [Getting started](https://developer.etrade.com/getting-started)
- [Developer guides and OAuth lifecycle](https://developer.etrade.com/getting-started/developer-guides)
- [Account API](https://apisb.etrade.com/docs/api/account/api-account-v1.html)
- [Market API and option chains](https://apisb.etrade.com/docs/api/market/api-market-v1.html)
- [Quote API](https://apisb.etrade.com/docs/api/market/api-quote-v1.html)
- [Order API](https://apisb.etrade.com/docs/api/order/api-order-v1.html)
- [API Developer License Agreement](https://us.etrade.com/l/f/agreement-library/api-developer-licensing-agreement)
- [Developer terms of use](https://developer.etrade.com/support/terms-of-use)
