"""The task model tracked by the state manager and orchestrator."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from core.errors import InvalidStateTransitionError


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    READY = "READY"
    RUNNING = "RUNNING"
    REVIEWING = "REVIEWING"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Explicit allow-list of legal status transitions. Kept close to the enum
# so the state machine is easy to audit and to extend.
_ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.PLANNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.PLANNING: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.REVIEWING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.REVIEWING: {
        TaskStatus.COMPLETED,
        TaskStatus.REVISION_REQUIRED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.REVISION_REQUIRED: {
        TaskStatus.PLANNING,
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


@dataclass
class Task:
    """A unit of work tracked through the Planner -> Executor -> Reviewer lifecycle."""

    title: str
    description: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)
    assigned_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    attempt: int = 0
    revision_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in _ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: TaskStatus) -> None:
        """Move the task to ``new_status``, raising if the transition is illegal."""
        if new_status == self.status:
            return
        if not self.can_transition_to(new_status):
            raise InvalidStateTransitionError(
                f"Cannot transition task {self.task_id} from {self.status.value} "
                f"to {new_status.value}",
                details={"task_id": self.task_id, "from": self.status.value, "to": new_status.value},
            )
        self.status = new_status
        self.updated_at = _utcnow_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "assigned_agent": self.assigned_agent,
            "parent_task_id": self.parent_task_id,
            "subtasks": list(self.subtasks),
            "dependencies": list(self.dependencies),
            "attempt": self.attempt,
            "revision_count": self.revision_count,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            title=data["title"],
            description=data["description"],
            task_id=data.get("task_id", str(uuid.uuid4())),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            priority=data.get("priority", 3),
            created_at=data.get("created_at", _utcnow_iso()),
            updated_at=data.get("updated_at", _utcnow_iso()),
            assigned_agent=data.get("assigned_agent"),
            parent_task_id=data.get("parent_task_id"),
            subtasks=list(data.get("subtasks", [])),
            dependencies=list(data.get("dependencies", [])),
            attempt=data.get("attempt", 0),
            revision_count=data.get("revision_count", 0),
            metadata=dict(data.get("metadata", {})),
        )
