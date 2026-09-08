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

from api_main import build_candidates_from_lead
from schemas import LeadJSON


DEFAULT_CASES = ROOT / "eval_cases" / "product_match_cases.json"
REPORT_DIR = ROOT / "docs" / "test_reports"


def load_cases(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_case_file(cases: List[Dict[str, Any]]) -> None:
    for index, case in enumerate(cases, start=1):
        if "case_id" not in case:
            raise ValueError(f"Case #{index} is missing case_id")
        if "lead" not in case:
            raise ValueError(f"Case {case['case_id']} is missing lead")
        if not any(key in case for key in ["expected_top1", "expected_top3_contains", "expected_top3_contains_any"]):
            raise ValueError(f"Case {case['case_id']} needs at least one expected assertion")


def run_eval(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    categories = Counter(case.get("category", "uncategorized") for case in cases)
    top1_total = 0
    top1_passed = 0
    top3_total = 0
    top3_passed = 0

    for case in cases:
        try:
            lead = LeadJSON.model_validate(case["lead"])
            product_match = build_candidates_from_lead(lead)
            ranked_ids = [candidate.product.product_id for candidate in product_match.candidates]
            top1 = ranked_ids[0] if ranked_ids else None
            failures: List[str] = []

            if "expected_top1" in case:
                top1_total += 1
                if top1 == case["expected_top1"]:
                    top1_passed += 1
                else:
                    failures.append(f"top1 expected {case['expected_top1']}, got {top1}")

            if "expected_top3_contains" in case:
                top3_total += 1
                expected = set(case["expected_top3_contains"])
                if expected.issubset(set(ranked_ids[:3])):
                    top3_passed += 1
                else:
                    failures.append(f"top3 missing {sorted(expected - set(ranked_ids[:3]))}, got {ranked_ids[:3]}")

            if "expected_top3_contains_any" in case:
                top3_total += 1
                expected_any = set(case["expected_top3_contains_any"])
                if expected_any.intersection(set(ranked_ids[:3])):
                    top3_passed += 1
                else:
                    failures.append(f"top3 expected any of {sorted(expected_any)}, got {ranked_ids[:3]}")

            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": not failures,
                    "top1": top1,
                    "ranked_ids": ranked_ids,
                    "recommended_product_id": product_match.recommended_product_id,
                    "failures": failures,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": False,
                    "top1": None,
                    "ranked_ids": [],
                    "recommended_product_id": None,
                    "failures": [f"{exc.__class__.__name__}: {exc}"],
                }
            )

    passed_cases = sum(1 for result in results if result["success"])
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "case_count": len(cases),
        "passed_cases": passed_cases,
        "case_accuracy": round(passed_cases / len(cases), 4) if cases else 0,
        "top1_accuracy": round(top1_passed / top1_total, 4) if top1_total else None,
        "top3_accuracy": round(top3_passed / top3_total, 4) if top3_total else None,
        "top1_assertions": {"passed": top1_passed, "total": top1_total},
        "top3_assertions": {"passed": top3_passed, "total": top3_total},
        "categories": dict(categories),
        "results": results,
    }


def write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Product Match Eval Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Cases: {report['case_count']}",
        f"- Case accuracy: {report['case_accuracy']:.2%}",
        f"- Top-1 accuracy: {report['top1_accuracy']:.2%}" if report["top1_accuracy"] is not None else "- Top-1 accuracy: n/a",
        f"- Top-3 accuracy: {report['top3_accuracy']:.2%}" if report["top3_accuracy"] is not None else "- Top-3 accuracy: n/a",
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
        lines.append(f"- Top 1: {result['top1']}")
        lines.append(f"- Ranked IDs: {', '.join(result['ranked_ids']) or '(none)'}")
        if result["failures"]:
            lines.append("- Failures:")
            for failure in result["failures"]:
                lines.append(f"  - {failure}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Product Match top-k accuracy.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to product match cases JSON")
    parser.add_argument("--validate-only", action="store_true", help="Validate case file without running matching")
    parser.add_argument("--report", default=None, help="Optional markdown report output path")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    validate_case_file(cases)
    if args.validate_only:
        print(f"Validated {len(cases)} product match cases.")
        return

    report = run_eval(cases)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))
    report_path = Path(args.report) if args.report else REPORT_DIR / f"product_match_eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.md"
    write_markdown_report(report, report_path)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
