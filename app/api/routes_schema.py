from fastapi import APIRouter

from app.database.inspector import SchemaSnapshot, get_cached_schema

router = APIRouter()


@router.get("/schema", response_model=SchemaSnapshot)
def schema() -> SchemaSnapshot:
    return get_cached_schema()


@router.post("/schema/refresh", response_model=SchemaSnapshot)
def refresh_schema() -> SchemaSnapshot:
    return get_cached_schema(force_refresh=True)
