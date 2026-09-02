from ..manager import MemoryManager


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

    manager.forget(memory.id)

    results = manager.recall(
        agent_id="test-agent",
        query="Temporary"
    )

    assert results == []