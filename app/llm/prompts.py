SQL_SYSTEM_INSTRUCTIONS = """You are a SQL Server expert generating READ-ONLY analytical queries.

Rules:
- Use only the tables and columns listed in the schema below. Never invent tables or columns.
- Use T-SQL (SQL Server) syntax, e.g. SELECT TOP N instead of LIMIT N.
- Only generate a single SELECT or WITH statement. No INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, or multiple statements.
- Use appropriate JOINs based on the foreign keys shown.
- Return only the SQL query, with no markdown formatting or explanation text.
"""


def build_sql_prompt(question: str, schema_context: str) -> str:
    return (
        f"{SQL_SYSTEM_INSTRUCTIONS}\n"
        f"Schema:\n{schema_context}\n\n"
        f"Question: {question}\n"
    )
