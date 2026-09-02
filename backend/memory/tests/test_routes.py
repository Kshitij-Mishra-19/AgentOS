from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_memory_health():
    response = client.get("/memory/health")

    assert response.status_code == 200
    assert response.json() == {
        "module": "memory",
        "status": "healthy"
    }


def test_create_memory():
    response = client.post(
        "/memory",
        json={
            "agent_id": "api-test-agent",
            "content": "Aegis uses memory to retain useful information.",
            "memory_type": "semantic",
            "importance": 0.8,
            "confidence": 0.9,
            "metadata": {
                "source": "api-test"
            }
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["agent_id"] == "api-test-agent"
    assert data["content"] == "Aegis uses memory to retain useful information."
    assert data["memory_type"] == "semantic"
    assert data["importance"] == 0.8
    assert data["confidence"] == 0.9
    assert data["metadata"]["source"] == "api-test"
    assert "id" in data



def test_recall_memory():
    agent_id = "api-recall-test-agent"

    create_response = client.post(
        "/memory",
        json={
            "agent_id": agent_id,
            "content": "This memory should be retrievable.",
            "memory_type": "episodic",
        }
    )

    assert create_response.status_code == 200

    response = client.get(f"/memory/{agent_id}")

    assert response.status_code == 200

    memories = response.json()

    assert any(
        memory["content"] == "This memory should be retrievable."
        for memory in memories
    )


def test_search_memory():
    agent_id = "api-search-test-agent"

    create_response = client.post(
        "/memory",
        json={
            "agent_id": agent_id,
            "content": "Python is used for backend development.",
            "memory_type": "semantic",
        }
    )

    assert create_response.status_code == 200

    response = client.post(
        "/memory/search",
        json={
            "agent_id": agent_id,
            "query": "What programming language is used for backend development?",
            "limit": 5,
        }
    )

    assert response.status_code == 200

    memories = response.json()

    assert len(memories) > 0
    assert any(
        memory["content"] == "Python is used for backend development."
        for memory in memories
    )



def test_update_memory():
    agent_id = "api-update-test-agent"

    create_response = client.post(
        "/memory",
        json={
            "agent_id": agent_id,
            "content": "The project uses Python.",
            "memory_type": "semantic",
        }
    )

    assert create_response.status_code == 200

    memory_id = create_response.json()["id"]

    response = client.put(
        f"/memory/{memory_id}",
        json={
            "agent_id": agent_id,
            "content": "The project uses Rust.",
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == memory_id
    assert data["agent_id"] == agent_id
    assert data["content"] == "The project uses Rust."


def test_delete_memory():
    agent_id = "api-delete-test-agent"

    create_response = client.post(
        "/memory",
        json={
            "agent_id": agent_id,
            "content": "This memory will be deleted.",
            "memory_type": "episodic",
        }
    )

    assert create_response.status_code == 200

    memory_id = create_response.json()["id"]

    response = client.delete(
        f"/memory/{memory_id}",
        params={
            "agent_id": agent_id
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == memory_id
    assert data["status"] == "deleted"

    # Verify it is actually gone
    get_response = client.get(f"/memory/{agent_id}")

    assert get_response.status_code == 200

    memories = get_response.json()

    assert all(
        memory["id"] != memory_id
        for memory in memories
    )



def test_set_working_memory():
    response = client.put(
        "/memory/working",
        json={
            "agent_id": "api-working-test-agent",
            "key": "current_task",
            "value": "Testing Aegis memory",
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["agent_id"] == "api-working-test-agent"
    assert data["key"] == "current_task"
    assert data["status"] == "stored"


def test_get_working_memory():
    agent_id = "api-working-get-agent"
    key = "status"

    set_response = client.put(
        "/memory/working",
        json={
            "agent_id": agent_id,
            "key": key,
            "value": "running",
        }
    )

    assert set_response.status_code == 200

    response = client.get(
        f"/memory/working/{agent_id}/{key}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["agent_id"] == agent_id
    assert data["key"] == key
    assert data["value"] == "running"


def test_delete_working_memory():
    agent_id = "api-working-delete-agent"
    key = "temporary"

    client.put(
        "/memory/working",
        json={
            "agent_id": agent_id,
            "key": key,
            "value": "delete me",
        }
    )

    response = client.delete(
        f"/memory/working/{agent_id}/{key}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["agent_id"] == agent_id
    assert data["key"] == key
    assert data["status"] == "deleted"

    get_response = client.get(
        f"/memory/working/{agent_id}/{key}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["value"] is None


def test_clear_working_memory():
    agent_id = "api-working-clear-agent"

    client.put(
        "/memory/working",
        json={
            "agent_id": agent_id,
            "key": "task",
            "value": "research",
        }
    )

    client.put(
        "/memory/working",
        json={
            "agent_id": agent_id,
            "key": "status",
            "value": "running",
        }
    )

    response = client.delete(
        f"/memory/working/{agent_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["agent_id"] == agent_id
    assert data["status"] == "cleared"

    task_response = client.get(
        f"/memory/working/{agent_id}/task"
    )

    status_response = client.get(
        f"/memory/working/{agent_id}/status"
    )

    assert task_response.json()["value"] is None
    assert status_response.json()["value"] is None


def test_create_memory_rejects_invalid_importance():
    response = client.post(
        "/memory",
        json={
            "agent_id": "validation-agent",
            "content": "Invalid importance test",
            "memory_type": "semantic",
            "importance": 2.0,
        }
    )

    assert response.status_code == 422



def test_create_memory_rejects_invalid_confidence():
    response = client.post(
        "/memory",
        json={
            "agent_id": "validation-agent",
            "content": "Invalid confidence test",
            "memory_type": "semantic",
            "confidence": -0.5,
        }
    )

    assert response.status_code == 422



def test_search_rejects_invalid_limit():
    response = client.post(
        "/memory/search",
        json={
            "agent_id": "validation-agent",
            "query": "test",
            "limit": 0,
        }
    )

    assert response.status_code == 422



def test_update_rejects_wrong_agent():
    create_response = client.post(
        "/memory",
        json={
            "agent_id": "real-owner",
            "content": "Protected memory",
            "memory_type": "semantic",
        }
    )

    memory_id = create_response.json()["id"]

    response = client.put(
        f"/memory/{memory_id}",
        json={
            "agent_id": "wrong-agent",
            "content": "Unauthorized update",
        }
    )

    assert response.status_code == 403



def test_delete_rejects_wrong_agent():
    create_response = client.post(
        "/memory",
        json={
            "agent_id": "real-owner-delete",
            "content": "Protected delete memory",
            "memory_type": "semantic",
        }
    )

    memory_id = create_response.json()["id"]

    response = client.delete(
        f"/memory/{memory_id}",
        params={
            "agent_id": "wrong-agent"
        }
    )

    assert response.status_code == 403



def test_update_returns_404_for_missing_memory():
    response = client.put(
        "/memory/00000000-0000-0000-0000-000000000000",
        json={
            "agent_id": "missing-agent",
            "content": "This memory does not exist",
        }
    )

    assert response.status_code == 404


def test_delete_returns_404_for_missing_memory():
    response = client.delete(
        "/memory/00000000-0000-0000-0000-000000000000",
        params={
            "agent_id": "missing-agent"
        }
    )

    assert response.status_code == 404