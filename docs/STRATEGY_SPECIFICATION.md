# Strategy specification

The first research strategy is a bull call debit spread. It requires two same-expiration calls, a lower long strike, a higher short strike, a positive executable debit, and model inputs for spot, risk-free rate, IV, forecast volatility, and drift. The candidate exposes legs, debit, maximum loss/profit, break-even, Greeks, probability beyond break-even, gross EV, estimated costs, risk-adjusted EV, and explicit assumptions.

The strategy interface is intentionally order-free: `generate_candidates`, `score_candidate`, `construct_trade`, `calculate_risk`, and `explain` return research objects. The planned modules for long calls, long puts, covered calls, cash-secured puts, bear put spreads, and event research must meet the same contract. Defined-risk structures are the default.

Every candidate must include an entry rule, DTE/strike/liquidity rules, maximum debit or credit, maximum loss, exit target, loss threshold, time exit, thesis invalidation, event restrictions, and expiration/assignment handling. A candidate is not an order and a probability is not a recommendation.

Research promotion stages are IDEA → RESEARCH → BACKTESTED → OUT-OF-SAMPLE → PAPER → LIVE-ELIGIBLE → RETIRED. “Live-eligible” means only that a user may review a ticket; it never grants automatic execution.
