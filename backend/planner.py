from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Plan:
    tool_name: str
    arguments: dict[str, Any]


class AgentPlanner:

    def create_plan(
        self,
        goal: str,
    ) -> Plan:

        goal = goal.strip()

        if not goal:
            raise ValueError("Goal cannot be empty.")

        # Temporary deterministic planner.
        # Later this layer can be replaced by an LLM planner.

        if goal.lower().startswith("echo:"):
            message = goal[5:].strip()

            if not message:
                raise ValueError(
                    "Echo goal must contain a message."
                )

            return Plan(
                tool_name="echo",
                arguments={
                    "message": message,
                },
            )

        raise ValueError(
            f"No plan available for goal: '{goal}'"
        )