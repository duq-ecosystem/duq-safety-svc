"""Alert sender for critical safety violations.

Implements AlerterProtocol from duq-agent-core.
Supports webhook alerts and logging fallback.
"""

from __future__ import annotations

import httpx
from loguru import logger

from duq_agent_core import AlerterProtocol, SafetyLevel

from duq_safety_svc.config import Settings


class WebhookAlerter:
    """Alert sender using webhooks.

    Implements AlerterProtocol interface.
    Sends alerts to configured webhook URL for critical violations.

    Args:
        settings: Service settings with webhook configuration
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send_alert(
        self,
        message: str,
        level: SafetyLevel,
        agent_name: str,
    ) -> None:
        """Send alert to configured webhook.

        Only sends for CRITICAL level. WARNING and BLOCKED are just logged.

        Args:
            message: Alert message content
            level: Safety level that triggered the alert
            agent_name: Name of the agent that triggered
        """
        # Always log
        log_msg = f"[SAFETY ALERT] agent={agent_name} level={level.value}: {message}"

        if level == SafetyLevel.CRITICAL:
            logger.critical(log_msg)
        elif level == SafetyLevel.BLOCKED:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # Send webhook for critical only
        if level == SafetyLevel.CRITICAL and self._settings.alert_webhook_url:
            await self._send_webhook(message, level, agent_name)

    async def _send_webhook(
        self,
        message: str,
        level: SafetyLevel,
        agent_name: str,
    ) -> None:
        """Send alert to webhook URL."""
        try:
            payload = {
                "text": f"SAFETY ALERT ({level.value})\nAgent: {agent_name}\n{message}",
                "level": level.value,
                "agent": agent_name,
                "service": "duq-safety-svc",
            }

            # Support Slack-style webhooks
            if "slack" in self._settings.alert_webhook_url.lower():
                payload = {
                    "text": payload["text"],
                    "username": "DUQ Safety",
                    "icon_emoji": ":warning:",
                }

            response = await self._client.post(
                self._settings.alert_webhook_url,
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Alert sent to webhook: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()


class LogOnlyAlerter:
    """Alert sender that only logs (no external notifications).

    Implements AlerterProtocol interface.
    Use when no webhook is configured.
    """

    async def send_alert(
        self,
        message: str,
        level: SafetyLevel,
        agent_name: str,
    ) -> None:
        """Log alert without external notification."""
        log_msg = f"[SAFETY ALERT] agent={agent_name} level={level.value}: {message}"

        if level == SafetyLevel.CRITICAL:
            logger.critical(log_msg)
        elif level == SafetyLevel.BLOCKED:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)


def create_alerter(settings: Settings) -> AlerterProtocol:
    """Create appropriate alerter based on settings.

    Returns:
        WebhookAlerter if webhook URL configured, LogOnlyAlerter otherwise
    """
    if settings.alert_webhook_url:
        return WebhookAlerter(settings)
    return LogOnlyAlerter()


__all__ = ["WebhookAlerter", "LogOnlyAlerter", "create_alerter"]
