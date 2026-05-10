"""Tests for LLM adapter module."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx

from duq_safety_svc.config import Settings
from duq_safety_svc.llm_adapter import LLMAdapter, LLMAdapterError


class TestLLMAdapter:
    """Tests for LLMAdapter class."""

    @pytest.fixture
    def adapter_anthropic(self) -> LLMAdapter:
        """Create adapter with Anthropic configured."""
        settings = Settings(
            anthropic_api_key="test-anthropic-key",
            openrouter_api_key=None,
            llm_default_provider="anthropic",
        )
        return LLMAdapter(settings)

    @pytest.fixture
    def adapter_openrouter(self) -> LLMAdapter:
        """Create adapter with OpenRouter configured."""
        settings = Settings(
            anthropic_api_key=None,
            openrouter_api_key="test-openrouter-key",
            llm_default_provider="openrouter",
        )
        return LLMAdapter(settings)

    @pytest.fixture
    def adapter_both(self) -> LLMAdapter:
        """Create adapter with both providers configured."""
        settings = Settings(
            anthropic_api_key="test-anthropic-key",
            openrouter_api_key="test-openrouter-key",
            llm_default_provider="anthropic",
        )
        return LLMAdapter(settings)

    @pytest.mark.asyncio
    async def test_generate_calls_anthropic(self, adapter_anthropic: LLMAdapter) -> None:
        """Test generate calls Anthropic API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"text": "SAFE: Test response"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter_anthropic._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await adapter_anthropic.generate(
                prompt="Test prompt",
                caller="test",
            )

        assert result == "SAFE: Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "api.anthropic.com" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_generate_calls_openrouter(self, adapter_openrouter: LLMAdapter) -> None:
        """Test generate calls OpenRouter API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SAFE: Test response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter_openrouter._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await adapter_openrouter.generate(
                prompt="Test prompt",
                caller="test",
            )

        assert result == "SAFE: Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "openrouter.ai" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, adapter_both: LLMAdapter) -> None:
        """Test fallback to secondary provider on primary failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SAFE: Fallback response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        async def side_effect(url: str, *args, **kwargs):
            if "anthropic.com" in url:
                raise httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock())
            return mock_response

        with patch.object(adapter_both._client, "post", side_effect=side_effect):
            result = await adapter_both.generate(
                prompt="Test prompt",
                caller="test",
            )

        assert result == "SAFE: Fallback response"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_error(self, adapter_both: LLMAdapter) -> None:
        """Test error raised when all providers fail."""
        with patch.object(
            adapter_both._client,
            "post",
            side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock()),
        ):
            with pytest.raises(LLMAdapterError) as exc_info:
                await adapter_both.generate(prompt="Test", caller="test")

        assert "All LLM providers failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_anthropic_model_prefix_stripped(self, adapter_anthropic: LLMAdapter) -> None:
        """Test anthropic/ prefix is stripped for Anthropic API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "OK"}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter_anthropic._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await adapter_anthropic.generate(
                prompt="Test",
                caller="test",
                model="anthropic/claude-3-haiku",
            )

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "claude-3-haiku"

    @pytest.mark.asyncio
    async def test_openrouter_model_prefix_added(self, adapter_openrouter: LLMAdapter) -> None:
        """Test anthropic/ prefix is added for OpenRouter API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter_openrouter._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await adapter_openrouter.generate(
                prompt="Test",
                caller="test",
                model="claude-3-haiku",
            )

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "anthropic/claude-3-haiku"

    @pytest.mark.asyncio
    async def test_close_closes_client(self, adapter_anthropic: LLMAdapter) -> None:
        """Test close method closes HTTP client."""
        with patch.object(adapter_anthropic._client, "aclose", new_callable=AsyncMock) as mock_close:
            await adapter_anthropic.close()
        mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_provider_raises_error(self) -> None:
        """Test error raised when no provider is configured."""
        settings = Settings(
            anthropic_api_key=None,
            openrouter_api_key=None,
            llm_default_provider="anthropic",
        )
        adapter = LLMAdapter(settings)

        with pytest.raises(LLMAdapterError):
            await adapter.generate(prompt="Test", caller="test")
