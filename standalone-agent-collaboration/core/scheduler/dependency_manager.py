"""
Dependency management for the task scheduler.

Handles:
- dependency validation
- cycle detection
- checking whether tasks are ready
- finding currently ready tasks
- finding dependent tasks
"""

from __future__ import annotations

from collections import defaultdict, deque


class DependencyManager:
    """Manages task dependency relationships."""

    def __init__(
        self,
        dependencies: dict[str, list[str]] | None = None,
    ) -> None:
        self._dependencies: dict[str, list[str]] = {
            task_id: list(deps)
            for task_id, deps in (dependencies or {}).items()
        }

        self._dependents: dict[str, set[str]] = defaultdict(set)

        for task_id, deps in self._dependencies.items():
            for dependency in deps:
                self._dependents[dependency].add(task_id)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, task_ids: list[str]) -> None:
        """
        Validate that:
        1. Every dependency refers to an existing task.
        2. The dependency graph contains no cycle.
        """

        known_tasks = set(task_ids)

        # Check for unknown dependencies.
        for task_id in known_tasks:
            for dependency in self._dependencies.get(task_id, []):
                if dependency not in known_tasks:
                    raise ValueError(
                        f"Task {task_id} depends on unknown task "
                        f"{dependency}"
                    )

        self._detect_cycle(known_tasks)

    def _detect_cycle(self, task_ids: set[str]) -> None:
        """Detect cycles using Kahn's topological-sort algorithm."""

        indegree: dict[str, int] = {
            task_id: 0
            for task_id in task_ids
        }

        for task_id in task_ids:
            for dependency in self._dependencies.get(task_id, []):
                if dependency in task_ids:
                    indegree[task_id] += 1

        queue = deque(
            task_id
            for task_id, degree in indegree.items()
            if degree == 0
        )

        processed = 0

        while queue:
            task_id = queue.popleft()
            processed += 1

            for dependent in self._dependents.get(task_id, set()):
                if dependent not in indegree:
                    continue

                indegree[dependent] -= 1

                if indegree[dependent] == 0:
                    queue.append(dependent)

        if processed != len(task_ids):
            cyclic_tasks = [
                task_id
                for task_id, degree in indegree.items()
                if degree > 0
            ]

            raise ValueError(
                "Dependency cycle detected involving tasks: "
                f"{cyclic_tasks}"
            )

    # ------------------------------------------------------------------
    # Dependency queries
    # ------------------------------------------------------------------

    def dependencies_of(self, task_id: str) -> list[str]:
        """Return the direct dependencies of a task."""

        return list(
            self._dependencies.get(task_id, [])
        )

    def dependents_of(self, task_id: str) -> list[str]:
        """Return tasks that directly depend on this task."""

        return list(
            self._dependents.get(task_id, set())
        )

    # ------------------------------------------------------------------
    # Readiness
    # ------------------------------------------------------------------

    def is_ready(
        self,
        task_id: str,
        completed: set[str],
    ) -> bool:
        """
        Return True if all dependencies of task_id are completed.

        A task with no dependencies is immediately ready.
        """

        dependencies = self._dependencies.get(
            task_id,
            [],
        )

        return all(
            dependency in completed
            for dependency in dependencies
        )

    def ready_tasks(
        self,
        pending: set[str] | list[str],
        completed: set[str],
    ) -> list[str]:
        """
        Return all pending tasks whose dependencies are satisfied.

        Example:

            subtask-1 -> no dependency
            subtask-2 -> subtask-1
            subtask-3 -> subtask-2

        Initially:

            completed = set()

        Result:

            ["subtask-1"]

        After subtask-1 completes:

            completed = {"subtask-1"}

        Result:

            ["subtask-2"]
        """

        return [
            task_id
            for task_id in pending
            if self.is_ready(
                task_id,
                completed,
            )
        ]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def all_dependencies_completed(
        self,
        task_id: str,
        completed: set[str],
    ) -> bool:
        """Return True when every dependency is completed."""

        return self.is_ready(
            task_id,
            completed,
        )

    def unresolved_dependencies(
        self,
        task_id: str,
        completed: set[str],
    ) -> list[str]:
        """Return dependencies that have not completed yet."""

        return [
            dependency
            for dependency in self._dependencies.get(
                task_id,
                [],
            )
            if dependency not in completed
        ]