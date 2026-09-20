# Known limitations

- Robinhood options live trading is disabled: no official public brokerage-options API covering the required chain/quote/order capabilities was verified.
- E*TRADE public docs were sufficient to document the OAuth/market/account/order surface, but production credentials, account approval, market-data entitlements, and current account permissions were not available in this workspace.
- E*TRADE sandbox responses are not a realistic paper market. The internal paper broker is the correct research fill path.
- No point-in-time historical option-chain vendor dataset is bundled, so no serious options backtest or profitability conclusion is claimed.
- The Backtests page currently runs a selected-contract quote-bar harness (hold or moving-average baseline); it does not yet implement a full multi-contract chain replay, assignment/exercise event model, or durable experiment registry.
- OAuth connection state is in-process only for local use. Restarting the API clears the session; production requires an encrypted secret store and authenticated UI.
- Persistence/audit storage is still MVP-level in-memory for paper/approval state; production must add durable encrypted storage and migrations.
- The dashboard has no authenticated live-approval workflow yet. The live approval API is deliberately fail-closed, so E*TRADE live execution is not enabled by default or by the shipped UI.
- The dashboard uses truthful empty states when no provider is configured. Synthetic data exists only in explicit unit-test and math-validation surfaces.
- GARCH, Heston, event calendars, multi-leg paper execution, assignment/exercise lifecycle, portfolio covariance, calibration plots, and full walk-forward orchestration are interfaces/roadmap items rather than completed production features.
- Quotes, Greeks, and fills are not guaranteed accurate or executable. This software is not financial advice and does not guarantee profitability.
