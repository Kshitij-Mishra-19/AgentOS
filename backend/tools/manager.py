from typing import Any
import time

from .audit import AuditLogger
from .executor import ToolExecutor
from .permissions import PermissionManager
from .registry import Tool, ToolRegistry
from .sandbox import SandboxManager
from .validator import ToolValidator


class ToolManager:

    def __init__(self):
        self.registry = ToolRegistry()
        self.permissions = PermissionManager()
        self.sandbox = SandboxManager()
        self.executor = ToolExecutor()
        self.validator = ToolValidator()
        self.audit = AuditLogger()

    def register_tool(self, tool: Tool) -> None:
        self.registry.register(tool)

    def unregister_tool(self, tool_name: str) -> None:
        self.registry.unregister(tool_name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "timeout": tool.timeout,
                "requires_permission": tool.requires_permission,
            }
            for tool in self.registry.list_tools()
        ]

    def get_audit_logs(self) -> list[dict[str, Any]]:
        return self.audit.get_logs()

    def execute_tool(
        self,
        agent_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        # 1. Check if tool exists
        if not self.registry.exists(tool_name):
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.audit.log(
                agent_id=agent_id,
                tool_name=tool_name,
                success=False,
                duration_ms=duration_ms,
                error_type="TOOL_NOT_FOUND",
            )

            return {
                "success": False,
                "error": {
                    "type": "TOOL_NOT_FOUND",
                    "message": f"Tool '{tool_name}' is not registered.",
                },
            }

        tool = self.registry.get(tool_name)

        # 2. Check permission
        if tool.requires_permission:

            allowed = self.permissions.check(
                agent_id=agent_id,
                tool_name=tool_name,
                action="execute",
            )

            if not allowed:
                duration_ms = (time.perf_counter() - start_time) * 1000

                self.audit.log(
                    agent_id=agent_id,
                    tool_name=tool_name,
                    success=False,
                    duration_ms=duration_ms,
                    error_type="PERMISSION_DENIED",
                )

                return {
                    "success": False,
                    "error": {
                        "type": "PERMISSION_DENIED",
                        "message": (
                            f"Agent '{agent_id}' is not authorized "
                            f"to execute '{tool_name}'."
                        ),
                    },
                }

        # 3. Validate input
        is_valid, error_message = self.validator.validate(
            arguments=arguments,
            schema=tool.input_schema,
        )

        if not is_valid:
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.audit.log(
                agent_id=agent_id,
                tool_name=tool_name,
                success=False,
                duration_ms=duration_ms,
                error_type="INVALID_INPUT",
            )

            return {
                "success": False,
                "error": {
                    "type": "INVALID_INPUT",
                    "message": error_message,
                },
            }

        # 4. Sandbox validation
        if not self.sandbox.validate(tool_name):
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.audit.log(
                agent_id=agent_id,
                tool_name=tool_name,
                success=False,
                duration_ms=duration_ms,
                error_type="SANDBOX_REJECTED",
            )

            return {
                "success": False,
                "error": {
                    "type": "SANDBOX_REJECTED",
                    "message": "Tool execution rejected by sandbox.",
                },
            }

        # 5. Execute tool
        result = self.executor.execute(
            tool=tool,
            arguments=arguments,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000

        # 6. Audit result
        error_type = None

        if not result.get("success"):
            error_type = result.get("error", {}).get("type")

        self.audit.log(
            agent_id=agent_id,
            tool_name=tool_name,
            success=result.get("success", False),
            duration_ms=duration_ms,
            error_type=error_type,
        )

        return result