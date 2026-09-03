from abc import ABC, abstractmethod
from backend.memory.db import get_connection
from .models import Memory, MemoryType
import json

class MemoryStorage(ABC):

    @abstractmethod
    def save(self, memory: Memory) -> None:
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Memory | None:
        pass

    @abstractmethod
    def get_all(self) -> list[Memory]:
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> None:
        pass


class InMemoryStorage(MemoryStorage):

    def __init__(self):
        self._data: dict[str, Memory] = {}

    def save(self, memory: Memory) -> None:
        self._data[memory.id] = memory

    def get(self, memory_id: str) -> Memory | None:
        return self._data.get(memory_id)

    def get_all(self) -> list[Memory]:
        return list(self._data.values())

    def delete(self, memory_id: str) -> None:
        self._data.pop(memory_id, None)


class PostgresStorage(MemoryStorage):

    def save(self, memory: Memory) -> None:

        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO memories (
                        id,
                        agent_id,
                        content,
                        memory_type,
                        importance,
                        confidence,
                        created_at,
                        updated_at,
                        expires_at,
                        metadata,
                        embedding
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        memory_type = EXCLUDED.memory_type,
                        importance = EXCLUDED.importance,
                        confidence = EXCLUDED.confidence,
                        updated_at = EXCLUDED.updated_at,
                        expires_at = EXCLUDED.expires_at,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        memory.id,
                        memory.agent_id,
                        memory.content,
                        memory.memory_type.value,
                        memory.importance,
                        memory.confidence,
                        memory.created_at,
                        memory.updated_at,
                        memory.expires_at,
                        json.dumps(memory.metadata),
                        memory.embedding
                    )
                )

            connection.commit()

    def get(self, memory_id: str) -> Memory | None:

        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        agent_id,
                        content,
                        memory_type,
                        importance,
                        confidence,
                        created_at,
                        updated_at,
                        expires_at,
                        metadata,
                        embedding
                    FROM memories
                    WHERE id = %s
                    """,
                    (memory_id,)
                )

                row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_memory(row)

    def get_all(self) -> list[Memory]:

        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        agent_id,
                        content,
                        memory_type,
                        importance,
                        confidence,
                        created_at,
                        updated_at,
                        expires_at,
                        metadata,
                        embedding
                    FROM memories
                    """
                )

                rows = cursor.fetchall()

        return [self._row_to_memory(row) for row in rows]

    def delete(self, memory_id: str) -> None:

        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    DELETE FROM memories
                    WHERE id = %s
                    """,
                    (memory_id,)
                )

            connection.commit()

    @staticmethod
    def _row_to_memory(row) -> Memory:

        return Memory(
            id=str(row[0]),
            agent_id=row[1],
            content=row[2],
            memory_type=MemoryType(row[3]),
            importance=row[4],
            confidence=row[5],
            created_at=row[6],
            updated_at=row[7],
            expires_at=row[8],
            metadata=row[9] or {},
            embedding = row[10]
        )