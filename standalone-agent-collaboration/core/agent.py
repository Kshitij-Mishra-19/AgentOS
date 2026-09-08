"""Common base agent abstraction.

Every concrete agent (Planner, Executor, Reviewer) subclasses
``BaseAgent`` and implements ``handle``. Agents never call each other's
methods directly or import each other's modules -- they only ever
receive an :class:`AgentMessage` and return an :class:`AgentMessage`
(or ``None``), communicating exclusively through the message bus. This
keeps every agent independently testable and replaceable.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from core.errors import MalformedAgentOutputError
from core.llm_provider import LLMProvider
from core.logging import get_logger, log_context
from schemas.message import AgentMessage, MessageType


class BaseAgent(ABC):
    """Shared behavior for all agents: identity, config, logging, and error handling.

    Subclasses implement :meth:`handle`, which must never raise a raw,
    unstructured exception outward for expected failure modes -- they
    should catch domain errors and encode them into a reply message
    (e.g. ``EXECUTION_FAILED``) so failures are always observable
    through the protocol rather than only through logs.
    """

    role: str = "agent"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        *,
        config: Optional[dict[str, Any]] = None,
        llm_provider: Optional[LLMProvider] = None,
    ) -> None:
        self.agent_id = agent_id or f"{self.role}-{uuid.uuid4().hex[:8]}"
        self.config = config or {}
        self.llm_provider = llm_provider
        self.logger = get_logger(self.role)

    @abstractmethod
    async def handle(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a single reply message."""

    def validate_input(self, message: AgentMessage, required_payload_keys: list[str]) -> None:
        """Ensure ``message.payload`` contains every key in ``required_payload_keys``."""
        missing = [k for k in required_payload_keys if k not in message.payload]
        if missing:
            raise MalformedAgentOutputError(
                f"{self.role} received message missing payload keys: {missing}",
                details={"message_id": message.message_id, "role": self.role},
            )

    def log_event(self, level: str, event: str, message: AgentMessage, **extra: Any) -> None:
        log_context(
            self.logger,
            level,
            event,
            task_id=message.task_id,
            correlation_id=message.correlation_id,
            agent_id=self.agent_id,
            **extra,
        )

    def build_reply(
        self,
        message: AgentMessage,
        *,
        message_type: MessageType,
        payload: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentMessage:
        return message.reply(
            sender=self.agent_id,
            message_type=message_type,
            payload=payload,
            metadata=metadata,
        )
