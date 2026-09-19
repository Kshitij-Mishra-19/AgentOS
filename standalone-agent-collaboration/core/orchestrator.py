# """The orchestrator: coordinates Planner, Executor, and Reviewer through the message bus.

# The orchestrator is the only component that knows the *shape* of the
# overall workflow (plan -> execute -> review -> approve/revise). Agents
# remain independently testable because they only ever see one message
# type at a time and reply with another -- none of them know about the
# loop, the revision limit, or each other.
# """

# from __future__ import annotations

# from dataclasses import dataclass, field
# from typing import Any, Optional

# from core.errors import (
#     ExecutorFailureError,
#     MaxRevisionCyclesExceededError,
#     OrchestrationError,
#     ReviewerFailureError,
# )
# from core.logging import get_logger, log_context
# from core.message_bus import MessageBus
# from core.state_manager import StateManager
# from core.task_manager import TaskManager
# from schemas.message import AgentMessage, MessageType
# from schemas.plan import Plan
# from schemas.result import ExecutionResult, ExecutionStatus
# from schemas.review import Review, ReviewDecision
# from schemas.task import TaskStatus

# logger = get_logger("orchestrator")


# @dataclass
# class WorkflowResult:
#     """The final, structured outcome of a single orchestrated workflow run."""

#     task_id: str
#     success: bool
#     status: str
#     final_output: dict[str, Any] = field(default_factory=dict)
#     revision_count: int = 0
#     review: Optional[dict[str, Any]] = None
#     error: Optional[str] = None
#     history: list[dict[str, Any]] = field(default_factory=list)

#     def to_dict(self) -> dict[str, Any]:
#         return {
#             "task_id": self.task_id,
#             "success": self.success,
#             "status": self.status,
#             "final_output": self.final_output,
#             "revision_count": self.revision_count,
#             "review": self.review,
#             "error": self.error,
#             "history": self.history,
#         }


# class Orchestrator:
#     """Coordinates a single task through the Planner -> Executor -> Reviewer lifecycle."""

#     def __init__(
#         self,
#         *,
#         bus: MessageBus,
#         task_manager: Optional[TaskManager] = None,
#         state_manager: Optional[StateManager] = None,
#         max_revision_cycles: int = 3,
#         fail_fast: bool = False,
#         require_review: bool = True,
#     ) -> None:
#         self.bus = bus
#         self.task_manager = task_manager or TaskManager()
#         self.state_manager = state_manager or StateManager()
#         self.max_revision_cycles = max_revision_cycles
#         self.fail_fast = fail_fast
#         self.require_review = require_review

#     async def run(self, title: str, description: str) -> WorkflowResult:
#         """Run the full Planner -> Executor -> Reviewer workflow for one user task."""
#         task = self.task_manager.create_task(title, description)
#         state = self.state_manager.create(task.task_id, f"{title}: {description}")

#         log_context(logger, "info", "task_created", task_id=task.task_id, title=title)

#         try:
#             revision_feedback = ""
#             for cycle in range(self.max_revision_cycles + 1):
#                 plan = await self._get_plan(task.task_id, title, description, revision_feedback)
#                 results = await self._execute_plan(task.task_id, plan)

#                 if not self.require_review:
#                     aggregate = self._aggregate_results(task.task_id, results)
#                     return self._finalize(task.task_id, aggregate, review=None)

#                 review = await self._review_results(task.task_id, title, description, results)

#                 if review.decision == ReviewDecision.APPROVED:
#                     aggregate = self._aggregate_results(task.task_id, results)
#                     return self._finalize(task.task_id, aggregate, review=review)

#                 # Rejected: record the revision and loop, unless we're out of budget.
#                 self.task_manager.update_status(task.task_id, TaskStatus.REVISION_REQUIRED)
#                 self.task_manager.increment_revision(task.task_id)
#                 self.state_manager.add_revision(
#                     task.task_id, reason="review_rejected", feedback=review.feedback
#                 )
#                 log_context(
#                     logger,
#                     "warning",
#                     "revision_requested",
#                     task_id=task.task_id,
#                     cycle=cycle,
#                     feedback=review.feedback,
#                 )

#                 if cycle >= self.max_revision_cycles:
#                     raise MaxRevisionCyclesExceededError(
#                         f"Task {task.task_id} exceeded max_revision_cycles="
#                         f"{self.max_revision_cycles} without approval.",
#                         details={"task_id": task.task_id},
#                     )

