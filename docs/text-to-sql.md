# Text-to-SQL

## Pipeline

1. **Schema retrieval** (`app/text_to_sql/schema_retriever.py`) — deterministic keyword-overlap matching between the question's tokens and each table's schema/table/column names. Only the top `max_tables` (default 6) go into the LLM prompt, not the full 40-table schema.
2. **Generation** (`app/text_to_sql/generator.py`) — calls `LLMProvider.generate()` with the schema context and question embedded in a prompt (`app/llm/prompts.py`) that explicitly requires T-SQL dialect, read-only SELECT/WITH only, no invented tables/columns.
3. **Validation** (`app/text_to_sql/validator.py`) — parses the generated SQL with `sqlglot` (dialect `tsql`) into a real AST, not a regex. Rejects: non-SELECT root, multiple statements, comments, `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`CREATE`/`MERGE`/`GRANT`/generic `Command` (covers `EXEC`), access to `sys`/`information_schema`/`master`/`msdb`/`tempdb`, and dangerous function calls (`xp_cmdshell`, `openrowset`, `sp_executesql`, etc.).
4. **Execution** (`app/text_to_sql/executor.py`) — bounded by `MAX_RESULT_ROWS` (via `fetchmany`) and `SQL_QUERY_TIMEOUT` (applied at the pyodbc connection level, not just login).
5. **Observability** — every attempt (success, validation-rejected, execution-failed) is recorded in `ai.AI_QueryHistory`/`ai.AI_QueryExecutionMetrics`/`ai.AI_QueryErrors` with per-stage latency.

## Mock LLM provider

By default (`LLM_API_KEY` unset), `app/llm/providers/mock.py` provides deterministic SQL for ~20 known business question patterns (revenue, top customers/products, monthly trends, returns, employee targets, inventory reorder/value, campaigns, late shipments, customers with no orders, ranking with `RANK() OVER`, running totals, revenue share percentage, cohort analysis, and `HAVING`-based filters). This makes the entire pipeline runnable and testable offline, with zero API cost, while still exercising every real layer (schema retrieval, validation, real SQL Server execution).

Out-of-scope questions raise `QuestionNotUnderstoodError` (HTTP 400) rather than hallucinating SQL.

## Swapping in a real LLM

Set `LLM_API_KEY` (and optionally `LLM_BASE_URL`/`LLM_MODEL`) in `.env`. `app/llm/factory.py` automatically switches to `OpenAICompatibleProvider`, which works with OpenAI, Azure OpenAI, or any OpenAI-compatible endpoint (vLLM, Ollama) without any application code changes — only the provider adapter differs.

## Known limitation

The schema retriever matches question tokens (expanded with a business-term synonym map, e.g. "revenue" → `totalamount`, "region" → `shippingstate`) against literal column names. Synonyms not yet in the map can still cause under-selection of tables, though the mock provider still generates correct SQL independently (it doesn't depend on the retrieved schema context). A real LLM would use the retrieved schema context more robustly; semantic (embedding-based) retrieval is a documented future improvement that would remove the need to maintain a synonym map by hand.
