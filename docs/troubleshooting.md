# Troubleshooting

Real issues encountered building this project, and how they were diagnosed and fixed — kept here as a record, not hypothetical guidance.

## Schema retriever missed tables for business-vocabulary questions

**Symptom**: "What is the total revenue?" answered correctly but `tables_used` came back empty in the UI, since no schema/table/column literally contains the token "revenue" (the actual column is `TotalAmount`).

**Fix**: Added a business-term synonym map (`_SYNONYMS` in `app/text_to_sql/schema_retriever.py`) that expands question tokens before matching — e.g. "revenue" → `totalamount`/`linetotal`/`revenuegenerated`, "region" → `shippingstate`, "target"/"performance" → `targetamount`/`achievedamount`. Verified: "What is the total revenue?" now correctly includes `sales.Orders` in `tables_used`.

## `pyodbc.Error: Function sequence error (0) (SQLFetch)`

**Symptom**: Observability writes (`INSERT ... OUTPUT INSERTED.QueryID`) intermittently failed with this pyodbc error.

**Cause**: SQL Server's row-count messages ("(1 row affected)") interleave with the `OUTPUT` clause's result set, which confuses pyodbc's cursor state unless `SET NOCOUNT ON` is issued first. A second, related bug: the database session was being closed before the returned scalar value was read, since the `return` statement inside a `with get_session() as session:` block runs `__exit__` (closing the session) before the caller receives the value.

**Fix**: Issue `SET NOCOUNT ON` before any `INSERT ... OUTPUT` statement; fetch scalar values *inside* the `with` block before it closes, not after.

## Cold SQL Server buffer pool after service restart

**Symptom**: A simple `COUNT(*)` on a 200K-row table took 47 seconds; even new connection logins started timing out during a heavy test run.

**Cause**: Right after a SQL Server service restart (or after a very heavy unindexed query), the buffer pool is cold — first reads hit disk. Not a code bug.

**Diagnosis**: Re-ran the same query twice in a row — 0.67s cold, 0.04s warm — confirming it was cache warm-up, not a connectivity or query-correctness issue.

## RAG stopword collision producing false-positive similarity

**Symptom**: An evaluation test expecting `NO_EVIDENCE` for an unrelated question ("What is the capital of France?") instead returned a grounded answer with 0.30+ similarity score.

**Cause**: The 256-dimension hashed bag-of-words embedding collided on common stopwords (`is`, `the`, `what`, `of`) shared between the unrelated question and every indexed document.

**Fix**: Added a stopword filter to `app/rag/embeddings.py` and the lexical-overlap scoring in `app/rag/retriever.py`, and increased embedding dimensions from 256 to 512 to reduce hash collisions further. False-positive score dropped from 0.36 to 0.05, well under the 0.12 grounding threshold.

## Agent planner tokenization bug

**Symptom**: A question ending in a question mark ("What is the total revenue?") wasn't classified with the `revenue` data-keyword signal.

**Cause**: `question.lower().split()` doesn't strip punctuation — the token was literally `"revenue?"`, which never matched the keyword set `{"revenue", ...}`.

**Fix**: Switched to regex tokenization (`re.findall(r"[a-z0-9]+", ...)`), matching the same pattern already used in `app/rag/embeddings.py`.

## Agent planner keyword collision ("product" vs. policy questions)

**Symptom**: "What is the refund policy for damaged products?" was routed to both `sql_tool` and `rag_tool` instead of `rag_tool` only.

**Cause**: `"products"` was in the general data-keyword set, so any policy question mentioning products triggered a false "mixed" intent classification.

**Fix**: Demoted `"product"`/`"products"` to weak signals that only count toward data-intent when no document keyword (`policy`, `refund`, `warranty`, ...) is present in the same question.

## Docker `apt-key: not found`

**Symptom**: `docker build` failed at the Microsoft ODBC driver installation step with `/bin/sh: 1: apt-key: not found`.

**Cause**: `python:3.11-slim` had moved to a newer Debian base (trixie/13) where `apt-key` was removed entirely.

**Fix**: Pinned the base image to `python:3.11-slim-bookworm` (Debian 12, matching Microsoft's published `msodbcsql17` repo) and switched to the modern keyring approach (`gpg --dearmor` into `/usr/share/keyrings/`, referenced via `signed-by=` in the sources list) instead of the deprecated `apt-key add`.

## Dependency pins failing on Python 3.14

**Symptom**: `pip install -r requirements.txt` failed to find wheels for `pandas==2.2.3`, `numpy==2.2.1`, and `psycopg[binary]==3.2.3` on this machine's Python 3.14 environment; building from source failed due to missing MSVC/vswhere.

**Fix**: Bumped to versions with confirmed prebuilt `cp314-win_amd64` wheels (`pandas==2.3.3`, `numpy==2.3.3`, `psycopg[binary]==3.2.13`, `pydantic==2.12.0`) — verified via `pip install --dry-run` before committing to each version.
