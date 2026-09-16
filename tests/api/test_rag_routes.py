from fastapi.testclient import TestClient

from app.main import app
from app.rag.retriever import reset_index

client = TestClient(app)


def setup_function():
    reset_index()


def test_ingest_indexes_sample_documents():
    response = client.post("/rag/ingest")
    assert response.status_code == 200
    body = response.json()
    assert body["total_chunks"] > 0
    names = {d["document_name"] for d in body["documents_indexed"]}
    assert "refund_policy.md" in names


def test_query_after_ingest_returns_grounded_answer_with_citation():
    client.post("/rag/ingest")
    response = client.post("/rag/query", json={"question": "What is the refund policy for damaged products?"})
    assert response.status_code == 200
    body = response.json()
    assert body["citations"]
    assert body["citations"][0]["document_name"] == "refund_policy.md"


def test_query_before_ingest_returns_no_evidence():
    response = client.post("/rag/query", json={"question": "What is the refund policy?"})
    assert response.status_code == 200
    assert response.json()["citations"] == []
