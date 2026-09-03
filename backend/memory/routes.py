from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.memory.manager import MemoryManager
from backend.memory.models import MemoryType


router = APIRouter(
    prefix="/memory",
    tags=["Memory"]
)

memory_manager = MemoryManager()


# ============================================================
# Request Models
# ============================================================

class RememberRequest(BaseModel):
    agent_id: str
    content: str
    memory_type: MemoryType
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    agent_id: str
    query: str
    limit: int = Field(default=5, ge=1, le=50)


class UpdateRequest(BaseModel):
    agent_id: str
    content: str


class WorkingMemoryRequest(BaseModel):
    agent_id: str
    key: str
    value: str
    ttl: int | None = Field(default=None, ge=1)


# ============================================================
# Health
# ============================================================

@router.get("/health")
def memory_health():
    return {
        "module": "memory",
        "status": "healthy"
    }


# ============================================================
# Long-Term Memory
# ============================================================

@router.post("")
def remember(request: RememberRequest):
    memory = memory_manager.remember(
        agent_id=request.agent_id,
        content=request.content,
        memory_type=request.memory_type,
        importance=request.importance,
        confidence=request.confidence,
        metadata=request.metadata,
    )

    return {
        "id": memory.id,
        "agent_id": memory.agent_id,
        "content": memory.content,
        "memory_type": memory.memory_type.value,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "metadata": memory.metadata,
    }


# ============================================================
# Semantic Search
# ============================================================

@router.post("/search")
def search(request: SearchRequest):
    memories = memory_manager.search(
        agent_id=request.agent_id,
        query=request.query,
        limit=request.limit,
    )

    return [
        {
            "id": memory.id,
            "agent_id": memory.agent_id,
            "content": memory.content,
            "memory_type": memory.memory_type.value,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "metadata": memory.metadata,
        }
        for memory in memories
    ]


# ============================================================
# Working Memory
# ============================================================

@router.put("/working")
def set_working_memory(
    request: WorkingMemoryRequest
):
    memory_manager.set_working_memory(
        agent_id=request.agent_id,
        key=request.key,
        value=request.value,
        ttl=request.ttl,
    )

    return {
        "agent_id": request.agent_id,
        "key": request.key,
        "status": "stored"
    }


@router.get("/working/{agent_id}/{key}")
def get_working_memory(
    agent_id: str,
    key: str
):
    value = memory_manager.get_working_memory(
        agent_id=agent_id,
        key=key,
    )

    return {
        "agent_id": agent_id,
        "key": key,
        "value": value,
    }


@router.delete("/working/{agent_id}/{key}")
def delete_working_memory(
    agent_id: str,
    key: str
):
    memory_manager.delete_working_memory(
        agent_id=agent_id,
        key=key,
    )

    return {
        "agent_id": agent_id,
        "key": key,
        "status": "deleted"
    }


@router.delete("/working/{agent_id}")
def clear_working_memory(
    agent_id: str
):
    memory_manager.clear_working_memory(
        agent_id=agent_id,
    )

    return {
        "agent_id": agent_id,
        "status": "cleared"
    }


# ============================================================
# Recall
# ============================================================

@router.get("/{agent_id}")
def recall(agent_id: str):
    memories = memory_manager.recall(
        agent_id=agent_id,
        query=""
    )

    return [
        {
            "id": memory.id,
            "agent_id": memory.agent_id,
            "content": memory.content,
            "memory_type": memory.memory_type.value,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "metadata": memory.metadata,
        }
        for memory in memories
    ]


# ============================================================
# Update Memory
# ============================================================

@router.put("/{memory_id}")
def update_memory(
    memory_id: str,
    request: UpdateRequest
):
    try:
        memory = memory_manager.update(
            memory_id=memory_id,
            agent_id=request.agent_id,
            content=request.content,
        )

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Agent cannot modify this memory"
        )

    return {
        "id": memory.id,
        "agent_id": memory.agent_id,
        "content": memory.content,
        "memory_type": memory.memory_type.value,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "metadata": memory.metadata,
    }


# ============================================================
# Forget Memory
# ============================================================

@router.delete("/{memory_id}")
def forget_memory(
    memory_id: str,
    agent_id: str
):
    try:
        memory_manager.forget(
            memory_id=memory_id,
            agent_id=agent_id,
        )

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Agent cannot delete this memory"
        )

    return {
        "id": memory_id,
        "status": "deleted"
    }