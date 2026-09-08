"""Tests for MessageBus publish/subscribe/routing behavior."""

from __future__ import annotations

import pytest

from core.errors import InvalidMessageError
from core.message_bus import MessageBus
from schemas.message import AgentMessage, MessageType


@pytest.mark.asyncio
async def test_publish_routes_to_the_correct_subscriber():
    bus = MessageBus()
    received: list[AgentMessage] = []

    async def handler(message: AgentMessage):
        received.append(message)
        return None

    bus.subscribe("planner", handler)

    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    await bus.publish(message)

    assert len(received) == 1
    assert received[0] is message
    assert bus.history == [message]


@pytest.mark.asyncio
async def test_publish_raises_when_no_subscriber_registered():
    bus = MessageBus()
    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    with pytest.raises(InvalidMessageError):
        await bus.publish(message)


@pytest.mark.asyncio
async def test_publish_returns_handler_replies():
    bus = MessageBus()

    async def handler(message: AgentMessage):
        return message.reply(sender="planner", message_type=MessageType.PLAN_CREATED, payload={"plan": {}})

    bus.subscribe("planner", handler)

    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    replies = await bus.publish(message)

    assert len(replies) == 1
    assert replies[0].message_type == MessageType.PLAN_CREATED
    assert replies[0].correlation_id == message.correlation_id


@pytest.mark.asyncio
async def test_publish_captures_and_reraises_handler_failures():
    bus = MessageBus()

    async def failing_handler(message: AgentMessage):
        raise RuntimeError("boom")

    bus.subscribe("planner", failing_handler)

    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    with pytest.raises(RuntimeError):
        await bus.publish(message)

    assert len(bus.failures) == 1
    assert bus.failures[0].message is message


@pytest.mark.asyncio
async def test_publish_rejects_invalid_message_before_routing():
    bus = MessageBus()

    async def handler(message: AgentMessage):
        return None

    bus.subscribe("planner", handler)

    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="",  # invalid: empty task_id
    )
    with pytest.raises(InvalidMessageError):
        await bus.publish(message)
