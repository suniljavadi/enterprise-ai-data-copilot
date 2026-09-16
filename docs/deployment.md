# Deployment

## Local development

```powershell
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
streamlit run frontend/streamlit_app.py
```

## Docker

```powershell
docker build -t enterprise-ai-data-copilot .
docker run -p 8000:8000 --env-file .env -e SQL_SERVER=host.docker.internal --add-host=host.docker.internal:host-gateway enterprise-ai-data-copilot
```

Verified: image builds on `python:3.11-slim-bookworm`, installs Microsoft ODBC Driver 17 via the modern GPG-keyring method (not the deprecated `apt-key`), runs as non-root `appuser`, and reports `healthy` via `HEALTHCHECK` hitting `/health`.

`docker-compose.yml` runs both the API and Streamlit UI, with the UI pointed at the API service by name (`http://api:8000`).

### Windows Authentication and containers

Windows Authentication (SSPI) only works when the app process runs on Windows with domain access. A Linux container **cannot** use `SQL_TRUSTED_CONNECTION=true`. Containerized/cloud deployments must set `SQL_TRUSTED_CONNECTION=false` and provide `SQL_USERNAME`/`SQL_PASSWORD` for a SQL Server Authentication login scoped to `SalesAI_DB`.

## CI/CD

`.github/workflows/ci.yml`: install deps → lint (compile check) → unit tests → Docker build. Integration, API, and evaluation tests are **not** run in hosted CI because they require a live SQL Server connection the runner doesn't have.

### Adding a database-backed CI job

To run the full suite (including evaluation) in CI, add a `services:` block running `mcr.microsoft.com/mssql/server`, then a setup step that runs the base schema script + `SalesAI_DB_V2_Enterprise_Extension.sql` before `pytest`. This wasn't wired up here because the base schema creation script lives outside this repository — document this dependency clearly if adopting this project as a template elsewhere.

## Cloud deployment (architecture-level, not implemented)

The app has no cloud-provider-specific code. Deployment target only changes:
- **Azure**: App Service or Container Apps for the API/UI; Azure SQL Database in place of a self-hosted SQL Server; Azure OpenAI as the `LLM_BASE_URL`.
- **Kubernetes**: the existing Dockerfile becomes a Deployment; `/health` and `/health/database` back liveness/readiness probes; `SQL_QUERY_TIMEOUT`/`MAX_RESULT_ROWS` become ConfigMap values; secrets (SQL credentials, LLM API key) go in a Secret, never baked into the image.
- **AMD Developer Cloud / local inference**: see the LLM provider abstraction (`app/llm/provider.py`) — a vLLM or Ollama server exposed via an OpenAI-compatible API needs only `LLM_BASE_URL` changed, no application code changes, since `OpenAICompatibleProvider` already targets any OpenAI-compatible endpoint.

## Scaling considerations

- FastAPI is stateless per request except for the module-level schema cache (TTL-based) and the in-memory FAISS index — both would need to move to shared storage (e.g. Redis for cache, a persisted FAISS index file or a managed vector DB) behind multiple replicas.
- SQL Server connection pooling (`pool_size=5, max_overflow=5`) should be tuned per replica count to avoid exceeding the database's max connections.
- Schema cache TTL (`SCHEMA_CACHE_TTL_SECONDS`) trades staleness for reduced metadata query load; increase it in low-change environments.
