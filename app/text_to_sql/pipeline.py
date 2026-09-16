import time

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import AppError, QuestionNotUnderstoodError, SQLValidationError
from app.observability.telemetry import record_query_error, record_query_history, record_query_metrics
from app.text_to_sql.executor import execute_readonly_sql
from app.text_to_sql.generator import generate_sql
from app.text_to_sql.validator import validate_sql


class QueryResult(BaseModel):
    request_id: str
    query_id: int | None
    question: str
    sql: str
    tables_used: list[str]
    explanation: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    execution_time_ms: float


def run_text_to_sql(question: str) -> QueryResult:
    started = time.perf_counter()

    generation_start = time.perf_counter()
    try:
        generation = generate_sql(question)
    except QuestionNotUnderstoodError as exc:
        request_id, query_id = record_query_history(question, None, get_settings().llm_model, "v1", "Rejected", str(exc.detail))
        record_query_error(query_id, "QUESTION_NOT_UNDERSTOOD", str(exc.detail))
        raise
    sql_generation_ms = round((time.perf_counter() - generation_start) * 1000, 2)

    validation_start = time.perf_counter()
    validation = validate_sql(generation.sql)
    validation_ms = round((time.perf_counter() - validation_start) * 1000, 2)

    if not validation.valid:
        error_message = "; ".join(validation.errors)
        request_id, query_id = record_query_history(
            question, generation.sql, get_settings().llm_model, "v1", "Rejected", error_message
        )
        record_query_error(query_id, "SQL_VALIDATION_ERROR", error_message)
        raise SQLValidationError(error_message)

    try:
        execution = execute_readonly_sql(validation.normalized_sql or generation.sql)
    except AppError as exc:
        request_id, query_id = record_query_history(
            question, generation.sql, get_settings().llm_model, "v1", "Failed", str(exc.detail)
        )
        record_query_error(query_id, "SQL_EXECUTION_ERROR", str(exc.detail))
        raise

    total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
    request_id, query_id = record_query_history(question, generation.sql, get_settings().llm_model, "v1", "Success")
    record_query_metrics(query_id, sql_generation_ms, validation_ms, execution.execution_time_ms, total_latency_ms, execution.row_count)

    return QueryResult(
        request_id=request_id,
        query_id=query_id,
        question=generation.question,
        sql=validation.normalized_sql or generation.sql,
        tables_used=generation.tables_used,
        explanation=generation.explanation,
        columns=execution.columns,
        rows=execution.rows,
        row_count=execution.row_count,
        execution_time_ms=execution.execution_time_ms,
    )

