"""Hard deterministic pre-trade controls and conservative sizing."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor, isfinite


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
            self.daily_warning_pct,
            self.daily_hard_stop_pct,
            self.weekly_warning_pct,
            self.weekly_hard_stop_pct,
            self.drawdown_warning_pct,
            self.drawdown_hard_stop_pct,
        )
        if any(not isfinite(value) or value < 0 for value in numeric):
            raise ValueError("risk percentages cannot be negative")
        if self.risk_per_trade_pct > self.absolute_max_risk_per_trade_pct:
            raise ValueError("target risk cannot exceed absolute risk limit")
        if self.normal_max_risk_per_trade_pct > self.absolute_max_risk_per_trade_pct:
            raise ValueError("normal risk cannot exceed absolute risk limit")
        if self.daily_warning_pct > self.daily_hard_stop_pct:
            raise ValueError("daily warning cannot exceed daily hard stop")
        if self.weekly_warning_pct > self.weekly_hard_stop_pct:
            raise ValueError("weekly warning cannot exceed weekly hard stop")
        if self.drawdown_warning_pct > self.drawdown_hard_stop_pct:
            raise ValueError("drawdown warning cannot exceed drawdown hard stop")
        if self.max_concurrent_positions < 1:
            raise ValueError("maximum concurrent positions must be positive")
        if not 0 < self.max_spread_pct <= 1 or self.min_volume < 0 or self.min_open_interest < 0:
            raise ValueError("liquidity limits are invalid")


@dataclass(frozen=True)
class RiskCheck:
    passed: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def fixed_risk_contracts(
    account_equity: float, risk_pct: float, max_loss_per_contract: float
) -> int:
    if (
        not all(isfinite(value) for value in (account_equity, risk_pct, max_loss_per_contract))
        or account_equity <= 0
        or risk_pct < 0
        or max_loss_per_contract <= 0
    ):
        raise ValueError("invalid position sizing inputs")
    return max(0, floor(account_equity * risk_pct / max_loss_per_contract))


def fractional_kelly(win_probability: float, reward_risk: float, fraction: float = 0.25) -> float:
    if (
        not all(isfinite(value) for value in (win_probability, reward_risk, fraction))
        or not 0 <= win_probability <= 1
        or reward_risk <= 0
        or not 0 <= fraction <= 1
    ):
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
    if not isfinite(account_equity) or account_equity <= 0:
        reasons.append("account equity must be positive")
    if not isfinite(max_loss_per_contract) or max_loss_per_contract <= 0:
        reasons.append("maximum loss per contract must be positive")
    if not isfinite(total_open_risk) or total_open_risk < 0:
        reasons.append("total open risk must be non-negative")
    if not isfinite(spread_pct) or spread_pct < 0:
        reasons.append("spread percentage must be non-negative")
    if not isfinite(quote_age_seconds) or quote_age_seconds < 0:
        reasons.append("quote age must be non-negative")
    if not isfinite(stale_seconds) or stale_seconds <= 0:
        reasons.append("stale threshold must be positive")
    if not isfinite(daily_loss_pct) or daily_loss_pct < 0:
        reasons.append("daily loss must be non-negative")
    if not isfinite(weekly_loss_pct) or weekly_loss_pct < 0:
        reasons.append("weekly loss must be non-negative")
    if volume < 0:
        reasons.append("volume must be non-negative")
    if open_interest < 0:
        reasons.append("open interest must be non-negative")
    if current_positions < 0:
        reasons.append("current positions must be non-negative")
    if emergency_stop:
        reasons.append("emergency stop is active")
    if contracts < 1:
        reasons.append("contracts must be positive")
    planned_risk = max_loss_per_contract * contracts if max_loss_per_contract > 0 else float("inf")
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
