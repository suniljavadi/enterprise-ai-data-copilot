from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import Role, require_role
from app.text_to_sql.executor import execute_readonly_sql
from app.text_to_sql.generator import SQLGenerationResult, generate_sql
from app.text_to_sql.pipeline import QueryResult, run_text_to_sql
from app.text_to_sql.validator import SQLValidationResult, validate_sql

router = APIRouter(prefix="/sql", tags=["text-to-sql"])


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class SQLRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=10000)


class ExecuteResponse(BaseModel):
    validation: SQLValidationResult
    columns: list[str] = []
    rows: list[dict] = []
    row_count: int = 0
    execution_time_ms: float | None = None


@router.post("/generate", response_model=SQLGenerationResult, dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST))])
def generate(request: QuestionRequest) -> SQLGenerationResult:
    return generate_sql(request.question)


@router.post("/execute", response_model=ExecuteResponse, dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST))])
def execute(request: SQLRequest) -> ExecuteResponse:
    validation = validate_sql(request.sql)
    if not validation.valid:
        return ExecuteResponse(validation=validation)
    result = execute_readonly_sql(validation.normalized_sql or request.sql)
    return ExecuteResponse(
        validation=validation,
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
    )


@router.post("/query", response_model=QueryResult, dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST, Role.VIEWER))])
def query(request: QuestionRequest) -> QueryResult:
    return run_text_to_sql(request.question)
