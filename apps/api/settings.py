"""Validated application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    trading_mode: str = "paper"
    live_trading_enabled: bool = False
    database_url: str = "sqlite:///./data/quantlab.db"
    app_secret_key: str = "local-development-secret-change-me"
    approval_token_secret: str = "local-development-approval-secret-change-me-32"
    etrade_env: str = "sandbox"
    etrade_consumer_key: str = ""
    etrade_consumer_secret: str = ""
    etrade_access_token: str = ""
    etrade_access_token_secret: str = ""
    etrade_account_id_key: str = ""
    market_data_provider: str = "mock"
    quote_stale_seconds: float = Field(default=120, gt=0)
    paper_initial_equity: float = Field(default=10_000, gt=0)
    paper_slippage_bps: float = Field(default=15, ge=0)
    paper_latency_ms: int = Field(default=250, ge=0)
    paper_partial_fill_rate: float = Field(default=0, ge=0, le=1)

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
