from app.evaluation.evaluator import run_security_evaluation, run_text_to_sql_evaluation


def test_text_to_sql_evaluation_meets_minimum_pass_rate():
    report = run_text_to_sql_evaluation()
    assert report["total_cases"] >= 30
    assert report["pass_rate"] >= 0.9, [c for c in report["cases"] if not c["passed"]]


def test_security_evaluation_has_zero_tolerance_for_failures():
    report = run_security_evaluation()
    assert report["pass_rate"] == 1.0, [c for c in report["cases"] if not c["passed"]]
