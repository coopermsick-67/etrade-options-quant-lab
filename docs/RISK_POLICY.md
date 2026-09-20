# Risk policy

Capital preservation is the default. The system may produce `PASS — no qualified opportunity` and does not require a daily trade.

The example $10,000 profile is configurable and intentionally conservative:

- target risk per trade: 0.50%;
- normal maximum risk per trade: 1.00%;
- absolute maximum risk per trade: 2.00%;
- maximum open defined risk: 8.00%;
- daily warning/hard stop: 2% / 3%;
- weekly warning/hard stop: 4% / 5%;
- account drawdown warning/hard stop: 7.5% / 10%.

Position size is `floor(risk budget / maximum loss per contract)` and is never rounded up. Fractional Kelly is research-only and cannot override hard limits. Naked calls, naked puts, unlimited-loss positions, 0DTE, martingale sizing, averaging down, and automatic rolling are disabled by default.

Pre-trade checks include defined risk, equity, total open risk, concurrent positions, spread, volume, open interest, quote age, emergency stop, and daily/weekly loss limits. Live checks additionally require production broker state, reconciliation, preview, explicit user approval, and no outstanding safety violation. A risk threshold blocks new live tickets; it does not automatically liquidate an E*TRADE position.

The emergency stop blocks new orders, invalidates approval tokens in a production implementation, and records who/when/why. It preserves positions and requires manual restart.
