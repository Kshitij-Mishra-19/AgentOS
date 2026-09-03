from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _model = None

    def __init__(self):
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer(
                "all-MiniLM-L6-v2"
            )

    def embed(self, text: str) -> list[float]:
        vector = EmbeddingService._model.encode(text)
        return vector.tolist()