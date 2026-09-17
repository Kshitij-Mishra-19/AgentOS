from datetime import datetime

from backend.models.job import Job
from backend.models.enums import JobStatus
from backend.agents.registry import AgentRegistry


class Executor:

    def __init__(
        self,
        registry: AgentRegistry
    ):

        self.registry = registry

    def execute(
        self,
        job: Job
    ) -> bool:

        try:

            print(
                f"Executing job: {job.name}"
            )

            agent = self.registry.get(
                job.agent_type
            )

            if agent is None:
                raise RuntimeError(
                    f"Agent not found: "
                    f"{job.agent_type}"
                )

            job.started_at = datetime.now()
            job.status = JobStatus.RUNNING

            result = agent.run(job.name)

            job.result = result
            job.error = None
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()

            print(
                f"Agent result: {result}"
            )

            return True

        except Exception as e:

            job.error = str(e)
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()

            print(
                f"Job failed: {e}"
            )

            return False