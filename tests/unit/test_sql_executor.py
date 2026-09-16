from contextlib import contextmanager

import pytest

from app.core.exceptions import DatabaseUnavailableError
from app.text_to_sql import executor


class FakeResult:
    def keys(self):
        return ["Revenue"]

    def fetchmany(self, _max_rows):
        return [(100,)]

    def close(self):
        pass


class FakeSession:
    def execute(self, _statement):
        return FakeResult()


def test_retries_azure_sql_resume_error(monkeypatch):
    attempts = 0
    delays = []

    @contextmanager
    def fake_session():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Azure SQL Database is unavailable: 40613")
        yield FakeSession()

    monkeypatch.setattr(executor, "get_session", fake_session)
    monkeypatch.setattr(executor.time, "sleep", delays.append)

    result = executor.execute_readonly_sql("SELECT 100 AS Revenue")

    assert attempts == 2
    assert delays == [10]
    assert result.rows == [{"Revenue": 100}]


def test_does_not_retry_other_database_errors(monkeypatch):
    @contextmanager
    def failing_session():
        raise RuntimeError("SQL login failed")
        yield

    monkeypatch.setattr(executor, "get_session", failing_session)
    monkeypatch.setattr(executor.time, "sleep", lambda _delay: pytest.fail("unexpected retry"))

    with pytest.raises(DatabaseUnavailableError):
        executor.execute_readonly_sql("SELECT 1")