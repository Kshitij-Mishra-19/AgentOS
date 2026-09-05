#right now failed job==zombie
#later we'll stuck/timeout job==zombie

from backend.models.job import Job
from backend.models.enums import JobStatus


class ZombieHandler:

    def is_zombie(self, job: Job) -> bool:
        """
        Checks whether a job is stuck or failed.
        """

        return job.status == JobStatus.FAILED

    def handle_zombie(self, job: Job) -> None:
        """
        Handles a zombie job.

        Actual retry/recovery logic will be added later.
        """

        if self.is_zombie(job):
            print(f"Zombie job detected: {job.name}")

            # Recovery logic will be connected later.
            # For now, keep the job marked as FAILED.