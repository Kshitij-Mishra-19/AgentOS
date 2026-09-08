from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    requires_permission: bool = True


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def _validate_tool(self, tool: Tool) -> None:

        if not tool.name or not tool.name.strip():
            raise ValueError("Tool name cannot be empty.")

        if not tool.description or not tool.description.strip():
            raise ValueError("Tool description cannot be empty.")

        if not callable(tool.handler):
            raise ValueError("Tool handler must be callable.")

        if not isinstance(tool.input_schema, dict):
            raise ValueError("Tool input_schema must be a dictionary.")

        if not isinstance(tool.timeout, int):
            raise ValueError("Tool timeout must be an integer.")

        if tool.timeout <= 0:
            raise ValueError("Tool timeout must be greater than 0.")

        if not isinstance(tool.requires_permission, bool):
            raise ValueError(
                "Tool requires_permission must be a boolean."
            )

    def register(self, tool: Tool) -> None:

        self._validate_tool(tool)

        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:

        if tool_name not in self._tools:
            raise KeyError(
                f"Tool not found: {tool_name}"
            )

        del self._tools[tool_name]

    def get(self, tool_name: str) -> Tool:

        tool = self._tools.get(tool_name)

        if tool is None:
            raise KeyError(
                f"Tool not found: {tool_name}"
            )

        return tool

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def exists(self, tool_name: str) -> bool:
        return tool_name in self._tools