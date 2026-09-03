from backend.memory.embeddings import EmbeddingService
from datetime import datetime, timedelta
from uuid import uuid4
from backend.memory.manager import MemoryManager
def test_semantic_search():
    manager = MemoryManager()

    unique_agent = "semantic-search-test-agent-unique"

    python_memory = manager.remember(
        agent_id=unique_agent,
        content="Python is the programming language used by the user for backend server development.",
        memory_type="semantic"
    )

    manager.remember(
        agent_id=unique_agent,
        content="The user enjoys playing cricket, watching cricket matches, and following sports news.",
        memory_type="semantic"
    )

    results = manager.search(
        agent_id=unique_agent,
        query="Which programming language does the user use for backend server development?",
        limit=1
    )

    # print("\nSEARCH RESULTS:")
    # for memory in results:
    #     print("ID:", memory.id)
    #     print("CONTENT:", memory.content)
    #     print("EMBEDDING EXISTS:", memory.embedding is not None)

def test_agent_isolation_in_semantic_search():
    manager = MemoryManager()

    agent_a = "agent-a-isolation-test"
    agent_b = "agent-b-isolation-test"

    agent_a_memory = manager.remember(
        agent_id=agent_a,
        content="Agent A knows that Python is used for backend development.",
        memory_type="semantic"
    )

    manager.remember(
        agent_id=agent_b,
        content="Agent B knows that JavaScript is used for frontend development.",
        memory_type="semantic"
    )

    results = manager.search(
        agent_id=agent_b,
        query="Which programming language does Agent A use for backend development?",
        limit=5
    )

    assert all(memory.id != agent_a_memory.id for memory in results)
    assert all(memory.agent_id == agent_b for memory in results)


def test_update_synchronizes_semantic_search():
    manager = MemoryManager()

    agent_id = f"update-sync-test-agent-{uuid4()}"

    memory = manager.remember(
        agent_id=agent_id,
        content="The user works with Python for backend development.",
        memory_type="semantic"
    )

    manager.update(
        memory_id=memory.id,
        agent_id=agent_id,
        content="The user exclusively develops AEGIS_BACKEND_7429 using Java."
    )

    results = manager.search(
        agent_id=agent_id,
        query="What technology does the user use for AEGIS_BACKEND_7429?",
        limit=1
    )

    assert len(results) == 1
    assert results[0].id == memory.id
    assert results[0].content == "The user exclusively develops AEGIS_BACKEND_7429 using Java."



def test_forget_synchronizes_semantic_search():
    manager = MemoryManager()

    agent_id = "forget-sync-test-agent"

    memory = manager.remember(
        agent_id=agent_id,
        content="The user uses Python for backend development.",
        memory_type="semantic"
    )

    # Verify it can initially be found
    results_before = manager.search(
        agent_id=agent_id,
        query="Which programming language does the user use for backend development?",
        limit=1
    )

    assert len(results_before) == 1
    assert results_before[0].id == memory.id

    # Forget the memory
    manager.forget(
        memory_id=memory.id,
        agent_id=agent_id
    )

    # It should no longer be searchable
    results_after = manager.search(
        agent_id=agent_id,
        query="Which programming language does the user use for backend development?",
        limit=5
    )

    assert all(result.id != memory.id for result in results_after)



def test_expired_memory_is_not_found_by_semantic_search():
    manager = MemoryManager()

    agent_id = f"expired-search-test-agent-{uuid4()}"

    memory = manager.remember(
        agent_id=agent_id,
        content="AEGIS_EXPIRED_MEMORY_7429 contains secret semantic information.",
        memory_type="semantic"
    )

    memory.expires_at = datetime.utcnow() - timedelta(minutes=1)
    manager.storage.save(memory)

    results = manager.search(
        agent_id=agent_id,
        query="What information is inside AEGIS_EXPIRED_MEMORY_7429?",
        limit=5
    )

    assert all(result.id != memory.id for result in results)