from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.risk_check_engine import check_workflow_risks
from schemas import CandidateProductsJSON, LeadJSON, PricingResultJSON


DEFAULT_CASES = ROOT / "eval_cases" / "risk_check_cases.json"
REPORT_DIR = ROOT / "docs" / "test_reports"


def load_cases(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_case_file(cases: List[Dict[str, Any]]) -> None:
    for index, case in enumerate(cases, start=1):
        if "case_id" not in case:
            raise ValueError(f"Case #{index} is missing case_id")
        if "lead" not in case:
            raise ValueError(f"Case {case['case_id']} is missing lead")
        if "expected_issue_codes" not in case:
            raise ValueError(f"Case {case['case_id']} is missing expected_issue_codes")


def build_optional_model(raw: Dict[str, Any] | None, model_type):
    if raw is None:
        return None
    return model_type.model_validate(raw)


def run_eval(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    passed = 0
    categories = Counter(case.get("category", "uncategorized") for case in cases)

    for case in cases:
        expected = set(case["expected_issue_codes"])
        try:
            lead = LeadJSON.model_validate(case["lead"])
            product_match = build_optional_model(case.get("product_match"), CandidateProductsJSON)
            pricing = build_optional_model(case.get("pricing"), PricingResultJSON)
            result = check_workflow_risks(
                lead=lead,
                product_match=product_match,
                pricing=pricing,
                itinerary_markdown=case.get("itinerary_markdown", ""),
            )
            actual = {issue.code for issue in result.issues}
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            success = not missing and not unexpected
            if success:
                passed += 1
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": success,
                    "expected_issue_codes": sorted(expected),
                    "actual_issue_codes": sorted(actual),
                    "missing": missing,
                    "unexpected": unexpected,
                    "human_review_required": result.human_review_required,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": False,
                    "expected_issue_codes": sorted(expected),
                    "actual_issue_codes": [],
                    "missing": sorted(expected),
                    "unexpected": [],
                    "error": f"{exc.__class__.__name__}: {exc}",
                }
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "case_count": len(cases),
        "passed_cases": passed,
        "case_accuracy": round(passed / len(cases), 4) if cases else 0,
        "categories": dict(categories),
        "results": results,
    }


def write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Risk Check Eval Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Cases: {report['case_count']}",
        f"- Case accuracy: {report['case_accuracy']:.2%}",
        f"- Passed: {report['passed_cases']} / {report['case_count']}",
        "",
        "## Categories",
        "",
    ]
    for category, count in sorted(report["categories"].items()):
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Cases", ""])
    for result in report["results"]:
        status = "PASS" if result["success"] else "FAIL"
        lines.append(f"### {result['case_id']} — {status}")
        lines.append("")
        lines.append(f"- Expected: {', '.join(result['expected_issue_codes']) or '(none)'}")
        lines.append(f"- Actual: {', '.join(result['actual_issue_codes']) or '(none)'}")
        if result.get("missing"):
            lines.append(f"- Missing: {', '.join(result['missing'])}")
        if result.get("unexpected"):
            lines.append(f"- Unexpected: {', '.join(result['unexpected'])}")
        if result.get("error"):
            lines.append(f"- Error: {result['error']}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate risk_check_tool issue detection.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to risk check cases JSON")
    parser.add_argument("--report", default=None, help="Optional markdown report output path")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    validate_case_file(cases)
    report = run_eval(cases)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))

    report_path = Path(args.report) if args.report else REPORT_DIR / f"risk_check_eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.md"
    write_markdown_report(report, report_path)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
