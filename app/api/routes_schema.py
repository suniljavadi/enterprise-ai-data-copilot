from fastapi import APIRouter, Depends

from app.core.security import Role, require_role
from app.database.inspector import SchemaSnapshot, get_cached_schema

router = APIRouter()


@router.get("/schema", response_model=SchemaSnapshot, dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST))])
def schema() -> SchemaSnapshot:
    return get_cached_schema()


@router.post("/schema/refresh", response_model=SchemaSnapshot, dependencies=[Depends(require_role(Role.ADMIN))])
def refresh_schema() -> SchemaSnapshot:
    return get_cached_schema(force_refresh=True)
