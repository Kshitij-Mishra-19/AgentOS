"""
AgentOS - FastAPI Backend Server
Run with: uvicorn backend.server:app --reload --port 8000
"""
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from backend.agents.coding_agent import CodingAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.registry import AgentRegistry
from backend.agents.research_agent import ResearchAgent
from backend.agents.testing_agent import TestingAgent
from backend.models.enums import PriorityLevel
from backend.models.job import Job
from backend.runtime.runtime import Runtime
from backend.scheduler.scheduler import Scheduler

app = FastAPI(title="AgentOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Persistence ───────────────────────────────────────────────────────

RUNS_FILE = Path("data/runs.json")
RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()


def load_runs() -> dict[str, Any]:
    if RUNS_FILE.exists():
        try:
            return json.loads(RUNS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_runs():
    with _lock:
        RUNS_FILE.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")


# Load existing runs on startup
runs: dict[str, dict[str, Any]] = load_runs()

PRIORITY_MAP = {
    "HIGH": PriorityLevel.HIGH,
    "MEDIUM": PriorityLevel.MEDIUM,
    "LOW": PriorityLevel.LOW,
}


# ── Models ────────────────────────────────────────────────────────────

class GoalRequest(BaseModel):
    goal: str


# ── Helpers ───────────────────────────────────────────────────────────

def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register("research", ResearchAgent())
    registry.register("coding", CodingAgent())
    registry.register("testing", TestingAgent())
    return registry


def execute_run(run_id: str, goal: str):
    run = runs[run_id]
    try:
        planner = PlannerAgent()
        tasks = planner.plan(goal)
        run["tasks"] = tasks
        run["status"] = "running"
        save_runs()

        if not tasks:
            raise ValueError("Planner returned no tasks")

        registry = build_registry()
        scheduler = Scheduler()
        runtime = Runtime(
            number_of_lanes=3,
            registry=registry,
            resource_limits={"research": 2, "coding": 2, "testing": 2},
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

        def snapshot():
            return [
                {
                    "id": j.job_id,
                    "name": j.name,
                    "agent_type": j.agent_type,
                    "status": j.status.value if hasattr(j.status, "value") else str(j.status),
                    "result": j.result,
                    "error": j.error,
                }
                for j in jobs
            ]

        run["jobs"] = snapshot()
        save_runs()

        stop_live = threading.Event()

        def live_update():
            while not stop_live.is_set():
                run["jobs"] = snapshot()
                save_runs()
                stop_live.wait(2)

        Thread(target=live_update, daemon=True).start()

        scheduler.run_all(runtime)
        runtime.shutdown()
        stop_live.set()

        run["jobs"] = snapshot()
        run["status"] = "completed"
        run["completed_at"] = datetime.now().isoformat()
        save_runs()

    except Exception as e:
        import traceback
        run["status"] = "failed"
        run["error"] = str(e)
        run["traceback"] = traceback.format_exc()
        save_runs()
        print(f"[execute_run ERROR] {e}\n{traceback.format_exc()}")


# ── Routes ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "AgentOS API running"}


@app.get("/agents")
def get_agents():
    return [
        {"name": "Planner Agent", "type": "planner", "description": "Breaks goals into tasks"},
        {"name": "Research Agent", "type": "research", "description": "Researches topics"},
        {"name": "Coding Agent", "type": "coding", "description": "Writes code"},
        {"name": "Testing Agent", "type": "testing", "description": "Writes tests"},
    ]


@app.post("/run")
def start_run(body: GoalRequest):
    if not body.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    run_id = str(uuid.uuid4())
    runs[run_id] = {
        "id": run_id,
        "goal": body.goal,
        "status": "planning",
        "tasks": [],
        "jobs": [],
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    Thread(target=execute_run, args=(run_id, body.goal), daemon=True).start()
    return {"run_id": run_id}


@app.get("/run/{run_id}")
def get_run(run_id: str):
    run = runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/runs")
def list_runs():
    return list(runs.values())
