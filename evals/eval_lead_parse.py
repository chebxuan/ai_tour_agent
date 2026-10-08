from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.llm_client import LLMConfigurationError, parse_lead_text
from backend.app.schemas import LeadJSON

DEFAULT_CASES = ROOT / "evals" / "cases" / "lead_parse_cases.json"
REPORT_DIR = ROOT / "docs" / "test_reports"


def load_cases(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================
# *_contains 断言语义（两类，避免对自由文本用"token 精确相等"造成假失败）
#
# 1) CANONICAL_TAG_KEYS：interests / travel_style / avoid 是要求模型输出的规范化 tag。
#    用"存在性包含"判断：期望 tag 归一化后是某个实际 tag 的子串即通过
#    （容忍模型输出更丰富的复合 tag，如期望 photography ⊆ skyline_photography）。
#    局限说明：自由文本字段无法做精确语义匹配，自由文本断言的是"概念关键词存在"，
#    方向性（如 avoid 与 like 相反）由精确的结构化字段承载 + bad-case 人工复核兜底。
#
# 2) FREE_TEXT_NOTE_KEYS：sales_notes / dietary_notes / must_have /
#    hotel_special_requirements / hotel_style_notes / budget_notes 是自由短语，
#    用"概念关键词整词包含"判断：期望短语去掉纯功能词后的每个实词，都需整词出现在
#    实际文本中（容忍 no/not、语序变化等改写）。
# ============================================================
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
    "for", "we", "our", "you", "your", "it", "they", "them", "is", "are",
    "be", "with", "have", "has", "had", "want", "wants", "like", "prefer",
    "prefers", "please", "would", "can", "could", "all", "some", "any",
    "one", "two", "very", "really", "also", "andor",
}


