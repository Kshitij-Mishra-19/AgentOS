"""Unit tests for the Planner, Executor, and Reviewer agents in isolation.

Each agent is tested purely through its `handle(message) -> message`
interface, using the deterministic MockLLMProvider, with no message bus
or orchestrator involved -- this is what "independently testable" means
in practice.
"""

from __future__ import annotations

import pytest

from schemas.message import AgentMessage, MessageType
from schemas.plan import Plan
from schemas.result import ExecutionResult, ExecutionStatus
from schemas.review import Review, ReviewDecision


@pytest.mark.asyncio
async def test_planner_generates_a_valid_plan(planner_agent):
    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
        payload={"title": "Launch website", "description": "Plan a website launch."},
    )

    reply = await planner_agent.handle(message)

    assert reply.message_type == MessageType.PLAN_CREATED
    plan = Plan.from_dict(reply.payload["plan"])
    assert plan.validate() == []
    assert len(plan.subtasks) > 0
    assert reply.correlation_id == message.correlation_id


@pytest.mark.asyncio
async def test_planner_rejects_unsupported_message_type(planner_agent):
    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.EXECUTION_COMPLETED,
        task_id="task-1",
        payload={},
    )
    with pytest.raises(Exception):
        await planner_agent.handle(message)


@pytest.mark.asyncio
async def test_executor_produces_a_valid_result(executor_agent):
    message = AgentMessage(
        sender="orchestrator",
        recipient="executor",
        message_type=MessageType.TASK_ASSIGNED,
        task_id="task-1",
        payload={
            "subtask_id": "subtask-1",
            "title": "Research requirements",
            "description": "Gather requirements for the website launch.",
        },
    )

    reply = await executor_agent.handle(message)

    assert reply.message_type == MessageType.EXECUTION_COMPLETED
    result = ExecutionResult.from_dict(reply.payload["result"])
    assert result.status == ExecutionStatus.SUCCESS
    assert result.errors == []


@pytest.mark.asyncio
async def test_executor_reports_failure_explicitly(executor_agent):
    message = AgentMessage(
        sender="orchestrator",
        recipient="executor",
        message_type=MessageType.TASK_ASSIGNED,
        task_id="task-1",
        payload={
            "subtask_id": "subtask-1",
            "title": "Research requirements",
            "description": "Gather requirements.",
            "force_failure": True,
        },
    )

    reply = await executor_agent.handle(message)

    assert reply.message_type == MessageType.EXECUTION_FAILED
    result = ExecutionResult.from_dict(reply.payload["result"])
    assert result.status == ExecutionStatus.FAILED
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_reviewer_approves_valid_output(reviewer_agent):
    execution_result = ExecutionResult(
        task_id="subtask-1",
        status=ExecutionStatus.SUCCESS,
        summary="Completed the research subtask.",
        output={"content": "requirements gathered"},
    )
    message = AgentMessage(
        sender="orchestrator",
        recipient="reviewer",
        message_type=MessageType.REVIEW_REQUESTED,
        task_id="task-1",
        payload={
            "original_title": "Launch website",
            "original_description": "Plan a website launch.",
            "result": execution_result.to_dict(),
        },
    )

    reply = await reviewer_agent.handle(message)

    assert reply.message_type == MessageType.REVIEW_APPROVED
    review = Review.from_dict(reply.payload["review"])
    assert review.decision == ReviewDecision.APPROVED


@pytest.mark.asyncio
async def test_reviewer_rejects_invalid_output(reviewer_agent):
    execution_result = ExecutionResult(
        task_id="subtask-1",
        status=ExecutionStatus.FAILED,
        summary="Could not complete the subtask.",
        errors=["Something went wrong."],
    )
    message = AgentMessage(
        sender="orchestrator",
        recipient="reviewer",
        message_type=MessageType.REVIEW_REQUESTED,
        task_id="task-1",
        payload={
            "original_title": "Launch website",
            "original_description": "Plan a website launch.",
            "result": execution_result.to_dict(),
        },
    )

    reply = await reviewer_agent.handle(message)

    assert reply.message_type == MessageType.REVIEW_REJECTED
    review = Review.from_dict(reply.payload["review"])
    assert review.decision == ReviewDecision.REJECTED
    assert review.required_changes
