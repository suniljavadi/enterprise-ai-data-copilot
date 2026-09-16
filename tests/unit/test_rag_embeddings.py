from app.rag.embeddings import cosine, embed


def test_embedding_is_normalized():
    vector = embed("refund policy for damaged products")
    assert abs(cosine(vector, vector) - 1.0) < 1e-6


def test_similar_text_has_higher_similarity_than_unrelated_text():
    query = embed("refund policy")
    related = embed("refund policy for damaged products")
    unrelated = embed("quarterly financial forecast for aerospace manufacturing")
    assert cosine(query, related) > cosine(query, unrelated)
