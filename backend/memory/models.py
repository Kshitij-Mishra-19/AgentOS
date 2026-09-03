#Yeh Python code ek AI Agent ke liye "Memory" (Yaaddasht) ka system banane ke liye hai. Jaise insaano ke paas alag-alag tarah ki memory hoti hai, vaise hi yeh code AI ko cheezein yaad rakhne me madad karta hai.

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


@dataclass
class Memory:
    agent_id: str
    content: str
    memory_type: MemoryType

    id: str = field(default_factory=lambda: str(uuid4()))

    importance: float = 0.5
    confidence: float = 1.0

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    expires_at: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    embedding: list[float] | None = None