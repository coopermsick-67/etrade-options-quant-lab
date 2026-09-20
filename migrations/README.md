# Database migrations

The local MVP is intentionally runnable without a database server. PostgreSQL is the deployment target; migrations should be added before exposing durable multi-user or production trading state. The persistence contract is described in `docs/ARCHITECTURE.md` and must preserve raw data, normalized snapshots, candidates, tickets, approvals, orders, fills, positions, experiments, risk snapshots, model versions, and audit events.
