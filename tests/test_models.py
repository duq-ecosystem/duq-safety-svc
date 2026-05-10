"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from duq_safety_svc.models import (
    SafetyCheckRequest,
    SafetyCheckResponse,
    BatchSafetyCheckRequest,
    BatchSafetyCheckResponse,
    HealthResponse,
    StatsResponse,
    RuleInfo,
    RulesResponse,
    ErrorResponse,
)


class TestSafetyCheckRequest:
    """Tests for SafetyCheckRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        request = SafetyCheckRequest(
            agent_name="test-agent",
            action="file_write",
            details={"path": "/tmp/test.txt"},
        )
        assert request.agent_name == "test-agent"
        assert request.action == "file_write"
        assert request.details["path"] == "/tmp/test.txt"

    def test_empty_agent_name_rejected(self) -> None:
        """Test empty agent name is rejected."""
        with pytest.raises(ValidationError):
            SafetyCheckRequest(
                agent_name="",
                action="file_write",
                details={},
            )

    def test_empty_action_rejected(self) -> None:
        """Test empty action is rejected."""
        with pytest.raises(ValidationError):
            SafetyCheckRequest(
                agent_name="test-agent",
                action="",
                details={},
            )

    def test_default_details(self) -> None:
        """Test default empty details."""
        request = SafetyCheckRequest(
            agent_name="test-agent",
            action="read",
        )
        assert request.details == {}


class TestSafetyCheckResponse:
    """Tests for SafetyCheckResponse model."""

    def test_valid_response(self) -> None:
        """Test valid response creation."""
        now = datetime.now(UTC)
        response = SafetyCheckResponse(
            allowed=True,
            level="safe",
            reason="No safety rules matched",
            timestamp=now,
        )
        assert response.allowed is True
        assert response.level == "safe"
        assert response.timestamp == now

    def test_blocked_response(self) -> None:
        """Test blocked response."""
        response = SafetyCheckResponse(
            allowed=False,
            level="critical",
            reason="Access to sensitive path blocked",
            rule_matched="sensitive_paths",
            checked_by="rules",
            timestamp=datetime.now(UTC),
        )
        assert response.allowed is False
        assert response.rule_matched == "sensitive_paths"


class TestBatchSafetyCheckRequest:
    """Tests for BatchSafetyCheckRequest model."""

    def test_valid_batch(self) -> None:
        """Test valid batch request."""
        request = BatchSafetyCheckRequest(
            checks=[
                SafetyCheckRequest(agent_name="a", action="read", details={}),
                SafetyCheckRequest(agent_name="b", action="write", details={}),
            ]
        )
        assert len(request.checks) == 2

    def test_empty_batch_rejected(self) -> None:
        """Test empty batch is rejected."""
        with pytest.raises(ValidationError):
            BatchSafetyCheckRequest(checks=[])

    def test_batch_max_limit(self) -> None:
        """Test batch respects max limit."""
        # Should succeed with 100 items
        checks = [
            SafetyCheckRequest(agent_name=f"agent-{i}", action="read", details={})
            for i in range(100)
        ]
        request = BatchSafetyCheckRequest(checks=checks)
        assert len(request.checks) == 100

        # Should fail with 101 items
        with pytest.raises(ValidationError):
            BatchSafetyCheckRequest(checks=checks + [checks[0]])


class TestBatchSafetyCheckResponse:
    """Tests for BatchSafetyCheckResponse model."""

    def test_all_allowed(self) -> None:
        """Test response when all allowed."""
        now = datetime.now(UTC)
        response = BatchSafetyCheckResponse(
            results=[
                SafetyCheckResponse(allowed=True, level="safe", reason="OK", timestamp=now),
                SafetyCheckResponse(allowed=True, level="safe", reason="OK", timestamp=now),
            ],
            all_allowed=True,
            blocked_count=0,
        )
        assert response.all_allowed is True
        assert response.blocked_count == 0

    def test_some_blocked(self) -> None:
        """Test response when some blocked."""
        now = datetime.now(UTC)
        response = BatchSafetyCheckResponse(
            results=[
                SafetyCheckResponse(allowed=True, level="safe", reason="OK", timestamp=now),
                SafetyCheckResponse(allowed=False, level="blocked", reason="Blocked", timestamp=now),
            ],
            all_allowed=False,
            blocked_count=1,
        )
        assert response.all_allowed is False
        assert response.blocked_count == 1


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_health_response(self) -> None:
        """Test health response creation."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            llm_available=True,
            rules_count=5,
        )
        assert response.status == "healthy"
        assert response.llm_available is True


class TestStatsResponse:
    """Tests for StatsResponse model."""

    def test_stats_response(self) -> None:
        """Test stats response creation."""
        response = StatsResponse(
            rule_checks=100,
            llm_checks=10,
            blocked=5,
            warnings=15,
            alerts_sent=2,
        )
        assert response.rule_checks == 100
        assert response.blocked == 5


class TestRuleInfo:
    """Tests for RuleInfo model."""

    def test_rule_info(self) -> None:
        """Test rule info creation."""
        rule = RuleInfo(
            name="sensitive_paths",
            description="Block access to sensitive system paths",
            priority=1000,
            enabled=True,
        )
        assert rule.name == "sensitive_paths"
        assert rule.priority == 1000


class TestRulesResponse:
    """Tests for RulesResponse model."""

    def test_rules_response(self) -> None:
        """Test rules response creation."""
        response = RulesResponse(
            rules=[
                RuleInfo(name="rule1", description="desc1", priority=100, enabled=True),
                RuleInfo(name="rule2", description="desc2", priority=200, enabled=False),
            ],
            total=2,
        )
        assert response.total == 2
        assert len(response.rules) == 2


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_error_response(self) -> None:
        """Test error response creation."""
        error = ErrorResponse(
            error="validation_error",
            message="Invalid input",
            detail="Field 'name' is required",
        )
        assert error.error == "validation_error"
        assert error.detail is not None

    def test_error_response_without_detail(self) -> None:
        """Test error response without detail."""
        error = ErrorResponse(
            error="internal_error",
            message="Something went wrong",
        )
        assert error.detail is None
