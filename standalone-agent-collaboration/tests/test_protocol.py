"""Tests for the message schema and protocol validation rules."""

from __future__ import annotations

import pytest

from core.errors import InvalidMessageError, UnknownAgentError
from core.protocol import validate_message
from schemas.message import AgentMessage, MessageType


def test_message_round_trips_through_json():
    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
        payload={"title": "Do the thing"},
    )

    restored = AgentMessage.from_json(message.to_json())

    assert restored.sender == message.sender
    assert restored.recipient == message.recipient
    assert restored.message_type == message.message_type
    assert restored.task_id == message.task_id
    assert restored.payload == message.payload
    assert restored.correlation_id == message.correlation_id


def test_message_from_dict_rejects_missing_fields():
    with pytest.raises(ValueError):
        AgentMessage.from_dict({"sender": "orchestrator"})


def test_message_from_dict_rejects_unknown_message_type():
    with pytest.raises(ValueError):
        AgentMessage.from_dict(
            {
                "sender": "orchestrator",
                "recipient": "planner",
                "message_type": "NOT_A_REAL_TYPE",
                "task_id": "task-1",
            }
        )


def test_validate_message_accepts_a_well_formed_message():
    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    validate_message(message)  # should not raise


def test_validate_message_rejects_unknown_recipient():
    message = AgentMessage(
        sender="orchestrator",
        recipient="not-a-real-agent",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    with pytest.raises(UnknownAgentError):
        validate_message(message)


def test_validate_message_rejects_missing_task_id():
    message = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="",
    )
    with pytest.raises(InvalidMessageError):
        validate_message(message)


def test_reply_preserves_correlation_id():
    original = AgentMessage(
        sender="orchestrator",
        recipient="planner",
        message_type=MessageType.TASK_CREATED,
        task_id="task-1",
    )
    reply = original.reply(
        sender="planner",
        message_type=MessageType.PLAN_CREATED,
        payload={"plan": {}},
    )
    assert reply.correlation_id == original.correlation_id
    assert reply.recipient == original.sender
    assert reply.sender == "planner"