def _norm_tag(value: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _token_presence_ok(actual: List[str], expected: List[str]) -> bool:
    actual_norm = [_norm_tag(x) for x in actual]
    for exp in expected:
        e = _norm_tag(exp)
        if not e:
            continue
        if not any(e in a for a in actual_norm):
            return False
    return True


def _content_words(text: str) -> set:
    import re as _re
    return {w for w in _re.split(r"[^a-z0-9]+", text.lower()) if w and w not in _STOPWORDS}


def _concept_kw_ok(actual_text: str, fragments: List[str]) -> bool:
    words = _content_words(actual_text)
    return all(_content_words(f).issubset(words) for f in fragments)


def _contains_actual(actual: List[str]) -> str:
    return "; ".join(str(x) for x in actual if x) if actual else "(empty)"


CANONICAL_TAG_KEYS = {
    "interests_contains": lambda lead: lead.intent.interests,
    "travel_style_contains": lambda lead: lead.intent.travel_style,
    "avoid_contains": lambda lead: lead.intent.avoid,
}
FREE_TEXT_NOTE_KEYS = {
    "must_have_contains": lambda lead: lead.intent.must_have,
    "dietary_notes_contains": lambda lead: lead.intent.dietary_notes,
    "sales_notes_contains": lambda lead: lead.sales_notes,
    "hotel_special_requirements_contains": lambda lead: lead.hotel_preference.special_requirements,
    "hotel_style_notes_contains": lambda lead: [lead.hotel_preference.style_notes],
    "budget_notes_contains": lambda lead: [lead.budget_preference.notes],
}


def _date_to_iso(value: Any) -> Any:
    """Normalize date / datetime / ISO-string values to 'YYYY-MM-DD' for equality checks."""
    import datetime as _dt

    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.strftime("%Y-%m-%d")
    return value


# Exact-key → nested LeadJSON location. Keys are the fields validated downstream in
# the product/pricing/risk chain; goldens must match the canonical value each field holds.
EXACT_VALUE_GETTERS = {
    "destination_cities": lambda lead: lead.intent.destination_cities,
    "trip_days": lambda lead: lead.intent.trip_days,
    "adults": lambda lead: lead.passenger_mix.adults,
    "children": lambda lead: lead.passenger_mix.children,
    "seniors": lambda lead: lead.passenger_mix.seniors,
    "need_guide": lambda lead: lead.intent.need_guide,
    "need_private_car": lambda lead: lead.intent.need_private_car,
    "need_airport_transfer": lambda lead: lead.intent.need_airport_transfer,
    "departure_city": lambda lead: lead.intent.departure_city,
    "transport_preference": lambda lead: lead.intent.transport_preference,
    "season": lambda lead: lead.travel_window.season,
    "start_date": lambda lead: _date_to_iso(lead.travel_window.start_date),
    "end_date": lambda lead: _date_to_iso(lead.travel_window.end_date),
    "flexible_days": lambda lead: lead.travel_window.flexible_days,
    "nationality": lambda lead: lead.contact.nationality,
    "budget_tier": lambda lead: lead.budget_preference.tier,
    "budget_max_total": lambda lead: lead.budget_preference.max_total,
    "budget_max_per_person": lambda lead: lead.budget_preference.max_per_person,
    "hotel_tier": lambda lead: lead.hotel_preference.tier,
    "room_view_priority": lambda lead: lead.hotel_preference.room_view_priority,
    "language": lambda lead: lead.language,
}


def get_actual_value(lead: LeadJSON, key: str) -> Any:
    if key not in EXACT_VALUE_GETTERS:
        raise ValueError(f"Unsupported exact assertion key: {key}")
    return EXACT_VALUE_GETTERS[key](lead)


def evaluate_expected(lead: LeadJSON, expected: Dict[str, Any]) -> Tuple[int, int, List[str]]:
    passed = 0
    total = 0
    failures: List[str] = []

    for key, expected_value in expected.items():
        total += 1
        ok = False
        actual_display = ""

        if key.endswith("_contains"):
            if key in CANONICAL_TAG_KEYS:
                actual_list = CANONICAL_TAG_KEYS[key](lead)
                expected_tags = expected_value if isinstance(expected_value, list) else [expected_value]
                ok = _token_presence_ok(actual_list, expected_tags)
                actual_display = repr(actual_list)
            elif key in FREE_TEXT_NOTE_KEYS:
                actual_list = FREE_TEXT_NOTE_KEYS[key](lead)
                fragments = expected_value if isinstance(expected_value, list) else [expected_value]
                actual_text = "\n".join(str(x) for x in actual_list if x)
                ok = _concept_kw_ok(actual_text, fragments)
                actual_display = repr(_contains_actual(actual_list))
            else:
                failures.append(f"Unsupported contains assertion: {key}")
                continue
        else:
            actual_value = get_actual_value(lead, key)
            ok = actual_value == expected_value
            actual_display = repr(actual_value)

        if ok:
            passed += 1
        else:
            failures.append(f"{key}: expected {expected_value!r}, got {actual_display}")

    return passed, total, failures


def run_eval(cases: List[Dict[str, Any]], limit: int | None = None, prompt_version: str = "lead_parse_v1") -> Dict[str, Any]:
    selected_cases = cases[:limit] if limit else cases
    results = []
    total_assertions = 0
    passed_assertions = 0

    for case in selected_cases:
        case_id = case["case_id"]
        expected_count = len(case.get("expected", {}))
        # Denominator is fixed up front so a transient infra error (ReadTimeout) that prevents
        # parsing never silently shrinks the accuracy denominator.
        total_assertions += expected_count

        def parse_once() -> LeadJSON:
            return parse_lead_text(
                case["customer_message"],
                lead_id=case_id,
                source_channel="eval",
                source_id=case_id,
                prompt_version=prompt_version,
            )

        try:
            lead = parse_once()
        except Exception as exc:
            if isinstance(exc, (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError)):
                try:
                    lead = parse_once()
                except Exception as retry_exc:
                    exc = retry_exc
                else:
                    exc = None
            if exc is not None:
                results.append(
                    {
                        "case_id": case_id,
                        "success": False,
                        "passed": 0,
                        "total": expected_count,
                        "failures": [f"{exc.__class__.__name__}: {exc}"],
                        "lead": None,
                    }
                )
                continue

        try:
            passed, total, failures = evaluate_expected(lead, case.get("expected", {}))
        except Exception as exc:
            results.append(
                {
                    "case_id": case_id,
                    "success": False,
                    "passed": 0,
                    "total": expected_count,
                    "failures": [f"evaluate error {exc.__class__.__name__}: {exc}"],
                    "lead": None,
                }
            )
            continue

        passed_assertions += passed
        results.append(
            {
                "case_id": case_id,
                "success": passed == total,
                "passed": passed,
                "total": total,
                "failures": failures,
                "lead": lead.model_dump(mode="json"),
            }
        )

    accuracy = passed_assertions / total_assertions if total_assertions else 0
    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "case_count": len(selected_cases),
        "passed_assertions": passed_assertions,
        "total_assertions": total_assertions,
        "field_accuracy": round(accuracy, 4),
        "results": results,
    }


