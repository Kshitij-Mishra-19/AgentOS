"""A simple, reliable in-process async message bus.

Deliberately not a distributed queue: everything runs inside one Python
process, in-memory, so the system has zero external infrastructure
dependencies and is trivial to test. The interface (``publish`` /
``subscribe``) is small enough that a distributed backend could be
swapped in later without changing agent code, since agents never touch
the bus directly -- they only implement ``handle(message)``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from core.errors import InvalidMessageError
from core.logging import get_logger, log_context
from core.protocol import validate_message
from schemas.message import AgentMessage

Handler = Callable[[AgentMessage], Awaitable[Optional[AgentMessage]]]

logger = get_logger("message_bus")


@dataclass
class DeliveryFailure:
    """Record of a message that a subscriber's handler failed to process."""

    message: AgentMessage
    error: Exception


@dataclass
class MessageBus:
    """Publish/subscribe bus routing :class:`AgentMessage` by recipient.

    Subscribers register a coroutine handler under a recipient name
    (typically an agent id). ``publish`` validates the message, routes
    it to the matching handler(s), awaits them, and returns any replies
    they produce. All history is kept for observability/testing.
    """

    _subscribers: dict[str, list[Handler]] = field(default_factory=dict)
    history: list[AgentMessage] = field(default_factory=list)
    failures: list[DeliveryFailure] = field(default_factory=list)

    def subscribe(self, recipient: str, handler: Handler) -> None:
        """Register ``handler`` to receive messages addressed to ``recipient``."""
        self._subscribers.setdefault(recipient, []).append(handler)
        log_context(logger, "debug", "handler_subscribed", recipient=recipient)

    def unsubscribe(self, recipient: str, handler: Handler) -> None:
        handlers = self._subscribers.get(recipient, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, message: AgentMessage) -> list[AgentMessage]:
        """Validate, log, and deliver ``message`` to all subscribers of its recipient.

        Returns the list of reply messages produced by handlers (in
        subscription order). Handler exceptions are captured in
        ``self.failures`` and re-raised only if no handler was
        registered for the recipient at all is a routing error and
        raises immediately -- silent drops are never acceptable.
        """
        validate_message(message)
        self.history.append(message)
        log_context(
            logger,
            "info",
            "message_published",
            task_id=message.task_id,
            correlation_id=message.correlation_id,
            message_type=message.message_type.value,
            sender=message.sender,
            recipient=message.recipient,
        )

        handlers = self._subscribers.get(message.recipient, [])
        if not handlers:
            raise InvalidMessageError(
                f"No subscriber registered for recipient '{message.recipient}'",
                details={"message_id": message.message_id, "recipient": message.recipient},
            )

        replies: list[AgentMessage] = []
        for handler in handlers:
            try:
                reply = await handler(message)
            except Exception as exc:  # noqa: BLE001 - deliberately broad, captured not swallowed
                self.failures.append(DeliveryFailure(message=message, error=exc))
                log_context(
                    logger,
                    "error",
                    "handler_failed",
                    task_id=message.task_id,
                    correlation_id=message.correlation_id,
                    recipient=message.recipient,
                    error=str(exc),
                )
                raise
            if reply is not None:
                replies.append(reply)
        return replies

    def clear_history(self) -> None:
        self.history.clear()
        self.failures.clear()


async def gather_replies(bus: MessageBus, messages: list[AgentMessage]) -> list[AgentMessage]:
    """Publish several messages concurrently and flatten their replies."""
    results = await asyncio.gather(*(bus.publish(m) for m in messages))
    flattened: list[AgentMessage] = []
    for replies in results:
        flattened.extend(replies)
    return flattened
