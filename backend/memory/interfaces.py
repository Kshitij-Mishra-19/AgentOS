#Yeh code ek Blueprint (Naksha) hai jise programming me CRUD (Create, Read, Update, Delete) operations kehte hain. Yeh yeh tay karta hai ki AI ka memory system kaam kaise karega, par yeh khud kaam nahi karta (kyunki isme pass likha hai).

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
    def update(
        self,
        memory_id: str,
        content: str
    ):
        pass

    @abstractmethod
    def forget(
        self,
        memory_id: str
    ):
        pass