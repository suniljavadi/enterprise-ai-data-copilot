import logging
import uuid

from sqlalchemy import text

from app.database.connection import get_session

logger = logging.getLogger(__name__)


def _safe_execute(sql: str, params: dict, fetch_scalar: bool = False) -> object | None:
    """Insert observability telemetry without ever breaking the main request path.

    If the ai.* tables are missing (not yet migrated), log a warning once and continue.
    Returns the scalar value (when fetch_scalar=True), True on success, or None on failure.
    """
    try:
        with get_session() as session:
            # SET NOCOUNT ON prevents pyodbc "function sequence error" when a statement
            # (e.g. INSERT ... OUTPUT) is combined with SQL Server row-count messages.
            session.execute(text("SET NOCOUNT ON"))
            result = session.execute(text(sql), params)
            value = result.scalar() if fetch_scalar else True
            session.commit()
            return value
    except Exception as exc:
        logger.warning("Observability write skipped (ai schema likely missing): %s", exc)
        return None


def record_query_history(
    user_question: str,
    generated_sql: str | None,
    model_name: str | None,
    prompt_version: str,
    status: str,
    error_message: str | None = None,
) -> tuple[str, int | None]:
    request_id = str(uuid.uuid4())
    query_id = _safe_execute(
        """
        INSERT INTO ai.AI_QueryHistory
            (RequestID, UserQuestion, GeneratedSQL, ModelName, PromptVersion, Status, ErrorMessage)
        OUTPUT INSERTED.QueryID
        VALUES (:request_id, :user_question, :generated_sql, :model_name, :prompt_version, :status, :error_message)
        """,
        {
            "request_id": request_id,
            "user_question": user_question,
            "generated_sql": generated_sql,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "status": status,
            "error_message": error_message,
        },
        fetch_scalar=True,
    )
    return request_id, query_id


def record_query_metrics(
    query_id: int | None,
    sql_generation_ms: float | None,
    validation_ms: float | None,
    database_execution_ms: float | None,
    total_latency_ms: float,
    rows_returned: int,
) -> None:
    if query_id is None:
        return
    _safe_execute(
        """
        INSERT INTO ai.AI_QueryExecutionMetrics
            (QueryID, SQLGenerationMs, ValidationMs, DatabaseExecutionMs, TotalLatencyMs, RowsReturned)
        VALUES (:query_id, :sql_generation_ms, :validation_ms, :database_execution_ms, :total_latency_ms, :rows_returned)
        """,
        {
            "query_id": query_id,
            "sql_generation_ms": sql_generation_ms,
            "validation_ms": validation_ms,
            "database_execution_ms": database_execution_ms,
            "total_latency_ms": total_latency_ms,
            "rows_returned": rows_returned,
        },
    )


def record_query_error(query_id: int | None, error_type: str, error_message: str) -> None:
    if query_id is None:
        return
    _safe_execute(
        """
        INSERT INTO ai.AI_QueryErrors (QueryID, ErrorType, ErrorMessage)
        VALUES (:query_id, :error_type, :error_message)
        """,
        {"query_id": query_id, "error_type": error_type, "error_message": error_message},
    )


def record_feedback(query_id: int, rating: int | None, is_correct: bool | None, comment: str | None) -> bool:
    result = _safe_execute(
        """
        INSERT INTO ai.AI_QueryFeedback (QueryID, Rating, IsCorrect, UserComment)
        VALUES (:query_id, :rating, :is_correct, :comment)
        """,
        {"query_id": query_id, "rating": rating, "is_correct": is_correct, "comment": comment},
    )
    return result is not None
