import json
from datetime import datetime, timezone
from pathlib import Path


def save_report(sql_report: dict, security_report: dict, directory: str = "data/evaluation") -> Path:
    Path(directory).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(directory) / f"evaluation_report_{timestamp}.json"

    report = {
        "generated_at": timestamp,
        "text_to_sql": sql_report,
        "security": security_report,
    }
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path


def print_summary(sql_report: dict, security_report: dict) -> None:
    print("=== Text-to-SQL Evaluation ===")
    print(f"Pass rate: {sql_report['passed']}/{sql_report['total_cases']} ({sql_report['pass_rate'] * 100:.1f}%)")
    print(f"Average latency: {sql_report['average_latency_ms']} ms")
    for category, stats in sql_report["by_category"].items():
        print(f"  {category}: {stats['passed']}/{stats['total']}")

    failing = [c for c in sql_report["cases"] if not c["passed"]]
    if failing:
        print("\nFailing cases:")
        for case in failing:
            print(f"  [{case['id']}] {case['reasons']}")

    print("\n=== Security Evaluation ===")
    print(f"Pass rate: {security_report['passed']}/{security_report['total_cases']} "
          f"({security_report['pass_rate'] * 100:.1f}%)")
    failing_security = [c for c in security_report["cases"] if not c["passed"]]
    if failing_security:
        print("Failing security cases:")
        for case in failing_security:
            print(f"  [{case['id']}] {case['sql']}")
