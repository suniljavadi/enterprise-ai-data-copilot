from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.headers.update({"X-API-Key": "dev-admin-key"})


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "enterprise-ai-data-copilot"}


def test_health_database_returns_ok_when_reachable():
    response = client.get("/health/database")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "SalesAI_DB"
