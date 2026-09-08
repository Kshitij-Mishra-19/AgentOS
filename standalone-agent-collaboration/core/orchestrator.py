"""The orchestrator: coordinates Planner, Executor, and Reviewer through the message bus.

The orchestrator is the only component that knows the *shape* of the
overall workflow (plan -> execute -> review -> approve/revise). Agents
remain independently testable because they only ever see one message
type at a time and reply with another -- none of them know about the
loop, the revision limit, or each other.
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


@dataclass
class WorkflowResult:
    """The final, structured outcome of a single orchestrated workflow run."""

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


class Orchestrator:
    """Coordinates a single task through the Planner -> Executor -> Reviewer lifecycle."""

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
        self.task_manager = task_manager or TaskManager()
        self.state_manager = state_manager or StateManager()
        self.max_revision_cycles = max_revision_cycles
        self.fail_fast = fail_fast
        self.require_review = require_review

    async def run(self, title: str, description: str) -> WorkflowResult:
        """Run the full Planner -> Executor -> Reviewer workflow for one user task."""
        task = self.task_manager.create_task(title, description)
        state = self.state_manager.create(task.task_id, f"{title}: {description}")

        log_context(logger, "info", "task_created", task_id=task.task_id, title=title)

        try:
            revision_feedback = ""
            for cycle in range(self.max_revision_cycles + 1):
                plan = await self._get_plan(task.task_id, title, description, revision_feedback)
                results = await self._execute_plan(task.task_id, plan)

                if not self.require_review:
                    aggregate = self._aggregate_results(task.task_id, results)
                    return self._finalize(task.task_id, aggregate, review=None)

                review = await self._review_results(task.task_id, title, description, results)

                if review.decision == ReviewDecision.APPROVED:
                    aggregate = self._aggregate_results(task.task_id, results)
                    return self._finalize(task.task_id, aggregate, review=review)

                # Rejected: record the revision and loop, unless we're out of budget.
                self.task_manager.update_status(task.task_id, TaskStatus.REVISION_REQUIRED)
                self.task_manager.increment_revision(task.task_id)
                self.state_manager.add_revision(
                    task.task_id, reason="review_rejected", feedback=review.feedback
                )
                log_context(
                    logger,
                    "warning",
                    "revision_requested",
                    task_id=task.task_id,
                    cycle=cycle,
                    feedback=review.feedback,
                )

                if cycle >= self.max_revision_cycles:
                    raise MaxRevisionCyclesExceededError(
                        f"Task {task.task_id} exceeded max_revision_cycles="
                        f"{self.max_revision_cycles} without approval.",
                        details={"task_id": task.task_id},
                    )

                revision_feedback = self._build_revision_feedback(review)

            # Unreachable in practice (loop always returns or raises), but keeps
            # type-checkers and readers honest about every code path.
            raise OrchestrationError(f"Workflow for task {task.task_id} ended without a decision.")

        except MaxRevisionCyclesExceededError as exc:
            return self._fail(task.task_id, exc)
        except (ExecutorFailureError, ReviewerFailureError, OrchestrationError) as exc:
            return self._fail(task.task_id, exc)

    async def _get_plan(
        self, task_id: str, title: str, description: str, revision_feedback: str
    ) -> Plan:
        self.task_manager.update_status(task_id, TaskStatus.PLANNING)
        message_type = MessageType.REVISION_REQUESTED if revision_feedback else MessageType.TASK_CREATED
        message = AgentMessage(
            sender="orchestrator",
            recipient="planner",
            message_type=message_type,
            task_id=task_id,
            payload={"title": title, "description": description, "feedback": revision_feedback},
        )
        replies = await self.bus.publish(message)
        plan_payload = self._first_payload(replies, "plan", context="planner")
        plan = Plan.from_dict(plan_payload)
        self.state_manager.set_plan(task_id, plan)
        self.task_manager.update_status(task_id, TaskStatus.READY)
        return plan

    async def _execute_plan(self, task_id: str, plan: Plan) -> list[ExecutionResult]:
        self.task_manager.update_status(task_id, TaskStatus.RUNNING)
        results: list[ExecutionResult] = []

        order = plan.execution_order or [st.subtask_id for st in plan.subtasks]
        subtasks_by_id = {st.subtask_id: st for st in plan.subtasks}

        for subtask_id in order:
            subtask = subtasks_by_id.get(subtask_id)
            if subtask is None:
                continue

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
            replies = await self.bus.publish(message)
            reply = replies[0] if replies else None

            if reply is None:
                raise ExecutorFailureError(
                    f"Executor produced no reply for subtask {subtask.subtask_id}",
                    details={"task_id": task_id},
                )

            result = ExecutionResult.from_dict(reply.payload["result"])
            results.append(result)
            self.state_manager.add_agent_output(task_id, result)

            if reply.message_type == MessageType.EXECUTION_FAILED:
                self.state_manager.add_error(task_id, "executor_failure", "; ".join(result.errors))
                if self.fail_fast:
                    raise ExecutorFailureError(
                        f"Executor failed subtask {subtask.subtask_id}: {result.errors}",
                        details={"task_id": task_id, "subtask_id": subtask.subtask_id},
                    )

        return results

    async def _review_results(
        self, task_id: str, title: str, description: str, results: list[ExecutionResult]
    ) -> Review:
        self.task_manager.update_status(task_id, TaskStatus.REVIEWING)
        aggregate = self._aggregate_results(task_id, results)

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
            replies = await self.bus.publish(message)
        except Exception as exc:  # noqa: BLE001 - translate to a domain error
            raise ReviewerFailureError(f"Reviewer failed to produce a review: {exc}") from exc

        review_payload = self._first_payload(replies, "review", context="reviewer")
        review = Review.from_dict(review_payload)
        self.state_manager.add_review_result(task_id, review)
        return review

    def _aggregate_results(self, task_id: str, results: list[ExecutionResult]) -> ExecutionResult:
        """Combine per-subtask results into one result representing the whole task."""
        all_errors: list[str] = []
        all_artifacts: list[str] = []
        summaries: list[str] = []
        combined_output: dict[str, Any] = {}

        for idx, result in enumerate(results):
            summaries.append(result.summary)
            all_errors.extend(result.errors)
            all_artifacts.extend(result.artifacts)
            combined_output[f"subtask_{idx + 1}"] = result.output

        overall_status = ExecutionStatus.SUCCESS
        if any(r.status == ExecutionStatus.FAILED for r in results):
            overall_status = ExecutionStatus.FAILED
        elif any(r.status == ExecutionStatus.NEEDS_CLARIFICATION for r in results):
            overall_status = ExecutionStatus.NEEDS_CLARIFICATION
        elif any(r.status == ExecutionStatus.PARTIAL for r in results):
            overall_status = ExecutionStatus.PARTIAL

        return ExecutionResult(
            task_id=task_id,
            status=overall_status,
            summary=" ".join(summaries) if summaries else "No subtasks executed.",
            output=combined_output,
            artifacts=all_artifacts,
            errors=all_errors,
        )

    def _finalize(
        self, task_id: str, result: ExecutionResult, review: Optional[Review]
    ) -> WorkflowResult:
        self.task_manager.update_status(task_id, TaskStatus.COMPLETED)
        self.state_manager.set_workflow_state(task_id, "COMPLETED")
        task = self.task_manager.get(task_id)
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
            review=review.to_dict() if review else None,
            history=[m.to_dict() for m in self.bus.history if m.task_id == task_id],
        )

    def _fail(self, task_id: str, exc: Exception) -> WorkflowResult:
        try:
            self.task_manager.update_status(task_id, TaskStatus.FAILED)
        except Exception:  # noqa: BLE001 - status may already be terminal
            pass
        self.state_manager.set_workflow_state(task_id, "FAILED")
        self.state_manager.add_error(task_id, type(exc).__name__, str(exc))
        task = self.task_manager.get(task_id)
        log_context(logger, "error", "workflow_failed", task_id=task_id, error=str(exc))
        return WorkflowResult(
            task_id=task_id,
            success=False,
            status=TaskStatus.FAILED.value,
            revision_count=task.revision_count,
            error=str(exc),
            history=[m.to_dict() for m in self.bus.history if m.task_id == task_id],
        )

    @staticmethod
    def _build_revision_feedback(review: Review) -> str:
        parts = [review.feedback] if review.feedback else []
        if review.required_changes:
            parts.append("Required changes: " + "; ".join(review.required_changes))
        if review.issues:
            parts.append("Issues: " + "; ".join(review.issues))
        return " ".join(parts) if parts else "Reviewer rejected the result without detailed feedback."

    @staticmethod
    def _first_payload(replies: list[AgentMessage], key: str, *, context: str) -> dict[str, Any]:
        if not replies:
            raise OrchestrationError(f"No reply received from {context}.")
        payload = replies[0].payload
        if key not in payload:
            raise OrchestrationError(f"Reply from {context} is missing expected key '{key}'.")
        return payload[key]
