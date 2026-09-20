# Bayesian models

The platform uses structured numerical evidence. Strategy code may pass returns, realized volatility, IV changes, event flags, or observed outcomes, but no free-text model opinion can become a probability.

For a binary hypothesis, the update is:

`P(H|D) = P(D|H) P(H) / P(D)`.

For binary strategy outcomes, a Beta prior is conjugate:

`p ~ Beta(alpha,beta)` and `p | data ~ Beta(alpha+w,beta+l)`.

The prior and posterior parameters, sample size, credible interval, data timestamp, and model version are persisted with a forecast. For example, a Beta(2,2) prior plus eight wins and two losses produces Beta(10,4), with mean 71.43%, not the raw 80%.

Win probability is not sufficient for an options strategy: payout asymmetry, fees, spread, slippage, and tail losses determine expectancy. The dashboard should show posterior uncertainty and the probability that expectancy exceeds zero when enough trade-level data exists.