#                 revision_feedback = self._build_revision_feedback(review)

#             # Unreachable in practice (loop always returns or raises), but keeps
#             # type-checkers and readers honest about every code path.
#             raise OrchestrationError(f"Workflow for task {task.task_id} ended without a decision.")

#         except MaxRevisionCyclesExceededError as exc:
#             return self._fail(task.task_id, exc)
#         except (ExecutorFailureError, ReviewerFailureError, OrchestrationError) as exc:
#             return self._fail(task.task_id, exc)

#     async def _get_plan(
#         self, task_id: str, title: str, description: str, revision_feedback: str
#     ) -> Plan:
#         self.task_manager.update_status(task_id, TaskStatus.PLANNING)
#         message_type = MessageType.REVISION_REQUESTED if revision_feedback else MessageType.TASK_CREATED
#         message = AgentMessage(
#             sender="orchestrator",
#             recipient="planner",
#             message_type=message_type,
#             task_id=task_id,
#             payload={"title": title, "description": description, "feedback": revision_feedback},
#         )
#         replies = await self.bus.publish(message)
#         plan_payload = self._first_payload(replies, "plan", context="planner")
#         plan = Plan.from_dict(plan_payload)
#         self.state_manager.set_plan(task_id, plan)
#         self.task_manager.update_status(task_id, TaskStatus.READY)
#         return plan

#     async def _execute_plan(self, task_id: str, plan: Plan) -> list[ExecutionResult]:
#         self.task_manager.update_status(task_id, TaskStatus.RUNNING)
#         results: list[ExecutionResult] = []

#         order = plan.execution_order or [st.subtask_id for st in plan.subtasks]
#         subtasks_by_id = {st.subtask_id: st for st in plan.subtasks}

#         for subtask_id in order:
#             subtask = subtasks_by_id.get(subtask_id)
#             if subtask is None:
#                 continue

#             message = AgentMessage(
#                 sender="orchestrator",
#                 recipient="executor",
#                 message_type=MessageType.TASK_ASSIGNED,
#                 task_id=task_id,
#                 payload={
#                     "subtask_id": subtask.subtask_id,
#                     "title": subtask.title,
#                     "description": subtask.description,
#                 },
#             )
#             replies = await self.bus.publish(message)
#             reply = replies[0] if replies else None

#             if reply is None:
#                 raise ExecutorFailureError(
#                     f"Executor produced no reply for subtask {subtask.subtask_id}",
#                     details={"task_id": task_id},
#                 )

#             result = ExecutionResult.from_dict(reply.payload["result"])
#             results.append(result)
#             self.state_manager.add_agent_output(task_id, result)

#             if reply.message_type == MessageType.EXECUTION_FAILED:
#                 self.state_manager.add_error(task_id, "executor_failure", "; ".join(result.errors))
#                 if self.fail_fast:
#                     raise ExecutorFailureError(
#                         f"Executor failed subtask {subtask.subtask_id}: {result.errors}",
#                         details={"task_id": task_id, "subtask_id": subtask.subtask_id},
#                     )

#         return results

#     async def _review_results(
#         self, task_id: str, title: str, description: str, results: list[ExecutionResult]
#     ) -> Review:
#         self.task_manager.update_status(task_id, TaskStatus.REVIEWING)
#         aggregate = self._aggregate_results(task_id, results)

#         message = AgentMessage(
#             sender="orchestrator",
#             recipient="reviewer",
#             message_type=MessageType.REVIEW_REQUESTED,
#             task_id=task_id,
#             payload={
#                 "original_title": title,
#                 "original_description": description,
#                 "result": aggregate.to_dict(),
#             },
#         )
#         try:
#             replies = await self.bus.publish(message)
#         except Exception as exc:  # noqa: BLE001 - translate to a domain error
#             raise ReviewerFailureError(f"Reviewer failed to produce a review: {exc}") from exc

#         review_payload = self._first_payload(replies, "review", context="reviewer")
#         review = Review.from_dict(review_payload)
#         self.state_manager.add_review_result(task_id, review)
#         return review

#     def _aggregate_results(self, task_id: str, results: list[ExecutionResult]) -> ExecutionResult:
#         """Combine per-subtask results into one result representing the whole task."""
#         all_errors: list[str] = []
#         all_artifacts: list[str] = []
#         summaries: list[str] = []
#         combined_output: dict[str, Any] = {}

