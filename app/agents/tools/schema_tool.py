from pydantic import BaseModel

from app.database.inspector import get_cached_schema


class SchemaToolInput(BaseModel):
    pass


def schema_tool(tool_input: SchemaToolInput | None = None) -> dict:
    snapshot = get_cached_schema()
    return {
        "tool": "schema_tool",
        "schema_count": snapshot.schema_count,
        "table_count": snapshot.table_count,
        "tables": [f"{t.schema_name}.{t.table_name}" for t in snapshot.tables],
    }
