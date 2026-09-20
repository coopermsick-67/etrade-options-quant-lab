# Robinhood capability report

**Audit date:** 2026-09-20  
**Scope:** Official, publicly accessible documentation for a brokerage integration that would retrieve equity/options data and submit options orders.

## Result

The platform does **not** implement Robinhood live trading. As of this audit, the official public Robinhood developer documentation I could verify is the Robinhood Crypto API documentation at <https://docs.robinhood.com/>, which currently resolves to <https://docs.robinhood.com/crypto/trading/>. I did not find an official, public brokerage API reference documenting equity option chains, option quotes, Greeks/IV, options order placement, order status, cancellation, or paper trading.

This is a documentation finding, not a claim that Robinhood can never offer such a capability. A future adapter may be enabled only after Robinhood publishes a current, authorized brokerage-options API and its terms explicitly permit the intended use.

## Capability matrix

| Capability | Verified official public brokerage-options API? | App decision |
| --- | --- | --- |
| Equity quotes | Not verified for a public brokerage API | Do not assume |
| Option-chain data | No | Disabled |
| Option quotes | No | Disabled |
| Greeks / IV | No | Disabled |
| Open interest / volume | No | Disabled |
| Single-leg option orders | No | Disabled |
| Multi-leg option orders | No | Disabled |
| Order status / cancellation | No | Disabled |
| Positions / balances / fills | No | Disabled |
| Sandbox / paper trading | No official brokerage sandbox verified | Internal paper broker only |
| Credentials | No username, password, MFA, cookies, or browser tokens accepted | Never collect |

## Prohibited substitutes

The repository does not use private Robinhood endpoints, reverse-engineered mobile traffic, Selenium, Playwright, CAPTCHA bypasses, MFA bypasses, session cookies, or unofficial login libraries to place trades. The Robinhood adapter raises a typed `BrokerCapabilityError` with a link back to this report.

## Recommended fallback

Use the internal `PaperBroker` with imported CSV/Parquet option-chain data for research. For an authorized broker integration, use the documented E*TRADE adapter described in [ETRADE_INTEGRATION.md](ETRADE_INTEGRATION.md), subject to current account permissions and agreements.

## Sources

- [Robinhood official developer documentation](https://docs.robinhood.com/)
- [Robinhood crypto trading API documentation](https://docs.robinhood.com/crypto/trading/)
- [Robinhood official learning center](https://learn.robinhood.com/)

