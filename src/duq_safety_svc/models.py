"""Pydantic models for Safety Service API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SafetyCheckRequest(BaseModel):
    """Request to check agent action safety.

    Attributes:
        agent_name: Name/identifier of the agent
        action: Type of action (e.g., "file_write", "bash", "http_request")
        details: Action-specific details (path, command, url, etc.)
    """

    agent_name: str = Field(..., min_length=1, description="Agent name/identifier")
    action: str = Field(..., min_length=1, description="Action type")
    details: dict[str, Any] = Field(default_factory=dict, description="Action details")


class SafetyCheckResponse(BaseModel):
    """Response from safety check.

    Attributes:
        allowed: Whether the action is allowed
        level: Safety level (safe, warning, blocked, critical)
        reason: Explanation of the decision
        rule_matched: Name of the rule that matched (if any)
        checked_by: How the decision was made ("rules" or "llm")
        timestamp: When the check was performed
    """

    allowed: bool
    level: str = Field(..., description="Safety level: safe, warning, blocked, critical")
    reason: str
    rule_matched: str | None = None
    checked_by: str = "rules"
    timestamp: datetime


class BatchSafetyCheckRequest(BaseModel):
    """Request to check multiple actions at once.

    Attributes:
        checks: List of individual check requests
    """

    checks: list[SafetyCheckRequest] = Field(
        ..., min_length=1, max_length=100, description="Actions to check"
    )


class BatchSafetyCheckResponse(BaseModel):
    """Response from batch safety check.

    Attributes:
        results: List of individual check responses
        all_allowed: True if all actions are allowed
        blocked_count: Number of blocked actions
    """

    results: list[SafetyCheckResponse]
    all_allowed: bool
    blocked_count: int


class HealthResponse(BaseModel):
    """Health check response.

    Attributes:
        status: Service status
        version: Service version
        llm_available: Whether LLM fallback is available
        rules_count: Number of active safety rules
    """

    status: str = "healthy"
    version: str
    llm_available: bool
    rules_count: int


class StatsResponse(BaseModel):
    """Safety checker statistics.

    Attributes:
        rule_checks: Total rule-based checks
        llm_checks: Total LLM-based checks
        blocked: Total blocked actions
        warnings: Total warnings
        alerts_sent: Total alerts sent
    """

    rule_checks: int
    llm_checks: int
    blocked: int
    warnings: int
    alerts_sent: int


class RuleInfo(BaseModel):
    """Information about a safety rule.

    Attributes:
        name: Rule name/identifier
        description: Human-readable description
        priority: Rule priority (higher = checked first)
        enabled: Whether the rule is active
    """

    name: str
    description: str
    priority: int
    enabled: bool


class RulesResponse(BaseModel):
    """List of active safety rules.

    Attributes:
        rules: List of rule information
        total: Total number of rules
    """

    rules: list[RuleInfo]
    total: int


class ErrorResponse(BaseModel):
    """Error response.

    Attributes:
        error: Error type/code
        message: Human-readable error message
        detail: Additional error details (optional)
    """

    error: str
    message: str
    detail: str | None = None


__all__ = [
    "SafetyCheckRequest",
    "SafetyCheckResponse",
    "BatchSafetyCheckRequest",
    "BatchSafetyCheckResponse",
    "HealthResponse",
    "StatsResponse",
    "RuleInfo",
    "RulesResponse",
    "ErrorResponse",
]
