from abc import ABC, abstractmethod

from .models import Memory


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