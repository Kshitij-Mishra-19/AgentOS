from __future__ import annotations

import asyncio


class ResourceManager:

    def __init__(
        self,
        limits: dict[str, int] | None = None,
    ) -> None:

        self.limits = limits or {}

        self._active: dict[str, int] = {}

        self._condition = asyncio.Condition()

    def can_execute(
        self,
        agent_type: str,
    ) -> bool:

        limit = self.limits.get(agent_type)

        if limit is None:
            return False

        return (
            self._active.get(
                agent_type,
                0,
            )
            < limit
        )

    async def acquire(
        self,
        agent_type: str,
    ) -> bool:

        limit = self.limits.get(agent_type)

        if limit is None:
            return False

        async with self._condition:

            while (
                self._active.get(
                    agent_type,
                    0,
                )
                >= limit
            ):
                await self._condition.wait()

            self._active[agent_type] = (
                self._active.get(
                    agent_type,
                    0,
                )
                + 1
            )

            return True

    async def release(
        self,
        agent_type: str,
    ) -> None:

        async with self._condition:

            if agent_type not in self._active:
                return

            self._active[agent_type] -= 1

            if self._active[agent_type] <= 0:
                del self._active[agent_type]

            self._condition.notify_all()

    def active_count(
        self,
        agent_type: str,
    ) -> int:

        return self._active.get(
            agent_type,
            0,
        )

    def total_active(self) -> int:
        return sum(
            self._active.values()
        )