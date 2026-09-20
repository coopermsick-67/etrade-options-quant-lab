# Live trading checklist

Live is disabled by default and this repository does not enable unattended execution.

Before a production E*TRADE order can be considered:

- current official documentation and account permissions have been reviewed;
- credentials are present only server-side and the environment is explicitly production;
- quote and risk data are fresh and reconciled;
- the exact ticket is immutable and hashed;
- the ticket includes a canonical SHA-256 hash of the exact broker payload;
- deterministic risk, liquidity, defined-risk, buying-power, and duplicate-order checks pass;
- E*TRADE preview succeeds;
- the user gives a fresh explicit confirmation for that exact ticket;
- the short-lived single-use approval token is consumed once;
- ambiguous submission results are reconciled by status/account state before any retry.

Modification, cancellation, exit, roll, and assignment decisions require a new explicit user instruction. There is no scheduler, LLM, hidden toggle, or `autotrade-live` command that can create approval tokens or submit orders.
