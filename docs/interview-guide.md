# Interview Guide

Answers grounded in what this codebase actually does, not generic talking points.

### Why this architecture?

Separation between generation (LLM, untrusted) and execution (deterministic validator, trusted) so the system's safety doesn't depend on the LLM behaving well. Each domain (text-to-sql, rag, agents) is independently testable through its `pipeline.py` entry point.

### Why FastAPI?

Async-native, Pydantic-typed request/response models give free request validation and auto-generated OpenAPI docs, and a centralized exception handler (`app/core/exceptions.py`) maps internal errors to safe client-facing messages without leaking stack traces.

### Why SQLAlchemy?

Database-agnostic connection pooling and, critically, `sqlalchemy.inspect()` for dynamic schema discovery (`app/database/inspector.py`) — the app never hardcodes the 40-table schema; it introspects it and caches the result with a TTL.

### Why schema retrieval before generation?

Sending the full schema to the LLM on every request is expensive and increases hallucination risk. `app/text_to_sql/schema_retriever.py` does deterministic keyword-overlap matching to select only relevant tables first — a known limitation (documented in `docs/text-to-sql.md`) is that this can miss tables when question wording doesn't match column names literally; semantic (embedding-based) retrieval is a documented future improvement.

### Why deterministic SQL validation over "trust the LLM's system prompt"?

Prompt instructions are not a security boundary — they can be bypassed by injection or model drift. `app/text_to_sql/validator.py` parses generated SQL into a real AST with `sqlglot` and enforces an allow-list (SELECT/WITH only, no system schemas, no dangerous functions) regardless of what the LLM was told to do. Verified against 13 real attack-pattern test cases (100% blocked).

### Why RAG?

Grounding answers in actual indexed documents with traceable citations, instead of letting the model answer from parametric memory (which can't be verified and drifts from actual company policy).

### Why agents?

Some questions need both structured data and unstructured document context (e.g. "why did revenue decrease *and* what is the refund policy?"). The planner (`app/agents/planner.py`) decides which tools apply per question rather than always calling everything — cheaper and reduces irrelevant tool noise.

### How is prompt injection handled?

Treated as untrusted input at every layer. RAG citations come from retrieval metadata, never parsed from generated text (a malicious document can't fabricate a citation). SQL from any source — direct question or agent-triggered — passes through the same validator; there's no privileged code path.

### How is hallucination reduced?

Text-to-SQL: schema retrieval narrows context, and the prompt explicitly forbids invented tables/columns; more importantly, hallucinated table/column names simply fail at SQL parse/execution time, not silently. RAG: `NO_EVIDENCE` fallback when nothing clears the similarity threshold, and citations are structurally tied to real retrieved chunks.

### How is SQL correctness evaluated?

Semantically, not by exact string match — see `docs/evaluation.md`. Checks: expected tables/keywords present in generated SQL, minimum row counts, and correct rejection of out-of-scope questions. 30/30 currently passing against the real `SalesAI_DB`.

### How is latency measured?

Per-stage timing in `app/text_to_sql/pipeline.py` (`sql_generation_ms`, `validation_ms`, `database_execution_ms`, `total_latency_ms`), persisted to `ai.AI_QueryExecutionMetrics` for every request, success or failure.

### How would this scale?

Stateless FastAPI replicas behind a load balancer; the schema cache and FAISS index (currently in-process, module-level) would need to move to shared storage (Redis, a persisted index, or a managed vector DB) to work correctly across multiple replicas. SQL Server connection pool sizing needs to account for total replica count.

### How would this be deployed to Kubernetes?

The existing Dockerfile becomes a Deployment; `/health` and `/health/database` back liveness/readiness probes directly; secrets (SQL credentials, `LLM_API_KEY`) go into a Kubernetes Secret, never the image.

### How would this be deployed to Azure?

Azure Container Apps or App Service for API/UI, Azure SQL Database instead of self-hosted SQL Server, Azure OpenAI as `LLM_BASE_URL` — no application code changes required since the LLM provider is already abstracted behind `LLMProvider`.

### How would GPU inference be introduced?

`app/llm/provider.py`'s abstract interface means swapping in a vLLM or Ollama server exposed over an OpenAI-compatible API only requires changing `LLM_BASE_URL`. Model serving stays fully decoupled from business logic — see `docs/deployment.md`'s AMD GPU section.

### What happens if the LLM is unavailable?

`OpenAICompatibleProvider` catches provider exceptions and raises `LLMUnavailableError` (HTTP 502) — a clean, typed error, not a raw exception leaking implementation details. The mock provider (default, no API key) has no such dependency and can't go down.

### What happens if SQL Server is unavailable?

`app/database/connection.py::check_database_connection()` raises `DatabaseUnavailableError` (HTTP 503), and any query execution failure during a request is caught and recorded to `ai.AI_QueryErrors` (which itself degrades gracefully if the `ai.*` tables are also unreachable) rather than propagating a raw exception.
