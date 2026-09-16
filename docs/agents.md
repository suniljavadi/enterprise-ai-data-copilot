# Agents

## Design

`app/agents/state.py` defines `AgentState` (question, intent, selected_tools, tool_calls, tool_results, reasoning_summary, final_answer, errors, execution_time_ms) — the agent's entire trace is a typed, inspectable object, not a black box.

## Planner (`app/agents/planner.py`)

Deterministic keyword-based intent classification, not an LLM call:

| Signal | Result |
|---|---|
| Data keywords only (revenue, customer, order, ...) | `sql_tool` |
| Document keywords only (policy, refund, warranty, ...) | `rag_tool` |
| Both | both tools |
| Analysis keywords (why, decrease, trend, ...) + data | both tools |
| Neither | defaults to `sql_tool` |

`"product"`/`"products"` are treated as **weak** data signals — they appear in both analytical questions ("top products by revenue") and policy questions ("refund policy for damaged products"), so they only count as a data signal when no document keyword is present. This was a real bug found during testing (see `docs/troubleshooting.md`) where a policy question was misrouted to both tools.

## Tools (`app/agents/tools/`)

Each tool takes a validated Pydantic input and calls the **same pipeline function** the direct API endpoints use (`run_text_to_sql`, `answer_query`). There is no separate, less-validated execution path for agent-triggered SQL — a compromised or manipulated agent still cannot bypass the `sqlglot` validator.

## Iteration limits and failure recovery

`app/agents/agent.py` caps tool execution at `_MAX_ITERATIONS` (3) and wraps each tool call in try/except: an `AppError` or any other exception is recorded in `state.errors` and the agent continues with whatever tools did succeed, rather than crashing the whole request. A question with zero successful tools still returns a valid (if unhelpful) `final_answer`, never a 500 error.

## Example: mixed intent

`"Why did revenue decrease and what is the refund policy?"` → intent `analysis` → both `sql_tool` and `rag_tool` run → `final_answer` concatenates the SQL result summary and the grounded RAG answer.
