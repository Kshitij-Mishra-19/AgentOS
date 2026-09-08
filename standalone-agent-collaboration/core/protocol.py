"""Protocol-level validation for the collaboration system.

This module is deliberately separate from ``schemas.message``: the
schema defines *shape* (what fields exist), while the protocol defines
*rules* (which messages are valid to send, and to whom). Keeping them
apart means the schema can be reused even if the routing rules change.
"""

from __future__ import annotations

from typing import Iterable

from core.errors import InvalidMessageError, UnknownAgentError
from schemas.message import AgentMessage, MessageType

# The canonical set of agent roles/ids known to the system. The message
# bus and orchestrator use this to reject messages addressed to nobody.
KNOWN_RECIPIENTS: set[str] = {"planner", "executor", "reviewer", "orchestrator"}

_REQUIRED_FIELDS = ("sender", "recipient", "message_type", "task_id")


def validate_message(message: AgentMessage) -> None:
    """Raise ``InvalidMessageError``/``UnknownAgentError`` if ``message`` is invalid.

    A message is invalid if any required field is empty, or if its
    ``message_type`` isn't a recognized :class:`MessageType`. A message
    is unroutable if its recipient isn't a known agent.
    """
    for field_name in _REQUIRED_FIELDS:
        value = getattr(message, field_name, None)
        if value in (None, ""):
            raise InvalidMessageError(
                f"Message is missing required field '{field_name}'",
                details={"message_id": message.message_id},
            )

    if not isinstance(message.message_type, MessageType):
        raise InvalidMessageError(
            f"Unknown message_type: {message.message_type!r}",
            details={"message_id": message.message_id},
        )

    if message.recipient not in KNOWN_RECIPIENTS:
        raise UnknownAgentError(
            f"No known agent registered for recipient '{message.recipient}'",
            details={"message_id": message.message_id, "recipient": message.recipient},
        )


def is_terminal(message_type: MessageType) -> bool:
    """Whether a message type represents the end of a workflow (success or failure)."""
    return message_type in (MessageType.TASK_COMPLETED, MessageType.TASK_FAILED)


def register_recipient(name: str) -> None:
    """Allow an additional agent id to be addressed (used when adding new agents)."""
    KNOWN_RECIPIENTS.add(name)


def known_recipients() -> Iterable[str]:
    return sorted(KNOWN_RECIPIENTS)
