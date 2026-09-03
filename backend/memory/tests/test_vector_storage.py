from backend.memory.vector_storage import VectorStorage

def test_vector_storage_creation():

  storage = VectorStorage(path="data/test_chroma")

  assert storage.client is not None

  assert storage.collection is not None



def test_vector_storage_add_and_search():

  storage = VectorStorage(path="data/test_chroma")

  memory_id = "test-memory-1"

  embedding = [1.0, 0.0, 0.0]

  metadata = {

  "agent_id": "agent-1",

  "memory_type": "semantic"

  }

  storage.add(

  memory_id=memory_id,

  embedding=embedding,

  metadata=metadata

  )

  results = storage.search(

  embedding=[1.0, 0.0, 0.0],

  limit=1

  )

  assert results["ids"][0][0] == memory_id