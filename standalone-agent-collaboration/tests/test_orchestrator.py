"""Orchestration-level tests exercising the full Planner -> Executor -> Reviewer loop.

Where a scenario needs a deterministic failure that the default
MockLLMProvider wouldn't naturally produce end-to-end (e.g. "the
Executor fails"), a small stub handler is subscribed directly to the
bus in place of the real agent. This keeps the orchestrator test
focused on *orchestration behavior* (routing, status transitions,
fail_fast, error translation) rather than re-testing agent internals,
which are already covered in test_agents.py.
"""

from __future__ import annotations

import pytest

from core.errors import ExecutorFailureError
from core.message_bus import MessageBus
from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from core.task_manager import TaskManager
from schemas.message import MessageType
from schemas.result import ExecutionResult, ExecutionStatus
from schemas.task import TaskStatus


@pytest.mark.asyncio
async def test_successful_workflow_completes_without_revisions(wired_bus):
    orchestrator = Orchestrator(
        bus=wired_bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=3,
        fail_fast=False,
    )

    result = await orchestrator.run(
        "Launch website", "Create a simple project plan for launching a website."
    )

    assert result.success is True
    assert result.status == TaskStatus.COMPLETED.value
    assert result.revision_count == 0
    assert result.review is not None
    assert result.review["decision"] == "APPROVED"
    task = orchestrator.task_manager.get(result.task_id)
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_orchestrator_returns_final_structured_result_shape(wired_bus):
    orchestrator = Orchestrator(bus=wired_bus, max_revision_cycles=3)

    result = await orchestrator.run("Write docs", "Write documentation for the API.")

    result_dict = result.to_dict()
    for key in ("task_id", "success", "status", "final_output", "revision_count", "review", "history"):
        assert key in result_dict
    assert len(result_dict["history"]) > 0


@pytest.mark.asyncio
async def test_executor_failure_with_fail_fast_stops_the_workflow(planner_agent, reviewer_agent):
    bus = MessageBus()
    bus.subscribe("planner", planner_agent.handle)
    bus.subscribe("reviewer", reviewer_agent.handle)

    async def always_fails(message):
        result = ExecutionResult(
            task_id=message.payload["subtask_id"],
            status=ExecutionStatus.FAILED,
            summary="Simulated hard failure.",
            errors=["Stub executor always fails."],
        )
        return message.reply(
            sender="executor",
            message_type=MessageType.EXECUTION_FAILED,
            payload={"result": result.to_dict()},
        )

    bus.subscribe("executor", always_fails)

    orchestrator = Orchestrator(
        bus=bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=3,
        fail_fast=True,
    )

    result = await orchestrator.run("Do something", "A task whose executor always fails.")

    assert result.success is False
    assert result.status == TaskStatus.FAILED.value
    assert "always fails" in (result.error or "") or "Executor failed" in (result.error or "")
    task = orchestrator.task_manager.get(result.task_id)
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_executor_failure_without_fail_fast_is_forwarded_to_reviewer(
    planner_agent, reviewer_agent
):
    bus = MessageBus()
    bus.subscribe("planner", planner_agent.handle)
    bus.subscribe("reviewer", reviewer_agent.handle)

    call_count = {"n": 0}

    async def fails_then_would_retry(message):
        call_count["n"] += 1
        result = ExecutionResult(
            task_id=message.payload["subtask_id"],
            status=ExecutionStatus.FAILED,
            summary="Simulated soft failure.",
            errors=["Stub executor failure."],
        )
        return message.reply(
            sender="executor",
            message_type=MessageType.EXECUTION_FAILED,
            payload={"result": result.to_dict()},
        )

    bus.subscribe("executor", fails_then_would_retry)

    orchestrator = Orchestrator(
        bus=bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=1,
        fail_fast=False,
    )

    result = await orchestrator.run("Do something", "A task whose executor keeps failing.")

    # Reviewer auto-rejects any result carrying reported errors, so with a
    # revision budget of 1 the workflow should exhaust its cycles and fail
    # cleanly rather than raising an unhandled exception.
    assert result.success is False
    assert result.status == TaskStatus.FAILED.value
    assert call_count["n"] > 0
