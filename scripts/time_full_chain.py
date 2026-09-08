"""Time the deterministic full chain (LeadJSON -> match -> pricing -> markdown -> risk -> delivery).

What this measures / does NOT measure (be explicit, this file feeds docs/test_reports/time_trial.md):

- It times ONLY the deterministic in-process chain via `run_full_chain_for_lead`, which is the
  production path behind `POST /api/v2/lead-full-chain`. Cold/warm data-loading is separated by a
  warmup run so the reported numbers reflect steady-state auto-generation.
- It does NOT re-call the LLM lead parser. LLM parse latency (a few seconds per call on DashScope)
  is reported separately from the real historical `logs/llm_calls.jsonl`, so this file stays cheap
  and reproducible and we never conflate "auto chain" with "LLM extraction".

Output: prints a compact JSON summary; per sample also lists risk issues that still require human
review (the "还剩什么人工" part of the 30min->auto narrative).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_main import run_full_chain_for_lead  # noqa: E402
from schemas import ContactInfo, LeadIntent, LeadJSON, PassengerMix, TravelWindow  # noqa: E402

REPORT_DIR = ROOT / "docs" / "test_reports"

# Representative sample leads. Texts are synthetic, derived from the lead-parse eval set, and cover
# (a) a clean Shanghai couple, (b) a Beijing pair who need a guide with private car optional (car
# confirmation risk), (c) a multi-generation Xi'an group with a senior (pace risk). Each maps to a
# real product so the chain reaches pricing + risk.
SAMPLE_LEADS: List[Dict[str, Any]] = [
    {
        "label": "shanghai_couple_2d_clean",
        "text": "Two adults, 2 days in Shanghai, architecture and local food, no guide, no private car.",
        "lead": LeadJSON(
            lead_id="time_sh_2d",
            contact=ContactInfo(nationality="International"),
            travel_window=TravelWindow(),
            passenger_mix=PassengerMix(adults=2, children=0, seniors=0),
            intent=LeadIntent(
                destination_cities=["上海"],
                trip_days=2,
                interests=["architecture", "local_food"],
                need_guide=False,
                need_private_car=False,
            ),
        ),
    },
    {
        "label": "beijing_3d_guide_car_optional",
        "text": "Two adults, 3 days in Beijing, history and hutongs, need an English guide; private car is optional.",
        "lead": LeadJSON(
            lead_id="time_bj_3d",
            contact=ContactInfo(nationality="Canada"),
            travel_window=TravelWindow(),
            passenger_mix=PassengerMix(adults=2, children=0, seniors=0),
            intent=LeadIntent(
                destination_cities=["北京"],
                trip_days=3,
                interests=["history", "local_life"],
                need_guide=True,
                need_private_car=None,
            ),
        ),
    },
    {
        "label": "xian_2d_senior_pace",
        "text": "Two adults with my 70-year-old mother, 2 days in Xi'an, Terracotta Army a must, slow pace, need a guide.",
        "lead": LeadJSON(
            lead_id="time_xa_senior",
            contact=ContactInfo(nationality="Australia"),
            travel_window=TravelWindow(),
            passenger_mix=PassengerMix(adults=2, children=0, seniors=1),
            intent=LeadIntent(
                destination_cities=["西安"],
                trip_days=2,
                interests=["history"],
                must_have=["Terracotta Army"],
                travel_style=["slow_pace"],
                need_guide=True,
            ),
        ),
    },
]


def _timed_result(lead: LeadJSON, is_peak: bool) -> Dict[str, Any]:
    started = time.perf_counter()
    result = run_full_chain_for_lead(lead=lead, is_peak=is_peak)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    human_items: List[str] = []
    if result.risk_check is not None:
        for issue in result.risk_check.issues:
            if issue.requires_human_review:
                human_items.append(f"[{issue.code}] {issue.message}")
    return {
        "success": bool(result.success),
        "error": result.error,
        "elapsed_ms": elapsed_ms,
        "recommended_product_id": (
            result.product_match.recommended_product_id if result.product_match else None
        ),
        "grand_total": (
            result.pricing.summary.grand_total if result.pricing and result.pricing.summary else None
        ),
        "risk_human_review_required": bool(result.risk_check and result.risk_check.human_review_required),
        "human_review_items": human_items,
    }


def run_trial(runs: int, is_peak: bool) -> Dict[str, Any]:
    # Warmup: each sample once, so data files / engine caches are loaded before timing.
    for sample in SAMPLE_LEADS:
        _timed_result(sample["lead"], is_peak=is_peak)

    per_sample: List[Dict[str, Any]] = []
    all_ms: List[float] = []
    for sample in SAMPLE_LEADS:
        measurements: List[float] = []
        meta = None
        for _ in range(runs):
            res = _timed_result(sample["lead"], is_peak=is_peak)
            measurements.append(res["elapsed_ms"])
            meta = res
        all_ms.extend(measurements)
        per_sample.append(
            {
                "label": sample["label"],
                "text": sample["text"],
                "runs": runs,
                "mean_ms": round(statistics.mean(measurements), 1),
                "min_ms": min(measurements),
                "max_ms": max(measurements),
                "success": meta["success"],
                "error": meta["error"],
                "recommended_product_id": meta["recommended_product_id"],
                "grand_total": meta["grand_total"],
                "risk_human_review_required": meta["risk_human_review_required"],
                "human_review_items": meta["human_review_items"],
            }
        )

    return {
        "method": (
            "Deterministic in-process chain: run_full_chain_for_lead "
            "(product match -> pricing -> itinerary markdown -> risk check -> delivery draft). "
            "Warmup once per sample; then N timed runs. LLM lead-parse not re-called here."
        ),
        "is_peak": is_peak,
        "runs_per_sample": runs,
        "samples": len(SAMPLE_LEADS),
        "overall_mean_ms": round(statistics.mean(all_ms), 1),
        "overall_min_ms": min(all_ms),
        "overall_max_ms": max(all_ms),
        "per_sample": per_sample,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Time the deterministic full chain.")
    parser.add_argument("--runs", type=int, default=3, help="Timed runs per sample (warmup excluded)")
    parser.add_argument("--peak", action="store_true", help="Assume peak-season pricing")
    parser.add_argument("--out", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    report = run_trial(runs=args.runs, is_peak=args.peak)
    summary = {k: v for k, v in report.items() if k != "per_sample"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\nper_sample:")
    for s in report["per_sample"]:
        print(
            f"  {s['label']}: mean={s['mean_ms']}ms range=[{s['min_ms']},{s['max_ms']}] "
            f"success={s['success']} product={s['recommended_product_id']} total={s['grand_total']} "
            f"human_review={s['risk_human_review_required']}"
        )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON written to {out_path}")


if __name__ == "__main__":
    main()
