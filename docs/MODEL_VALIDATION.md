# Model validation

Validation is layered:

1. Unit and property tests check identities, bounds, monotonicity, finite-difference Greeks, and reproducibility.
2. Backtests use time-aware splits and realistic fills.
3. Out-of-sample tests remain untouched during model selection.
4. Paper trading compares expected price, simulated fill, spread, slippage, and realized outcomes.
5. Calibration is checked with reliability diagrams, Brier score, log loss, and calibration error.

The research qualification gate is intentionally configurable and should start with at least 500 backtest trades, 150 out-of-sample trades, 100 paper trades, profit factor above 1.30, positive net expectancy after fees, maximum drawdown below 10%, Sharpe above 1.0, no single trade generating more than 10% of total historical profit, positive realistic-fill performance, and more than one market regime. These are screening thresholds, not evidence of future profitability.

Material divergence between paper/live observations and validated expectations flags or disables a model. The system should prefer a simpler model when out-of-sample performance is statistically indistinguishable from a complex one.
