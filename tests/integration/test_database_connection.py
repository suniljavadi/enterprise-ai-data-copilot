from sqlalchemy import text

from app.database.connection import get_engine, get_session


def test_can_execute_simple_query_against_sql_server():
    with get_engine().connect() as connection:
        result = connection.execute(text("SELECT 1 AS value"))
        assert result.scalar() == 1


def test_can_query_seeded_schema_tables():
    with get_session() as session:
        row = session.execute(
            text(
                "SELECT COUNT(*) FROM sys.tables t "
                "JOIN sys.schemas s ON s.schema_id = t.schema_id "
                "WHERE s.name = 'sales'"
            )
        ).scalar()
        assert row is not None and row > 0
