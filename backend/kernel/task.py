from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from datetime import datetime


class TaskStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    agent_id: str
    description: str

    id: str = field(default_factory=lambda: str(uuid4()))

    status: TaskStatus = TaskStatus.CREATED

    priority: int = 5

    def __post_init__(self):
        if not isinstance(self.priority, int):
            raise TypeError("Task priority must be an integer")

        if not 1 <= self.priority <= 10:
            raise ValueError("Task priority must be between 1 and 10")

    result: str | None = None

    error: str | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None

    def cancel(self) -> None:

        if self.status not in {
            TaskStatus.CREATED,
            TaskStatus.QUEUED,
        }:
            raise RuntimeError(
                f"Task cannot be cancelled from status: {self.status}"
            )

        self.status = TaskStatus.CANCELLED
        
    def queue(self) -> None:

        if self.status != TaskStatus.CREATED:
            raise RuntimeError(
                f"Task cannot be queued from status: {self.status}"
            )

        self.status = TaskStatus.QUEUED