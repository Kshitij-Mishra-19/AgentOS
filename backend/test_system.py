import time

from backend.agents.research_agent import ResearchAgent
from backend.agents.coding_agent import CodingAgent
from backend.agents.testing_agent import TestingAgent
from backend.agents.registry import AgentRegistry

from backend.models.job import Job
from backend.models.enums import (
    PriorityLevel,
    JobStatus
)

from backend.scheduler.scheduler import Scheduler
from backend.runtime.runtime import Runtime


# ============================================================
# Helper Agents
# ============================================================

class FailingAgent:

    def run(self, task: str) -> str:
        raise RuntimeError(
            "Simulated agent failure"
        )


class SlowResearchAgent:

    def run(self, task: str) -> str:

        print(f"Starting: {task}")

        time.sleep(2)

        print(f"Finished: {task}")

        return f"Research completed for: {task}"


# ============================================================
# Helper Function
# ============================================================

def create_registry():

    registry = AgentRegistry()

    registry.register(
        "research",
        ResearchAgent()
    )

    registry.register(
        "coding",
        CodingAgent()
    )

    registry.register(
        "testing",
        TestingAgent()
    )

    return registry


# ============================================================
# 1. Normal Dependency Test
# ============================================================

def test_dependency_chain():

    print("\n--- Scheduler Runtime Integration ---")

    registry = create_registry()

    runtime = Runtime(
        number_of_lanes=1,
        registry=registry,
        resource_limits={
            "research": 2,
            "coding": 1,
            "testing": 1
        }
    )

    scheduler = Scheduler()

    research = Job(
        name="Research",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    coding = Job(
        name="Coding",
        agent_type="coding",
        priority=PriorityLevel.MEDIUM,
        dependencies=[
            research.job_id
        ]
    )

    testing = Job(
        name="Testing",
        agent_type="testing",
        priority=PriorityLevel.LOW,
        dependencies=[
            coding.job_id
        ]
    )

    scheduler.add_job(research)
    scheduler.add_job(coding)
    scheduler.add_job(testing)

    print("Initial states:")
    print("Research:", research.status)
    print("Coding:", coding.status)
    print("Testing:", testing.status)

    scheduler.run_all(runtime)

    print("\nFinal states:")
    print("Research:", research.status)
    print("Coding:", coding.status)
    print("Testing:", testing.status)

    assert research.status == JobStatus.COMPLETED
    assert coding.status == JobStatus.COMPLETED
    assert testing.status == JobStatus.COMPLETED

    runtime.shutdown()


# ============================================================
# 2. Failure Test
# ============================================================

def test_failure():

    print("\n--- Failure Test ---")

    failure_registry = AgentRegistry()

    failure_registry.register(
        "research",
        FailingAgent()
    )

    failure_registry.register(
        "coding",
        CodingAgent()
    )

    failure_runtime = Runtime(
        number_of_lanes=2,
        registry=failure_registry,
        resource_limits={
            "research": 1,
            "coding": 1
        }
    )

    failure_scheduler = Scheduler()

    failed_job = Job(
        name="Failed Research",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    dependent_job = Job(
        name="Dependent Coding",
        agent_type="coding",
        priority=PriorityLevel.MEDIUM,
        dependencies=[
            failed_job.job_id
        ]
    )

    failure_scheduler.add_job(failed_job)
    failure_scheduler.add_job(dependent_job)

    print("Before failure:")
    print("Failed Research:", failed_job.status)
    print("Dependent Coding:", dependent_job.status)

    failure_scheduler.run_all(
        failure_runtime
    )

    print("\nAfter failure:")
    print("Failed Research:", failed_job.status)
    print("Dependent Coding:", dependent_job.status)

    assert failed_job.status == JobStatus.FAILED

    assert (
        dependent_job.status
        == JobStatus.PENDING
    )

    failure_runtime.shutdown()


# ============================================================
# 3. Agent Registry Test
# ============================================================

def test_registry():

    print("\n--- Agent Registry Test ---")

    registry = create_registry()

    print(
        "Research exists:",
        registry.exists("research")
    )

    print(
        "Coding exists:",
        registry.exists("coding")
    )

    print(
        "Testing exists:",
        registry.exists("testing")
    )

    print(
        "Research output:",
        registry.get("research").run(
            "Find information about AI"
        )
    )

    print(
        "Coding output:",
        registry.get("coding").run(
            "Implement the AI feature"
        )
    )

    print(
        "Testing output:",
        registry.get("testing").run(
            "Test the AI feature"
        )
    )

    assert registry.exists("research")
    assert registry.exists("coding")
    assert registry.exists("testing")


# ============================================================
# 4. Invalid Agent Test
# ============================================================

def test_invalid_agent():

    print("\n--- Invalid Agent Test ---")

    registry = create_registry()

    runtime = Runtime(
        number_of_lanes=1,
        registry=registry,
        resource_limits={
            "research": 1,
            "coding": 1,
            "testing": 1
        }
    )

    invalid_job = Job(
        name="Unknown Task",
        agent_type="unknown",
        priority=PriorityLevel.MEDIUM
    )

    print("Before invalid agent:")
    print("Unknown Task:", invalid_job.status)

    result = runtime.run_job(
        invalid_job
    )

    print("After invalid agent:")
    print("Unknown Task:", invalid_job.status)

    assert result is False
    assert invalid_job.status == JobStatus.FAILED

    runtime.shutdown()


# ============================================================
# 5. Resource Manager Test
# ============================================================

def test_resource_manager():

    print("\n--- Resource Manager Test ---")

    registry = create_registry()

    runtime = Runtime(
        number_of_lanes=1,
        registry=registry,
        resource_limits={
            "research": 2,
            "coding": 1,
            "testing": 1
        }
    )

    active_jobs = (
        runtime.resource_manager
        .get_active_count("research")
    )

    can_research = (
        runtime.resource_manager
        .can_execute("research")
    )

    can_unknown = (
        runtime.resource_manager
        .can_execute("unknown")
    )

    print(
        "Research active jobs:",
        active_jobs
    )

    print(
        "Can execute research:",
        can_research
    )

    print(
        "Can execute unknown agent:",
        can_unknown
    )

    assert active_jobs == 0
    assert can_research is True
    assert can_unknown is False

    runtime.shutdown()


# ============================================================
# 6. Parallel Execution Test
# ============================================================

def test_parallel_execution():

    print("\n--- Parallel Execution Test ---")

    registry = AgentRegistry()

    registry.register(
        "research",
        SlowResearchAgent()
    )

    runtime = Runtime(
        number_of_lanes=2,
        registry=registry,
        resource_limits={
            "research": 2
        }
    )

    scheduler = Scheduler()

    job1 = Job(
        name="Research A",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    job2 = Job(
        name="Research B",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    scheduler.add_job(job1)
    scheduler.add_job(job2)

    start_time = time.time()

    scheduler.run_all(runtime)

    elapsed = time.time() - start_time

    print("Job 1:", job1.status)
    print("Job 2:", job2.status)

    print(
        "Total execution time:",
        round(elapsed, 2),
        "seconds"
    )

    assert job1.status == JobStatus.COMPLETED
    assert job2.status == JobStatus.COMPLETED

    # Two 2-second jobs should finish in around 2 seconds
    assert elapsed < 3

    runtime.shutdown()


# ============================================================
# 7. Parallel Resource Limit Test
# ============================================================

def test_parallel_resource_limit():

    print("\n--- Parallel Resource Limit Test ---")

    registry = AgentRegistry()

    registry.register(
        "research",
        SlowResearchAgent()
    )

    runtime = Runtime(
        number_of_lanes=3,
        registry=registry,
        resource_limits={
            "research": 2
        }
    )

    scheduler = Scheduler()

    research1 = Job(
        name="Research 1",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    research2 = Job(
        name="Research 2",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    research3 = Job(
        name="Research 3",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    scheduler.add_job(research1)
    scheduler.add_job(research2)
    scheduler.add_job(research3)

    start_time = time.time()

    scheduler.run_all(runtime)

    elapsed = time.time() - start_time

    print(
        "Research 1:",
        research1.status
    )

    print(
        "Research 2:",
        research2.status
    )

    print(
        "Research 3:",
        research3.status
    )

    print(
        "Total execution time:",
        round(elapsed, 2),
        "seconds"
    )

    assert research1.status == JobStatus.COMPLETED
    assert research2.status == JobStatus.COMPLETED
    assert research3.status == JobStatus.COMPLETED

    # Resource limit = 2
    # First 2 jobs run together (~2 sec)
    # Third job runs after them (~2 sec)
    assert elapsed >= 4

    runtime.shutdown()


# ============================================================
# 8. Parallel Dependency Test
# ============================================================

def test_parallel_dependencies():

    print("\n--- Parallel Dependency Test ---")

    registry = AgentRegistry()

    registry.register(
        "research",
        SlowResearchAgent()
    )

    registry.register(
        "coding",
        CodingAgent()
    )

    runtime = Runtime(
        number_of_lanes=2,
        registry=registry,
        resource_limits={
            "research": 2,
            "coding": 2
        }
    )

    scheduler = Scheduler()

    research_a = Job(
        name="Research A",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    research_b = Job(
        name="Research B",
        agent_type="research",
        priority=PriorityLevel.HIGH
    )

    coding_a = Job(
        name="Coding A",
        agent_type="coding",
        priority=PriorityLevel.MEDIUM,
        dependencies=[
            research_a.job_id
        ]
    )

    coding_b = Job(
        name="Coding B",
        agent_type="coding",
        priority=PriorityLevel.MEDIUM,
        dependencies=[
            research_b.job_id
        ]
    )

    scheduler.add_job(research_a)
    scheduler.add_job(research_b)
    scheduler.add_job(coding_a)
    scheduler.add_job(coding_b)

    start_time = time.time()

    scheduler.run_all(runtime)

    elapsed = time.time() - start_time

    print(
        "Research A:",
        research_a.status
    )

    print(
        "Research B:",
        research_b.status
    )

    print(
        "Coding A:",
        coding_a.status
    )

    print(
        "Coding B:",
        coding_b.status
    )

    print(
        "Total execution time:",
        round(elapsed, 2),
        "seconds"
    )

    assert research_a.status == JobStatus.COMPLETED
    assert research_b.status == JobStatus.COMPLETED

    assert coding_a.status == JobStatus.COMPLETED
    assert coding_b.status == JobStatus.COMPLETED

    # Research A + B execute concurrently.
    assert elapsed < 3

    runtime.shutdown()


# ============================================================
# Run All Tests
# ============================================================

if __name__ == "__main__":

    test_dependency_chain()

    test_failure()

    test_registry()

    test_invalid_agent()

    test_resource_manager()

    test_parallel_execution()

    test_parallel_resource_limit()

    test_parallel_dependencies()

    print(
        "\n========================================"
    )

    print(
        "ALL TESTS PASSED"
    )

    print(
        "========================================"
    )