from backend.memory.embeddings import EmbeddingService
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