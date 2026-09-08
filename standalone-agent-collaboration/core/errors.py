"""Structured error hierarchy for the agent collaboration system.

All errors raised anywhere in the system should derive from
``CollaborationError`` so callers can catch a single base class when
they only care that "something in the workflow went wrong", while still
being able to catch more specific subclasses when they need to react
differently.

Exceptions are never swallowed silently: agents and the orchestrator
are expected to catch these, log them, and translate them into
structured results (see ``schemas.result`` and ``schemas.review``)
rather than letting failures disappear.
"""

from __future__ import annotations

from typing import Any, Optional


class CollaborationError(Exception):
    """Base class for all errors raised by the collaboration system."""

    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message


class InvalidMessageError(CollaborationError):
    """Raised when a message fails schema validation or is malformed."""


class UnknownAgentError(CollaborationError):
    """Raised when a message is addressed to an agent that isn't registered."""


class InvalidStateTransitionError(CollaborationError):
    """Raised when a task is asked to move to a status that isn't reachable
    from its current status."""


class ExecutorFailureError(CollaborationError):
    """Raised when the Executor agent cannot complete a subtask."""


class ReviewerFailureError(CollaborationError):
    """Raised when the Reviewer agent cannot produce a valid review."""


class MalformedAgentOutputError(CollaborationError):
    """Raised when an agent's structured output does not match the expected schema."""


class MaxRevisionCyclesExceededError(CollaborationError):
    """Raised when a task exhausts its configured revision budget without approval."""


class OrchestrationError(CollaborationError):
    """Raised for orchestration-level failures that don't fit a more specific category."""


class ConfigurationError(CollaborationError):
    """Raised when system or agent configuration is missing or invalid."""
