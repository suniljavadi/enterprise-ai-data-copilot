from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_agent import router as agent_router
from app.api.routes_feedback import router as feedback_router
from app.api.routes_health import router as health_router
from app.api.routes_rag import router as rag_router
from app.api.routes_schema import router as schema_router
from app.api.routes_sql import router as sql_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging

configure_logging(get_settings().log_level)

app = FastAPI(title="Enterprise AI Data Copilot", version="0.1.0")
app.include_router(health_router)
app.include_router(schema_router)
app.include_router(sql_router)
app.include_router(feedback_router)
app.include_router(rag_router)
app.include_router(agent_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
