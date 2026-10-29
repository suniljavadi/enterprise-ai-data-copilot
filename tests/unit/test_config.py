import pytest
from sqlalchemy.engine import make_url

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


def test_sql_auth_connection_string_encodes_reserved_credential_characters():
    settings = Settings(
        sql_trusted_connection=False,
        sql_username="app@user",
        sql_password="s:e/c%ret",
    )

    url = make_url(settings.sql_connection_string)

    assert url.username == "app@user"
    assert url.password == "s:e/c%ret"


def test_production_settings_reject_development_api_keys():
    with pytest.raises(ValueError, match="Development API keys"):
        Settings(app_env="production", llm_api_key="test-llm-key")


def test_production_settings_require_api_keys():
    with pytest.raises(ValueError, match="API_KEYS must contain"):
        Settings(app_env="production", api_keys="{}", llm_api_key="test-llm-key")


def test_production_settings_require_a_real_llm_provider():
    with pytest.raises(ValueError, match="LLM_API_KEY is required"):
        Settings(
            app_env="production",
            api_keys='{"production-test-key-at-least-thirty-two-characters": {"name": "prod", "role": "admin"}}',
        )


def test_production_settings_accept_explicit_credentials():
    settings = Settings(
        app_env="production",
        api_keys='{"production-test-key-at-least-thirty-two-characters": {"name": "prod", "role": "admin"}}',
        llm_api_key="test-llm-key",
    )

    assert settings.app_env == "production"


def test_production_settings_reject_short_api_keys():
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            app_env="production",
            api_keys='{"short-key": {"name": "prod", "role": "admin"}}',
            llm_api_key="test-llm-key",
        )
