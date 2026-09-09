from dataclasses import dataclass
from typing import Any

from planner import AgentPlanner
from tools.manager import ToolManager


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    success: bool
    data: dict[str, Any]


class Agent:

    def __init__(
        self,
        agent_id: str,
        tool_manager: ToolManager,
    ):
        self.agent_id = agent_id
        self.tool_manager = tool_manager
        self.planner = AgentPlanner()

    def execute_tool(
        self,
        request: ToolRequest,
    ) -> ToolResult:

        result = self.tool_manager.execute_tool(
            agent_id=self.agent_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
        )

        return ToolResult(
            success=result.get("success", False),
            data=result,
        )

    def run(
        self,
        goal: str,
    ) -> ToolResult:

        plan = self.planner.create_plan(goal)

        request = ToolRequest(
            tool_name=plan.tool_name,
            arguments=plan.arguments,
        )

        return self.execute_tool(request)