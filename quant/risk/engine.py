"""Hard deterministic pre-trade controls and conservative sizing."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor


class RiskLimitError(ValueError):
    """Raised when a risk invariant is violated."""


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade_pct: float = 0.005
    normal_max_risk_per_trade_pct: float = 0.01
    absolute_max_risk_per_trade_pct: float = 0.02
    max_total_open_defined_risk_pct: float = 0.08
    daily_warning_pct: float = 0.02
    daily_hard_stop_pct: float = 0.03
    weekly_warning_pct: float = 0.04
    weekly_hard_stop_pct: float = 0.05
    drawdown_warning_pct: float = 0.075
    drawdown_hard_stop_pct: float = 0.10
    max_spread_pct: float = 0.08
    min_volume: int = 1
    min_open_interest: int = 1
    max_concurrent_positions: int = 10

    def __post_init__(self) -> None:
        numeric = (
            self.risk_per_trade_pct,
            self.normal_max_risk_per_trade_pct,
            self.absolute_max_risk_per_trade_pct,
            self.max_total_open_defined_risk_pct,
        )
        if any(value < 0 for value in numeric):
            raise ValueError("risk percentages cannot be negative")
        if self.risk_per_trade_pct > self.absolute_max_risk_per_trade_pct:
            raise ValueError("target risk cannot exceed absolute risk limit")
        if self.normal_max_risk_per_trade_pct > self.absolute_max_risk_per_trade_pct:
            raise ValueError("normal risk cannot exceed absolute risk limit")
        if not 0 < self.max_spread_pct <= 1 or self.min_volume < 0 or self.min_open_interest < 0:
            raise ValueError("liquidity limits are invalid")


@dataclass(frozen=True)
class RiskCheck:
    passed: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def fixed_risk_contracts(
    account_equity: float, risk_pct: float, max_loss_per_contract: float
) -> int:
    if account_equity <= 0 or risk_pct < 0 or max_loss_per_contract <= 0:
        raise ValueError("invalid position sizing inputs")
    return max(0, floor(account_equity * risk_pct / max_loss_per_contract))


def fractional_kelly(win_probability: float, reward_risk: float, fraction: float = 0.25) -> float:
    if not 0 <= win_probability <= 1 or reward_risk <= 0 or not 0 <= fraction <= 1:
        raise ValueError("invalid Kelly inputs")
    q = 1 - win_probability
    full = (reward_risk * win_probability - q) / reward_risk
    return max(0.0, full * fraction)


def pretrade_check(
    *,
    account_equity: float,
    max_loss_per_contract: float,
    contracts: int,
    total_open_risk: float,
    spread_pct: float,
    volume: int,
    open_interest: int,
    quote_age_seconds: float,
    stale_seconds: float,
    current_positions: int,
    limits: RiskLimits,
    daily_loss_pct: float = 0.0,
    weekly_loss_pct: float = 0.0,
    emergency_stop: bool = False,
) -> RiskCheck:
    reasons: list[str] = []
    if emergency_stop:
        reasons.append("emergency stop is active")
    if account_equity <= 0:
        reasons.append("account equity must be positive")
    if contracts < 1:
        reasons.append("contracts must be positive")
    planned_risk = max_loss_per_contract * contracts
    if planned_risk > account_equity * limits.absolute_max_risk_per_trade_pct:
        reasons.append("trade exceeds absolute risk-per-trade limit")
    if total_open_risk + planned_risk > account_equity * limits.max_total_open_defined_risk_pct:
        reasons.append("trade exceeds total open defined-risk limit")
    if spread_pct > limits.max_spread_pct:
        reasons.append("spread exceeds configured maximum")
    if volume < limits.min_volume:
        reasons.append("volume is below configured minimum")
    if open_interest < limits.min_open_interest:
        reasons.append("open interest is below configured minimum")
    if quote_age_seconds > stale_seconds:
        reasons.append("quote is stale")
    if current_positions >= limits.max_concurrent_positions:
        reasons.append("maximum concurrent positions reached")
    if daily_loss_pct >= limits.daily_hard_stop_pct:
        reasons.append("daily hard stop reached")
    if weekly_loss_pct >= limits.weekly_hard_stop_pct:
        reasons.append("weekly hard stop reached")
    return RiskCheck(passed=not reasons, reasons=tuple(reasons))
