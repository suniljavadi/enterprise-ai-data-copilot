import logging
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(
        settings.sql_connection_string,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"timeout": settings.sql_query_timeout},
    )

    @event.listens_for(engine, "connect")
    def _set_query_timeout(dbapi_connection, connection_record):
        # pyodbc's connect_args timeout only bounds login; this bounds query execution too.
        dbapi_connection.timeout = settings.sql_query_timeout

    return engine


@lru_cache
def get_session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


@contextmanager
def get_session():
    session: Session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> dict:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": get_settings().sql_database}
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        raise DatabaseUnavailableError(f"Cannot reach SQL Server: {exc.__class__.__name__}") from exc
