# Volatility models

Implemented estimators:

- close-to-close volatility from log returns;
- rolling volatility with an explicit window and annualization factor;
- EWMA volatility with a configurable decay;
- Parkinson high/low volatility;
- Garman-Klass OHLC volatility;
- expected move, IV rank, and IV percentile.

The provider contract can supply an IV surface keyed by strike, log-moneyness, and maturity. Surface work must preserve whether a value is observed or interpolated; extrapolation outside reliable data is a flagged condition. Put skew, call skew, smile, smirk, term structure, and IV-minus-forecast-RV are analytics, not automatic signals.

GARCH(1,1), stochastic volatility, jumps, and Heston are extension points, not enabled production signals in this MVP. If added, each model must report convergence, fitted period, parameters, calibration error, out-of-sample performance, and failure state. A failed fit must disable the forecast.

The sign convention used for volatility risk premium is `IV - forecast realized volatility`. High IV does not mean “sell”; event risk, skew, liquidity, early exercise, tail risk, and forecast error are required context.
