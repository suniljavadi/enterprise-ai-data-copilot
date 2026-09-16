# Troubleshooting

Real issues encountered building this project, and how they were diagnosed and fixed — kept here as a record, not hypothetical guidance.

## Azure SQL Database migration: base setup script incompatible with an existing database

**Symptom**: The local `SalesAI_DB_SQLServer_Setup.sql` script's prologue (`USE master; ALTER DATABASE ... SET SINGLE_USER; DROP DATABASE; CREATE DATABASE; ALTER DATABASE ... SET RECOVERY SIMPLE;`) can't run against an already-provisioned Azure SQL Database — `SINGLE_USER`/`RECOVERY` aren't supported there, and re-running `CREATE DATABASE` would either fail or silently replace the carefully-configured free-tier database with a default (potentially paid) one.

**Fix**: Stripped everything before the `/* SCHEMAS */` section and ran the remainder directly against the pre-created free-tier database. Verified with `Select-String` that no other on-prem-only statements (`DBCC`, `BACKUP`, `sp_configure`, `xp_cmdshell`, etc.) existed in either script before running them.

## Computed-column table failed to create only on Azure SQL (not locally)

**Symptom**: `CREATE TABLE inventory.PurchaseOrderItems` (which has `LineAmount AS (Quantity * UnitCost) PERSISTED`) failed via `sqlcmd` against Azure SQL with `Msg 1934: CREATE TABLE failed because the following SET options have incorrect settings: 'QUOTED_IDENTIFIER'` — even though the exact same script ran fine locally via SSMS. This cascaded into two more errors (`Invalid object name`, `Cannot find the object`) for statements that depended on the table.

**Cause**: SSMS enables `QUOTED_IDENTIFIER ON` by default; `sqlcmd` does not. Persisted computed columns require it.

**Fix**: Ran `SET QUOTED_IDENTIFIER ON;` before recreating just that table and its 150,000 rows of data. Caught by a full local-vs-Azure row-count comparison script after migration — every other table matched exactly, which is what made this one gap obvious.

## Shell-quoting corrupted a JSON environment variable during Azure deployment

**Symptom**: The deployed container returned `500` on every authenticated request with `ValueError: API_KEYS is not valid JSON: Expecting property name enclosed in double quotes`.

**Cause**: Passing a JSON string like `{"key": {"name": "x", "role": "admin"}}` through `az containerapp create --env-vars "API_KEYS=$json"` in PowerShell stripped the double quotes somewhere across the PowerShell → Azure CLI → ARM template layers, turning valid JSON into invalid YAML-ish text.

**Fix**: Exported the container app config to a YAML file (`az containerapp show -o yaml`), patched the `API_KEYS` value using PyYAML (which handles quoting correctly when serializing), and applied it with `az containerapp update --yaml` — bypassing shell argument parsing entirely.

## Windows PowerShell's `Out-File -Encoding utf8` adds a BOM that breaks `json.loads()`

**Symptom**: After fixing the quoting issue above, the same endpoint still failed with `ValueError: API_KEYS is not valid JSON: Unexpected UTF-8 BOM (decode using utf-8-sig)`.

**Cause**: Windows PowerShell 5.1's `Out-File -Encoding utf8` writes a UTF-8 byte-order-mark by default (PowerShell 7+ does not). Reading that file with Python's default `open(..., encoding="utf-8")` includes the BOM character as part of the string, which breaks JSON parsing both locally (when validating) and once embedded in the deployed environment variable.

**Fix**: Read the file with `encoding="utf-8-sig"` instead, and validated with `json.loads()` locally before applying the fix to Azure — catching the corruption before redeploying a second time.

## Azure SQL serverless free-tier auto-pause looks like a database outage

**Symptom**: Right after fixing the above two issues, the same request failed again with `pyodbc.Error: [SQL Server]Database 'SalesAI_DB' ... is not currently available. Please retry the connection later. ... (40613)`.

**Cause**: Not a bug — the free-tier serverless database had auto-paused after ~60 minutes of no queries (while the container app deployment issues above were being debugged) and needed ~30-60 seconds to resume on the next request, which is expected serverless behavior, not an error condition.

**Fix**: No code change needed — retried after a short wait and the query succeeded normally. Documented in `docs/deployment.md` as expected behavior so it isn't mistaken for an outage in the future.

## `tests/unit` silently required a live SQL Server connection in hosted CI

**Symptom**: The first push to GitHub Actions failed at the "Unit tests (no database required)" step with `pyodbc.Error: Can't open lib 'ODBC Driver 17 for SQL Server' : file not found` — even though the CI workflow explicitly only runs `tests/unit`, which is supposed to have no database dependency.

**Cause**: `tests/unit/test_schema_retriever.py` called `select_relevant_tables(question)` without passing a `snapshot`, so it silently fell through to `get_cached_schema()`, which tries to connect to a real SQL Server. This worked locally (a real `SalesAI_DB` and ODBC driver are present) but broke on the hosted runner, which has neither. The test was misclassified as a pure unit test when it actually had a hidden integration dependency.

**Fix**: Rewrote the test to construct a fake in-memory `SchemaSnapshot` (via `SchemaSnapshot`/`TableMetadata`/`ColumnMetadata`) and pass it explicitly to `select_relevant_tables(question, snapshot=...)`. Verified the fix by setting `SQL_SERVER` to an unreachable host locally and confirming `tests/unit` still passes in under a second — then verified again for real by watching the actual GitHub Actions run turn green.

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
