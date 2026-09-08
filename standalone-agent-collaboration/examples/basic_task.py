"""Run a single task through the full Planner -> Executor -> Reviewer workflow.

Usage:
    python examples/basic_task.py

This is deterministic: it uses the built-in MockLLMProvider, so running
it repeatedly produces the same plan, execution results, and review
decision every time -- useful for demos and for eyeballing behavior
without needing any external API.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.bootstrap import Application  # noqa: E402


async def main() -> None:
    app = Application.from_config_path()

    title = "Launch a website"
    description = "Create a simple project plan for launching a website."

    print(f"=== Running task: {title} ===\n")
    result = await app.run_task(title, description)

    print(f"Status: {result.status}")
    print(f"Revision cycles used: {result.revision_count}\n")

    if result.success:
        print("Final output:")
        print(json.dumps(result.final_output, indent=2))
        print("\nFinal review:")
        print(json.dumps(result.review, indent=2))
    else:
        print(f"Workflow failed: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
