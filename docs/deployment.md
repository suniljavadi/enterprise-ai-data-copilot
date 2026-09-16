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

## Cloud deployment (Azure — actually deployed, not hypothetical)

**Live**: https://enterprise-ai-copilot-api.orangesky-0c279ec4.centralindia.azurecontainerapps.io

What's actually running:
- **Azure SQL Database**: `SalesAI_DB` on a free-tier serverless database (`GP_S_Gen5_2`, `useFreeLimit: true`, `AutoPause` behavior — genuinely $0 within the monthly free limit), region Central India. Full schema + data replicated from local via the same two SQL scripts used for local setup.
- **Azure Container Apps**: Consumption plan (free monthly grant: 180,000 vCPU-seconds + 360,000 GiB-seconds), `min-replicas 0` (scales to zero when idle), pulling the image from **GitHub Container Registry** (`ghcr.io/suniljavadi/enterprise-ai-data-copilot-api`) rather than Azure Container Registry, to avoid ACR's ~$5/month Basic-tier cost.
- Authentication uses `SQL_TRUSTED_CONNECTION=false` with a dedicated `sqladmin` SQL login, since Linux containers can't use Windows Authentication (see below).
- Production API keys (`API_KEYS` env var) are distinct from the local dev keys in `.env.example` — never reuse `dev-*` keys outside local development.

### Deployment steps (repeatable)

```powershell
# 1. Resource group + free-tier SQL
az group create --name rg-enterprise-ai-copilot --location centralindia
az sql server create --name <unique-name> -g rg-enterprise-ai-copilot --admin-user sqladmin --admin-password <generated>
az sql db create -g rg-enterprise-ai-copilot -s <server> -n SalesAI_DB -e GeneralPurpose -f Gen5 -c 2 \
  --compute-model Serverless --use-free-limit --free-limit-exhaustion-behavior AutoPause
az sql server firewall-rule create -g rg-enterprise-ai-copilot -s <server> -n AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0

# 2. Push image to GHCR
gh auth refresh -h github.com -s write:packages,read:packages
gh auth token | docker login ghcr.io -u <github-username> --password-stdin
docker build -t ghcr.io/<user>/enterprise-ai-data-copilot-api:latest .
docker push ghcr.io/<user>/enterprise-ai-data-copilot-api:latest

# 3. Container Apps environment + app
az extension add --name containerapp --upgrade
az containerapp env create -g rg-enterprise-ai-copilot -n cae-enterprise-ai-copilot --location centralindia
az containerapp create -n enterprise-ai-copilot-api -g rg-enterprise-ai-copilot \
  --environment cae-enterprise-ai-copilot \
  --image ghcr.io/<user>/enterprise-ai-data-copilot-api:latest \
  --target-port 8000 --ingress external \
  --registry-server ghcr.io --registry-username <user> --registry-password <gh-token> \
  --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 1 \
  --env-vars SQL_SERVER=<fqdn> SQL_DATABASE=SalesAI_DB SQL_TRUSTED_CONNECTION=false \
             SQL_USERNAME=sqladmin SQL_PASSWORD=<pw> API_KEYS='<json>' APP_ENV=production
```

**Real issues hit and fixed during this deployment** (see `docs/troubleshooting.md` for full detail):
- The base setup script's `CREATE DATABASE`/`ALTER DATABASE ... SET SINGLE_USER` prologue isn't supported against an already-provisioned Azure SQL Database — stripped before running.
- A computed-column table (`inventory.PurchaseOrderItems`) failed to create via `sqlcmd` on Azure due to a `QUOTED_IDENTIFIER` session setting difference from SSMS — fixed with an explicit `SET QUOTED_IDENTIFIER ON` before that table's creation.
- Passing a JSON value through nested PowerShell → Azure CLI `--env-vars` shell quoting corrupted the JSON — fixed by patching the container app via a YAML manifest instead of CLI string arguments.
- A `Get-Content -Encoding utf8` roundtrip on Windows PowerShell added a BOM that broke `json.loads()` on the server — fixed by reading with `utf-8-sig`.
- First request after the serverless database auto-pauses returns SQL error 40613 ("database... is not currently available") for 30-60s while it resumes — this is expected free-tier behavior, not a bug.

### Windows Authentication and containers

Windows Authentication (SSPI) only works when the app process runs on Windows with domain access. A Linux container **cannot** use `SQL_TRUSTED_CONNECTION=true`. Containerized/cloud deployments must set `SQL_TRUSTED_CONNECTION=false` and provide `SQL_USERNAME`/`SQL_PASSWORD` for a SQL Server Authentication login scoped to `SalesAI_DB`.

## CI/CD

`.github/workflows/ci.yml`: install deps → lint (compile check) → unit tests → Docker build. Integration, API, and evaluation tests are **not** run in hosted CI because they require a live SQL Server connection the runner doesn't have.

### Adding a database-backed CI job

To run the full suite (including evaluation) in CI, add a `services:` block running `mcr.microsoft.com/mssql/server`, then a setup step that runs the base schema script + `SalesAI_DB_V2_Enterprise_Extension.sql` before `pytest`. This wasn't wired up here because the base schema creation script lives outside this repository — document this dependency clearly if adopting this project as a template elsewhere.

## Other cloud targets (architecture-level, not implemented)

The app has no cloud-provider-specific code beyond the Azure deployment above:
- **Kubernetes**: the existing Dockerfile becomes a Deployment; `/health` and `/health/database` back liveness/readiness probes; `SQL_QUERY_TIMEOUT`/`MAX_RESULT_ROWS` become ConfigMap values; secrets (SQL credentials, LLM API key) go in a Secret, never baked into the image.
- **AMD Developer Cloud / local inference**: see the LLM provider abstraction (`app/llm/provider.py`) — a vLLM or Ollama server exposed via an OpenAI-compatible API needs only `LLM_BASE_URL` changed, no application code changes, since `OpenAICompatibleProvider` already targets any OpenAI-compatible endpoint.

## Scaling considerations

- FastAPI is stateless per request except for the module-level schema cache (TTL-based) and the in-memory FAISS index — both would need to move to shared storage (e.g. Redis for cache, a persisted FAISS index file or a managed vector DB) behind multiple replicas.
- SQL Server connection pooling (`pool_size=5, max_overflow=5`) should be tuned per replica count to avoid exceeding the database's max connections.
- Schema cache TTL (`SCHEMA_CACHE_TTL_SECONDS`) trades staleness for reduced metadata query load; increase it in low-change environments.
- Container Apps `min-replicas 0` means the first request after scale-to-zero has a cold-start delay; combined with the database's own auto-pause, the very first request after a long idle period can take longer than subsequent ones.

