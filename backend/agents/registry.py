from typing import Dict


class AgentRegistry:

    def __init__(self):
        self.agents: Dict[str, object] = {}

    def register(self, name: str, agent: object):
        self.agents[name] = agent

    def get(self, name: str):
        return self.agents.get(name)

    def exists(self, name: str) -> bool:
        return name in self.agents