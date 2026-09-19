from datetime import datetime

from backend.models.job import Job
from backend.models.enums import JobStatus


class ZombieHandler:

    def __init__(
        self,
        timeout_seconds: float = 60
    ):

        self.timeout_seconds = timeout_seconds

    def is_zombie(
        self,
        job: Job
    ) -> bool:

        if job.status != JobStatus.RUNNING:
            return False

        if job.started_at is None:
            return False

        elapsed = (
            datetime.now() - job.started_at
        ).total_seconds()

        return elapsed > self.timeout_seconds

    def recover(
        self,
        job: Job
    ) -> bool:

        if not self.is_zombie(job):
            return False

        job.status = JobStatus.FAILED

        job.error = (
            "Job timeout / zombie detected"
        )

        job.completed_at = datetime.now()

        return True