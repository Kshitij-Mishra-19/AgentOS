"""A more elaborate example showing a workflow that goes through a
review rejection and a revision cycle before finishing.

Usage:
    python examples/sample_workflow.py

This wires the components manually (rather than through
``app.bootstrap.Application``) to show what's happening under the hood:
building the message bus, agents, and orchestrator directly, and using
a scripted Reviewer stub to force one rejection before approval so the
revision loop is visible without depending on the LLM provider's
specific heuristics.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.executor.agent import ExecutorAgent  # noqa: E402
from agents.planner.agent import PlannerAgent  # noqa: E402
from core.llm_provider import MockLLMProvider  # noqa: E402
from core.message_bus import MessageBus  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402
from schemas.message import MessageType  # noqa: E402
from schemas.result import ExecutionResult  # noqa: E402
from schemas.review import Review, ReviewDecision  # noqa: E402


def build_scripted_reviewer():
    """A reviewer stub that rejects the first attempt, then approves the second."""
    state = {"calls": 0}

    async def handler(message):
        state["calls"] += 1
        result = ExecutionResult.from_dict(message.payload["result"])

        if state["calls"] == 1:
            review = Review(
                task_id=result.task_id,
                decision=ReviewDecision.REJECTED,
                score=0.4,
                feedback="The summary section needs more detail on launch timeline.",
                required_changes=["Add a concrete launch timeline to the summary."],
            )
            message_type = MessageType.REVIEW_REJECTED
        else:
            review = Review(
                task_id=result.task_id,
                decision=ReviewDecision.APPROVED,
                score=0.92,
                feedback="Launch timeline is now included. Approved.",
            )
            message_type = MessageType.REVIEW_APPROVED

        return message.reply(sender="reviewer", message_type=message_type, payload={"review": review.to_dict()})

    return handler


async def main() -> None:
    llm_provider = MockLLMProvider()
    bus = MessageBus()

    planner = PlannerAgent(agent_id="planner", config={}, llm_provider=llm_provider)
    executor = ExecutorAgent(agent_id="executor", config={}, llm_provider=llm_provider)

    bus.subscribe("planner", planner.handle)
    bus.subscribe("executor", executor.handle)
    bus.subscribe("reviewer", build_scripted_reviewer())

    orchestrator = Orchestrator(bus=bus, max_revision_cycles=3)

    title = "Prepare launch announcement"
    description = "Draft an announcement plan for a product launch, including a timeline."

    print(f"=== Running task: {title} ===\n")
    result = await orchestrator.run(title, description)

    print(f"Status: {result.status}")
    print(f"Revision cycles used: {result.revision_count}")
    print(f"Final decision: {result.review['decision'] if result.review else 'n/a'}\n")
    print("Final output:")
    print(json.dumps(result.final_output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