def write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Lead Parse Eval Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Cases: {report['case_count']}",
        f"- Field accuracy: {report['field_accuracy']:.2%}",
        f"- Assertions: {report['passed_assertions']} / {report['total_assertions']}",
        "",
        "## Cases",
        "",
    ]
    for result in report["results"]:
        status = "PASS" if result["success"] else "FAIL"
        lines.append(f"### {result['case_id']} — {status}")
        lines.append("")
        if result["failures"]:
            lines.append("Failures:")
            for failure in result["failures"]:
                lines.append(f"- {failure}")
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def validate_case_file(cases: List[Dict[str, Any]]) -> None:
    exact_keys = {
        "destination_cities",
        "trip_days",
        "adults",
        "children",
        "seniors",
        "need_guide",
        "need_private_car",
        "need_airport_transfer",
        "departure_city",
        "transport_preference",
        "season",
        "start_date",
        "end_date",
        "flexible_days",
        "nationality",
        "budget_tier",
        "budget_max_total",
        "budget_max_per_person",
        "hotel_tier",
        "room_view_priority",
        "language",
    }
    contains_keys = {
        "interests_contains",
        "travel_style_contains",
        "avoid_contains",
        "must_have_contains",
        "dietary_notes_contains",
        "sales_notes_contains",
        "hotel_special_requirements_contains",
        "hotel_style_notes_contains",
        "budget_notes_contains",
    }
    for index, case in enumerate(cases, start=1):
        if "case_id" not in case:
            raise ValueError(f"Case #{index} is missing case_id")
        if "customer_message" not in case:
            raise ValueError(f"Case {case.get('case_id', index)} is missing customer_message")
        if "expected" not in case:
            raise ValueError(f"Case {case['case_id']} is missing expected")
        for key in case["expected"]:
            if key not in exact_keys and key not in contains_keys:
                raise ValueError(f"Case {case['case_id']} has unsupported expected key: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate customer text to LeadJSON parsing.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to lead parse eval cases JSON")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N cases")
    parser.add_argument("--validate-only", action="store_true", help="Validate case file without calling the LLM")
    parser.add_argument("--prompt-version", default="lead_parse_v1", help="Prompt file name in docs/prompts/ (without .md)")
    parser.add_argument("--report", default=None, help="Optional markdown report output path")
    parser.add_argument("--out-json", default=None, help="Optional full report JSON path (incl. per-case results)")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    validate_case_file(cases)

    if args.validate_only:
        print(f"Validated {len(cases)} lead parse cases.")
        return

    if not os.getenv("OPENAI_API_KEY"):
        raise LLMConfigurationError("OPENAI_API_KEY is required to run lead parse eval.")

    report = run_eval(cases, limit=args.limit, prompt_version=args.prompt_version)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))

    report_path = Path(args.report) if args.report else REPORT_DIR / f"lead_parse_eval_{args.prompt_version}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    write_markdown_report(report, report_path)
    print(f"Report written to {report_path}")

    if args.out_json:
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Full JSON written to {out_path}")


if __name__ == "__main__":
    main()
