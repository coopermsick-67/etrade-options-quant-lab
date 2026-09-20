# Stochastic models

The baseline scenario process is geometric Brownian motion, `dS = mu*S*dt + sigma*S*dW`, with vectorized terminal simulation. A standardized Student-t return shock model is available for sensitivity to heavier tails. Seeds are recorded for reproducibility.

The continuous-time foundation is Ito's lemma. If `V=V(S,t)` and `dS=mu*S*dt+sigma*S*dW`, then:

`dV = (V_t + mu*S*V_S + 0.5*sigma^2*S^2*V_SS)dt + sigma*S*V_S*dW`.

The Black-Scholes PDE replaces the physical drift through delta hedging and no-arbitrage:

`V_t + 0.5*sigma^2*S^2*V_SS + r*S*V_S - r*V = 0`.

Real markets have jumps, stochastic volatility, discrete events, liquidity constraints, and non-normal returns. Simulation results are therefore scenario distributions under stated assumptions, not forecasts with guaranteed coverage. Heston and jump-diffusion interfaces are intentionally deferred until simpler models are validated.
