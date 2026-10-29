import json
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_API_KEYS = frozenset({"dev-admin-key", "dev-analyst-key", "dev-viewer-key"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"

    embedding_model: str = "local"

    sql_server: str = "localhost"
    sql_database: str = "SalesAI_DB"
    sql_driver: str = "ODBC Driver 17 for SQL Server"
    sql_trusted_connection: bool = True
    sql_username: str | None = None
    sql_password: str | None = None

    sql_query_timeout: int = 30
    max_result_rows: int = 1000

    schema_cache_ttl_seconds: int = 300
    excluded_schemas: str = "dbo,sys,INFORMATION_SCHEMA,guest"

    # Role-based access control. JSON map of API key -> {"name": ..., "role": "admin"|"analyst"|"viewer"}.
    # The default below is for local development / tests only — override API_KEYS in production.
    api_keys: str = (
        '{"dev-admin-key": {"name": "dev-admin", "role": "admin"}, '
        '"dev-analyst-key": {"name": "dev-analyst", "role": "analyst"}, '
        '"dev-viewer-key": {"name": "dev-viewer", "role": "viewer"}}'
    )
    public_demo_key: str | None = None

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.casefold() != "production":
            return self

        try:
            configured_keys = json.loads(self.api_keys)
        except json.JSONDecodeError as exc:
            raise ValueError("API_KEYS must be valid JSON in production") from exc
        if not isinstance(configured_keys, dict) or not configured_keys:
            raise ValueError("API_KEYS must contain production credentials in production")
        allowed_roles = {"admin", "analyst", "viewer"}
        valid_entries = all(
            isinstance(api_key, str)
            and bool(api_key.strip())
            and isinstance(info, dict)
            and isinstance(info.get("name"), str)
            and bool(info["name"].strip())
            and info.get("role") in allowed_roles
            for api_key, info in configured_keys.items()
        )
        if not valid_entries:
            raise ValueError("API_KEYS entries must define a name and a supported role in production")
        if _DEVELOPMENT_API_KEYS.intersection(configured_keys) or self.public_demo_key in _DEVELOPMENT_API_KEYS:
            raise ValueError("Development API keys are not permitted in production")
        if any(len(api_key) < 32 for api_key in configured_keys):
            raise ValueError("Production API keys must be at least 32 characters long")
        if not self.llm_api_key or not self.llm_api_key.strip():
            raise ValueError("LLM_API_KEY is required in production; the mock provider is for development only")
        return self

    @property
    def excluded_schema_list(self) -> list[str]:
        return [item.strip() for item in self.excluded_schemas.split(",") if item.strip()]

    @property
    def sql_connection_string(self) -> str:
        driver = self.sql_driver.replace(" ", "+")
        if self.sql_trusted_connection:
            return (
                f"mssql+pyodbc://@{self.sql_server}/{self.sql_database}"
                f"?driver={driver}&trusted_connection=yes"
            )
        if not self.sql_username or not self.sql_password:
            raise ValueError("SQL_USERNAME and SQL_PASSWORD are required when SQL_TRUSTED_CONNECTION is false")
        return (
            f"mssql+pyodbc://{quote_plus(self.sql_username)}:{quote_plus(self.sql_password)}"
            f"@{self.sql_server}/{self.sql_database}"
            f"?driver={driver}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
