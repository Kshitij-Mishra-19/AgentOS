from backend.models.job import Job
from backend.models.enums import JobStatus
from backend.agents.registry import AgentRegistry

from .execution_lane import ExecutionLane
from .executor import Executor
from .resource_manager import ResourceManager


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

        self.executor = Executor(registry)

        self.resource_manager = ResourceManager(
            resource_limits or {}
        )

    def get_free_lane(self) -> ExecutionLane | None:

        for lane in self.lanes:
            if lane.is_free():
                return lane

        return None

    def run_job(self, job: Job) -> bool:

        # Check whether the requested agent exists
        agent = self.registry.get(job.agent_type)

        if agent is None:
            print(
                f"Agent not found: {job.agent_type}"
            )

            job.status = JobStatus.FAILED
            return False

        # Check whether an execution lane is available
        lane = self.get_free_lane()

        if lane is None:
            print("No execution lane available")
            return False

        # Check agent-specific resource limit
        if not self.resource_manager.can_execute(
            job.agent_type
        ):
            print(
                f"Resource limit reached for: "
                f"{job.agent_type}"
            )
            return False

        # Assign lane and reserve resource
        lane.assign_job(job)

        self.resource_manager.acquire(
            job.agent_type
        )

        # Execute the job
        success = self.executor.execute(job)

        # Release resource and lane
        self.resource_manager.release(
            job.agent_type
        )

        lane.release_job()

        if success:
            job.status = JobStatus.COMPLETED
        else:
            job.status = JobStatus.FAILED

        return success