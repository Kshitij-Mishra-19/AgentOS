from backend.memory.redis_client import get_redis


def test_redis_connection():
    redis_client = get_redis()

    redis_client.set("aegis_test_key", "hello")

    value = redis_client.get("aegis_test_key")

    assert value == "hello"

    redis_client.delete("aegis_test_key")

from backend.memory.working_memory import WorkingMemory


def test_working_memory_set_get_delete():
    working_memory = WorkingMemory()

    agent_id = "working-memory-test-agent"
    key = "current_task"
    value = "Analyze authentication architecture"

    working_memory.set(
        agent_id=agent_id,
        key=key,
        value=value
    )

    result = working_memory.get(
        agent_id=agent_id,
        key=key
    )

    assert result == value

    working_memory.delete(
        agent_id=agent_id,
        key=key
    )

    result_after_delete = working_memory.get(
        agent_id=agent_id,
        key=key
    )

    assert result_after_delete is None


def test_working_memory_ttl():
    working_memory = WorkingMemory()

    agent_id = "ttl-test-agent"
    key = "temporary_state"
    value = "This should expire"

    working_memory.set(
        agent_id=agent_id,
        key=key,
        value=value,
        ttl=1
    )

    result = working_memory.get(
        agent_id=agent_id,
        key=key
    )

    assert result == value

    import time
    time.sleep(2)

    result_after_expiry = working_memory.get(
        agent_id=agent_id,
        key=key
    )

    assert result_after_expiry is None

def test_working_memory_agent_isolation():
    working_memory = WorkingMemory()

    agent_a = "working-agent-a"
    agent_b = "working-agent-b"

    working_memory.set(
        agent_id=agent_a,
        key="current_task",
        value="Agent A private task"
    )

    result = working_memory.get(
        agent_id=agent_b,
        key="current_task"
    )

    assert result is None


def test_working_memory_clear_agent():
    working_memory = WorkingMemory()

    agent_a = "clear-agent-a"
    agent_b = "clear-agent-b"

    working_memory.set(
        agent_id=agent_a,
        key="current_task",
        value="Task A"
    )

    working_memory.set(
        agent_id=agent_a,
        key="last_tool",
        value="Tool A"
    )

    working_memory.set(
        agent_id=agent_b,
        key="current_task",
        value="Task B"
    )

    working_memory.clear_agent(agent_a)

    assert working_memory.get(
        agent_id=agent_a,
        key="current_task"
    ) is None

    assert working_memory.get(
        agent_id=agent_a,
        key="last_tool"
    ) is None

    assert working_memory.get(
        agent_id=agent_b,
        key="current_task"
    ) == "Task B"