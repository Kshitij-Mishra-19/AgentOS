from backend.kernel.task import Task, TaskStatus
import pytest


def test_task_creation():

    task = Task(
        agent_id="agent-123",
        description="Research FastAPI authentication."
    )

    assert task.agent_id == "agent-123"
    assert task.description == "Research FastAPI authentication."
    assert task.status == TaskStatus.CREATED
    assert task.priority == 5
    assert task.id is not None


def test_task_custom_priority():

    task = Task(
        agent_id="agent-123",
        description="Fix critical bug.",
        priority=1
    )

    assert task.priority == 1

def test_task_initial_result_and_error_are_none():

    task = Task(
        agent_id="agent-123",
        description="Research FastAPI authentication."
    )

    assert task.result is None
    assert task.error is None
    assert task.started_at is None
    assert task.completed_at is None


def test_task_can_store_result_and_error():

    task = Task(
        agent_id="agent-123",
        description="Run a research task."
    )

    task.result = "Research completed successfully"

    assert task.result == "Research completed successfully"

    task.status = TaskStatus.FAILED
    task.error = "Agent failed to execute task."

    assert task.status == TaskStatus.FAILED
    assert task.error == "Agent failed to execute task."

def test_task_can_be_cancelled():

    task = Task(
        agent_id="agent-123",
        description="Cancel this task."
    )

    task.cancel()

    assert task.status == TaskStatus.CANCELLED


def test_completed_task_cannot_be_cancelled():

    task = Task(
        agent_id="agent-123",
        description="Completed task."
    )

    task.status = TaskStatus.COMPLETED

    with pytest.raises(RuntimeError):
        task.cancel()

def test_task_can_be_queued():

    task = Task(
        agent_id="agent-123",
        description="Queue this task."
    )

    task.queue()

    assert task.status == TaskStatus.QUEUED


def test_completed_task_cannot_be_queued():

    task = Task(
        agent_id="agent-123",
        description="Completed task."
    )

    task.status = TaskStatus.COMPLETED

    with pytest.raises(RuntimeError):
        task.queue()

def test_task_priority_must_be_between_1_and_10():

    task = Task(
        agent_id="agent-123",
        description="High priority task.",
        priority=1
    )

    assert task.priority == 1

    task = Task(
        agent_id="agent-123",
        description="Low priority task.",
        priority=10
    )

    assert task.priority == 10


def test_task_rejects_invalid_priority():

    with pytest.raises(ValueError):
        Task(
            agent_id="agent-123",
            description="Invalid priority.",
            priority=0
        )

    with pytest.raises(ValueError):
        Task(
            agent_id="agent-123",
            description="Invalid priority.",
            priority=11
        )


def test_task_rejects_non_integer_priority():

    with pytest.raises(TypeError):
        Task(
            agent_id="agent-123",
            description="Invalid priority.",
            priority="high"
        )

def test_non_created_task_cannot_be_queued():

    statuses = [
        TaskStatus.QUEUED,
        TaskStatus.RUNNING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    ]

    for status in statuses:

        task = Task(
            agent_id="agent-123",
            description="Invalid queue transition."
        )

        task.status = status

        with pytest.raises(RuntimeError):
            task.queue()

def test_non_cancellable_task_cannot_be_cancelled():

    statuses = [
        TaskStatus.RUNNING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    ]

    for status in statuses:

        task = Task(
            agent_id="agent-123",
            description="Invalid cancellation transition."
        )

        task.status = status

        with pytest.raises(RuntimeError):
            task.cancel()

def test_task_rejects_empty_description():

    with pytest.raises(ValueError):
        Task(
            agent_id="agent-123",
            description=""
        )

    with pytest.raises(ValueError):
        Task(
            agent_id="agent-123",
            description="   "
        )


def test_task_rejects_non_string_description():

    with pytest.raises(TypeError):
        Task(
            agent_id="agent-123",
            description=123
        )