#         for idx, result in enumerate(results):
#             summaries.append(result.summary)
#             all_errors.extend(result.errors)
#             all_artifacts.extend(result.artifacts)
#             combined_output[f"subtask_{idx + 1}"] = result.output

#         overall_status = ExecutionStatus.SUCCESS
#         if any(r.status == ExecutionStatus.FAILED for r in results):
#             overall_status = ExecutionStatus.FAILED
#         elif any(r.status == ExecutionStatus.NEEDS_CLARIFICATION for r in results):
#             overall_status = ExecutionStatus.NEEDS_CLARIFICATION
#         elif any(r.status == ExecutionStatus.PARTIAL for r in results):
#             overall_status = ExecutionStatus.PARTIAL

#         return ExecutionResult(
#             task_id=task_id,
#             status=overall_status,
#             summary=" ".join(summaries) if summaries else "No subtasks executed.",
#             output=combined_output,
#             artifacts=all_artifacts,
#             errors=all_errors,
#         )

#     def _finalize(
#         self, task_id: str, result: ExecutionResult, review: Optional[Review]
#     ) -> WorkflowResult:
#         self.task_manager.update_status(task_id, TaskStatus.COMPLETED)
#         self.state_manager.set_workflow_state(task_id, "COMPLETED")
#         task = self.task_manager.get(task_id)
#         log_context(
#             logger,
#             "info",
#             "workflow_completed",
#             task_id=task_id,
#             revision_count=task.revision_count,
#         )
#         return WorkflowResult(
#             task_id=task_id,
#             success=True,
#             status=TaskStatus.COMPLETED.value,
#             final_output=result.to_dict(),
#             revision_count=task.revision_count,
#             review=review.to_dict() if review else None,
#             history=[m.to_dict() for m in self.bus.history if m.task_id == task_id],
#         )

#     def _fail(self, task_id: str, exc: Exception) -> WorkflowResult:
#         try:
#             self.task_manager.update_status(task_id, TaskStatus.FAILED)
#         except Exception:  # noqa: BLE001 - status may already be terminal
#             pass
#         self.state_manager.set_workflow_state(task_id, "FAILED")
#         self.state_manager.add_error(task_id, type(exc).__name__, str(exc))
#         task = self.task_manager.get(task_id)
#         log_context(logger, "error", "workflow_failed", task_id=task_id, error=str(exc))
#         return WorkflowResult(
#             task_id=task_id,
#             success=False,
#             status=TaskStatus.FAILED.value,
#             revision_count=task.revision_count,
#             error=str(exc),
#             history=[m.to_dict() for m in self.bus.history if m.task_id == task_id],
#         )

#     @staticmethod
#     def _build_revision_feedback(review: Review) -> str:
#         parts = [review.feedback] if review.feedback else []
#         if review.required_changes:
#             parts.append("Required changes: " + "; ".join(review.required_changes))
#         if review.issues:
#             parts.append("Issues: " + "; ".join(review.issues))
#         return " ".join(parts) if parts else "Reviewer rejected the result without detailed feedback."

#     @staticmethod
#     def _first_payload(replies: list[AgentMessage], key: str, *, context: str) -> dict[str, Any]:
#         if not replies:
#             raise OrchestrationError(f"No reply received from {context}.")
#         payload = replies[0].payload
#         if key not in payload:
#             raise OrchestrationError(f"Reply from {context} is missing expected key '{key}'.")
#         return payload[key]

