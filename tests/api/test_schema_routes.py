from fastapi.testclient import TestClient

from app.database.inspector import clear_schema_cache
from app.main import app

client = TestClient(app)


def setup_function():
    clear_schema_cache()


def test_get_schema_returns_business_tables():
    response = client.get("/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["table_count"] > 0
    schema_names = {t["schema_name"] for t in body["tables"]}
    assert "sales" in schema_names
    assert "catalog" in schema_names


def test_schema_refresh_forces_new_discovery():
    first = client.get("/schema").json()
    refreshed = client.post("/schema/refresh").json()
    assert refreshed["discovered_at"] >= first["discovered_at"]
    assert refreshed["table_count"] == first["table_count"]
