from app.core.config import Settings


def test_trusted_connection_string_uses_windows_auth():
    settings = Settings(sql_server="localhost", sql_database="SalesAI_DB", sql_trusted_connection=True)
    conn_str = settings.sql_connection_string
    assert "trusted_connection=yes" in conn_str
    assert "SalesAI_DB" in conn_str
    assert "localhost" in conn_str


def test_sql_auth_connection_string_requires_credentials():
    settings = Settings(sql_trusted_connection=False, sql_username=None, sql_password=None)
    try:
        settings.sql_connection_string
    except ValueError as exc:
        assert "SQL_USERNAME" in str(exc)
    else:
        raise AssertionError("Expected ValueError when SQL auth credentials are missing")


def test_sql_auth_connection_string_includes_credentials_when_provided():
    settings = Settings(sql_trusted_connection=False, sql_username="app_user", sql_password="secret")
    conn_str = settings.sql_connection_string
    assert "app_user:secret@" in conn_str
    assert "trusted_connection" not in conn_str
