"""Shared workflow state, kept storage-agnostic behind a small interface.

``StateBackend`` defines the storage contract. ``InMemoryStateBackend``
is the only implementation shipped here, which is enough for a
single-process system and for tests. A database-backed implementation
(e.g. SQLite/Postgres) can be added later by implementing the same
interface -- ``StateManager`` and the agents never depend on the
backend's storage details.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from schemas.plan import Plan
from schemas.result import ExecutionResult
from schemas.review import Review


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowState:
    """Everything the orchestrator and agents need to know about one workflow run."""

    task_id: str
    original_task: str
    current_plan: Optional[Plan] = None
    subtasks: list[dict[str, Any]] = field(default_factory=list)
    agent_outputs: list[dict[str, Any]] = field(default_factory=list)
    review_results: list[Review] = field(default_factory=list)
    revision_history: list[dict[str, Any]] = field(default_factory=list)
    current_workflow_state: str = "CREATED"
    errors: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)


class StateBackend(ABC):
    """Storage contract that any backend (in-memory, DB, ...) must implement."""

    @abstractmethod
    def get(self, task_id: str) -> Optional[WorkflowState]:
        ...

    @abstractmethod
    def put(self, state: WorkflowState) -> None:
        ...

    @abstractmethod
    def delete(self, task_id: str) -> None:
        ...

    @abstractmethod
    def all_task_ids(self) -> list[str]:
        ...


class InMemoryStateBackend(StateBackend):
    """A plain dict-backed store. Deep-copies on write/read to avoid aliasing bugs."""

    def __init__(self) -> None:
        self._store: dict[str, WorkflowState] = {}

    def get(self, task_id: str) -> Optional[WorkflowState]:
        state = self._store.get(task_id)
        return copy.deepcopy(state) if state is not None else None

    def put(self, state: WorkflowState) -> None:
        state.updated_at = _utcnow_iso()
        self._store[state.task_id] = copy.deepcopy(state)

    def delete(self, task_id: str) -> None:
        self._store.pop(task_id, None)

    def all_task_ids(self) -> list[str]:
        return list(self._store.keys())


class StateManager:
    """High-level API the orchestrator/agents use to read and mutate workflow state.

    Every mutation goes through a method here (never direct field
    assignment on a stored object) so backends can be swapped without
    the calling code changing.
    """

    def __init__(self, backend: Optional[StateBackend] = None) -> None:
        self.backend = backend or InMemoryStateBackend()

    def create(self, task_id: str, original_task: str) -> WorkflowState:
        state = WorkflowState(task_id=task_id, original_task=original_task)
        self.backend.put(state)
        return state

    def get(self, task_id: str) -> WorkflowState:
        state = self.backend.get(task_id)
        if state is None:
            raise KeyError(f"No workflow state found for task_id={task_id}")
        return state

    def set_plan(self, task_id: str, plan: Plan) -> None:
        state = self.get(task_id)
        state.current_plan = plan
        state.subtasks = [st.to_dict() for st in plan.subtasks]
        self.backend.put(state)

    def add_agent_output(self, task_id: str, result: ExecutionResult) -> None:
        state = self.get(task_id)
        state.agent_outputs.append(result.to_dict())
        self.backend.put(state)

    def add_review_result(self, task_id: str, review: Review) -> None:
        state = self.get(task_id)
        state.review_results.append(review)
        self.backend.put(state)

    def add_revision(self, task_id: str, reason: str, feedback: str) -> None:
        state = self.get(task_id)
        state.revision_history.append(
            {"reason": reason, "feedback": feedback, "timestamp": _utcnow_iso()}
        )
        self.backend.put(state)

    def set_workflow_state(self, task_id: str, workflow_state: str) -> None:
        state = self.get(task_id)
        state.current_workflow_state = workflow_state
        self.backend.put(state)

    def add_error(self, task_id: str, error_type: str, message: str) -> None:
        state = self.get(task_id)
        state.errors.append(
            {"type": error_type, "message": message, "timestamp": _utcnow_iso()}
        )
        self.backend.put(state)

    def exists(self, task_id: str) -> bool:
        return self.backend.get(task_id) is not None
