from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
            f"mssql+pyodbc://{self.sql_username}:{self.sql_password}@{self.sql_server}/{self.sql_database}"
            f"?driver={driver}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
