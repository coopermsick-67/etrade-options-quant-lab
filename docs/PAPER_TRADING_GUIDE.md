# Paper trading guide

Paper mode is the default. It uses the internal broker, not the E*TRADE sandbox, because a broker sandbox is an integration/request-validation environment and should not be treated as a realistic fill simulator.

Paper fills use bid/ask, configurable slippage, latency configuration, optional partial fills, fees, limit-order rules, cash, positions, realized/unrealized marks, and idempotent client order IDs. Paper P&L is labelled separately from live P&L and has a data-delay/source indicator.

Start the API and dashboard without credentials. Confirm `PAPER` and `DEMO MODE`, run the math demo, inspect a candidate, place a small simulated order, and verify the journal/portfolio response. Do not infer live execution quality from a paper midpoint fill; compare paper fills with the contemporaneous quote and report spread/slippage differences.
