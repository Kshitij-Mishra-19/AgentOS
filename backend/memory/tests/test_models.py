#Yeh aapka Testing Code (Pytest) hai. Iska kaam yeh pakka karna hai ki jo Memory dataclass aapne sabse pehle banayi thi, woh sahi se kaam kar rahi hai ya nahi.

from backend.memory.models import Memory, MemoryType


def test_memory_creation():
    memory = Memory(
        agent_id="test-agent",
        content="Aegis is running.",
        memory_type=MemoryType.WORKING
    )

    assert memory.agent_id == "test-agent"
    assert memory.content == "Aegis is running."
    assert memory.memory_type == MemoryType.WORKING
    assert memory.id is not None