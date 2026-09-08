"""The message envelope used for all inter-agent communication.

Agents never call each other directly. Every interaction is expressed
as an ``AgentMessage`` published on the message bus (see
``core.message_bus``), keeping agents decoupled from one another's
implementations.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class MessageType(str, Enum):
    """All message types recognized by the collaboration protocol."""

    TASK_CREATED = "TASK_CREATED"
    PLAN_CREATED = "PLAN_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    REVIEW_REQUESTED = "REVIEW_REQUESTED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentMessage:
    """A single, strongly typed message passed between agents.

    ``payload`` and ``metadata`` must be JSON-compatible (only str, int,
    float, bool, None, list, and dict values) so that messages can be
    logged, persisted, or sent across a process boundary without any
    special-casing.
    """

    sender: str
    recipient: str
    message_type: MessageType
    task_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_utcnow_iso)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "task_id": self.task_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessage":
        required = {"sender", "recipient", "message_type", "task_id"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Message missing required fields: {sorted(missing)}")

        try:
            message_type = MessageType(data["message_type"])
        except ValueError as exc:
            raise ValueError(f"Unknown message_type: {data['message_type']!r}") from exc

        return cls(
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=message_type,
            task_id=data["task_id"],
            payload=data.get("payload", {}),
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", _utcnow_iso()),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, raw: str) -> "AgentMessage":
        return cls.from_dict(json.loads(raw))

    def reply(
        self,
        *,
        sender: str,
        message_type: MessageType,
        payload: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "AgentMessage":
        """Build a reply message that preserves this message's correlation ID."""
        return AgentMessage(
            sender=sender,
            recipient=self.sender,
            message_type=message_type,
            task_id=self.task_id,
            payload=payload or {},
            correlation_id=self.correlation_id,
            metadata=metadata or {},
        )
