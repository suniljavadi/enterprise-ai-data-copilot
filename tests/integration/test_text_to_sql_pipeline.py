from app.core.exceptions import QuestionNotUnderstoodError
from app.text_to_sql.pipeline import run_text_to_sql


def test_top_customers_by_revenue_returns_real_rows():
    result = run_text_to_sql("Who are the top customers by revenue?")
    assert result.sql.lower().startswith("select")
    assert result.row_count > 0
    assert "Revenue" in result.columns
    assert result.rows[0]["Revenue"] is not None


def test_total_revenue_returns_single_numeric_row():
    result = run_text_to_sql("What is the total revenue?")
    assert result.row_count == 1
    assert result.rows[0]["Revenue"] is not None
    assert float(result.rows[0]["Revenue"]) > 0


def test_ambiguous_question_raises_question_not_understood():
    try:
        run_text_to_sql("What is the weather today?")
    except QuestionNotUnderstoodError as exc:
        assert "ambiguous" in exc.detail
    else:
        raise AssertionError("Expected ambiguous question to raise QuestionNotUnderstoodError")
