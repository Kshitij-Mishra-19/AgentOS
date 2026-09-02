import pytest

from backend.kernel.agent import Agent
from backend.kernel.registry import AgentRegistry


def test_register_agent():

    registry = AgentRegistry()

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    registry.register(agent)

    assert registry.get(agent.id) == agent


def test_list_agents():

    registry = AgentRegistry()

    agent1 = Agent(
        name="Research Agent",
        agent_type="research"
    )

    agent2 = Agent(
        name="Code Agent",
        agent_type="code"
    )

    registry.register(agent1)
    registry.register(agent2)

    agents = registry.list_agents()

    assert len(agents) == 2
    assert agent1 in agents
    assert agent2 in agents


def test_remove_agent():

    registry = AgentRegistry()

    agent = Agent(
        name="Research Agent",
        agent_type="research"
    )

    registry.register(agent)

    registry.remove(agent.id)

    with pytest.raises(KeyError):
        registry.get(agent.id)


def test_get_unknown_agent():

    registry = AgentRegistry()

    with pytest.raises(KeyError):
        registry.get("unknown-agent")