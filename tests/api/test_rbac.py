from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ADMIN = {"X-API-Key": "dev-admin-key"}
ANALYST = {"X-API-Key": "dev-analyst-key"}
VIEWER = {"X-API-Key": "dev-viewer-key"}


def test_health_is_public_no_api_key_required():
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_route_without_api_key_is_401():
    response = client.get("/schema")
    assert response.status_code == 401


def test_protected_route_with_invalid_api_key_is_401():
    response = client.get("/schema", headers={"X-API-Key": "not-a-real-key"})
    assert response.status_code == 401


def test_viewer_cannot_view_raw_schema():
    response = client.get("/schema", headers=VIEWER)
    assert response.status_code == 403


def test_viewer_cannot_refresh_schema():
    response = client.post("/schema/refresh", headers=VIEWER)
    assert response.status_code == 403


def test_analyst_cannot_refresh_schema():
    response = client.post("/schema/refresh", headers=ANALYST)
    assert response.status_code == 403


def test_admin_can_refresh_schema():
    response = client.post("/schema/refresh", headers=ADMIN)
    assert response.status_code == 200


def test_analyst_can_view_schema():
    response = client.get("/schema", headers=ANALYST)
    assert response.status_code == 200


def test_viewer_cannot_generate_raw_sql():
    response = client.post("/sql/generate", json={"question": "What is the total revenue?"}, headers=VIEWER)
    assert response.status_code == 403


def test_viewer_cannot_execute_raw_sql():
    response = client.post("/sql/execute", json={"sql": "SELECT 1"}, headers=VIEWER)
    assert response.status_code == 403


def test_viewer_can_run_curated_sql_query():
    response = client.post("/sql/query", json={"question": "What is the total revenue?"}, headers=VIEWER)
    assert response.status_code == 200


def test_analyst_can_generate_and_execute_raw_sql():
    generate_response = client.post(
        "/sql/generate", json={"question": "What is the total revenue?"}, headers=ANALYST
    )
    assert generate_response.status_code == 200
    execute_response = client.post("/sql/execute", json={"sql": "SELECT 1 AS one"}, headers=ANALYST)
    assert execute_response.status_code == 200


def test_viewer_cannot_ingest_documents():
    response = client.post("/rag/ingest", headers=VIEWER)
    assert response.status_code == 403


def test_analyst_cannot_ingest_documents():
    response = client.post("/rag/ingest", headers=ANALYST)
    assert response.status_code == 403


def test_admin_can_ingest_documents():
    response = client.post("/rag/ingest", headers=ADMIN)
    assert response.status_code == 200


def test_viewer_can_query_rag():
    response = client.post("/rag/query", json={"question": "What is the refund policy?"}, headers=VIEWER)
    assert response.status_code == 200


def test_viewer_can_query_agent():
    response = client.post("/agent/query", json={"question": "What is the total revenue?"}, headers=VIEWER)
    assert response.status_code == 200


def test_viewer_can_submit_feedback():
    query_response = client.post(
        "/sql/query", json={"question": "What is the total revenue?"}, headers=VIEWER
    )
    query_id = query_response.json()["query_id"]
    response = client.post("/feedback", json={"query_id": query_id, "rating": 5}, headers=VIEWER)
    assert response.status_code == 200


def test_health_database_requires_analyst_or_admin_not_viewer():
    admin_response = client.get("/health/database", headers=ADMIN)
    assert admin_response.status_code == 200
    viewer_response = client.get("/health/database", headers=VIEWER)
    assert viewer_response.status_code == 403
