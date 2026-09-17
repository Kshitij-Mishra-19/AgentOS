from backend.models.job import Job
from backend.models.enums import JobStatus


class DependencyManager:

    def dependencies_completed(
        self,
        job: Job,
        jobs: dict[str, Job]
    ) -> bool:

        for dependency_id in job.dependencies:

            dependency = jobs.get(dependency_id)

            if dependency is None:
                return False

            if dependency.status != JobStatus.COMPLETED:
                return False

        return True

    def update_job_status(
        self,
        job: Job,
        jobs: dict[str, Job]
    ):

        if job.status != JobStatus.PENDING:
            return

        if self.dependencies_completed(
            job,
            jobs
        ):
            job.status = JobStatus.READY