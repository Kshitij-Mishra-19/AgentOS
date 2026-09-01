from collections import deque

from backend.models.job import Job
from backend.models.enums import PriorityLevel


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

        for priority in PriorityLevel:

            if self.queues[priority]:
                return self.queues[priority].popleft()

        return None



if __name__ == "__main__":

    from backend.models.job import Job

    scheduler = MLFQScheduler()

    j1 = Job(
        name="High Priority Task",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    j2 = Job(
        name="Medium Priority Task",
        agent_type="coding",
        priority=PriorityLevel.MEDIUM
    )

    j3 = Job(
        name="Low Priority Task",
        agent_type="testing",
        priority=PriorityLevel.LOW
    )

    scheduler.add_job(j2)
    scheduler.add_job(j3)
    scheduler.add_job(j1)

    print("Execution order:")

    while True:
        job = scheduler.get_next_job()

        if job is None:
            break

        print(job.name)