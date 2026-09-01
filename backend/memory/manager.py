from typing import Any

from .interfaces import MemoryInterface
from .models import Memory, MemoryType
from .storage import InMemoryStorage, MemoryStorage


class MemoryManager(MemoryInterface):

    def __init__(self, storage: MemoryStorage | None = None):
        self.storage = storage or InMemoryStorage()

    def remember(
        self,
        agent_id: str,
        content: str,
        memory_type: str,
        metadata: dict[str, Any] | None = None
    ) -> Memory:

        memory = Memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType(memory_type),
            metadata=metadata or {}
        )

        self.storage.save(memory)

        return memory

    def recall(
        self,
        agent_id: str,
        query: str
    ) -> list[Memory]:

        results = []

        for memory in self.storage.get_all():

            if memory.agent_id != agent_id:
                continue

            if query.lower() in memory.content.lower():
                results.append(memory)

        return results

    def update(
        self,
        memory_id: str,
        content: str
    ) -> Memory:

        memory = self.storage.get(memory_id)

        if memory is None:
            raise KeyError(f"Memory not found: {memory_id}")

        memory.content = content

        self.storage.save(memory)

        return memory

    def forget(
        self,
        memory_id: str
    ) -> None:

        memory = self.storage.get(memory_id)

        if memory is None:
            raise KeyError(f"Memory not found: {memory_id}")

        self.storage.delete(memory_id)