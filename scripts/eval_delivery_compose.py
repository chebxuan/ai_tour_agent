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

from engines.delivery_composer import compose_delivery_draft
from schemas import CandidateProductsJSON, LeadJSON, PricingResultJSON, RiskCheckResultJSON


DEFAULT_CASES = ROOT / "eval_cases" / "delivery_compose_cases.json"
REPORT_DIR = ROOT / "docs" / "test_reports"


def load_cases(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_case_file(cases: List[Dict[str, Any]]) -> None:
    for index, case in enumerate(cases, start=1):
        if "case_id" not in case:
            raise ValueError(f"Case #{index} is missing case_id")
        if "lead" not in case:
            raise ValueError(f"Case {case['case_id']} is missing lead")
        if "expected_contains" not in case:
            raise ValueError(f"Case {case['case_id']} is missing expected_contains")


def optional_model(raw: Dict[str, Any] | None, model_type):
    return model_type.model_validate(raw) if raw else None


def run_eval(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    categories = Counter(case.get("category", "uncategorized") for case in cases)
    for case in cases:
        try:
            draft = compose_delivery_draft(
                lead=LeadJSON.model_validate(case["lead"]),
                product_match=optional_model(case.get("product_match"), CandidateProductsJSON),
                pricing=optional_model(case.get("pricing"), PricingResultJSON),
                risk_check=optional_model(case.get("risk_check"), RiskCheckResultJSON),
                itinerary_markdown=case.get("itinerary_markdown", ""),
            )
            haystack = f"{draft.subject}\n{draft.body_markdown}"
            missing = [token for token in case["expected_contains"] if token not in haystack]
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": not missing,
                    "missing": missing,
                    "subject": draft.subject,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": False,
                    "missing": case.get("expected_contains", []),
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "subject": None,
                }
            )
    passed = sum(1 for result in results if result["success"])
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
        "# Delivery Compose Eval Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Cases: {report['case_count']}",
        f"- Case accuracy: {report['case_accuracy']:.2%}",
        f"- Passed: {report['passed_cases']} / {report['case_count']}",
        "",
        "## Cases",
        "",
    ]
    for result in report["results"]:
        status = "PASS" if result["success"] else "FAIL"
        lines.append(f"### {result['case_id']} — {status}")
        lines.append("")
        lines.append(f"- Subject: {result['subject']}")
        if result.get("missing"):
            lines.append(f"- Missing: {', '.join(result['missing'])}")
        if result.get("error"):
            lines.append(f"- Error: {result['error']}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic delivery draft composer.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to delivery compose cases JSON")
    parser.add_argument("--report", default=None, help="Optional markdown report output path")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    validate_case_file(cases)
    report = run_eval(cases)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))
    report_path = Path(args.report) if args.report else REPORT_DIR / f"delivery_compose_eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.md"
    write_markdown_report(report, report_path)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
