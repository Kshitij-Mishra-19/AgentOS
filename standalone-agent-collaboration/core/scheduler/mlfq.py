"""Multi-Level Feedback Queue scheduler.

The scheduler adapts classical MLFQ ideas to agent tasks.

Priority levels:

    HIGH   -> 0
    MEDIUM -> 1
    LOW    -> 2

Tasks within the same level are executed FIFO.

Aging promotes waiting tasks so that lower-priority tasks cannot
starve indefinitely.
"""

from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class QueueLevel(IntEnum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2


@dataclass
class ScheduledItem:
    """An item waiting in the scheduler."""

    task_id: str
    priority: int
    sequence: int
    queue_level: QueueLevel
    enqueued_at: float


class MLFQScheduler:
    """Priority-based scheduler using multiple FIFO priority levels."""

    def __init__(
        self,
        *,
        aging_threshold: float = 30.0,
    ) -> None:

        self.aging_threshold = max(
            0.0,
            aging_threshold,
        )

        self._queues: dict[
            QueueLevel,
            list[tuple[int, int, ScheduledItem]],
        ] = {
            QueueLevel.HIGH: [],
            QueueLevel.MEDIUM: [],
            QueueLevel.LOW: [],
        }

        self._sequence = itertools.count()

        self._items: dict[str, ScheduledItem] = {}

    # ---------------------------------------------------------
    # Priority mapping
    # ---------------------------------------------------------

    @staticmethod
    def level_for_priority(
        priority: int,
    ) -> QueueLevel:

        priority = int(priority)

        if priority <= 1:
            return QueueLevel.HIGH

        if priority <= 2:
            return QueueLevel.MEDIUM

        return QueueLevel.LOW

    # ---------------------------------------------------------
    # Enqueue
    # ---------------------------------------------------------

    def enqueue(
        self,
        task_id: str,
        priority: int = 3,
    ) -> None:

        if task_id in self._items:
            return

        sequence = next(self._sequence)

        level = self.level_for_priority(
            priority
        )

        item = ScheduledItem(
            task_id=task_id,
            priority=priority,
            sequence=sequence,
            queue_level=level,
            enqueued_at=time.monotonic(),
        )

        self._items[task_id] = item

        heapq.heappush(
            self._queues[level],
            (
                sequence,
                sequence,
                item,
            ),
        )

    # ---------------------------------------------------------
    # Aging
    # ---------------------------------------------------------

    def _promote_aged_tasks(self) -> None:

        if self.aging_threshold <= 0:
            return

        now = time.monotonic()

        for level in (
            QueueLevel.LOW,
            QueueLevel.MEDIUM,
        ):

            aged: list[ScheduledItem] = []

            remaining: list[
                tuple[int, int, ScheduledItem]
            ] = []

            while self._queues[level]:

                _, _, item = heapq.heappop(
                    self._queues[level]
                )

                if (
                    now - item.enqueued_at
                    >= self.aging_threshold
                ):

                    aged.append(item)

                else:

                    remaining.append(
                        (
                            item.sequence,
                            item.sequence,
                            item,
                        )
                    )

            for entry in remaining:
                heapq.heappush(
                    self._queues[level],
                    entry,
                )

            for item in aged:

                new_level = QueueLevel(
                    max(
                        QueueLevel.HIGH,
                        level - 1,
                    )
                )

                item.queue_level = new_level

                heapq.heappush(
                    self._queues[new_level],
                    (
                        item.sequence,
                        item.sequence,
                        item,
                    ),
                )

    # ---------------------------------------------------------
    # Dequeue
    # ---------------------------------------------------------

    def dequeue(self) -> Optional[ScheduledItem]:

        self._promote_aged_tasks()

        for level in (
            QueueLevel.HIGH,
            QueueLevel.MEDIUM,
            QueueLevel.LOW,
        ):

            queue = self._queues[level]

            while queue:

                _, _, item = heapq.heappop(
                    queue
                )

                if item.task_id not in self._items:
                    continue

                del self._items[
                    item.task_id
                ]

                return item

        return None

    # ---------------------------------------------------------
    # Remove
    # ---------------------------------------------------------

    def remove(
        self,
        task_id: str,
    ) -> bool:

        return (
            self._items.pop(
                task_id,
                None,
            )
            is not None
        )

    # ---------------------------------------------------------
    # State
    # ---------------------------------------------------------

    def contains(
        self,
        task_id: str,
    ) -> bool:

        return task_id in self._items

    def empty(self) -> bool:

        return not self._items

    def size(self) -> int:

        return len(self._items)

    def clear(self) -> None:

        for queue in self._queues.values():
            queue.clear()

        self._items.clear()