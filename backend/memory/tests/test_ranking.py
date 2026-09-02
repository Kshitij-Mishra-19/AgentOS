from backend.memory.ranking import RetrievalRanker


def test_retrieval_score():
    score = RetrievalRanker.score(
        semantic_similarity=0.90,
        importance=0.80,
        confidence=1.00
    )

    assert score == 0.89


def test_higher_importance_gets_higher_score():
    low_importance = RetrievalRanker.score(
        semantic_similarity=0.90,
        importance=0.20,
        confidence=1.00
    )

    high_importance = RetrievalRanker.score(
        semantic_similarity=0.90,
        importance=0.90,
        confidence=1.00
    )

    assert high_importance > low_importance


def test_higher_confidence_gets_higher_score():
    low_confidence = RetrievalRanker.score(
        semantic_similarity=0.90,
        importance=0.80,
        confidence=0.20
    )

    high_confidence = RetrievalRanker.score(
        semantic_similarity=0.90,
        importance=0.80,
        confidence=0.90
    )

    assert high_confidence > low_confidence

def test_ranking_changes_search_order():
    high_importance_score = RetrievalRanker.score(
        semantic_similarity=0.80,
        importance=1.0,
        confidence=1.0
    )

    low_importance_score = RetrievalRanker.score(
        semantic_similarity=0.80,
        importance=0.1,
        confidence=1.0
    )

    assert high_importance_score > low_importance_score