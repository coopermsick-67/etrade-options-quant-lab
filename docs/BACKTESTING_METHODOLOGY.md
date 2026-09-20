# Backtesting methodology

The event loop gives a strategy only `bars[:index+1]` at each timestamp. Entry and exit fills use optimistic, realistic, or conservative bid/ask models plus configurable slippage and per-contract fees. A signal that relies on future chain rows is a defect, not an edge.

Serious options validation requires point-in-time historical chains containing quote timestamp, underlying price, expiration, strike, type, bid, ask, volume, open interest, IV/Greeks or enough inputs to recompute them, source, and data-quality status. The current mock provider is only for deterministic development; it is not historical evidence.

Production research should separate training, validation, and untouched test periods; use walk-forward expanding or rolling windows; purge/embargo overlapping samples; preserve dataset hashes and Git SHA; and report realistic, conservative, and optimistic fills. Bootstrap trade returns and reshuffled sequences to quantify luck. Multiple experiments must be registered rather than cherry-picking the best run. The repository's synthetic provider is a unit-test fixture only and cannot supply historical evidence.

Required reporting includes after-fee P&L, slippage sensitivity, spread cost, exposure, turnover, drawdown, profit factor, expectancy, Sharpe, Sortino, CVaR, performance by regime/DTE/delta/underlying, outlier dependency, loss streaks, and uncertainty intervals. A positive in-sample result is never a profitability claim.
