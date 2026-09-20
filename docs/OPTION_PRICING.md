# Option pricing

The production benchmark is Black-Scholes-Merton with continuous dividend yield. It is used for transparent European-style comparisons, IV inversion, and analytic Greeks. American equity-option research uses a Cox-Ross-Rubinstein tree with early exercise at each node. Tree convergence should be checked by increasing `steps`; it is not a guarantee of vendor mark agreement.

Market price selection is explicit: an entry debit uses the long-leg ask and short-leg bid in the bull-call research constructor, so a midpoint-only result is not silently treated as executable. The data model preserves bid, ask, midpoint, timestamp, source, multiplier, and vendor Greeks.

The pricing library rejects non-positive spot/strike, negative time/volatility, impossible option prices, and zero-time IV requests without intrinsic-value equality. The caller must record the risk-free rate, dividend assumption, exercise style, and quote timestamp.

The model does not capture jumps, stochastic volatility, discrete dividends, borrow constraints, market impact, assignment probability, or a time-varying volatility surface. Use the output as a benchmark and scenario input, not as an assertion that a market is mispriced.
