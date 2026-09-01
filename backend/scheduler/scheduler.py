from backend.models.job import Job
from backend.models.enums import JobStatus

from .dependency_manager import DependencyManager
from .mlfq import MLFQScheduler


class Scheduler:

    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.dependency_manager = DependencyManager()
        self.mlfq = MLFQScheduler()

    def add_job(self, job: Job):
        self.jobs[job.job_id] = job

        self.dependency_manager.update_job_status(
            job,
            self.jobs
        )

        if job.status == JobStatus.READY:
            self.mlfq.add_job(job)

    def get_next_job(self) -> Job | None:
        return self.mlfq.get_next_job()





if __name__ == "__main__":

    from backend.models.enums import PriorityLevel, JobStatus

    scheduler = Scheduler()

    j1 = Job(
        name="Research",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    j2 = Job(
        name="Coding",
        agent_type="coding",
        priority=PriorityLevel.MEDIUM,
        dependencies=[j1.job_id]
    )

    j3 = Job(
        name="Testing",
        agent_type="testing",
        priority=PriorityLevel.LOW,
        dependencies=[j2.job_id]
    )

    scheduler.add_job(j1)
    scheduler.add_job(j2)
    scheduler.add_job(j3)

    print("Initial states:")
    print("J1:", j1.status)
    print("J2:", j2.status)
    print("J3:", j3.status)

    print("\nFirst job selected:")
    job = scheduler.get_next_job()
    print(job.name)

    j1.status = JobStatus.COMPLETED

    scheduler.dependency_manager.update_job_status(j2, scheduler.jobs)

    print("\nAfter J1 completes:")
    print("J2:", j2.status)