import pytest

from backend.kernel.kernel import AIKernel
from backend.kernel.task import Task


def test_kernel_start():

    kernel = AIKernel()

    assert kernel.status == "initialized"

    kernel.start()

    assert kernel.status == "running"


def test_kernel_stop():

    kernel = AIKernel()

    kernel.start()
    kernel.stop()

    assert kernel.status == "stopped"


def test_kernel_create_agent():

    kernel = AIKernel()
    kernel.start()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    assert agent.name == "Research Agent"
    assert agent.agent_type == "research"

    assert kernel.get_agent(agent.id) == agent


def test_kernel_start_agent():

    kernel = AIKernel()
    kernel.start()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    kernel.start_agent(agent.id)

    assert agent.status.value == "running"


def test_kernel_pause_and_resume_agent():

    kernel = AIKernel()
    kernel.start()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    kernel.start_agent(agent.id)

    kernel.pause_agent(agent.id)

    assert agent.status.value == "paused"

    kernel.resume_agent(agent.id)

    assert agent.status.value == "running"


def test_kernel_stop_agent():

    kernel = AIKernel()
    kernel.start()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    kernel.start_agent(agent.id)
    kernel.stop_agent(agent.id)

    assert agent.status.value == "stopped"


def test_agent_cannot_start_when_kernel_is_stopped():

    kernel = AIKernel()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    with pytest.raises(RuntimeError):
        kernel.start_agent(agent.id)

def test_kernel_execute_task():

    kernel = AIKernel()
    kernel.start()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    kernel.start_agent(agent.id)

    task = Task(
        agent_id=agent.id,
        description="Research FastAPI authentication."
    )

    task.queue()

    result = kernel.execute_task(task)

    assert result.status.value == "completed"

def test_kernel_cannot_execute_task_when_stopped():

    kernel = AIKernel()

    agent = kernel.create_agent(
        name="Research Agent",
        agent_type="research"
    )

    task = Task(
        agent_id=agent.id,
        description="Research something."
    )

    try:
        kernel.execute_task(task)
        assert False
    except RuntimeError:
        assert True

def test_kernel_execute_task_with_unknown_agent():

    kernel = AIKernel()
    kernel.start()

    task = Task(
        agent_id="unknown-agent-123",
        description="Research something."
    )

    with pytest.raises(KeyError):
        kernel.execute_task(task)