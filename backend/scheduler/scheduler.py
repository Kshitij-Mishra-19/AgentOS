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

    def run_next_job(self, runtime) -> bool:
        job = self.get_next_job()

        if job is None:
            return False

        success = runtime.run_job(job)

        if success:
            self.mark_job_completed(job)

        return success

    def run_all(self, runtime):
        """
        Run all currently READY jobs.

        Failed jobs do not stop the complete scheduler.
        Other independent jobs can still execute.
        """

        while True:
            job = self.get_next_job()

            if job is None:
                break

            success = runtime.run_job(job)

            if success:
                self.mark_job_completed(job)

            else:
                # Failed job ko dobara queue mein add nahi karna.
                # Baaki READY jobs execute hoti rahengi.
                print(f"Scheduler: Job failed - {job.name}")

    def mark_job_completed(self, job: Job):
        job.status = JobStatus.COMPLETED

        for dependent_job in self.jobs.values():

            if dependent_job.status == JobStatus.PENDING:

                self.dependency_manager.update_job_status(
                    dependent_job,
                    self.jobs
                )

                if dependent_job.status == JobStatus.READY:
                    self.mlfq.add_job(dependent_job)