from concurrent.futures import (
    ThreadPoolExecutor,
    Future
)

from backend.models.job import Job
from backend.models.enums import JobStatus
from backend.agents.registry import AgentRegistry

from .execution_lane import ExecutionLane
from .executor import Executor
from .resource_manager import ResourceManager
from .zombie_handler import ZombieHandler


class Runtime:

    def __init__(
        self,
        number_of_lanes: int = 2,
        registry: AgentRegistry | None = None,
        resource_limits: dict[str, int] | None = None
    ):

        self.lanes = [
            ExecutionLane(i)
            for i in range(number_of_lanes)
        ]

        self.registry = registry

        self.executor = Executor(
            registry
        )

        self.resource_manager = ResourceManager(
            resource_limits or {}
        )

        self.zombie_handler = ZombieHandler()

        self.worker_pool = ThreadPoolExecutor(
            max_workers=number_of_lanes
        )

    def get_free_lane(
        self
    ) -> ExecutionLane | None:

        for lane in self.lanes:

            if lane.is_free():
                return lane

        return None

    def run_job(
        self,
        job: Job
    ) -> bool:

        return self._execute_job(job)

    def submit_job(
        self,
        job: Job
    ) -> Future:

        return self.worker_pool.submit(
            self._execute_job,
            job
        )

    def _execute_job(
        self,
        job: Job
    ) -> bool:

        agent = self.registry.get(
            job.agent_type
        )

        if agent is None:

            print(
                f"Agent not found: "
                f"{job.agent_type}"
            )

            job.status = JobStatus.FAILED
            job.error = (
                f"Agent not found: "
                f"{job.agent_type}"
            )

            return False

        # Wait until an execution lane is available
        lane = self.get_free_lane()

        while lane is None:
            lane = self.get_free_lane()

        # Reserve the resource first
        resource_acquired = (
            self.resource_manager.acquire(
                job.agent_type
            )
        )

        if not resource_acquired:

            job.status = JobStatus.FAILED
            return False

        # Assign the lane
        if not lane.assign_job(job):

            self.resource_manager.release(
                job.agent_type
            )

            return False

        try:

            return self.executor.execute(job)

        finally:

            self.resource_manager.release(
                job.agent_type
            )

            lane.release_job()

    def shutdown(self):

        self.worker_pool.shutdown(
            wait=True
        )