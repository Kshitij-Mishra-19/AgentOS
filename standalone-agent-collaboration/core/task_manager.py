"""Task lifecycle management.

``TaskManager`` owns the authoritative :class:`~schemas.task.Task`
records. It's intentionally separate from :class:`~core.state_manager.StateManager`:
the task manager tracks *lifecycle/status* of tasks and subtasks, while
the state manager tracks the *content* produced during a workflow
(plans, results, reviews). The orchestrator uses both.
"""

from __future__ import annotations

from typing import Optional

from schemas.task import Task, TaskStatus


class TaskManager:
    """In-memory registry of :class:`Task` records with lifecycle helpers."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create_task(
        self,
        title: str,
        description: str,
        *,
        parent_task_id: Optional[str] = None,
        priority: int = 3,
        assigned_agent: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            parent_task_id=parent_task_id,
            priority=priority,
            assigned_agent=assigned_agent,
            dependencies=list(dependencies or []),
        )
        self._tasks[task.task_id] = task
        if parent_task_id and parent_task_id in self._tasks:
            self._tasks[parent_task_id].subtasks.append(task.task_id)
        return task

    def get(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"No task found with task_id={task_id}")
        return self._tasks[task_id]

    def update_status(self, task_id: str, status: TaskStatus) -> Task:
        task = self.get(task_id)
        task.transition_to(status)
        return task

    def increment_attempt(self, task_id: str) -> Task:
        task = self.get(task_id)
        task.attempt += 1
        return task

    def increment_revision(self, task_id: str) -> Task:
        task = self.get(task_id)
        task.revision_count += 1
        return task

    def assign_agent(self, task_id: str, agent_id: str) -> Task:
        task = self.get(task_id)
        task.assigned_agent = agent_id
        return task

    def children_of(self, task_id: str) -> list[Task]:
        parent = self.get(task_id)
        return [self._tasks[cid] for cid in parent.subtasks if cid in self._tasks]

    def all_tasks(self) -> list[Task]:
        return list(self._tasks.values())
