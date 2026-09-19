from collections import deque

from backend.models.job import Job
from backend.models.enums import PriorityLevel, JobStatus


class MLFQScheduler:

    def __init__(self):

        self.queues = {
            PriorityLevel.HIGH: deque(),
            PriorityLevel.MEDIUM: deque(),
            PriorityLevel.LOW: deque()
        }

    def add_job(self, job: Job):

        self.queues[job.priority].append(job)

    def get_next_job(self) -> Job | None:

        for priority in (
            PriorityLevel.HIGH,
            PriorityLevel.MEDIUM,
            PriorityLevel.LOW
        ):

            queue = self.queues[priority]

            while queue:

                job = queue.popleft()

                if job.status == JobStatus.READY:
                    return job

        return None

    def is_empty(self) -> bool:

        return all(
            len(queue) == 0
            for queue in self.queues.values()
        )