from backend.kernel.agent import Agent


class AgentRegistry:

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        if agent.id in self._agents:
            raise ValueError(f"Agent already registered: {agent.id}")

        self._agents[agent.id] = agent

        return agent

    def get(self, agent_id: str) -> Agent:
        if agent_id not in self._agents:
            raise KeyError(f"Agent not found: {agent_id}")

        return self._agents[agent_id]

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())

    def remove(self, agent_id: str) -> None:
        if agent_id not in self._agents:
            raise KeyError(f"Agent not found: {agent_id}")

        del self._agents[agent_id]