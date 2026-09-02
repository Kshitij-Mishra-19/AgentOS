from typing import Any

from .interfaces import MemoryInterface
from .models import Memory, MemoryType
from .storage import InMemoryStorage, MemoryStorage

from backend.memory.storage import InMemoryStorage, MemoryStorage, PostgresStorage

from backend.memory.embeddings import EmbeddingService

from datetime import datetime
from backend.memory.vector_storage import VectorStorage
class MemoryManager(MemoryInterface):

    def __init__(
    self,
    storage: MemoryStorage | None = None,
    embedding_service: EmbeddingService | None = None,
    vector_storage: VectorStorage | None = None
    ):
        self.storage = storage or PostgresStorage()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_storage = vector_storage or VectorStorage()

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
        memory.embedding = self.embedding_service.embed(content)
        self.storage.save(memory)
        self.vector_storage.add(
            memory_id = memory.id,
            embedding = memory.embedding,
            metadata = {
                "agent_id"  : memory.agent_id,
                "memory_type": memory.memory_type.value
            }
        )
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
            if (
                memory.expires_at is not None and memory.expires_at <= datetime.utcnow()
            ):
                continue
            if query.lower() in memory.content.lower():
                results.append(memory)

        return results

    def update(
        self,
        memory_id: str,
        agent_id : str,
        content: str
    ) -> Memory:

        memory = self.storage.get(memory_id)

        if memory is None:
            raise KeyError(f"Memory not found: {memory_id}")
        if memory.agent_id != agent_id:
            raise PermissionError("Agent cannot modify this memory")
        memory.content = content

        self.storage.save(memory)

        return memory

    def forget(
        self,
        memory_id: str,
        agent_id : str
    ) -> None:

        memory = self.storage.get(memory_id)

        if memory is None:
            raise KeyError(f"Memory not found: {memory_id}")
        if memory.agent_id != agent_id:
            raise PermissionError("Agent cannot delete this memory")
        self.storage.delete(memory_id)



    def search(self , agent_id:str , query:str , limit:int = 5)-> list[Memory]:
        query_embedding = self.embedding_service.embed(query)
        results = self.vector_storage.search(embedding=query_embedding,  limit = limit)
        memory_ids = results["ids"][0]
        memories = []
        for memory_id in memory_ids:
            memory = self.storage.get(memory_id)
            if memory is None:
                continue
            if memory.agent_id != agent_id:
                continue
            if(memory.expires_at is not None and memory.expires_at <= datetime.utcnow):
                continue
        memories.append(memory)
        return memories