from threading import Condition


class ResourceManager:

    def __init__(
        self,
        limits: dict[str, int]
    ):

        self.limits = limits
        self.active_jobs: dict[str, int] = {}
        self.condition = Condition()

    def can_execute(
        self,
        agent_type: str
    ) -> bool:

        with self.condition:

            limit = self.limits.get(agent_type)

            if limit is None:
                return False

            active = self.active_jobs.get(
                agent_type,
                0
            )

            return active < limit

    def acquire(
        self,
        agent_type: str
    ) -> bool:

        with self.condition:

            limit = self.limits.get(agent_type)

            if limit is None:
                return False

            while (
                self.active_jobs.get(
                    agent_type,
                    0
                ) >= limit
            ):
                self.condition.wait()

            self.active_jobs[agent_type] = (
                self.active_jobs.get(
                    agent_type,
                    0
                ) + 1
            )

            return True

    def release(
        self,
        agent_type: str
    ):

        with self.condition:

            if agent_type in self.active_jobs:

                self.active_jobs[agent_type] -= 1

                if self.active_jobs[agent_type] <= 0:
                    del self.active_jobs[agent_type]

            self.condition.notify_all()

    def get_active_count(
        self,
        agent_type: str
    ) -> int:

        with self.condition:
            return self.active_jobs.get(
                agent_type,
                0
            )