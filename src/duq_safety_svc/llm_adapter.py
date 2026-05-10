"""Lightweight LLM adapter for Safety Service.

Implements LLMRouterProtocol from duq-agent-core without heavy dependencies.
Uses httpx for direct API calls to Anthropic/OpenRouter.

This is a LIGHTWEIGHT adapter - no database logging, no Redis, no tracing.
For full-featured LLM routing, use the main LLMRouter from duq-core.
"""

from __future__ import annotations

import httpx
from loguru import logger

from duq_safety_svc.config import Settings


class LLMAdapterError(Exception):
    """Error from LLM adapter."""

    pass


class LLMAdapter:
    """Lightweight LLM adapter implementing LLMRouterProtocol.

    Supports:
    - Anthropic direct API
    - OpenRouter as fallback (OpenAI-compatible)

    Args:
        settings: Service settings with API keys
    """

    ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(timeout=60.0)

    async def generate(
        self,
        prompt: str,
        caller: str,
        model: str | None = None,
        user_id: int | None = None,
    ) -> str:
        """Generate text using LLM.

        Implements LLMRouterProtocol.generate() interface.

        Args:
            prompt: The prompt to send
            caller: Identifier for tracking (logged but not persisted)
            model: Model to use (default from settings)
            user_id: User ID (logged but not persisted)

        Returns:
            Generated text

        Raises:
            LLMAdapterError: If all providers fail
        """
        model = model or self._settings.llm_safety_model
        provider = self._settings.llm_default_provider

        # Try primary provider
        try:
            if provider == "anthropic" and self._settings.anthropic_api_key:
                return await self._call_anthropic(prompt, model)
            elif provider == "openrouter" and self._settings.openrouter_api_key:
                return await self._call_openrouter(prompt, model)
        except Exception as e:
            logger.warning(f"Primary provider {provider} failed: {e}")

        # Try fallback
        try:
            if provider == "anthropic" and self._settings.openrouter_api_key:
                return await self._call_openrouter(prompt, model)
            elif provider == "openrouter" and self._settings.anthropic_api_key:
                return await self._call_anthropic(prompt, model)
        except Exception as e:
            logger.error(f"Fallback provider also failed: {e}")

        raise LLMAdapterError("All LLM providers failed")

    async def _call_anthropic(self, prompt: str, model: str) -> str:
        """Call Anthropic API directly."""
        if not self._settings.anthropic_api_key:
            raise LLMAdapterError("Anthropic API key not configured")

        # Strip anthropic/ prefix if present
        if model.startswith("anthropic/"):
            model = model[10:]

        headers = {
            "x-api-key": self._settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = await self._client.post(
            self.ANTHROPIC_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data.get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "")
        return ""

    async def _call_openrouter(self, prompt: str, model: str) -> str:
        """Call OpenRouter API (OpenAI-compatible)."""
        if not self._settings.openrouter_api_key:
            raise LLMAdapterError("OpenRouter API key not configured")

        # Add anthropic/ prefix for Claude models
        if not model.startswith("anthropic/") and model.startswith("claude"):
            model = f"anthropic/{model}"

        headers = {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "content-type": "application/json",
            "HTTP-Referer": "https://duq.ai",
            "X-Title": "DUQ Safety Service",
        }

        payload = {
            "model": model,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = await self._client.post(
            self.OPENROUTER_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if choices and len(choices) > 0:
            message = choices[0].get("message", {})
            return message.get("content", "")
        return ""

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()


__all__ = ["LLMAdapter", "LLMAdapterError"]
