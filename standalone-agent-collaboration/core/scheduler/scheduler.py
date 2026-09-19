"""
Priority-based task scheduler.

The scheduler:
- validates task dependencies
- uses MLFQ for priority ordering
- executes independent tasks concurrently
- waits for dependencies before dispatching tasks
- supports fail-fast execution
- records task lifecycle state through TaskManager
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from core.task_manager import TaskManager
from schemas.plan import Plan, Subtask
from schemas.result import ExecutionResult, ExecutionStatus
from schemas.task import Task, TaskStatus

from .dependency_manager import DependencyManager
from .mlfq import MLFQScheduler
from .runtime import SchedulerRuntime


@dataclass
class ScheduledTask:
    """Internal representation of a scheduled subtask."""

    subtask_id: str
    title: str
    description: str
    assigned_role: str
    depends_on: list[str]
    priority: int
    task_id: Optional[str] = None


class Scheduler:
    """
    Dependency-aware priority scheduler.

    Independent tasks can execute concurrently up to the runtime
    lane limit. MLFQ determines which ready task gets dispatched next.
    """

    def __init__(
        self,
        *,
        task_manager: TaskManager,
        runtime: SchedulerRuntime,
        mlfq: Optional[MLFQScheduler] = None,
        fail_fast: bool = False,
    ) -> None:
        self.task_manager = task_manager
        self.runtime = runtime
        self.mlfq = mlfq or MLFQScheduler()
        self.fail_fast = fail_fast

        self._active_runs: set[str] = set()

    async def run_plan(
        self,
        *,
        parent_task_id: str,
        plan: Plan,
        priority: int = 3,
    ) -> list[ExecutionResult]:
        """
        Execute all subtasks in a plan according to dependencies
        and priority.
        """

        if parent_task_id in self._active_runs:
            raise RuntimeError(
                f"Scheduler is already running task {parent_task_id}"
            )

        self._active_runs.add(parent_task_id)

        try:
            return await self._run_plan(
                parent_task_id=parent_task_id,
                plan=plan,
                priority=priority,
            )
        finally:
            self._active_runs.discard(parent_task_id)
            self.mlfq.clear()

    async def _run_plan(
        self,
        *,
        parent_task_id: str,
        plan: Plan,
        priority: int,
    ) -> list[ExecutionResult]:

        scheduled_tasks = self._build_tasks(
            plan=plan,
            priority=priority,
        )

        if not scheduled_tasks:
            return []

        # Dependency graph uses planner subtask IDs.
        dependencies = {
            task.subtask_id: list(task.depends_on)
            for task in scheduled_tasks
        }

        dependency_manager = DependencyManager(dependencies)

        dependency_manager.validate(
            [task.subtask_id for task in scheduled_tasks]
        )

        # Create authoritative Task records.
        self._create_task_records(
            parent_task_id=parent_task_id,
            tasks=scheduled_tasks,
        )

        pending: set[str] = {
            task.subtask_id for task in scheduled_tasks
        }

        running: dict[str, asyncio.Task[ExecutionResult]] = {}

        completed: set[str] = set()
        failed: set[str] = set()

        results: dict[str, ExecutionResult] = {}

        # Map planner subtask ID -> TaskManager UUID.
        task_records = {
            task.subtask_id: task.task_id
            for task in scheduled_tasks
            if task.task_id is not None
        }

        while pending or running:

            # ---------------------------------------------------------
            # 1. Find tasks whose dependencies are satisfied.
            # ---------------------------------------------------------

            ready = dependency_manager.ready_tasks(
                pending=pending,
                completed=completed,
            )

            for subtask_id in ready:
                if subtask_id not in pending:
                    continue

                pending.remove(subtask_id)

                self.mlfq.enqueue(
                    task_id=subtask_id,
                    priority=self._priority_for(
                        scheduled_tasks,
                        subtask_id,
                    ),
                )

            # ---------------------------------------------------------
            # 2. Dispatch ready tasks while execution lanes exist.
            # ---------------------------------------------------------

            while (
                not self.mlfq.empty()
                and len(running) < self.runtime.number_of_lanes
            ):
                item = self.mlfq.dequeue()

                if item is None:
                    break

                subtask_id = item.task_id

                if subtask_id in completed or subtask_id in failed:
                    continue

                task = self._find_task(
                    scheduled_tasks,
                    subtask_id,
                )

                task_uuid = task_records[subtask_id]

                self._mark_running(task_uuid)

                running[subtask_id] = asyncio.create_task(
                    self._execute_subtask(
                        parent_task_id=parent_task_id,
                        task=task,
                        task_uuid=task_uuid,
                    )
                )

            # ---------------------------------------------------------
            # 3. If tasks are running, wait for at least one to finish.
            # ---------------------------------------------------------

            if running:
                done, _ = await asyncio.wait(
                    running.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                finished_subtasks: list[str] = []

                for subtask_id, future in list(running.items()):
                    if future not in done:
                        continue

                    finished_subtasks.append(subtask_id)

                    try:
                        result = future.result()
                    except Exception as exc:
                        result = ExecutionResult(
                            task_id=subtask_id,
                            status=ExecutionStatus.FAILED,
                            summary="Task execution failed.",
                            output={},
                            errors=[str(exc)],
                        )

                    del running[subtask_id]

                    results[subtask_id] = result

                    # -------------------------------------------------
                    # 4. Handle execution failure.
                    # -------------------------------------------------

                    if result.status == ExecutionStatus.FAILED:
                        failed.add(subtask_id)

                        task_uuid = task_records[subtask_id]

                        self._mark_failed(task_uuid)

                        # IMPORTANT:
                        # In fail-fast mode we stop immediately.
                        # We do NOT continue dependency resolution,
                        # otherwise dependent tasks can cause a
                        # false "scheduler deadlock".
                        if self.fail_fast:
                            await self._stop_remaining_tasks(
                                pending=pending,
                                task_records=task_records,
                            )

                            pending.clear()

                            # Remove anything waiting in MLFQ.
                            self.mlfq.clear()

                            # Cancel tasks currently executing.
                            for other_subtask_id, other_future in list(
                                running.items()
                            ):
                                if not other_future.done():
                                    other_future.cancel()

                            if running:
                                await asyncio.gather(
                                    *running.values(),
                                    return_exceptions=True,
                                )

                            running.clear()

                            return self._ordered_results(
                                plan=plan,
                                results=results,
                            )

                    else:
                        completed.add(subtask_id)

                        task_uuid = task_records[subtask_id]

                        self._mark_completed(task_uuid)

                # Continue loop so newly-unlocked tasks can be scheduled.
                continue

            # ---------------------------------------------------------
            # 5. No running tasks and pending tasks remain.
            #
            # If dependencies cannot be satisfied, this is a genuine
            # deadlock rather than a normal executor failure.
            # ---------------------------------------------------------

            if pending:

                blocked = {}

                for subtask_id in pending:
                    deps = dependency_manager.dependencies_of(
                        subtask_id
                    )

                    unresolved = [
                        dependency
                        for dependency in deps
                        if dependency not in completed
                    ]

                    blocked[subtask_id] = unresolved

                raise RuntimeError(
                    "Scheduler deadlock detected. "
                    f"Unresolved dependencies: {blocked}"
                )

        return self._ordered_results(
            plan=plan,
            results=results,
        )

    # -----------------------------------------------------------------
    # Task construction
    # -----------------------------------------------------------------

    def _build_tasks(
        self,
        *,
        plan: Plan,
        priority: int,
    ) -> list[ScheduledTask]:

        return [
            ScheduledTask(
                subtask_id=subtask.subtask_id,
                title=subtask.title,
                description=subtask.description,
                assigned_role=subtask.assigned_role,
                depends_on=list(subtask.depends_on),
                priority=priority,
            )
            for subtask in plan.subtasks
        ]

    def _create_task_records(
        self,
        *,
        parent_task_id: str,
        tasks: list[ScheduledTask],
    ) -> None:

        # First create all records so dependency references can point
        # to actual TaskManager task IDs.
        records: dict[str, Task] = {}

        for scheduled_task in tasks:
            task = self.task_manager.create_task(
                title=scheduled_task.title,
                description=scheduled_task.description,
                parent_task_id=parent_task_id,
                priority=scheduled_task.priority,
                assigned_agent=scheduled_task.assigned_role,
                dependencies=[],
            )

            task.metadata["subtask_id"] = scheduled_task.subtask_id
            task.metadata["depends_on"] = list(
                scheduled_task.depends_on
            )

            records[scheduled_task.subtask_id] = task

        # Store the TaskManager UUID on each ScheduledTask.
        for scheduled_task in tasks:
            scheduled_task.task_id = records[
                scheduled_task.subtask_id
            ].task_id

        # Now that every record exists, store actual TaskManager
        # dependency IDs.
        for scheduled_task in tasks:
            task = records[scheduled_task.subtask_id]

            task.dependencies = [
                records[dependency].task_id
                for dependency in scheduled_task.depends_on
                if dependency in records
            ]

    # -----------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------

    async def _execute_subtask(
        self,
        *,
        parent_task_id: str,
        task: ScheduledTask,
        task_uuid: str,
    ) -> ExecutionResult:

        return await self.runtime.execute(
            parent_task_id=parent_task_id,
            subtask_id=task.subtask_id,
            title=task.title,
            description=task.description,
            assigned_role=task.assigned_role,
            task_id=task_uuid,
        )

    # -----------------------------------------------------------------
    # Lifecycle helpers
    # -----------------------------------------------------------------

    def _mark_running(self, task_id: str) -> None:

        task = self.task_manager.get(task_id)

        if task.status == TaskStatus.PENDING:
            self.task_manager.update_status(
                task_id,
                TaskStatus.READY,
            )

        task = self.task_manager.get(task_id)

        if task.status == TaskStatus.READY:
            self.task_manager.update_status(
                task_id,
                TaskStatus.RUNNING,
            )

    def _mark_completed(self, task_id: str) -> None:

        task = self.task_manager.get(task_id)

        if task.status == TaskStatus.RUNNING:
            self.task_manager.update_status(
                task_id,
                TaskStatus.COMPLETED,
            )

    def _mark_failed(self, task_id: str) -> None:

        task = self.task_manager.get(task_id)

        if task.status == TaskStatus.PENDING:
            self.task_manager.update_status(
                task_id,
                TaskStatus.READY,
            )

            task = self.task_manager.get(task_id)

        if task.status == TaskStatus.READY:
            self.task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
            )

        elif task.status == TaskStatus.RUNNING:
            self.task_manager.update_status(
                task_id,
                TaskStatus.FAILED,
            )

    async def _stop_remaining_tasks(
        self,
        *,
        pending: set[str],
        task_records: dict[str, str],
    ) -> None:

        for subtask_id in list(pending):

            task_uuid = task_records.get(subtask_id)

            if task_uuid is None:
                continue

            try:
                task = self.task_manager.get(task_uuid)

                if task.status == TaskStatus.PENDING:
                    self.task_manager.update_status(
                        task_uuid,
                        TaskStatus.FAILED,
                    )

                elif task.status == TaskStatus.READY:
                    self.task_manager.update_status(
                        task_uuid,
                        TaskStatus.FAILED,
                    )

            except (KeyError, ValueError):
                # The workflow is already failing. Do not mask the
                # original executor failure with cleanup errors.
                continue

    # -----------------------------------------------------------------
    # Utility helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _find_task(
        tasks: list[ScheduledTask],
        subtask_id: str,
    ) -> ScheduledTask:

        for task in tasks:
            if task.subtask_id == subtask_id:
                return task

        raise KeyError(
            f"Unknown scheduled task: {subtask_id}"
        )

    @staticmethod
    def _priority_for(
        tasks: list[ScheduledTask],
        subtask_id: str,
    ) -> int:

        return Scheduler._find_task(
            tasks,
            subtask_id,
        ).priority

    @staticmethod
    def _ordered_results(
        *,
        plan: Plan,
        results: dict[str, ExecutionResult],
    ) -> list[ExecutionResult]:

        if plan.execution_order:
            ordered_ids = plan.execution_order
        else:
            ordered_ids = [
                subtask.subtask_id
                for subtask in plan.subtasks
            ]

        return [
            results[subtask_id]
            for subtask_id in ordered_ids
            if subtask_id in results
        ]