from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_main import PricingRequestV2, build_user_intent_from_pricing_request, get_normalized_product_by_id
from engines.cost_engine import calculate_total_cost
from schemas import LeadJSON, PricingResultJSON


DEFAULT_CASES = ROOT / "eval_cases" / "pricing_cases.json"
REPORT_DIR = ROOT / "docs" / "test_reports"


def load_cases(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_case_file(cases: List[Dict[str, Any]]) -> None:
    for index, case in enumerate(cases, start=1):
        if "case_id" not in case:
            raise ValueError(f"Case #{index} is missing case_id")
        if "product_id" not in case:
            raise ValueError(f"Case {case['case_id']} is missing product_id")
        if "lead" not in case:
            raise ValueError(f"Case {case['case_id']} is missing lead")
        if "expected" not in case:
            raise ValueError(f"Case {case['case_id']} is missing expected")


def close_money(actual: float | int | None, expected: float | int, tolerance: float = 0.01) -> bool:
    if actual is None:
        return False
    return abs(float(actual) - float(expected)) <= tolerance


def run_pricing_case(case: Dict[str, Any]) -> PricingResultJSON:
    lead = LeadJSON.model_validate(case["lead"])
    product = get_normalized_product_by_id(case["product_id"])
    if not product:
        raise ValueError(f"Product not found: {case['product_id']}")
    options = case.get("pricing_options", {})
    request = PricingRequestV2(
        lead=lead,
        selected_product_id=case["product_id"],
        is_peak=options.get("is_peak", True),
        guide_code=options.get("guide_code"),
        hotel_code=options.get("hotel_code"),
        hotel_nights=options.get("hotel_nights"),
        transfer_code=options.get("transfer_code"),
        transfer_times=options.get("transfer_times", 0),
        car_days=options.get("car_days"),
        selected_optional_item_codes=options.get("selected_optional_item_codes", []),
    )
    user_intent = build_user_intent_from_pricing_request(request, product)
    with contextlib.redirect_stdout(io.StringIO()):
        raw_result = calculate_total_cost(product, user_intent)
    return PricingResultJSON(**raw_result)


def evaluate_case(case: Dict[str, Any]) -> Dict[str, Any]:
    expected = case["expected"]
    result = run_pricing_case(case)
    failures: List[str] = []

    if "success" in expected and result.success != expected["success"]:
        failures.append(f"success expected {expected['success']}, got {result.success}")

    if result.summary is None:
        failures.append("summary missing")
    else:
        if "grand_total" in expected and not close_money(result.summary.grand_total, expected["grand_total"]):
            failures.append(f"grand_total expected {expected['grand_total']}, got {result.summary.grand_total}")
        if "per_person" in expected and not close_money(result.summary.per_person, expected["per_person"]):
            failures.append(f"per_person expected {expected['per_person']}, got {result.summary.per_person}")

    for category, expected_subtotal in expected.get("category_subtotals", {}).items():
        actual_subtotal = result.category_subtotals.get(category)
        if not close_money(actual_subtotal, expected_subtotal):
            failures.append(f"{category} subtotal expected {expected_subtotal}, got {actual_subtotal}")

    if "validation_issue_count" in expected and len(result.validation_issues) != expected["validation_issue_count"]:
        failures.append(f"validation issue count expected {expected['validation_issue_count']}, got {len(result.validation_issues)}")

    if "validation_issue_fields_contains" in expected:
        actual_fields = {issue.field for issue in result.validation_issues}
        expected_fields = set(expected["validation_issue_fields_contains"])
        missing = expected_fields - actual_fields
        if missing:
            failures.append(f"validation issue fields missing {sorted(missing)}, got {sorted(actual_fields)}")

    return {
        "case_id": case["case_id"],
        "category": case.get("category", "uncategorized"),
        "success": not failures,
        "failures": failures,
        "pricing_success": result.success,
        "grand_total": result.summary.grand_total if result.summary else None,
        "per_person": result.summary.per_person if result.summary else None,
        "category_subtotals": result.category_subtotals,
        "validation_issue_count": len(result.validation_issues),
    }


def run_eval(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    categories = Counter(case.get("category", "uncategorized") for case in cases)
    for case in cases:
        try:
            results.append(evaluate_case(case))
        except Exception as exc:
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case.get("category", "uncategorized"),
                    "success": False,
                    "failures": [f"{exc.__class__.__name__}: {exc}"],
                    "pricing_success": None,
                    "grand_total": None,
                    "per_person": None,
                    "category_subtotals": {},
                    "validation_issue_count": None,
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
        "# Pricing Eval Report",
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
        lines.append(f"- Pricing success: {result['pricing_success']}")
        lines.append(f"- Grand total: {result['grand_total']}")
        lines.append(f"- Per person: {result['per_person']}")
        lines.append(f"- Validation issues: {result['validation_issue_count']}")
        if result["failures"]:
            lines.append("- Failures:")
            for failure in result["failures"]:
                lines.append(f"  - {failure}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic pricing results.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to pricing cases JSON")
    parser.add_argument("--validate-only", action="store_true", help="Validate case file without running pricing")
    parser.add_argument("--report", default=None, help="Optional markdown report output path")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    validate_case_file(cases)
    if args.validate_only:
        print(f"Validated {len(cases)} pricing cases.")
        return

    report = run_eval(cases)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))
    report_path = Path(args.report) if args.report else REPORT_DIR / f"pricing_eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.md"
    write_markdown_report(report, report_path)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
