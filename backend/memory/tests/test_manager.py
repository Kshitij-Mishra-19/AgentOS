from ..manager import MemoryManager , MemoryType
from datetime import datetime, timedelta
from uuid import uuid4
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


def test_manager_has_working_memory():
    manager = MemoryManager()

    assert manager.working_memory is not None



def test_manager_working_memory():
    manager = MemoryManager()

    agent_id = "manager-working-memory-test"

    manager.set_working_memory(
        agent_id=agent_id,
        key="current_task",
        value="Build authentication module"
    )

    result = manager.get_working_memory(
        agent_id=agent_id,
        key="current_task"
    )

    assert result == "Build authentication module"

    manager.delete_working_memory(
        agent_id=agent_id,
        key="current_task"
    )

    result_after_delete = manager.get_working_memory(
        agent_id=agent_id,
        key="current_task"
    )

    assert result_after_delete is None


def test_manager_clear_working_memory():
    manager = MemoryManager()

    agent_a = "manager-clear-agent-a"
    agent_b = "manager-clear-agent-b"

    manager.set_working_memory(
        agent_id=agent_a,
        key="current_task",
        value="Task A"
    )

    manager.set_working_memory(
        agent_id=agent_a,
        key="last_tool",
        value="Tool A"
    )

    manager.set_working_memory(
        agent_id=agent_b,
        key="current_task",
        value="Task B"
    )

    manager.clear_working_memory(agent_a)

    assert manager.get_working_memory(
        agent_id=agent_a,
        key="current_task"
    ) is None

    assert manager.get_working_memory(
        agent_id=agent_a,
        key="last_tool"
    ) is None

    assert manager.get_working_memory(
        agent_id=agent_b,
        key="current_task"
    ) == "Task B"


def test_search_returns_ranked_memories():
    manager = MemoryManager()

    agent_id = f"ranking-integration-agent-{uuid4()}"

    low_importance = manager.remember(
        agent_id=agent_id,
        content="Python is used for backend development.",
        memory_type=MemoryType.SEMANTIC,
        metadata={"importance_test": "low"},
    )

    high_importance = manager.remember(
        agent_id=agent_id,
        content="Python is used for backend development.",
        memory_type=MemoryType.SEMANTIC,
        metadata={"importance_test": "high"},
    )

    low_importance.importance = 0.1
    high_importance.importance = 1.0

    manager.storage.save(low_importance)
    manager.storage.save(high_importance)

    results = manager.search(
        agent_id=agent_id,
        query="What programming language is used for backend development?",
        limit=2,
    )

    assert len(results) == 2
    assert results[0].id == high_importance.id



def test_update_keeps_search_consistent():
    manager = MemoryManager()

    agent_id = f"manager-update-agent-{uuid4()}"

    memory = manager.remember(
        agent_id=agent_id,
        content="The project uses Python.",
        memory_type=MemoryType.SEMANTIC,
    )

    manager.update(
        memory_id=memory.id,
        agent_id=agent_id,
        content="The project uses Rust.",
    )

    results = manager.search(
        agent_id=agent_id,
        query="Which programming language does the project use?",
        limit=5,
    )

    assert any(
        result.id == memory.id
        and result.content == "The project uses Rust."
        for result in results
    )


def test_forget_removes_memory_from_search():
    manager = MemoryManager()

    agent_id = f"manager-forget-agent-{uuid4()}"

    memory = manager.remember(
        agent_id=agent_id,
        content="The project uses PostgreSQL for persistent storage.",
        memory_type=MemoryType.SEMANTIC,
    )

    manager.forget(
        memory_id=memory.id,
        agent_id=agent_id,
    )

    results = manager.search(
        agent_id=agent_id,
        query="What database does the project use for persistent storage?",
        limit=5,
    )

    assert all(result.id != memory.id for result in results)
    assert manager.storage.get(memory.id) is None