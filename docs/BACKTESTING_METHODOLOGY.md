# Backtesting methodology

## Local backtest workflow

The dashboard's **Backtests** page now supports a real file-backed workflow. It
accepts a validated CSV upload, lets the researcher select the full available
range, 30 days, 3/6 months, 1/3 years, or explicit start/end dates, and records
the fill model and cost assumptions with each run. There is no built-in market
sample and no generated option quote fallback.

The minimum CSV schema is:

```text
timestamp,close,option_mid,option_bid,option_ask
```

`symbol` and `multiplier` are optional. Timestamps must be timezone-aware ISO
8601 values. Every row is a point-in-time observation for one selected option
contract; a serious historical options dataset should also preserve the
contract identity, expiration, strike, type, volume, open interest, source,
and data-quality flags. The API rejects incomplete rows, duplicate timestamps,
crossed markets, invalid prices, and timezone-naive timestamps.

The current UI runs two explicit research baselines: a buy-and-hold selected
contract and a moving-average signal over the underlying close. These are
validation harnesses, not claimed trading strategies. The run history is held
in the API process for the current session; a durable experiment registry and
database persistence remain deployment work.

The event loop gives a strategy only `bars[:index+1]` at each timestamp. Entry and exit fills use optimistic, realistic, or conservative bid/ask models plus configurable slippage and per-contract fees. A signal that relies on future chain rows is a defect, not an edge.

Serious options validation requires point-in-time historical chains containing quote timestamp, underlying price, expiration, strike, type, bid, ask, volume, open interest, IV/Greeks or enough inputs to recompute them, source, and data-quality status. The current mock provider is only for deterministic development; it is not historical evidence. A live E*TRADE chain is not a historical dataset and must not be used as if it were one.

Production research should separate training, validation, and untouched test periods; use walk-forward expanding or rolling windows; purge/embargo overlapping samples; preserve dataset hashes and Git SHA; and report realistic, conservative, and optimistic fills. Bootstrap trade returns and reshuffled sequences to quantify luck. Multiple experiments must be registered rather than cherry-picking the best run. The repository's synthetic provider is a unit-test fixture only and cannot supply historical evidence.

Required reporting includes after-fee P&L, slippage sensitivity, spread cost, exposure, turnover, drawdown, profit factor, expectancy, Sharpe, Sortino, CVaR, performance by regime/DTE/delta/underlying, outlier dependency, loss streaks, and uncertainty intervals. A positive in-sample result is never a profitability claim.
