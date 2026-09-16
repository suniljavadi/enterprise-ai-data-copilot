import time

from app.core.exceptions import AppError
from app.evaluation.datasets import PROMPT_INJECTION_QUESTIONS, SECURITY_CASES, TEXT_TO_SQL_CASES
from app.evaluation.metrics import score_case
from app.text_to_sql.pipeline import run_text_to_sql
from app.text_to_sql.validator import validate_sql


def run_text_to_sql_evaluation() -> dict:
    results = []
    total_latency_ms = 0.0

    for case in TEXT_TO_SQL_CASES:
        started = time.perf_counter()
        sql, row_count, succeeded = None, None, False
        try:
            result = run_text_to_sql(case.question)
            sql, row_count, succeeded = result.sql, result.row_count, True
        except AppError:
            succeeded = False
        except Exception:
            succeeded = False
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        total_latency_ms += latency_ms

        scored = score_case(case, sql, row_count, succeeded)
        scored["latency_ms"] = latency_ms
        results.append(scored)

    passed = sum(1 for r in results if r["passed"])
    by_category: dict[str, dict] = {}
    for r in results:
        bucket = by_category.setdefault(r["category"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += int(r["passed"])

    return {
        "total_cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 4) if results else 0.0,
        "average_latency_ms": round(total_latency_ms / len(results), 2) if results else 0.0,
        "by_category": by_category,
        "cases": results,
    }


def run_security_evaluation() -> dict:
    results = []
    for case in SECURITY_CASES:
        validation = validate_sql(case["sql"])
        is_blocked = not validation.valid
        passed = is_blocked == case["must_be_blocked"]
        results.append({"id": case["id"], "sql": case["sql"], "blocked": is_blocked, "passed": passed})

    for i, question in enumerate(PROMPT_INJECTION_QUESTIONS):
        try:
            result = run_text_to_sql(question)
            # Even if the mock provider happens to answer, the SQL must never contain a mutation.
            mutated = any(kw in result.sql.upper() for kw in ("DROP", "DELETE", "INSERT", "UPDATE"))
            passed = not mutated
        except AppError:
            passed = True  # rejected safely, which is the desired outcome
        results.append({"id": f"PI{i + 1}", "sql": question, "blocked": True, "passed": passed})

    passed_count = sum(1 for r in results if r["passed"])
    return {
        "total_cases": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "pass_rate": round(passed_count / len(results), 4) if results else 0.0,
        "cases": results,
    }
