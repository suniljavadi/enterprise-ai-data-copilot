import time

from pydantic import BaseModel
from sqlalchemy import inspect

from app.core.config import get_settings
from app.database.connection import get_engine


class ColumnMetadata(BaseModel):
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool


class ForeignKeyMetadata(BaseModel):
    columns: list[str]
    referred_schema: str | None
    referred_table: str
    referred_columns: list[str]


class TableMetadata(BaseModel):
    schema_name: str
    table_name: str
    columns: list[ColumnMetadata]
    primary_keys: list[str]
    foreign_keys: list[ForeignKeyMetadata]


class SchemaSnapshot(BaseModel):
    tables: list[TableMetadata]
    discovered_at: float
    schema_count: int
    table_count: int


def discover_schema() -> SchemaSnapshot:
    settings = get_settings()
    inspector = inspect(get_engine())
    excluded = set(settings.excluded_schema_list)

    schema_names = [name for name in inspector.get_schema_names() if name not in excluded]
    tables: list[TableMetadata] = []

    for schema_name in schema_names:
        for table_name in inspector.get_table_names(schema=schema_name):
            pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
            primary_keys = pk_constraint.get("constrained_columns") or []

            columns = [
                ColumnMetadata(
                    name=col["name"],
                    data_type=str(col["type"]),
                    nullable=col["nullable"],
                    is_primary_key=col["name"] in primary_keys,
                )
                for col in inspector.get_columns(table_name, schema=schema_name)
            ]

            foreign_keys = [
                ForeignKeyMetadata(
                    columns=fk["constrained_columns"],
                    referred_schema=fk.get("referred_schema"),
                    referred_table=fk["referred_table"],
                    referred_columns=fk["referred_columns"],
                )
                for fk in inspector.get_foreign_keys(table_name, schema=schema_name)
            ]

            tables.append(
                TableMetadata(
                    schema_name=schema_name,
                    table_name=table_name,
                    columns=columns,
                    primary_keys=primary_keys,
                    foreign_keys=foreign_keys,
                )
            )

    return SchemaSnapshot(
        tables=tables,
        discovered_at=time.time(),
        schema_count=len(schema_names),
        table_count=len(tables),
    )


_cache: SchemaSnapshot | None = None


def get_cached_schema(force_refresh: bool = False) -> SchemaSnapshot:
    global _cache
    settings = get_settings()
    is_stale = _cache is None or (time.time() - _cache.discovered_at) > settings.schema_cache_ttl_seconds
    if force_refresh or is_stale:
        _cache = discover_schema()
    return _cache


def clear_schema_cache() -> None:
    global _cache
    _cache = None
