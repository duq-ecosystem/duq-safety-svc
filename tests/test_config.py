"""Tests for configuration module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from duq_safety_svc.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        # Clear env vars that might affect test
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.host == "0.0.0.0"
        assert settings.port == 8083
        assert settings.log_level == "INFO"
        assert settings.llm_default_provider == "anthropic"
        assert settings.use_llm_fallback is True

    def test_env_override(self) -> None:
        """Test environment variable override."""
        env_vars = {
            "SAFETY_HOST": "127.0.0.1",
            "SAFETY_PORT": "9000",
            "LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.log_level == "DEBUG"

    def test_has_llm_provider_with_anthropic(self) -> None:
        """Test has_llm_provider with Anthropic key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True):
            settings = Settings()
        assert settings.has_llm_provider is True

    def test_has_llm_provider_with_openrouter(self) -> None:
        """Test has_llm_provider with OpenRouter key."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=True):
            settings = Settings()
        assert settings.has_llm_provider is True

    def test_has_llm_provider_without_keys(self) -> None:
        """Test has_llm_provider without any API keys."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        assert settings.has_llm_provider is False

    def test_llm_safety_model_default(self) -> None:
        """Test default LLM safety model."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        assert "claude" in settings.llm_safety_model.lower()

    def test_alert_webhook_url(self) -> None:
        """Test alert webhook URL configuration."""
        webhook = "https://hooks.slack.com/services/test"
        with patch.dict(os.environ, {"ALERT_WEBHOOK_URL": webhook}, clear=True):
            settings = Settings()
        assert settings.alert_webhook_url == webhook


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings_instance(self) -> None:
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
