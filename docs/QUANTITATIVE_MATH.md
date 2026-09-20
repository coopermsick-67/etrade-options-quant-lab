# Quantitative math

This document states the conventions used by the deterministic library. Prices are per underlying share unless a multiplier is explicitly applied. Volatility and rates are decimals: `0.40` means 40%. Time is years unless a function says DTE.

## Returns and volatility

Arithmetic return is `(P_t - P_(t-1)) / P_(t-1)`. Log return is `ln(P_t / P_(t-1))`. The implementation uses log returns for close-to-close volatility because they add across time. Sample volatility is the sample standard deviation of returns, annualized as `sigma_period * sqrt(periods_per_year)`; daily data uses 252 by default.

The expected-move approximation is `S * IV * sqrt(DTE / 365)`. It is a one-standard-deviation model scale, not a guaranteed range. IV rank uses the min/max history; IV percentile is the fraction of historical observations strictly below current IV. They are different statistics.

## Option value and payoffs

For a long call, expiration profit is `max(S_T - K, 0) - premium`. For a long put it is `max(K - S_T, 0) - premium`. Multiply by the contract multiplier to obtain contract dollars. Call break-even is `K + premium`; put break-even is `K - premium`.

For a call debit spread with `K_short > K_long` and debit `D`, profit is `max(S_T-K_long,0) - max(S_T-K_short,0) - D`. Maximum loss is `D * multiplier`, maximum profit is `(K_short-K_long-D) * multiplier`, and break-even is `K_long + D`. The put debit spread is analogous with the strikes reversed.

Covered calls and cash-secured puts are implemented as explicit expiration payoffs. Unlimited-loss and naked short structures are not enabled by default.

## Black-Scholes-Merton benchmark

For continuous dividend yield `q`,

`d1 = [ln(S/K) + (r-q+sigma^2/2)T] / (sigma*sqrt(T))`

`d2 = d1 - sigma*sqrt(T)`

`C = S*exp(-qT)*N(d1) - K*exp(-rT)*N(d2)`

`P = K*exp(-rT)*N(-d2) - S*exp(-qT)*N(-d1)`.

The benchmark assumes European exercise, continuous carry, frictionless markets, and a constant volatility. U.S. equity options can be American-style and can have early-exercise and discrete-dividend effects; `quant.pricing.american` supplies a CRR tree for research.

## Greeks

The library returns delta, gamma, theta, vega, and rho per share. Theta is the derivative with respect to calendar time (the conventional displayed decay is normally negative). Vega and rho are per unit change in volatility/rate; a one-vol-point change is `vega * 0.01`. Portfolio Greek totals multiply each Greek by signed quantity and contract multiplier. Analytic BSM Greeks are validated against central finite differences in tests.

The local P&L approximation is:

`dV ~= delta*dS + 0.5*gamma*dS^2 + vega*dSigma + theta*dt + rho*dr`.

This is a local approximation, not a replacement for repricing.

## Implied volatility and no-arbitrage

IV solves `model_price(sigma) = executable option price`. The solver checks European no-arbitrage bounds before using Brent's bracketed method and reports convergence, iterations, method, and pricing residual. A failed solve is an error/unknown, never a fabricated IV.

For zero-dividend European calls, `max(0, S-K*exp(-rT)) <= C <= S`. For puts, `max(0, K*exp(-rT)-S) <= P <= K*exp(-rT)`. Put-call parity is a diagnostic when assumptions match; a deviation is not automatically a free arbitrage after costs, borrow, exercise, and data errors.

## Probability, EV, and uncertainty

Under a lognormal model, `ln(S_T)` is normal with mean `ln(S_0)+(mu-sigma^2/2)T` and variance `sigma^2*T`. The probability engine distinguishes real-world drift from risk-neutral pricing assumptions. Delta is not silently treated as probability ITM.

For simulated outcomes, `EV = mean(P&L)`. The trade decision uses a conservative form of `net edge`: modeled payoff minus executable cost, fees, slippage, market-impact allowance, and a model-uncertainty penalty. A positive point estimate alone does not qualify a trade.

## Bayesian updating

The binary strategy model uses `p ~ Beta(alpha,beta)`. After `w` wins and `l` losses, the posterior is `Beta(alpha+w,beta+l)`, with posterior mean `(alpha+w)/(alpha+beta+w+l)` and a credible interval. The general binary Bayes helper updates `P(H)` from numerical likelihoods. Evidence is structured data, not an LLM opinion.

## Portfolio and performance statistics

Portfolio variance is `w^T Sigma w`. Sharpe uses consistent per-period returns and annualization. Sortino uses downside deviation. Maximum drawdown is the minimum of `(equity - running_peak) / running_peak`; it is not a VaR estimate. Profit factor is gross profit divided by absolute gross loss, and expectancy is the mean trade P&L.

## Simulation

The baseline GBM simulator uses `S_(t+dt) = S_t*exp((mu-sigma^2/2)dt + sigma*sqrt(dt)*Z)`. A standardized Student-t shock model is available to stress tail sensitivity. The output records seed, model, number of paths, terminal prices, P&L, percentiles, VaR, and expected shortfall. GBM is a reference model, not a claim about reality.
