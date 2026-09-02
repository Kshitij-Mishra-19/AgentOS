import pytest

from backend.kernel.agent import Agent, AgentStatus


def test_agent_creation():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    assert agent.name == "Research Agent"
    assert agent.agent_type == "research"
    assert agent.status == AgentStatus.CREATED
    assert agent.id is not None


def test_agent_capabilities():

    agent = Agent(
        name="Code Agent",
        agent_type="code",
        capabilities=["write_code", "run_tests"]
    )

    assert "write_code" in agent.capabilities
    assert "run_tests" in agent.capabilities


def test_agent_lifecycle():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    assert agent.status == AgentStatus.CREATED

    agent.mark_ready()
    assert agent.status == AgentStatus.READY

    agent.start()
    assert agent.status == AgentStatus.RUNNING

    agent.pause()
    assert agent.status == AgentStatus.PAUSED

    agent.resume()
    assert agent.status == AgentStatus.RUNNING

    agent.stop()
    assert agent.status == AgentStatus.STOPPED


def test_invalid_start():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    with pytest.raises(RuntimeError):
        agent.start()


def test_agent_failure():

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent.fail()

    assert agent.status == AgentStatus.FAILED