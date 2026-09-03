import pytest

from backend.kernel.agent import Agent
from backend.kernel.executor import SimpleTaskExecutor

from datetime import datetime

from backend.kernel.task import Task, TaskStatus


def test_task_execution():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()

    task = Task(
        agent_id=agent.id,
        description="Research FastAPI authentication."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    result = executor.execute(
        agent,
        task
    )

    assert result.status.value == "completed"
    assert result.result == "Task completed successfully"
    assert result.error is None
    assert result.started_at is not None
    assert result.completed_at is not None


def test_task_wrong_agent():

    agent1 = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent2 = Agent(
        name="Code Agent",
        agent_type="code"
    )

    task = Task(
        agent_id=agent1.id,
        description="Research something."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    with pytest.raises(ValueError):
        executor.execute(agent2, task)


def test_created_task_cannot_be_executed():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    task = Task(
        agent_id=agent.id,
        description="Research something."
    )

    executor = SimpleTaskExecutor()

    with pytest.raises(RuntimeError):
        executor.execute(agent, task)

def test_failed_task_stores_error():

    class FailingExecutor(SimpleTaskExecutor):

        def execute(self, agent, task):

            if agent.id != task.agent_id:
                raise ValueError(
                    "Task is assigned to a different agent"
                )

            try:
                task.started_at = datetime.now()
                task.status = TaskStatus.RUNNING

                raise RuntimeError("Simulated task failure")

            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.completed_at = datetime.now()

                return task

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    task = Task(
        agent_id=agent.id,
        description="Fail this task."
    )

    task.queue()

    executor = FailingExecutor()

    result = executor.execute(
        agent,
        task
    )

    assert result.status.value == "failed"
    assert result.error == "Simulated task failure"
    assert result.result is None
    assert result.started_at is not None
    assert result.completed_at is not None

def test_stopped_agent_cannot_execute_task():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()
    agent.stop()

    task = Task(
        agent_id=agent.id,
        description="Research something."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    with pytest.raises(RuntimeError):
        executor.execute(agent, task)


def test_failed_agent_cannot_execute_task():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.fail()

    task = Task(
        agent_id=agent.id,
        description="Research something."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    with pytest.raises(RuntimeError):
        executor.execute(agent, task)

def test_cancelled_task_cannot_be_executed():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()

    task = Task(
        agent_id=agent.id,
        description="Cancel this task."
    )

    task.queue()
    task.cancel()

    executor = SimpleTaskExecutor()

    with pytest.raises(RuntimeError):
        executor.execute(agent, task)

def test_completed_task_has_no_error():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()

    task = Task(
        agent_id=agent.id,
        description="Complete this task."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    result = executor.execute(agent, task)

    assert result.status == TaskStatus.COMPLETED
    assert result.result is not None
    assert result.error is None

def test_failed_task_has_no_result():

    class FailingExecutor(SimpleTaskExecutor):

        def execute(self, agent, task):

            if agent.id != task.agent_id:
                raise ValueError(
                    "Task is assigned to a different agent"
                )

            if agent.status.value not in {"ready", "running"}:
                raise RuntimeError(
                    f"Agent cannot execute task from status: {agent.status}"
                )

            if task.status != TaskStatus.QUEUED:
                raise RuntimeError(
                    f"Task cannot be executed from status: {task.status}"
                )

            try:
                task.started_at = datetime.now()
                task.status = TaskStatus.RUNNING

                raise RuntimeError("Simulated task failure")

            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.result = None
                task.error = str(exc)
                task.completed_at = datetime.now()

                return task

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()

    task = Task(
        agent_id=agent.id,
        description="Fail this task."
    )

    task.queue()

    executor = FailingExecutor()

    result = executor.execute(agent, task)

    assert result.status == TaskStatus.FAILED
    assert result.result is None
    assert result.error == "Simulated task failure"

def test_task_completion_time_is_after_start_time():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()

    task = Task(
        agent_id=agent.id,
        description="Check task timestamps."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    result = executor.execute(agent, task)

    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.completed_at >= result.started_at

def test_paused_agent_cannot_execute_task():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.mark_ready()
    agent.start()
    agent.pause()

    task = Task(
        agent_id=agent.id,
        description="Research something."
    )

    task.queue()

    executor = SimpleTaskExecutor()

    with pytest.raises(RuntimeError):
        executor.execute(agent, task)