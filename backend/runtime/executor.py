from backend.models.job import Job
from backend.models.enums import JobStatus
from backend.agents.registry import AgentRegistry


class Executor:

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def execute(self, job: Job) -> bool:
        try:
            print(f"Executing job: {job.name}")

            # Temporary failure simulation
            if job.name == "Failed Research":
                raise Exception("Simulated execution failure")

            # Fetch the correct agent using job.agent_type
            agent = self.registry.get(job.agent_type)

            if agent is None:
                raise Exception(
                    f"Agent not found: {job.agent_type}"
                )

            # Execute the actual agent
            result = agent.run(job.name)

            print(f"Agent result: {result}")

            job.status = JobStatus.COMPLETED
            return True

        except Exception as e:
            print(f"Job failed: {e}")
            job.status = JobStatus.FAILED
            return False