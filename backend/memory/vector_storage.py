import chromadb
class VectorStorage:
  def __init__(self, path: str = "data/chroma"):
    self.client = chromadb.PersistentClient(path=path)
    self.collection = self.client.get_or_create_collection(name="memories")

  def add(self , memory_id:str , embedding : list[float] , metadata:dict)->None:
    self.collection.upsert(ids = [memory_id] , embeddings = [embedding] , metadatas = [metadata])

  def search(self , embedding: list[float] , limit:int=5 , agent_id: str | None = None):
    where = None
    if agent_id is not None:
      where = {"agent_id": agent_id}
    return self.collection.query(
      query_embeddings = [embedding],
      n_results = limit,
      where = where
    )

  def delete(self , memory_id:str)->None:
    self.collection.delete(ids = [memory_id])