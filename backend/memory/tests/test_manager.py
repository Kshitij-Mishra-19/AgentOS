from ..manager import MemoryManager
from datetime import datetime, timedelta

def test_remember_and_recall():

    manager = MemoryManager()

    memory = manager.remember(
        agent_id="research-agent",
        content="Deployment failed because DATABASE_URL was missing.",
        memory_type="episodic"
    )

    results = manager.recall(
        agent_id="research-agent",
        query="DATABASE_URL"
    )

    assert memory in results


def test_update():

    manager = MemoryManager()

    memory = manager.remember(
        agent_id="test-agent",
        content="Old information",
        memory_type="semantic"
    )

    manager.update(
        memory.id,
        "test-agent",
        "New information"
    )

    # 1. Fetch the updated results from the database
    results = manager.recall(
        agent_id="test-agent",
        query="New information"
    )

    # 2. Extract the updated item from the returned list
    assert len(results) > 0
    updated_memory = results[0]

    # 3. Assert against the freshly pulled record
    assert updated_memory.content == "New information"



def test_forget():

    manager = MemoryManager()

    memory = manager.remember(
        agent_id="test-agent",
        content="Temporary information",
        memory_type="working"
    )

    manager.forget(memory.id , "test-agent")

    results = manager.recall(
        agent_id="test-agent",
        query="Temporary"
    )

    assert results == []

def test_agent_cannot_modify_other_agents_memory():

    manager = MemoryManager()

    memory = manager.remember(
        agent_id="research-agent",
        content="Private research information",
        memory_type="episodic"
    )

    try:
        manager.update(
            memory.id,
            "code-agent",
            "Malicious modification"
        )
        assert False
    except PermissionError:
        pass



def test_agent_cannot_delete_other_agents_memory():

    manager = MemoryManager()

    memory = manager.remember(
        agent_id="research-agent",
        content="Private research information",
        memory_type="episodic"
    )

    try:
        manager.forget(
            memory.id,
            "code-agent"
        )
        assert False
    except PermissionError:
        pass


def test_expired_memory_is_not_recalled():

    manager = MemoryManager()

    memory = manager.remember(
        agent_id="test-agent",
        content="Temporary information",
        memory_type="working"
    )

    memory.expires_at = datetime.utcnow() - timedelta(minutes=1)

    manager.storage.save(memory)

    results = manager.recall(
        agent_id="test-agent",
        query="Temporary"
    )

    assert results == []