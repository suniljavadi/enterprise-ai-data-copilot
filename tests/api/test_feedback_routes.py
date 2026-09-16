from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_feedback_round_trip_after_query():
    query_response = client.post("/sql/query", json={"question": "What is the total revenue?"})
    query_id = query_response.json()["query_id"]
    assert query_id is not None

    feedback_response = client.post(
        "/feedback", json={"query_id": query_id, "rating": 5, "is_correct": True, "comment": "Correct answer"}
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json() == {"status": "recorded", "query_id": query_id}


def test_feedback_rejects_out_of_range_rating():
    response = client.post("/feedback", json={"query_id": 1, "rating": 9})
    assert response.status_code == 422
