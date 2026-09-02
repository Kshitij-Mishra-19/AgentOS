class RetrievalRanker:

    SEMANTIC_WEIGHT = 0.70
    IMPORTANCE_WEIGHT = 0.20
    CONFIDENCE_WEIGHT = 0.10

    @classmethod
    def score(
        cls,
        semantic_similarity: float,
        importance: float,
        confidence: float
    ) -> float:
        return (
            cls.SEMANTIC_WEIGHT * semantic_similarity
            + cls.IMPORTANCE_WEIGHT * importance
            + cls.CONFIDENCE_WEIGHT * confidence
        )