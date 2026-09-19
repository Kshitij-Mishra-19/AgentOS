"""Execution lane abstraction.

A lane represents one concurrent execution slot for an agent task.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExecutionLane:
    """Represents one scheduler execution lane."""

    lane_id: int
    busy: bool = False
    current_task_id: Optional[str] = None

    _lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        repr=False,
    )

    async def acquire(
        self,
        task_id: str,
    ) -> None:

        await self._lock.acquire()

        self.busy = True
        self.current_task_id = task_id

    def release(self) -> None:

        self.busy = False
        self.current_task_id = None

        if self._lock.locked():
            self._lock.release()


class ExecutionLanePool:
    """Pool of concurrent execution lanes."""

    def __init__(
        self,
        number_of_lanes: int,
    ) -> None:

        if number_of_lanes < 1:
            raise ValueError(
                "number_of_lanes must be at least 1."
            )

        self.lanes = [
            ExecutionLane(
                lane_id=index,
            )
            for index in range(
                number_of_lanes
            )
        ]

    def free_lane(
        self,
    ) -> Optional[ExecutionLane]:

        for lane in self.lanes:

            if not lane.busy:
                return lane

        return None

    def active_count(self) -> int:

        return sum(
            1
            for lane in self.lanes
            if lane.busy
        )

    def capacity(self) -> int:

        return len(self.lanes)