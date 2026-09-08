"""Tests for the iterative review -> revision -> re-review cycle.

These tests use a small scripted Reviewer stub (subscribed directly to
the bus) so the sequence of decisions (reject, then approve; or always
reject) is fully deterministic, independent of the MockLLMProvider's
own heuristics.
"""

from __future__ import annotations

import pytest

from core.errors import MaxRevisionCyclesExceededError
from core.message_bus import MessageBus
from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from core.task_manager import TaskManager
from schemas.message import MessageType
from schemas.result import ExecutionResult
from schemas.review import Review, ReviewDecision
from schemas.task import TaskStatus


def _make_scripted_reviewer(decisions: list[ReviewDecision]):
    """Return a bus handler that yields ``decisions`` in order, one per call."""
    calls = {"n": 0}

    async def handler(message):
        idx = min(calls["n"], len(decisions) - 1)
        decision = decisions[idx]
        calls["n"] += 1

        result = ExecutionResult.from_dict(message.payload["result"])
        review = Review(
            task_id=result.task_id,
            decision=decision,
            score=0.95 if decision == ReviewDecision.APPROVED else 0.3,
            feedback="Looks good." if decision == ReviewDecision.APPROVED else "Please redo the summary section.",
            required_changes=[] if decision == ReviewDecision.APPROVED else ["Expand the summary section."],
        )
        message_type = (
            MessageType.REVIEW_APPROVED if decision == ReviewDecision.APPROVED else MessageType.REVIEW_REJECTED
        )
        return message.reply(sender="reviewer", message_type=message_type, payload={"review": review.to_dict()})

    handler.calls = calls
    return handler


@pytest.mark.asyncio
async def test_rejected_review_triggers_a_revision_and_then_succeeds(planner_agent, executor_agent):
    bus = MessageBus()
    bus.subscribe("planner", planner_agent.handle)
    bus.subscribe("executor", executor_agent.handle)

    scripted_reviewer = _make_scripted_reviewer([ReviewDecision.REJECTED, ReviewDecision.APPROVED])
    bus.subscribe("reviewer", scripted_reviewer)

    orchestrator = Orchestrator(
        bus=bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=3,
    )

    result = await orchestrator.run("Build landing page", "Create a landing page for a product launch.")

    assert result.success is True
    assert result.status == TaskStatus.COMPLETED.value
    assert result.revision_count == 1
    assert scripted_reviewer.calls["n"] == 2

    # The Planner should have been asked twice: once for the initial plan,
    # once for the revision.
    plan_messages = [
        m for m in orchestrator.bus.history
        if m.message_type in (MessageType.TASK_CREATED, MessageType.REVISION_REQUESTED)
    ]
    assert len(plan_messages) == 2
    assert plan_messages[1].payload["feedback"]


@pytest.mark.asyncio
async def test_maximum_revision_cycles_is_enforced(planner_agent, executor_agent):
    bus = MessageBus()
    bus.subscribe("planner", planner_agent.handle)
    bus.subscribe("executor", executor_agent.handle)

    # Always rejects: the workflow must give up after max_revision_cycles.
    scripted_reviewer = _make_scripted_reviewer([ReviewDecision.REJECTED])
    bus.subscribe("reviewer", scripted_reviewer)

    max_cycles = 2
    orchestrator = Orchestrator(
        bus=bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=max_cycles,
    )

    result = await orchestrator.run("Build landing page", "Create a landing page for a product launch.")

    assert result.success is False
    assert result.status == TaskStatus.FAILED.value
    assert "revision" in (result.error or "").lower()
    # cycle 0..max_cycles inclusive means max_cycles + 1 review attempts.
    assert scripted_reviewer.calls["n"] == max_cycles + 1


@pytest.mark.asyncio
async def test_reviewer_failure_is_translated_into_a_failed_workflow(planner_agent, executor_agent):
    bus = MessageBus()
    bus.subscribe("planner", planner_agent.handle)
    bus.subscribe("executor", executor_agent.handle)

    async def broken_reviewer(message):
        raise RuntimeError("reviewer backend unavailable")

    bus.subscribe("reviewer", broken_reviewer)

    orchestrator = Orchestrator(
        bus=bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=2,
    )

    result = await orchestrator.run("Build landing page", "Create a landing page for a product launch.")

    assert result.success is False
    assert result.status == TaskStatus.FAILED.value
    assert "reviewer" in (result.error or "").lower()