"""
Orchestrator for the standalone multi-agent workflow.

Flow:

    User Task
       |
       v
    Planner
       |
       v
    Executor
       |
       v
    Reviewer
       |
       +---- APPROVED ----> COMPLETED
       |
       +---- REJECTED ----> REVISION -> Planner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.errors import (
    ExecutorFailureError,
    MaxRevisionCyclesExceededError,
    OrchestrationError,
    ReviewerFailureError,
)

from core.logging import get_logger, log_context
from core.message_bus import MessageBus
from core.state_manager import StateManager
from core.task_manager import TaskManager

from schemas.message import AgentMessage, MessageType
from schemas.plan import Plan
from schemas.result import ExecutionResult, ExecutionStatus
from schemas.review import Review, ReviewDecision
from schemas.task import TaskStatus


logger = get_logger("orchestrator")


# ============================================================
# WORKFLOW RESULT
# ============================================================

@dataclass
class WorkflowResult:
    task_id: str
    success: bool
    status: str

    final_output: dict[str, Any] = field(default_factory=dict)

    revision_count: int = 0

    review: Optional[dict[str, Any]] = None

    error: Optional[str] = None

    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "status": self.status,
            "final_output": self.final_output,
            "revision_count": self.revision_count,
            "review": self.review,
            "error": self.error,
            "history": self.history,
        }


# ============================================================
# ORCHESTRATOR
# ============================================================

class Orchestrator:
    """
    Coordinates:

        Planner -> Executor -> Reviewer

    The MessageBus owns the actual agent handlers.

    IMPORTANT:
    We do NOT instantiate PlannerAgent(bus=...)
    or ReviewerAgent(bus=...).

    Tests already register their handlers on MessageBus.
    """

    def __init__(
        self,
        *,
        bus: MessageBus,
        task_manager: Optional[TaskManager] = None,
        state_manager: Optional[StateManager] = None,
        max_revision_cycles: int = 3,
        fail_fast: bool = False,
        require_review: bool = True,
    ) -> None:

        self.bus = bus

        self.task_manager = (
            task_manager
            if task_manager is not None
            else TaskManager()
        )

        self.state_manager = (
            state_manager
            if state_manager is not None
            else StateManager()
        )

        self.max_revision_cycles = max_revision_cycles
        self.fail_fast = fail_fast
        self.require_review = require_review

    # ========================================================
    # PUBLIC API
    # ========================================================

    async def run(
        self,
        title: str,
        description: str,
        priority: int = 3,
        assigned_agent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> WorkflowResult:

        # ----------------------------------------------------
        # IMPORTANT:
        # TaskManager.create_task DOES NOT accept metadata.
        # Therefore metadata is intentionally NOT passed here.
        # ----------------------------------------------------

        task = self.task_manager.create_task(
            title,
            description,
            priority=priority,
            assigned_agent=assigned_agent,
        )

        # Store metadata only after task creation, if supported.
        if metadata:
            task_metadata = getattr(task, "metadata", None)

            if isinstance(task_metadata, dict):
                task_metadata.update(metadata)

        # StateManager API used by this project.
        self.state_manager.create(
            task.task_id,
            f"{title}: {description}",
        )

        log_context(
            logger,
            "info",
            "task_created",
            task_id=task.task_id,
            title=title,
        )

        revision_feedback = ""

        try:

            # ------------------------------------------------
            # Revision cycle
            #
            # cycle = 0 -> first execution
            # cycle = 1 -> first revision
            # cycle = 2 -> second revision
            # ...
            # ------------------------------------------------

            for cycle in range(self.max_revision_cycles + 1):

                # --------------------------------------------
                # 1. PLANNER
                # --------------------------------------------

                plan = await self._get_plan(
                    task_id=task.task_id,
                    title=title,
                    description=description,
                    revision_feedback=revision_feedback,
                )

                # --------------------------------------------
                # 2. EXECUTOR
                # --------------------------------------------

                results = await self._execute_plan(
                    task_id=task.task_id,
                    plan=plan,
                )

                # --------------------------------------------
                # No reviewer mode
                # --------------------------------------------

                if not self.require_review:

                    aggregate = self._aggregate_results(
                        task.task_id,
                        results,
                    )

                    return self._finalize(
                        task.task_id,
                        aggregate,
                        review=None,
                    )

                # --------------------------------------------
                # 3. REVIEWER
                # --------------------------------------------

                review = await self._review_results(
                    task_id=task.task_id,
                    title=title,
                    description=description,
                    results=results,
                )

                # --------------------------------------------
                # APPROVED
                # --------------------------------------------

                if review.decision == ReviewDecision.APPROVED:

                    aggregate = self._aggregate_results(
                        task.task_id,
                        results,
                    )

                    return self._finalize(
                        task.task_id,
                        aggregate,
                        review=review,
                    )

                # --------------------------------------------
                # REJECTED
                # --------------------------------------------

                self.task_manager.update_status(
                    task.task_id,
                    TaskStatus.REVISION_REQUIRED,
                )

                self.task_manager.increment_revision(
                    task.task_id
                )

                self.state_manager.add_revision(
                    task.task_id,
                    reason="review_rejected",
                    feedback=review.feedback,
                )

                log_context(
                    logger,
                    "warning",
                    "revision_requested",
                    task_id=task.task_id,
                    cycle=cycle,
                    feedback=review.feedback,
                )

                # --------------------------------------------
                # Revision limit reached
                # --------------------------------------------

                if cycle >= self.max_revision_cycles:

                    raise MaxRevisionCyclesExceededError(
                        f"Task {task.task_id} exceeded "
                        f"max_revision_cycles="
                        f"{self.max_revision_cycles} "
                        f"without approval.",
                        details={
                            "task_id": task.task_id,
                        },
                    )

                revision_feedback = (
                    self._build_revision_feedback(review)
                )

            raise OrchestrationError(
                f"Workflow for task {task.task_id} "
                f"ended without a decision."
            )

        except MaxRevisionCyclesExceededError as exc:

            return self._fail(
                task.task_id,
                exc,
            )

        except (
            ExecutorFailureError,
            ReviewerFailureError,
            OrchestrationError,
        ) as exc:

            return self._fail(
                task.task_id,
                exc,
            )

        except Exception as exc:

            # Final safety net so the orchestrator never
            # leaks an unexpected exception to the caller.

            return self._fail(
                task.task_id,
                exc,
            )

    # ========================================================
    # PLANNER
    # ========================================================

    async def _get_plan(
        self,
        task_id: str,
        title: str,
        description: str,
        revision_feedback: str = "",
    ) -> Plan:

        # PENDING -> PLANNING
        #
        # On revision:
        #
        # REVISION_REQUIRED -> PLANNING

        current_task = self.task_manager.get(task_id)

        if current_task.status == TaskStatus.PENDING:

            self.task_manager.update_status(
                task_id,
                TaskStatus.PLANNING,
            )

        elif current_task.status == TaskStatus.REVISION_REQUIRED:

            self.task_manager.update_status(
                task_id,
                TaskStatus.PLANNING,
            )

        log_context(
            logger,
            "info",
            "planning_requested",
            task_id=task_id,
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # There is NO MessageType.PLAN_REQUESTED.
        #
        # Planner is triggered by TASK_CREATED on first run
        # and REVISION_REQUESTED on revision.
        # ----------------------------------------------------

        if revision_feedback:

            message_type = MessageType.REVISION_REQUESTED

        else:

            message_type = MessageType.TASK_CREATED

        message = AgentMessage(
            sender="orchestrator",
            recipient="planner",
            message_type=message_type,
            task_id=task_id,
            payload={
                "title": title,
                "description": description,
                "feedback": revision_feedback,
            },
        )

        try:

            replies = await self.bus.publish(
                message
            )

        except Exception as exc:

            raise OrchestrationError(
                f"Planner failed to produce a plan: {exc}"
            ) from exc

        plan_payload = self._first_payload(
            replies,
            "plan",
            context="planner",
        )

        try:

            plan = Plan.from_dict(
                plan_payload
            )

        except Exception as exc:

            raise OrchestrationError(
                f"Invalid plan received from planner: {exc}"
            ) from exc

        self.state_manager.set_plan(
            task_id,
            plan,
        )

        # PLANNING -> READY
        self.task_manager.update_status(
            task_id,
            TaskStatus.READY,
        )

        return plan

    # ========================================================
    # EXECUTOR
    # ========================================================

    async def _execute_plan(
        self,
        task_id: str,
        plan: Plan,
    ) -> list[ExecutionResult]:

        # READY -> RUNNING
        self.task_manager.update_status(
            task_id,
            TaskStatus.RUNNING,
        )

        results: list[ExecutionResult] = []

        # Respect planner execution order.
        order = (
            plan.execution_order
            if plan.execution_order
            else [
                subtask.subtask_id
                for subtask in plan.subtasks
            ]
        )

        subtasks_by_id = {
            subtask.subtask_id: subtask
            for subtask in plan.subtasks
        }

        for subtask_id in order:

            subtask = subtasks_by_id.get(
                subtask_id
            )

            if subtask is None:

                raise ExecutorFailureError(
                    f"Planner referenced unknown subtask "
                    f"{subtask_id}",
                    details={
                        "task_id": task_id,
                        "subtask_id": subtask_id,
                    },
                )

            message = AgentMessage(
                sender="orchestrator",
                recipient="executor",
                message_type=MessageType.TASK_ASSIGNED,
                task_id=task_id,
                payload={
                    "subtask_id": subtask.subtask_id,
                    "title": subtask.title,
                    "description": subtask.description,
                },
            )

            try:

                replies = await self.bus.publish(
                    message
                )

            except Exception as exc:

                raise ExecutorFailureError(
                    f"Executor failed while executing "
                    f"subtask {subtask.subtask_id}: {exc}",
                    details={
                        "task_id": task_id,
                        "subtask_id": subtask.subtask_id,
                    },
                ) from exc

            if not replies:

                raise ExecutorFailureError(
                    f"Executor produced no reply for "
                    f"subtask {subtask.subtask_id}",
                    details={
                        "task_id": task_id,
                        "subtask_id": subtask.subtask_id,
                    },
                )

            reply = replies[0]

            # ------------------------------------------------
            # Validate executor response
            # ------------------------------------------------

            if not isinstance(reply.payload, dict):

                raise ExecutorFailureError(
                    f"Executor returned invalid payload "
                    f"for subtask {subtask.subtask_id}",
                    details={
                        "task_id": task_id,
                        "subtask_id": subtask.subtask_id,
                    },
                )

            result_payload = reply.payload.get(
                "result"
            )

            if result_payload is None:

                raise ExecutorFailureError(
                    f"Executor reply is missing result "
                    f"for subtask {subtask.subtask_id}",
                    details={
                        "task_id": task_id,
                        "subtask_id": subtask.subtask_id,
                    },
                )

            try:

                result = ExecutionResult.from_dict(
                    result_payload
                )

            except Exception as exc:

                raise ExecutorFailureError(
                    f"Invalid executor result for "
                    f"subtask {subtask.subtask_id}: {exc}",
                    details={
                        "task_id": task_id,
                        "subtask_id": subtask.subtask_id,
                    },
                ) from exc

            results.append(result)

            self.state_manager.add_agent_output(
                task_id,
                result,
            )

            # ------------------------------------------------
            # Executor failure
            # ------------------------------------------------

            if (
                reply.message_type
                == MessageType.EXECUTION_FAILED
            ):

                error_text = "; ".join(
                    result.errors
                )

                self.state_manager.add_error(
                    task_id,
                    "executor_failure",
                    error_text,
                )

                if self.fail_fast:

                    raise ExecutorFailureError(
                        f"Executor failed subtask "
                        f"{subtask.subtask_id}: "
                        f"{error_text}",
                        details={
                            "task_id": task_id,
                            "subtask_id": subtask.subtask_id,
                        },
                    )

        return results

    # ========================================================
    # REVIEWER
    # ========================================================

    async def _review_results(
        self,
        task_id: str,
        title: str,
        description: str,
        results: list[ExecutionResult],
    ) -> Review:

        # RUNNING -> REVIEWING
        self.task_manager.update_status(
            task_id,
            TaskStatus.REVIEWING,
        )

        aggregate = self._aggregate_results(
            task_id,
            results,
        )

        message = AgentMessage(
            sender="orchestrator",
            recipient="reviewer",
            message_type=MessageType.REVIEW_REQUESTED,
            task_id=task_id,
            payload={
                "original_title": title,
                "original_description": description,
                "result": aggregate.to_dict(),
            },
        )

        try:

            replies = await self.bus.publish(
                message
            )

        except Exception as exc:

            raise ReviewerFailureError(
                f"Reviewer failed to produce a review: "
                f"{exc}"
            ) from exc

        review_payload = self._first_payload(
            replies,
            "review",
            context="reviewer",
        )

        try:

            review = Review.from_dict(
                review_payload
            )

        except Exception as exc:

            raise ReviewerFailureError(
                f"Invalid review received from reviewer: "
                f"{exc}"
            ) from exc

        self.state_manager.add_review_result(
            task_id,
            review,
        )

        return review

    # ========================================================
    # AGGREGATE RESULTS
    # ========================================================

    def _aggregate_results(
        self,
        task_id: str,
        results: list[ExecutionResult],
    ) -> ExecutionResult:

        all_errors: list[str] = []
        all_artifacts: list[str] = []
        summaries: list[str] = []

        combined_output: dict[str, Any] = {}

        for index, result in enumerate(results):

            summaries.append(
                result.summary
            )

            all_errors.extend(
                result.errors
            )

            all_artifacts.extend(
                result.artifacts
            )

            combined_output[
                f"subtask_{index + 1}"
            ] = result.output

        # ----------------------------------------------------
        # Determine aggregate execution status
        # ----------------------------------------------------

        overall_status = ExecutionStatus.SUCCESS

        if any(
            result.status == ExecutionStatus.FAILED
            for result in results
        ):

            overall_status = ExecutionStatus.FAILED

        elif any(
            result.status
            == ExecutionStatus.NEEDS_CLARIFICATION
            for result in results
        ):

            overall_status = (
                ExecutionStatus.NEEDS_CLARIFICATION
            )

        elif any(
            result.status == ExecutionStatus.PARTIAL
            for result in results
        ):

            overall_status = ExecutionStatus.PARTIAL

        return ExecutionResult(
            task_id=task_id,
            status=overall_status,
            summary=(
                " ".join(summaries)
                if summaries
                else "No subtasks executed."
            ),
            output=combined_output,
            artifacts=all_artifacts,
            errors=all_errors,
        )

    # ========================================================
    # FINALIZE
    # ========================================================

    def _finalize(
        self,
        task_id: str,
        result: ExecutionResult,
        review: Optional[Review],
    ) -> WorkflowResult:

        self.task_manager.update_status(
            task_id,
            TaskStatus.COMPLETED,
        )

        self.state_manager.set_workflow_state(
            task_id,
            "COMPLETED",
        )

        task = self.task_manager.get(
            task_id
        )

        log_context(
            logger,
            "info",
            "workflow_completed",
            task_id=task_id,
            revision_count=task.revision_count,
        )

        return WorkflowResult(
            task_id=task_id,
            success=True,
            status=TaskStatus.COMPLETED.value,
            final_output=result.to_dict(),
            revision_count=task.revision_count,
            review=(
                review.to_dict()
                if review is not None
                else None
            ),
            history=[
                message.to_dict()
                for message in self.bus.history
                if message.task_id == task_id
            ],
        )

    # ========================================================
    # FAILURE
    # ========================================================

    def _fail(
        self,
        task_id: str,
        exc: Exception,
    ) -> WorkflowResult:

        try:

            current_task = self.task_manager.get(
                task_id
            )

            if current_task.status not in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:

                self.task_manager.update_status(
                    task_id,
                    TaskStatus.FAILED,
                )

        except Exception:
            # Do not hide the original workflow error.
            pass

        try:

            self.state_manager.set_workflow_state(
                task_id,
                "FAILED",
            )

        except Exception:
            pass

        try:

            self.state_manager.add_error(
                task_id,
                type(exc).__name__,
                str(exc),
            )

        except Exception:
            pass

        task = self.task_manager.get(
            task_id
        )

        log_context(
            logger,
            "error",
            "workflow_failed",
            task_id=task_id,
            error=str(exc),
        )

        return WorkflowResult(
            task_id=task_id,
            success=False,
            status=TaskStatus.FAILED.value,
            revision_count=task.revision_count,
            error=str(exc),
            history=[
                message.to_dict()
                for message in self.bus.history
                if message.task_id == task_id
            ],
        )

    # ========================================================
    # REVISION FEEDBACK
    # ========================================================

    @staticmethod
    def _build_revision_feedback(
        review: Review,
    ) -> str:

        parts: list[str] = []

        if review.feedback:

            parts.append(
                review.feedback
            )

        if review.required_changes:

            parts.append(
                "Required changes: "
                + "; ".join(
                    review.required_changes
                )
            )

        if review.issues:

            parts.append(
                "Issues: "
                + "; ".join(
                    review.issues
                )
            )

        if not parts:

            return (
                "Reviewer rejected the result "
                "without detailed feedback."
            )

        return " ".join(parts)

    # ========================================================
    # RESPONSE EXTRACTION
    # ========================================================

    @staticmethod
    def _first_payload(
        replies: list[AgentMessage],
        key: str,
        *,
        context: str,
    ) -> dict[str, Any]:

        if not replies:

            raise OrchestrationError(
                f"No reply received from {context}."
            )

        for reply in replies:

            payload = reply.payload

            if not isinstance(payload, dict):
                continue

            value = payload.get(key)

            if isinstance(value, dict):

                return value

        raise OrchestrationError(
            f"Reply from {context} is missing "
            f"expected key '{key}'."
        )