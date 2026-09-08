"""The structured result produced by the Executor agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


@dataclass
class ExecutionResult:
    """The Executor's structured output for a single subtask (or the task as a whole)."""

    task_id: str
    status: ExecutionStatus
    summary: str
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "summary": self.summary,
            "output": dict(self.output),
            "artifacts": list(self.artifacts),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionResult":
        return cls(
            task_id=data["task_id"],
            status=ExecutionStatus(data["status"]),
            summary=data.get("summary", ""),
            output=dict(data.get("output", {})),
            artifacts=list(data.get("artifacts", [])),
            errors=list(data.get("errors", [])),
            metadata=dict(data.get("metadata", {})),
        )
