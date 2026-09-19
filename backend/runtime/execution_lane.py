from threading import Lock

from backend.models.job import Job
from backend.models.enums import JobStatus


class ExecutionLane:

    def __init__(self, lane_id: int):

        self.lane_id = lane_id
        self.current_job: Job | None = None
        self.lock = Lock()

    def is_free(self) -> bool:

        with self.lock:
            return self.current_job is None

    def assign_job(self, job: Job) -> bool:

        with self.lock:

            if self.current_job is not None:
                return False

            self.current_job = job
            job.status = JobStatus.RUNNING

            return True

    def release_job(self) -> Job | None:

        with self.lock:

            completed_job = self.current_job
            self.current_job = None

            return completed_job

    def get_current_job(self) -> Job | None:

        with self.lock:
            return self.current_job