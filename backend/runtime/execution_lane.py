from backend.models.job import Job
from backend.models.enums import JobStatus


class ExecutionLane:

    def __init__(self, lane_id: int):
        self.lane_id = lane_id
        self.current_job: Job | None = None

    def is_free(self) -> bool:
        return self.current_job is None

    def assign_job(self, job: Job) -> bool:

        if not self.is_free():
            return False

        self.current_job = job
        job.status = JobStatus.RUNNING

        return True

    def release_job(self) -> Job | None:

        completed_job = self.current_job
        self.current_job = None

        return completed_job