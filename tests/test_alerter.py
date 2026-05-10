"""Tests for alerter module."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from duq_agent_core import SafetyLevel

from duq_safety_svc.config import Settings
from duq_safety_svc.alerter import (
    WebhookAlerter,
    LogOnlyAlerter,
    create_alerter,
)


class TestLogOnlyAlerter:
    """Tests for LogOnlyAlerter class."""

    @pytest.mark.asyncio
    async def test_send_alert_logs_critical(self) -> None:
        """Test critical alerts are logged."""
        alerter = LogOnlyAlerter()

        with patch("duq_safety_svc.alerter.logger") as mock_logger:
            await alerter.send_alert(
                message="Test critical alert",
                level=SafetyLevel.CRITICAL,
                agent_name="test-agent",
            )

        mock_logger.critical.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_logs_blocked(self) -> None:
        """Test blocked alerts are logged as warning."""
        alerter = LogOnlyAlerter()

        with patch("duq_safety_svc.alerter.logger") as mock_logger:
            await alerter.send_alert(
                message="Test blocked alert",
                level=SafetyLevel.BLOCKED,
                agent_name="test-agent",
            )

        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_logs_warning(self) -> None:
        """Test warning alerts are logged as info."""
        alerter = LogOnlyAlerter()

        with patch("duq_safety_svc.alerter.logger") as mock_logger:
            await alerter.send_alert(
                message="Test warning alert",
                level=SafetyLevel.WARNING,
                agent_name="test-agent",
            )

        mock_logger.info.assert_called_once()


class TestWebhookAlerter:
    """Tests for WebhookAlerter class."""

    @pytest.fixture
    def alerter(self) -> WebhookAlerter:
        """Create webhook alerter."""
        settings = Settings(
            alert_webhook_url="https://hooks.slack.com/test",
        )
        return WebhookAlerter(settings)

    @pytest.mark.asyncio
    async def test_send_critical_sends_webhook(self, alerter: WebhookAlerter) -> None:
        """Test critical alerts send webhook."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(alerter._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await alerter.send_alert(
                message="Critical alert",
                level=SafetyLevel.CRITICAL,
                agent_name="test-agent",
            )

        mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_critical_does_not_send_webhook(self, alerter: WebhookAlerter) -> None:
        """Test non-critical alerts don't send webhook."""
        with patch.object(alerter._client, "post", new_callable=AsyncMock) as mock_post:
            await alerter.send_alert(
                message="Warning alert",
                level=SafetyLevel.WARNING,
                agent_name="test-agent",
            )

        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_failure_is_handled(self, alerter: WebhookAlerter) -> None:
        """Test webhook failure doesn't raise exception."""
        with patch.object(
            alerter._client,
            "post",
            side_effect=Exception("Webhook failed"),
        ):
            # Should not raise
            await alerter.send_alert(
                message="Critical alert",
                level=SafetyLevel.CRITICAL,
                agent_name="test-agent",
            )

    @pytest.mark.asyncio
    async def test_slack_webhook_format(self, alerter: WebhookAlerter) -> None:
        """Test Slack webhook uses correct format."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(alerter._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await alerter.send_alert(
                message="Test alert",
                level=SafetyLevel.CRITICAL,
                agent_name="test-agent",
            )

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert "text" in payload
        assert "username" in payload  # Slack format

    @pytest.mark.asyncio
    async def test_close_closes_client(self, alerter: WebhookAlerter) -> None:
        """Test close method closes HTTP client."""
        with patch.object(alerter._client, "aclose", new_callable=AsyncMock) as mock_close:
            await alerter.close()
        mock_close.assert_called_once()


class TestCreateAlerter:
    """Tests for create_alerter function."""

    def test_creates_webhook_alerter_with_url(self) -> None:
        """Test creates WebhookAlerter when URL configured."""
        settings = Settings(
            alert_webhook_url="https://example.com/webhook",
        )
        alerter = create_alerter(settings)
        assert isinstance(alerter, WebhookAlerter)

    def test_creates_log_only_alerter_without_url(self) -> None:
        """Test creates LogOnlyAlerter when no URL configured."""
        settings = Settings(
            alert_webhook_url=None,
        )
        alerter = create_alerter(settings)
        assert isinstance(alerter, LogOnlyAlerter)
