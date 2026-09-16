import sqlglot
from sqlglot import exp
from pydantic import BaseModel

_DANGEROUS_FUNCTIONS = {
    "xp_cmdshell",
    "openrowset",
    "opendatasource",
    "sp_executesql",
    "exec",
    "execute",
}

_BLOCKED_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Merge,
    exp.Grant,
    exp.Command,
)

_SYSTEM_SCHEMA_PREFIXES = ("sys", "information_schema", "master", "msdb", "tempdb")


class SQLValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    normalized_sql: str | None = None


def validate_sql(raw_sql: str) -> SQLValidationResult:
    errors: list[str] = []
    stripped = raw_sql.strip().rstrip(";")

    if not stripped:
        return SQLValidationResult(valid=False, errors=["Generated SQL is empty"])

    if "--" in stripped or "/*" in stripped:
        errors.append("SQL comments are not allowed")

    try:
        statements = sqlglot.parse(stripped, read="tsql")
    except Exception as exc:
        return SQLValidationResult(valid=False, errors=[f"SQL failed to parse: {exc}"])

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        errors.append("Only a single SQL statement is allowed")

    if statements:
        root = statements[0]
        if not isinstance(root, exp.Select):
            errors.append("Only read-only SELECT or WITH queries are allowed")

        if isinstance(root, _BLOCKED_EXPRESSION_TYPES):
            errors.append("Mutation and administrative SQL is not allowed")

        for node in root.walk():
            expression = node[0] if isinstance(node, tuple) else node
            if isinstance(expression, _BLOCKED_EXPRESSION_TYPES):
                errors.append("Mutation and administrative SQL is not allowed")
            if isinstance(expression, exp.Anonymous) and expression.name.lower() in _DANGEROUS_FUNCTIONS:
                errors.append(f"Use of '{expression.name}' is not allowed")
            if isinstance(expression, exp.Table):
                schema_name = (expression.db or "").lower()
                if schema_name in _SYSTEM_SCHEMA_PREFIXES:
                    errors.append(f"Access to system schema '{schema_name}' is not allowed")

    if errors:
        return SQLValidationResult(valid=False, errors=sorted(set(errors)))

    return SQLValidationResult(valid=True, errors=[], normalized_sql=statements[0].sql(dialect="tsql"))
