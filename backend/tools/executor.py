import multiprocessing
import queue
import traceback
from typing import Any

from .registry import Tool


def _run_tool(
    handler,
    arguments: dict[str, Any],
    result_queue,
) -> None:
    try:
        result = handler(**arguments)

        result_queue.put({
            "success": True,
            "result": result,
        })

    except Exception as exc:
        result_queue.put({
            "success": False,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "traceback": traceback.format_exc(),
        })


class ToolExecutor:

    def execute(
        self,
        tool: Tool,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue()

        process = context.Process(
            target=_run_tool,
            args=(
                tool.handler,
                arguments,
                result_queue,
            ),
        )

        process.start()

        process.join(timeout=tool.timeout)

        if process.is_alive():
            process.terminate()
            process.join(timeout=2)

            if process.is_alive():
                process.kill()
                process.join()

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

        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            return {
                "success": False,
                "tool": tool.name,
                "error": {
                    "type": "NO_RESULT",
                    "message": (
                        "Tool process exited without "
                        "returning a result."
                    ),
                },
            }

        if result["success"]:
            return {
                "success": True,
                "tool": tool.name,
                "result": result["result"],
            }

        return {
            "success": False,
            "tool": tool.name,
            "error": result["error"],
        }