"""Validated application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    trading_mode: str = "paper"
    live_trading_enabled: bool = False
    live_approval_ui_enabled: bool = False
    database_url: str = "sqlite:///./data/quantlab.db"
    app_secret_key: str = "local-development-secret-change-me"
    approval_token_secret: str = "local-development-approval-secret-change-me-32"
    etrade_env: str = "sandbox"
    etrade_consumer_key: str = ""
    etrade_consumer_secret: str = ""
    etrade_access_token: str = ""
    etrade_access_token_secret: str = ""
    etrade_account_id_key: str = ""
    # ``none`` is deliberate: the application must never manufacture market data
    # for the operational UI. Configure ``etrade`` only after the OAuth tokens
    # and account permissions have been obtained through the documented flow.
    market_data_provider: str = "none"
    quote_stale_seconds: float = Field(default=120, gt=0)
    paper_initial_equity: float = Field(default=10_000, gt=0)
    paper_slippage_bps: float = Field(default=15, ge=0)
    paper_latency_ms: int = Field(default=250, ge=0)
    paper_partial_fill_rate: float = Field(default=0, ge=0, le=1)
    paper_fee_per_contract: float = Field(default=0.65, ge=0)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    risk_per_trade_pct: float = Field(default=0.005, gt=0, le=0.02)
    max_open_risk_pct: float = Field(default=0.08, gt=0, le=1)
    daily_loss_limit_pct: float = Field(default=0.03, gt=0, le=1)
    weekly_loss_limit_pct: float = Field(default=0.05, gt=0, le=1)
    max_drawdown_pct: float = Field(default=0.10, gt=0, le=1)

    @field_validator("trading_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in {"analysis", "paper", "live"}:
            raise ValueError("trading_mode must be analysis, paper, or live")
        return value

    @field_validator("etrade_env")
    @classmethod
    def validate_etrade_env(cls, value: str) -> str:
        if value not in {"sandbox", "production"}:
            raise ValueError("etrade_env must be sandbox or production")
        return value

    @field_validator("market_data_provider")
    @classmethod
    def validate_market_data_provider(cls, value: str) -> str:
        if value not in {"none", "etrade"}:
            raise ValueError("market_data_provider must be none or etrade")
        return value

    @field_validator("live_approval_ui_enabled")
    @classmethod
    def reject_unimplemented_live_ui(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "LIVE_APPROVAL_UI_ENABLED cannot be enabled until authenticated human review is implemented"
            )
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_live_trading_enabled(self) -> bool:
        """Return whether the application may expose live approval plumbing.

        The explicit setting is intentionally not sufficient.  Live approval remains
        disabled unless the app is in LIVE mode, production credentials/account are
        configured, and an authenticated approval UI has been deliberately enabled.
        """

        placeholder_secrets = {
            "",
            "local-development-secret-change-me",
            "local-development-approval-secret-change-me-32",
            "replace-with-a-long-random-local-secret",
            "replace-with-a-different-long-random-local-secret",
        }
        credentials_ready = all(
            value not in placeholder_secrets
            for value in (
                self.etrade_consumer_key,
                self.etrade_consumer_secret,
                self.etrade_access_token,
                self.etrade_access_token_secret,
                self.etrade_account_id_key,
            )
        )
        return (
            self.live_trading_enabled
            and self.live_approval_ui_enabled
            and self.trading_mode == "live"
            and self.etrade_env == "production"
            and len(self.approval_token_secret) >= 32
            and credentials_ready
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
