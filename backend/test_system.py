from backend.agents.research_agent import ResearchAgent
from backend.agents.coding_agent import CodingAgent
from backend.agents.testing_agent import TestingAgent
from backend.agents.registry import AgentRegistry

from backend.models.job import Job
from backend.models.enums import PriorityLevel

from backend.scheduler.scheduler import Scheduler
from backend.runtime.runtime import Runtime


# ---------------- Agent Registry Setup ----------------

registry = AgentRegistry()

registry.register("research", ResearchAgent())
registry.register("coding", CodingAgent())
registry.register("testing", TestingAgent())


# ---------------- Runtime Setup ----------------

runtime = Runtime(
    number_of_lanes=1,
    registry=registry,
    resource_limits={
        "research": 2,
        "coding": 1,
        "testing": 1
    }
)


# ---------------- Normal Dependency Test ----------------

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
    dependencies=[research.job_id]
)

testing = Job(
    name="Testing",
    agent_type="testing",
    priority=PriorityLevel.LOW,
    dependencies=[coding.job_id]
)


# Jobs ko scheduler mein add karna zaroori hai
scheduler.add_job(research)
scheduler.add_job(coding)
scheduler.add_job(testing)


print("Initial states:")
print("Research:", research.status)
print("Coding:", coding.status)
print("Testing:", testing.status)


print("\n--- Scheduler Runtime Integration ---")

scheduler.run_all(runtime)


print("\nFinal states:")
print("Research:", research.status)
print("Coding:", coding.status)
print("Testing:", testing.status)


# ---------------- Failure Test ----------------

print("\n--- Failure Test ---")

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
    dependencies=[failed_job.job_id]
)


failure_scheduler.add_job(failed_job)
failure_scheduler.add_job(dependent_job)


print("Before failure:")
print("Failed Research:", failed_job.status)
print("Dependent Coding:", dependent_job.status)


failure_scheduler.run_all(runtime)


print("\nAfter failure:")
print("Failed Research:", failed_job.status)
print("Dependent Coding:", dependent_job.status)


# ---------------- Agent Registry Test ----------------

print("\n--- Agent Registry Test ---")

print("Research exists:", registry.exists("research"))
print("Coding exists:", registry.exists("coding"))
print("Testing exists:", registry.exists("testing"))

print(
    "Research output:",
    registry.get("research").run("Find information about AI")
)

print(
    "Coding output:",
    registry.get("coding").run("Implement the AI feature")
)

print(
    "Testing output:",
    registry.get("testing").run("Test the AI feature")
)


# ---------------- Invalid Agent Test ----------------

print("\n--- Invalid Agent Test ---")

invalid_job = Job(
    name="Unknown Task",
    agent_type="unknown",
    priority=PriorityLevel.MEDIUM
)

print("Before invalid agent:")
print("Unknown Task:", invalid_job.status)

runtime.run_job(invalid_job)

print("After invalid agent:")
print("Unknown Task:", invalid_job.status)


# ---------------- Resource Manager Test ----------------

print("\n--- Resource Manager Test ---")

print(
    "Research active jobs:",
    runtime.resource_manager.get_active_count("research")
)

print(
    "Can execute research:",
    runtime.resource_manager.can_execute("research")
)

print(
    "Can execute unknown agent:",
    runtime.resource_manager.can_execute("unknown")
)