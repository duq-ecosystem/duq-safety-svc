"""DUQ Safety Service - FastAPI application.

Provides HTTP API for safety checking of agent actions.
Uses SafetyChecker from duq-agent-core with:
- Rule-based fast path for common patterns
- LLM fallback for complex cases

Endpoints:
    POST /api/safety/check - Check single action
    POST /api/safety/batch - Check multiple actions
    GET /api/safety/rules - List active rules
    GET /api/safety/stats - Get statistics
    GET /health - Health check
    GET /ready - Readiness check
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from duq_agent_core import SafetyChecker, DEFAULT_RULES

from duq_safety_svc import __version__
from duq_safety_svc.config import get_settings, Settings
from duq_safety_svc.llm_adapter import LLMAdapter
from duq_safety_svc.alerter import create_alerter
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


# Global instances (initialized in lifespan)
_safety_checker: SafetyChecker | None = None
_llm_adapter: LLMAdapter | None = None
_settings: Settings | None = None


def get_checker() -> SafetyChecker:
    """Get safety checker instance."""
    if _safety_checker is None:
        raise RuntimeError("Safety checker not initialized")
    return _safety_checker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - initialize and cleanup resources."""
    global _safety_checker, _llm_adapter, _settings

    logger.info("Starting DUQ Safety Service...")

    # Load settings
    _settings = get_settings()

    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level=_settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Create LLM adapter if configured
    if _settings.has_llm_provider and _settings.use_llm_fallback:
        _llm_adapter = LLMAdapter(_settings)
        logger.info("LLM fallback enabled")
    else:
        _llm_adapter = None
        logger.info("LLM fallback disabled (no API keys or disabled in settings)")

    # Create alerter
    alerter = create_alerter(_settings)

    # Create safety checker using existing implementation from duq-agent-core
    _safety_checker = SafetyChecker(
        llm_router=_llm_adapter,  # Implements LLMRouterProtocol
        alerter=alerter,
        rules=DEFAULT_RULES,
        llm_safety_model=_settings.llm_safety_model,
        use_llm_fallback=_settings.use_llm_fallback and _llm_adapter is not None,
    )

    logger.info(
        f"Safety checker initialized: {len(DEFAULT_RULES)} rules, "
        f"LLM fallback={'enabled' if _llm_adapter else 'disabled'}"
    )

    yield

    # Cleanup
    logger.info("Shutting down DUQ Safety Service...")

    if _llm_adapter:
        await _llm_adapter.close()

    if hasattr(alerter, "close"):
        await alerter.close()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DUQ Safety Service",
    description="Watchdog microservice for agent action safety checking",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Health check endpoint."""
    checker = get_checker()
    return HealthResponse(
        status="healthy",
        version=__version__,
        llm_available=_llm_adapter is not None,
        rules_count=len(checker.rules),
    )


@app.get("/ready", response_model=HealthResponse, tags=["Health"])
async def ready() -> HealthResponse:
    """Readiness check endpoint."""
    try:
        checker = get_checker()
        return HealthResponse(
            status="ready",
            version=__version__,
            llm_available=_llm_adapter is not None,
            rules_count=len(checker.rules),
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )


# =============================================================================
# Safety Check Endpoints
# =============================================================================


@app.post(
    "/api/safety/check",
    response_model=SafetyCheckResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Safety"],
)
async def check_action(request: SafetyCheckRequest) -> SafetyCheckResponse:
    """Check if an agent action is safe.

    Uses rule-based fast path first, then LLM fallback for complex cases.

    Args:
        request: Action details to check

    Returns:
        Safety check result with allowed/blocked decision
    """
    checker = get_checker()

    try:
        result = await checker.check_action(
            agent_name=request.agent_name,
            action=request.action,
            details=request.details,
        )

        return SafetyCheckResponse(
            allowed=result.allowed,
            level=result.level.value,
            reason=result.reason,
            rule_matched=result.rule_matched,
            checked_by=result.checked_by,
            timestamp=result.timestamp,
        )

    except Exception as e:
        logger.exception(f"Safety check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety check failed: {e}",
        )


@app.post(
    "/api/safety/batch",
    response_model=BatchSafetyCheckResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Safety"],
)
async def check_batch(request: BatchSafetyCheckRequest) -> BatchSafetyCheckResponse:
    """Check multiple agent actions at once.

    Processes checks sequentially (not parallel) to respect rate limits.

    Args:
        request: List of actions to check

    Returns:
        List of safety check results with summary
    """
    checker = get_checker()
    results: list[SafetyCheckResponse] = []
    blocked_count = 0

    for check_request in request.checks:
        try:
            result = await checker.check_action(
                agent_name=check_request.agent_name,
                action=check_request.action,
                details=check_request.details,
            )

            response = SafetyCheckResponse(
                allowed=result.allowed,
                level=result.level.value,
                reason=result.reason,
                rule_matched=result.rule_matched,
                checked_by=result.checked_by,
                timestamp=result.timestamp,
            )
            results.append(response)

            if not result.allowed:
                blocked_count += 1

        except Exception as e:
            logger.exception(f"Batch check failed for {check_request.agent_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch check failed: {e}",
            )

    return BatchSafetyCheckResponse(
        results=results,
        all_allowed=blocked_count == 0,
        blocked_count=blocked_count,
    )


# =============================================================================
# Management Endpoints
# =============================================================================


@app.get(
    "/api/safety/rules",
    response_model=RulesResponse,
    tags=["Management"],
)
async def list_rules() -> RulesResponse:
    """List all active safety rules.

    Returns:
        List of rules with their configuration
    """
    checker = get_checker()

    rules = [
        RuleInfo(
            name=rule.name,
            description=rule.description,
            priority=rule.priority,
            enabled=rule.enabled,
        )
        for rule in checker.rules
    ]

    return RulesResponse(rules=rules, total=len(rules))


@app.get(
    "/api/safety/stats",
    response_model=StatsResponse,
    tags=["Management"],
)
async def get_stats() -> StatsResponse:
    """Get safety checker statistics.

    Returns:
        Counters for checks, blocks, warnings, and alerts
    """
    checker = get_checker()
    stats = checker.get_stats()

    return StatsResponse(
        rule_checks=stats.get("rule_checks", 0),
        llm_checks=stats.get("llm_checks", 0),
        blocked=stats.get("blocked", 0),
        warnings=stats.get("warnings", 0),
        alerts_sent=stats.get("alerts_sent", 0),
    )


@app.post(
    "/api/safety/rules/{rule_name}/disable",
    response_model=dict,
    tags=["Management"],
)
async def disable_rule(rule_name: str) -> dict:
    """Disable a safety rule by name.

    Args:
        rule_name: Name of the rule to disable

    Returns:
        Success status
    """
    checker = get_checker()

    if checker.disable_rule(rule_name):
        logger.info(f"Rule disabled: {rule_name}")
        return {"success": True, "rule": rule_name, "status": "disabled"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Rule not found: {rule_name}",
    )


# =============================================================================
# Main entry point
# =============================================================================


def main() -> None:
    """Run the safety service."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "duq_safety_svc.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
