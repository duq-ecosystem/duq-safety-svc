"""DUQ Safety Service - Watchdog microservice for agent actions.

Provides HTTP API for safety checking of agent actions using:
- Rule-based fast path for common patterns
- LLM fallback for complex cases

Based on SafetyChecker from duq-agent-core.
"""

__version__ = "0.1.0"
