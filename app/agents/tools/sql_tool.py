from pydantic import BaseModel

from app.text_to_sql.pipeline import run_text_to_sql


class SQLToolInput(BaseModel):
    question: str


def sql_tool(tool_input: SQLToolInput) -> dict:
    result = run_text_to_sql(tool_input.question)
    return {
        "tool": "sql_tool",
        "sql": result.sql,
        "tables_used": result.tables_used,
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
    }
