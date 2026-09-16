from sqlalchemy import text

from app.database.connection import get_session
from app.text_to_sql.pipeline import run_text_to_sql


def test_successful_query_is_recorded_in_ai_query_history():
    result = run_text_to_sql("What is the total revenue?")
    assert result.query_id is not None

    with get_session() as session:
        row = session.execute(
            text("SELECT Status, UserQuestion FROM ai.AI_QueryHistory WHERE QueryID = :id"),
            {"id": result.query_id},
        ).first()
    assert row is not None
    assert row.Status == "Success"
    assert row.UserQuestion == "What is the total revenue?"


def test_successful_query_records_execution_metrics():
    result = run_text_to_sql("What is the total revenue?")

    with get_session() as session:
        row = session.execute(
            text("SELECT TotalLatencyMs, RowsReturned FROM ai.AI_QueryExecutionMetrics WHERE QueryID = :id"),
            {"id": result.query_id},
        ).first()
    assert row is not None
    assert row.TotalLatencyMs is not None
    assert row.RowsReturned == result.row_count


def test_rejected_question_is_recorded_as_error():
    from app.core.exceptions import QuestionNotUnderstoodError

    try:
        run_text_to_sql("Tell me a joke")
    except QuestionNotUnderstoodError:
        pass

    with get_session() as session:
        row = session.execute(
            text(
                "SELECT TOP 1 h.Status, e.ErrorType FROM ai.AI_QueryHistory h "
                "JOIN ai.AI_QueryErrors e ON e.QueryID = h.QueryID "
                "WHERE h.UserQuestion = 'Tell me a joke' ORDER BY h.QueryID DESC"
            )
        ).first()
    assert row is not None
    assert row.Status == "Rejected"
    assert row.ErrorType == "QUESTION_NOT_UNDERSTOOD"
