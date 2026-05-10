"""Configuration for DUQ Safety Service.

Environment variables:
    SAFETY_HOST: Host to bind to (default: 0.0.0.0)
    SAFETY_PORT: Port to bind to (default: 8083)
    LOG_LEVEL: Logging level (default: INFO)

    # LLM Configuration (for complex safety checks)
    ANTHROPIC_API_KEY: Anthropic API key
    OPENROUTER_API_KEY: OpenRouter API key (fallback)
    LLM_DEFAULT_PROVIDER: Default provider (anthropic/openrouter)
    LLM_SAFETY_MODEL: Model for safety checks (default: claude-haiku-4-5-20251001)
    USE_LLM_FALLBACK: Enable LLM for unmatched rules (default: true)

    # Alerting
    ALERT_WEBHOOK_URL: Webhook URL for critical alerts (optional)
    OWNER_TELEGRAM_ID: Telegram ID for alerts (optional)
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Safety service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = Field(default="0.0.0.0", alias="SAFETY_HOST")
    port: int = Field(default=8083, alias="SAFETY_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # LLM Configuration
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    llm_default_provider: Literal["anthropic", "openrouter"] = Field(
        default="anthropic", alias="LLM_DEFAULT_PROVIDER"
    )
    llm_safety_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="LLM_SAFETY_MODEL"
    )
    use_llm_fallback: bool = Field(default=True, alias="USE_LLM_FALLBACK")

    # Alerting
    alert_webhook_url: str | None = Field(default=None, alias="ALERT_WEBHOOK_URL")
    owner_telegram_id: int | None = Field(default=None, alias="OWNER_TELEGRAM_ID")

    @property
    def has_llm_provider(self) -> bool:
        """Check if any LLM provider is configured."""
        return bool(self.anthropic_api_key or self.openrouter_api_key)


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


__all__ = ["Settings", "get_settings"]
