import re

from app.database.inspector import SchemaSnapshot, TableMetadata, get_cached_schema

_WORD_PATTERN = re.compile(r"[a-z]+")

# Business vocabulary doesn't always match literal column names (e.g. "revenue" vs. the
# actual TotalAmount column). These synonyms expand the question's tokens with the schema
# tokens a business user actually means, without requiring semantic/embedding retrieval.
_SYNONYMS: dict[str, set[str]] = {
    "revenue": {"totalamount", "linetotal", "revenuegenerated"},
    "sales": {"totalamount", "orders"},
    "cost": {"unitcost"},
    "price": {"unitprice"},
    "profit": {"unitprice", "unitcost"},
    "region": {"shippingstate", "state"},
    "area": {"shippingstate", "state"},
    "stock": {"quantityonhand", "inventory"},
    "reorder": {"reorderlevel"},
    "target": {"targetamount", "achievedamount"},
    "performance": {"targetamount", "achievedamount"},
    "signup": {"signupdate"},
    "cohort": {"signupdate"},
    "late": {"expecteddate", "delivereddate"},
    "delay": {"expecteddate", "delivereddate"},
    "aov": {"totalamount"},
    "average": {"totalamount"},
}


def _tokenize(text: str) -> set[str]:
    return set(_WORD_PATTERN.findall(text.lower()))


def _expand_with_synonyms(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in tokens:
        expanded |= _SYNONYMS.get(token, set())
    return expanded


def _table_tokens(table: TableMetadata) -> set[str]:
    tokens = _tokenize(table.table_name) | _tokenize(table.schema_name)
    for column in table.columns:
        tokens |= _tokenize(column.name)
    return tokens


def select_relevant_tables(question: str, snapshot: SchemaSnapshot | None = None, max_tables: int = 6) -> list[TableMetadata]:
    """Deterministic keyword-overlap relevance matching between the question and schema metadata.

    Scores each table by how many question tokens (expanded with business-term synonyms)
    appear in its schema/table/column names, so only a relevant subset of the database is
    sent to the LLM instead of the full schema.
    """
    snapshot = snapshot or get_cached_schema()
    question_tokens = _expand_with_synonyms(_tokenize(question))
    if not question_tokens:
        return []

    scored: list[tuple[int, TableMetadata]] = []
    for table in snapshot.tables:
        overlap = len(question_tokens & _table_tokens(table))
        if overlap > 0:
            scored.append((overlap, table))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [table for _, table in scored[:max_tables]]


def format_schema_context(tables: list[TableMetadata]) -> str:
    lines = []
    for table in tables:
        columns = ", ".join(c.name for c in table.columns)
        lines.append(f"{table.schema_name}.{table.table_name}({columns})")
        for fk in table.foreign_keys:
            lines.append(
                f"  FK: {table.schema_name}.{table.table_name}.{fk.columns} -> "
                f"{fk.referred_schema}.{fk.referred_table}.{fk.referred_columns}"
            )
    return "\n".join(lines)
