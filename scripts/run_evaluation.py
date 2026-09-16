import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.evaluation.evaluator import run_security_evaluation, run_text_to_sql_evaluation
from app.evaluation.reports import print_summary, save_report


def main() -> int:
    sql_report = run_text_to_sql_evaluation()
    security_report = run_security_evaluation()

    print_summary(sql_report, security_report)
    path = save_report(sql_report, security_report)
    print(f"\nReport saved to {path}")

    return 0 if sql_report["failed"] == 0 and security_report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
