from fastapi import APIRouter, Depends

from app.core.security import Role, require_role
from app.database.connection import check_database_connection

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "enterprise-ai-data-copilot"}


@router.get("/health/database", dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST))])
def health_database() -> dict:
    return check_database_connection()
