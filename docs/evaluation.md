# Evaluation

## Methodology

`app/evaluation/datasets.py` defines 30 Text-to-SQL cases and 13 security cases. Correctness is scored **semantically** (`app/evaluation/metrics.py`), never by exact SQL string comparison, because multiple valid SQL queries can answer the same question:

- Does the generated SQL reference all `expected_tables`? (substring match on `schema.table`)
- Does it contain all `expected_sql_keywords`? (e.g. `JOIN`, `GROUP BY`, `LEFT JOIN`, `IS NULL`)
- Does execution return at least `min_rows`, when specified?
- For out-of-scope questions (`should_succeed=False`), is the question correctly rejected rather than hallucinated?

## Categories (38 cases)

| Category | Count | Examples |
|---|---|---|
| Basic | 5 | total revenue, average order value |
| Intermediate | 8 | top customers/products by revenue (joins), monthly revenue trend (GROUP BY), employees below target |
| Advanced | 13 | return rate by category (multi-table + LEFT JOIN), campaign revenue, ranking (`RANK() OVER`), running totals (`SUM() OVER`), revenue share percentage, cohort analysis, `HAVING`-based filters, revenue by region, inventory value by warehouse |
| Business | 7 | customers with no orders (LEFT JOIN + IS NULL), late shipments, inventory reorder |
| Negative | 5 | out-of-scope questions (weather, jokes) — must be gracefully rejected, not hallucinated |

## Security evaluation (13 cases)

Directly validates `app/text_to_sql/validator.py::validate_sql()` against: `DROP`/`DELETE`/`UPDATE`/`INSERT`, multi-statement injection, comment-based injection, `sys.tables` access, `xp_cmdshell`, `OPENROWSET` — plus 3 prompt-injection questions run through the full pipeline to confirm no mutation SQL ever reaches execution even if the LLM were manipulated.

## Running the evaluation

```powershell
python scripts/run_evaluation.py
```

Prints a category breakdown and average latency, and saves a timestamped JSON report to `data/evaluation/`. Also wired into `pytest` (`tests/evaluation/test_evaluation_suite.py`) with pass-rate gates: ≥90% functional, 100% security (zero tolerance).

## Current results (against real `SalesAI_DB`)

```
Text-to-SQL: 38/38 (100%) — avg latency ~190ms
  basic: 5/5, intermediate: 8/8, advanced: 13/13, business: 7/7, negative: 5/5
Security: 13/13 (100%)
```

## Two real dataset bugs found and fixed during evaluation

1. A question's wording didn't include a keyword ("monthly") the deterministic mock provider required, causing it to silently generate the wrong (but structurally valid) SQL for a different question pattern.
2. A question was missing the word "inventory," causing it to fall through to the "ambiguous question" rejection instead of matching the intended pattern.

Both are documented here because they demonstrate why evaluation datasets need their own validation pass — a wrong expected-answer dataset can hide real regressions as easily as buggy code can.
