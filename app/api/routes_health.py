from fastapi import APIRouter

from app.database.connection import check_database_connection

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "enterprise-ai-data-copilot"}


@router.get("/health/database")
def health_database() -> dict:
    return check_database_connection()
