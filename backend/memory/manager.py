from typing import Any

from .interfaces import MemoryInterface
from .models import Memory, MemoryType
from .storage import InMemoryStorage, MemoryStorage

from backend.memory.storage import InMemoryStorage, MemoryStorage, PostgresStorage

from backend.memory.embeddings import EmbeddingService

from datetime import datetime
from backend.memory.vector_storage import VectorStorage

from backend.memory.working_memory import WorkingMemory


from backend.memory.ranking import RetrievalRanker

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
        self.working_memory = WorkingMemory()

    def remember(
        self,
        agent_id: str,
        content: str,
        memory_type: str,
        importance: float = 0.5,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None
    ) -> Memory:

        memory = Memory(
            agent_id=agent_id,
            content=content,
            memory_type=MemoryType(memory_type),
            importance=importance,
            confidence=confidence,
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
        memory.embedding = self.embedding_service.embed(content)
        self.storage.save(memory)
        self.vector_storage.add(
            memory_id=memory.id,
            embedding=memory.embedding,
            metadata={
            "agent_id": memory.agent_id,
            "memory_type": memory.memory_type.value
            }
        )
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
        self.vector_storage.delete(memory_id)





    def search(self , agent_id:str , query:str , limit:int = 5)-> list[Memory]:
        query_embedding = self.embedding_service.embed(query)
        results = self.vector_storage.search(embedding=query_embedding,  limit = limit , agent_id = agent_id)
        memory_ids = results["ids"][0]
        distances = results["distances"][0]
        ranked_memories = []
        for memory_id, distance in zip(memory_ids, distances):
            semantic_similarity = 1 - distance

            memory = self.storage.get(memory_id)
            retrieval_score = RetrievalRanker.score(
            semantic_similarity=semantic_similarity,
            importance=memory.importance,
            confidence=memory.confidence
            )
            if memory is None:
                continue
            if memory.agent_id != agent_id:
                continue
            if(memory.expires_at is not None and memory.expires_at <= datetime.utcnow()):
                continue
            ranked_memories.append((memory, retrieval_score))
            ranked_memories.sort(
            key=lambda item: item[1],
            reverse=True
            )
        return [memory for memory, score in ranked_memories]


    def set_working_memory(
        self,
        agent_id: str,
        key: str,
        value: str,
        ttl: int | None = None
    ) -> None:
        self.working_memory.set(
            agent_id=agent_id,
            key=key,
            value=value,
            ttl=ttl
        )

    def get_working_memory(
            self,
            agent_id: str,
            key: str
        ) -> str | None:
            return self.working_memory.get(
                agent_id=agent_id,
                key=key
            )

    def delete_working_memory(
            self,
            agent_id: str,
            key: str
        ) -> None:
            self.working_memory.delete(
                agent_id=agent_id,
                key=key
            )

    def clear_working_memory(self, agent_id: str) -> None:
        self.working_memory.clear_agent(agent_id)