from pydantic import BaseModel

from app.core.exceptions import QuestionNotUnderstoodError
from app.llm.factory import get_llm_provider
from app.llm.prompts import build_sql_prompt
from app.text_to_sql.schema_retriever import format_schema_context, select_relevant_tables


class SQLGenerationResult(BaseModel):
    question: str
    sql: str
    tables_used: list[str]
    explanation: str


def generate_sql(question: str) -> SQLGenerationResult:
    tables = select_relevant_tables(question)
    schema_context = format_schema_context(tables)
    prompt = build_sql_prompt(question, schema_context)

    try:
        sql = get_llm_provider().generate(prompt)
    except ValueError as exc:
        raise QuestionNotUnderstoodError(str(exc)) from exc

    tables_used = [f"{t.schema_name}.{t.table_name}" for t in tables]
    explanation = (
        f"Generated using {len(tables_used)} relevant table(s): {', '.join(tables_used)}"
        if tables_used
        else "Generated without matching a specific table; review the SQL before executing."
    )
    return SQLGenerationResult(question=question, sql=sql, tables_used=tables_used, explanation=explanation)
