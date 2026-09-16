# Architecture

## Layered design

```
app/
├── api/            # Thin FastAPI routers — request/response models only, no business logic
├── core/           # Config, logging, centralized exceptions
├── database/        # Connection pooling, schema inspection + caching
├── llm/             # LLMProvider abstraction, mock + OpenAI-compatible adapters, prompts
├── text_to_sql/      # schema_retriever → generator → validator → executor → pipeline
├── rag/              # loader → chunker → embeddings → vector_store → retriever → pipeline
├── agents/            # state, planner, tools (each tool calls the same validated pipelines)
└── observability/      # telemetry writes to ai.* SQL Server tables
```

## Why this structure

Each domain (`text_to_sql`, `rag`, `agents`) is independently testable and has no import dependency on the others except through their public `pipeline.py` entry points. The agent's tools call the *exact same* `run_text_to_sql` / `answer_query` functions the direct API endpoints use — there is no separate, looser code path for agent-triggered execution.

## Request flow (Text-to-SQL)

```
Question → schema_retriever.select_relevant_tables()
         → llm.factory.get_llm_provider().generate(prompt)
         → text_to_sql.validator.validate_sql()  [sqlglot AST parse, allow-list]
         → text_to_sql.executor.execute_readonly_sql()  [row cap + timeout]
         → observability.telemetry.record_query_history/metrics/errors()
         → QueryResult (sql, rows, tables_used, explanation, request_id, query_id)
```

## Request flow (RAG)

```
Question → rag.retriever.search()  [hybrid: FAISS cosine + lexical overlap]
         → threshold filter (score >= 0.12)
         → citations built from retrieved chunk metadata (never LLM-invented)
         → optional LLM phrasing (falls back to deterministic concatenation)
         → RAGResult (answer, citations, evidence_count)
```

## Request flow (Agent)

```
Question → planner.select_tools()  [deterministic keyword-based intent classification]
         → for each tool: validated Pydantic input → tool function → AppError caught, never crashes
         → reasoning_summary + final_answer merged from tool_results
         → AgentState (full trace: tool_calls, tool_results, errors, execution_time_ms)
```

## Data flow guarantee

At every layer boundary where model output crosses into deterministic code, the model's output is treated as untrusted:

- Text-to-SQL: LLM's SQL string → `sqlglot` parse → allow-list check → only then executed
- RAG: LLM's phrased answer is optional cosmetic wrapping; citations always come from retrieval metadata, never from the LLM's text
- Agent: tool inputs are validated Pydantic models; a failing tool is caught and recorded as an error, never allowed to crash or bypass validation
