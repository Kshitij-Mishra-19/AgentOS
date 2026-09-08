from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from .registry import Tool


class ToolExecutor:

    def execute(
        self,
        tool: Tool,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        executor = ThreadPoolExecutor(max_workers=1)

        try:
            future = executor.submit(
                tool.handler,
                **arguments,
            )

            result = future.result(
                timeout=tool.timeout
            )

            return {
                "success": True,
                "tool": tool.name,
                "result": result,
            }

        except TimeoutError:

            return {
                "success": False,
                "tool": tool.name,
                "error": {
                    "type": "TIMEOUT",
                    "message": (
                        f"Tool execution exceeded "
                        f"{tool.timeout} seconds."
                    ),
                },
            }

        except Exception as exc:

            return {
                "success": False,
                "tool": tool.name,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

        finally:
            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )