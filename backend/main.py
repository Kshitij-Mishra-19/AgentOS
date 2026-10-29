"""
AgentOS - Main Entry Point

Usage:
    python -m backend.main
    python backend/main.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Load .env from project root
from dotenv import load_dotenv
load_dotenv()

from backend.agents.registry import AgentRegistry
from backend.agents.research_agent import ResearchAgent
from backend.agents.coding_agent import CodingAgent
from backend.agents.testing_agent import TestingAgent
from backend.agents.planner_agent import PlannerAgent

from backend.models.job import Job
from backend.models.enums import PriorityLevel

from backend.scheduler.scheduler import Scheduler
from backend.runtime.runtime import Runtime


PRIORITY_MAP = {
    "HIGH": PriorityLevel.HIGH,
    "MEDIUM": PriorityLevel.MEDIUM,
    "LOW": PriorityLevel.LOW,
}


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register("research", ResearchAgent())
    registry.register("coding", CodingAgent())
    registry.register("testing", TestingAgent())
    return registry


def run_goal(goal: str):
    print("\n" + "=" * 60)
    print(f"  GOAL: {goal}")
    print("=" * 60)

    # Step 1: Plan
    planner = PlannerAgent()
    tasks = planner.plan(goal)

    print(f"\nPlan ({len(tasks)} tasks):")
    for i, t in enumerate(tasks, 1):
        print(f"  {i}. [{t['agent_type'].upper()}] {t['name']}")

    # Step 2: Build jobs with sequential dependencies
    registry = build_registry()
    scheduler = Scheduler()

    resource_limits = {
        "research": 2,
        "coding": 2,
        "testing": 2,
    }

    runtime = Runtime(
        number_of_lanes=3,
        registry=registry,
        resource_limits=resource_limits,
    )

    job_ids = []
    jobs = []

    for task in tasks:
        priority = PRIORITY_MAP.get(task.get("priority", "MEDIUM"), PriorityLevel.MEDIUM)
        deps = [job_ids[-1]] if job_ids else []

        job = Job(
            name=task["name"],
            agent_type=task["agent_type"],
            priority=priority,
            dependencies=deps,
        )

        jobs.append(job)
        job_ids.append(job.job_id)
        scheduler.add_job(job)

    # Step 3: Execute
    print("\nExecuting...\n")
    scheduler.run_all(runtime)
    runtime.shutdown()

    # Step 4: Save results to output folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    goal_slug = goal[:40].replace(" ", "_").replace("/", "-")
    out_dir = Path("output") / f"{timestamp}_{goal_slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save full results
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)

    for i, job in enumerate(jobs, 1):
        print(f"\n[{job.status.upper()}] {job.name}")
        print("-" * 40)

        # Determine file extension based on agent type
        ext = "md"
        if job.agent_type == "coding":
            ext = "md"  # markdown with code blocks
        elif job.agent_type == "testing":
            ext = "py"

        filename = f"{i:02d}_{job.agent_type}_{job.name[:30].replace(' ', '_')}.{ext}"
        filepath = out_dir / filename

        if job.result:
            print(job.result)

            # For testing agent, extract code block if present
            content = job.result
            if job.agent_type == "testing" and "```python" in content:
                code_start = content.find("```python") + 9
                code_end = content.find("```", code_start)
                content = content[code_start:code_end].strip()

            filepath.write_text(content, encoding="utf-8")
            print(f"  → Saved: {filepath}")
        if job.error:
            print(f"ERROR: {job.error}")
            filepath.with_suffix(".error.txt").write_text(job.error, encoding="utf-8")

    print(f"\n Output folder: {out_dir.resolve()}")
    print("=" * 60)


def main():
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
    else:
        print("AgentOS - AI Multi-Agent System")
        print("Enter your goal (or 'quit' to exit)\n")
        goal = input("Goal: ").strip()

        if not goal or goal.lower() == "quit":
            print("Exiting.")
            return

    run_goal(goal)


if __name__ == "__main__":
    main()
