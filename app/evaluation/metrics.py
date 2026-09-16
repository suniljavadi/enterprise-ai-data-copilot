from app.evaluation.datasets import EvalCase


def check_sql_contains_tables(sql: str, expected_tables: list[str]) -> list[str]:
    missing = [t for t in expected_tables if t.lower() not in sql.lower()]
    return missing


def check_sql_contains_keywords(sql: str, expected_keywords: list[str]) -> list[str]:
    missing = [k for k in expected_keywords if k.lower() not in sql.lower()]
    return missing


def check_min_rows(row_count: int, min_rows: int | None) -> bool:
    return min_rows is None or row_count >= min_rows


def score_case(case: EvalCase, sql: str | None, row_count: int | None, succeeded: bool) -> dict:
    if not case.should_succeed:
        passed = not succeeded
        reasons = [] if passed else ["Expected the question to be rejected as out-of-scope, but it succeeded"]
        return {"id": case.id, "category": case.category, "passed": passed, "reasons": reasons}

    if not succeeded:
        return {
            "id": case.id,
            "category": case.category,
            "passed": False,
            "reasons": ["Expected the question to succeed, but it was rejected"],
        }

    reasons = []
    missing_tables = check_sql_contains_tables(sql, case.expected_tables)
    if missing_tables:
        reasons.append(f"SQL missing expected table(s): {missing_tables}")

    missing_keywords = check_sql_contains_keywords(sql, case.expected_sql_keywords)
    if missing_keywords:
        reasons.append(f"SQL missing expected keyword(s): {missing_keywords}")

    if not check_min_rows(row_count, case.min_rows):
        reasons.append(f"Expected at least {case.min_rows} row(s), got {row_count}")

    return {"id": case.id, "category": case.category, "passed": not reasons, "reasons": reasons}
