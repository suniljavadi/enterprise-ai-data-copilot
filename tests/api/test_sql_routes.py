from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.headers.update({"X-API-Key": "dev-admin-key"})


def test_generate_returns_sql_for_known_question():
    response = client.post("/sql/generate", json={"question": "Who are the top customers by revenue?"})
    assert response.status_code == 200
    body = response.json()
    assert "select" in body["sql"].lower()
    assert body["tables_used"]


def test_execute_runs_valid_select():
    response = client.post("/sql/execute", json={"sql": "SELECT TOP 5 * FROM sales.Orders"})
    assert response.status_code == 200
    body = response.json()
    assert body["validation"]["valid"] is True
    assert body["row_count"] == 5


def test_execute_blocks_mutation_sql():
    response = client.post("/sql/execute", json={"sql": "DELETE FROM sales.Orders"})
    assert response.status_code == 200
    body = response.json()
    assert body["validation"]["valid"] is False
    assert body["row_count"] == 0


def test_execute_blocks_multi_statement_injection():
    response = client.post(
        "/sql/execute", json={"sql": "SELECT * FROM sales.Orders; DROP TABLE sales.Orders"}
    )
    body = response.json()
    assert body["validation"]["valid"] is False
    assert any("single SQL statement" in e for e in body["validation"]["errors"])


def test_query_end_to_end_returns_grounded_result():
    response = client.post("/sql/query", json={"question": "What is the total revenue?"})
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 1
    assert body["rows"][0]["Revenue"] is not None


def test_query_rejects_out_of_scope_question_with_400():
    response = client.post("/sql/query", json={"question": "Tell me a joke"})
    assert response.status_code == 400
