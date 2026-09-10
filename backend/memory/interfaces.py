from abc import ABC, abstractmethod
from typing import Any


class MemoryInterface(ABC):

    @abstractmethod
    def remember(
        self,
        agent_id: str,
        content: str,
        memory_type: str,
        metadata: dict[str, Any] | None = None
    ):
        pass

    @abstractmethod
    def recall(
        self,
        agent_id: str,
        query: str
    ):
        pass

    @abstractmethod
    def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 5
    ):
        pass
    
    @abstractmethod
    def update(
        self,
        memory_id: str,
        agent_id:str,
        content: str
    ):
        pass

    @abstractmethod
    def forget(
        self,
        memory_id: str
    ):
        pass
