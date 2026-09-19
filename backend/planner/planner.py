from backend.models.job import Job
from backend.models.enums import PriorityLevel


class Planner:

    def create_job(
        self,
        name: str,
        agent_type: str,
        priority: PriorityLevel,
        dependencies: list[str] | None = None
    ) -> Job:

        return Job(
            name=name,
            agent_type=agent_type,
            priority=priority,
            dependencies=dependencies or []
        )

    def create_pipeline(
        self,
        tasks: list[tuple[str, str, PriorityLevel]]
    ) -> list[Job]:

        jobs = []
        previous_job_id = None

        for name, agent_type, priority in tasks:

            dependencies = []

            if previous_job_id is not None:
                dependencies.append(previous_job_id)

            job = self.create_job(
                name,
                agent_type,
                priority,
                dependencies
            )

            jobs.append(job)
            previous_job_id = job.job_id

        return jobs