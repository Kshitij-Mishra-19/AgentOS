from backend.models.job import Job
from backend.models.enums import JobStatus


class DependencyManager:

    def are_dependencies_completed(
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
    ) -> None:

        if self.are_dependencies_completed(job, jobs):
            job.status = JobStatus.READY



if __name__ == "__main__":

    from backend.models.job import Job
    from backend.models.enums import JobStatus

    j1 = Job(
        name="Research",
        agent_type="research"
    )

    j2 = Job(
        name="Coding",
        agent_type="coding",
        dependencies=[j1.job_id]
    )

    jobs = {
        j1.job_id: j1,
        j2.job_id: j2
    }

    manager = DependencyManager()

    manager.update_job_status(j2, jobs)

    print("Before J1 completes:")
    print("J1:", j1.status)
    print("J2:", j2.status)

    j1.status = JobStatus.COMPLETED

    manager.update_job_status(j2, jobs)

    print("\nAfter J1 completes:")
    print("J1:", j1.status)
    print("J2:", j2.status)