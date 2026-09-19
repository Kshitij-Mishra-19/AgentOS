"""Runtime responsible for dispatching scheduled tasks to agents."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from core.message_bus import MessageBus
from schemas.message import AgentMessage, MessageType
from schemas.result import (
    ExecutionResult,
    ExecutionStatus,
)


class SchedulerRuntime:
    """Executes scheduled subtasks through the MessageBus."""

    def __init__(
        self,
        *,
        bus: MessageBus,
        number_of_lanes: int = 2,
        resource_limits: Optional[
            dict[str, int]
        ] = None,
        default_timeout: float = 60.0,
    ) -> None:

        self.bus = bus

        self.number_of_lanes = max(
            1,
            int(number_of_lanes),
        )

        self.resource_limits = (
            resource_limits
            or {
                "executor": self.number_of_lanes,
            }
        )

        self.default_timeout = max(
            0.1,
            float(default_timeout),
        )

        self._semaphore = asyncio.Semaphore(
            self.number_of_lanes
        )

    # ---------------------------------------------------------
    # Execute
    # ---------------------------------------------------------

    async def execute(
        self,
        *,
        task_id: str,
        subtask_id: str,
        title: str,
        description: str,
        assigned_role: str = "executor",
        timeout: Optional[float] = None,
        metadata: Optional[
            dict[str, Any]
        ] = None,
    ) -> ExecutionResult:

        resource = assigned_role or "executor"

        # The current collaboration repository has an
        # ExecutorAgent subscribed to "executor".
        # Future roles can use their own MessageBus subscriber.

        async with self._semaphore:

            message = AgentMessage(
                sender="scheduler",
                recipient=resource,
                message_type=MessageType.TASK_ASSIGNED,
                task_id=task_id,
                payload={
                    "subtask_id": subtask_id,
                    "title": title,
                    "description": description,
                },
                metadata=metadata or {},
            )

            try:

                replies = await asyncio.wait_for(
                    self.bus.publish(message),
                    timeout=(
                        timeout
                        if timeout is not None
                        else self.default_timeout
                    ),
                )

            except asyncio.TimeoutError:

                return ExecutionResult(
                    task_id=subtask_id,
                    status=ExecutionStatus.FAILED,
                    summary="Scheduled execution timed out.",
                    errors=[
                        f"Execution exceeded timeout of "
                        f"{timeout or self.default_timeout} seconds."
                    ],
                    metadata={
                        "scheduler": "mlfq",
                        "resource": resource,
                    },
                )

            except Exception as exc:

                return ExecutionResult(
                    task_id=subtask_id,
                    status=ExecutionStatus.FAILED,
                    summary="Scheduled execution failed.",
                    errors=[
                        str(exc)
                    ],
                    metadata={
                        "scheduler": "mlfq",
                        "resource": resource,
                    },
                )

            if not replies:

                return ExecutionResult(
                    task_id=subtask_id,
                    status=ExecutionStatus.FAILED,
                    summary="Executor returned no reply.",
                    errors=[
                        "No AgentMessage reply received from executor."
                    ],
                    metadata={
                        "scheduler": "mlfq",
                        "resource": resource,
                    },
                )

            reply = replies[0]

            if "result" not in reply.payload:

                return ExecutionResult(
                    task_id=subtask_id,
                    status=ExecutionStatus.FAILED,
                    summary="Executor returned malformed output.",
                    errors=[
                        "Missing 'result' in executor response."
                    ],
                    metadata={
                        "scheduler": "mlfq",
                        "resource": resource,
                    },
                )

            try:

                result = ExecutionResult.from_dict(
                    reply.payload["result"]
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:

                return ExecutionResult(
                    task_id=subtask_id,
                    status=ExecutionStatus.FAILED,
                    summary="Executor result could not be parsed.",
                    errors=[
                        str(exc)
                    ],
                    metadata={
                        "scheduler": "mlfq",
                        "resource": resource,
                    },
                )

            return result

    # ---------------------------------------------------------
    # Shutdown
    # ---------------------------------------------------------

    async def shutdown(self) -> None:
        """Reserved for future external runtime resources."""

        await asyncio.sleep(0)