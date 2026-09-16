import time

from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.database.connection import get_session


class SQLExecutionResult:
    def __init__(self, columns: list[str], rows: list[dict], row_count: int, execution_time_ms: float):
        self.columns = columns
        self.rows = rows
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms


def execute_readonly_sql(sql: str) -> SQLExecutionResult:
    settings = get_settings()
    started = time.perf_counter()
    try:
        with get_session() as session:
            result = session.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchmany(settings.max_result_rows)]
            # Discard any unread rows so the pooled connection isn't left mid-cursor for the next checkout.
            result.close()
    except Exception as exc:
        raise DatabaseUnavailableError(f"Query execution failed: {exc.__class__.__name__}") from exc

    execution_time_ms = round((time.perf_counter() - started) * 1000, 2)
    return SQLExecutionResult(columns=columns, rows=rows, row_count=len(rows), execution_time_ms=execution_time_ms)
