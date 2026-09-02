from backend.kernel.agent import Agent
from backend.kernel.executor import SimpleTaskExecutor
from backend.kernel.registry import AgentRegistry
from backend.kernel.task import Task


class AIKernel:

    def __init__(self):
        self.status = "initialized"
        self.registry = AgentRegistry()
        self.executor = SimpleTaskExecutor()

    def start(self):
        self.status = "running"

    def stop(self):
        self.status = "stopped"

    def create_agent(
        self,
        name: str,
        agent_type: str,
        capabilities: list[str] | None = None
    ) -> Agent:

        agent = Agent(
            name=name,
            agent_type=agent_type,
            capabilities=capabilities or []
        )

        self.registry.register(agent)

        return agent

    def get_agent(self, agent_id: str) -> Agent:
        return self.registry.get(agent_id)

    def list_agents(self) -> list[Agent]:
        return self.registry.list_agents()

    def remove_agent(self, agent_id: str) -> None:
        self.registry.remove(agent_id)

    def start_agent(self, agent_id: str) -> Agent:

        agent = self.get_agent(agent_id)

        if self.status != "running":
            raise RuntimeError("Kernel is not running")

        agent.mark_ready()
        agent.start()

        return agent

    def pause_agent(self, agent_id: str) -> Agent:

        agent = self.get_agent(agent_id)

        agent.pause()

        return agent

    def resume_agent(self, agent_id: str) -> Agent:

        agent = self.get_agent(agent_id)

        agent.resume()

        return agent

    def stop_agent(self, agent_id: str) -> Agent:

        agent = self.get_agent(agent_id)

        agent.stop()

        return agent

    def execute_task(self, task: Task) -> Task:

        if self.status != "running":
            raise RuntimeError("Kernel is not running")

        agent = self.get_agent(task.agent_id)

        return self.executor.execute(
            agent,
            task
        )