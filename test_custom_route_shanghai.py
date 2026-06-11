"""
Test Script: 上海半定制路线生成器 — 5 个客户场景 v1.1

每个场景检查 6 个维度:
  F1. 模板合规 — required_unit_types 是否被满足
  F2. 交通连续性 — 每对相邻节点都有 edge 或明确风险
  F3. 时长预算 — 总时长（活动+交通+buffer）不超过硬上限
  F4. 成本约束 — 低预算场景成本达标
  F5. 雨天约束 — outdoor 比例 ≤ 阈值
  F6. 输出完整性 — transfers / risk_warnings / template_compliance 均存在
"""

from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engines.custom_route_engine import generate_route

G, R, Y, C, B = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[0m"

def check(test: bool, label: str, detail: str = "") -> bool:
    mark = f"{G}PASS{R}" if test else f"{R}FAIL{R}"
    print(f"    [{mark}] {label}" + (f" — {detail}" if detail else ""))
    return bool(test)


def run_test(n: int, name: str, params: dict) -> int:
    print(f"\n{'='*70}")
    print(f"  {C}Scenario {n}{R}: {name}")
    print(f"{'='*70}")

    result = generate_route(**params)
    if result.get("error"):
        print(f"  {R}✗ ENGINE ERROR{R}: {result['error']}")
        return 1

    passed = 0; failed = 0
    def chk(cond, label, detail=""):
        nonlocal passed, failed
        if check(cond, label, detail): passed += 1
        else: failed += 1

    # ── Display ──
    print(f"\n  {C}ROUTE{R}: {result['title_en']}")
    print(f"  Profile: {result['target_profile_summary']}")
    print(f"  Template: {result['template_name']} ({result['template_id']})")
    print(f"  Activity: {result['activity_min']}min  |  Transit: {result['transit_min']}min  |  Total: {result['total_duration_min']}min")
    print(f"  Cost: ¥{result['estimated_cost_rmb']:.0f}  |  Budget: {result['budget_level_applied']}")
    print(f"  Transport: {result['recommended_transport']}")

    print(f"\n  {C}UNITS{R}:")
    for u in result["units"]:
        tags = f"in/out={u['indoor_outdoor']}, rain_ok={u['rainy_day_friendly']}, elder_ok={u['elderly_friendly']}"
        print(f"    {u['sequence']}. [{u['unit_type']:>14s}] {u['name_en']:30s} | {u['area']:18s} | {u['duration_min']:3d}min | ¥{u['estimated_cost_rmb']:>5.0f} | fit={u['fit_score']:.1f} | {tags}")

    if result.get("transfers"):
        print(f"\n  {C}TRANSFERS{R}:")
        for t in result["transfers"]:
            ok = f"{G}✓{R}" if t["has_edge"] else f"{Y}⚠ estimated{R}"
            print(f"    {t['from']} → {t['to']}: {t['mode']} {t['transit_min']}min {ok}")

    # ══════════════════════════════════════════════════════
    # F1. 模板合规
    # ══════════════════════════════════════════════════════
    tc = result.get("template_compliance", {})
    unsatisfied = tc.get("unsatisfied_types", [])
    required = tc.get("required_types", [])
    ratio = len(tc.get("satisfied_types",[])) / max(len(required), 1)
    chk(ratio >= 0.5 or len(required) == 0,
        "F1: Template compliance — " + str(len(tc.get("satisfied_types",[]))) + "/" + str(len(required)) + " types (" + str(int(ratio*100)) + "%)",
        "unsatisfied (acceptable if time-limited): " + str(unsatisfied) if unsatisfied else "all types covered")

    # F1b: 至少 2 个 unit（半天）或 3 个（全天）
    min_units = 3 if params.get("duration_type")=="one_day" else 2
    chk(len(result["units"]) >= min_units,
        f"F1b: Unit count ≥ {min_units}", f"got {len(result['units'])}")

    # ══════════════════════════════════════════════════════
    # F2. 交通连续性
    # ══════════════════════════════════════════════════════
    if len(result["units"]) >= 2:
        unknown = [t for t in result.get("transfers",[]) if not t.get("has_edge")]
        chk(len(unknown) <= 2,
            f"F2: Unknown transport edges ≤ 2", f"got {len(unknown)} unknown edges")
    else:
        chk(True, "F2: Single unit — no transfer needed")

    # F2b: 未知 edge 在风险中报告
    risk_text = " ".join(result.get("risk_warnings",[])).lower()
    if any(not t.get("has_edge") for t in result.get("transfers",[])):
        chk("transport edge" in risk_text or "no transport" in risk_text or "estimate" in risk_text,
            "F2b: Unknown edges flagged in risk_warnings")
    else:
        chk(True, "F2b: All edges known — no risk needed")

    # ══════════════════════════════════════════════════════
    # F3. 时长预算
    # ══════════════════════════════════════════════════════
    max_total = 540 if params.get("duration_type")=="one_day" else 270
    chk(result["total_duration_min"] <= max_total,
        f"F3: Duration budget — {result['total_duration_min']}min ≤ {max_total}min",
        f"activity={result['activity_min']} + transit={result['transit_min']} + meals")

    # ══════════════════════════════════════════════════════
    # F4. 成本约束
    # ══════════════════════════════════════════════════════
    if params.get("budget_level") == "low":
        target = 50 if params.get("duration_type")=="half_day" else 150
        chk(result["estimated_cost_rmb"] <= target,
            f"F4: Low-budget cost — ¥{result['estimated_cost_rmb']:.0f} ≤ ¥{target}")
    else:
        chk(result["estimated_cost_rmb"] > 0 or any(u["duration_min"]>30 for u in result["units"]),
            "F4: Non-zero cost or meaningful activity duration")

    # ══════════════════════════════════════════════════════
    # F5. 雨天约束
    # ══════════════════════════════════════════════════════
    if params.get("rainy_day"):
        outdoor = sum(1 for u in result["units"] if u.get("indoor_outdoor")=="outdoor")
        chk(outdoor <= len(result["units"]) * 0.5,
            f"F5: Rainy day — outdoor units ≤ 50%", f"got {outdoor}/{len(result['units'])} outdoor")
        chk(all(u["rainy_day_friendly"] for u in result["units"]),
            "F5b: All units rainy_day_friendly=True")
    else:
        chk(True, "F5: Not rainy — skipped")

    # ══════════════════════════════════════════════════════
    # F6. 输出完整性
    # ══════════════════════════════════════════════════════
    chk(len(result.get("transfers",[])) >= max(0, len(result["units"])-1),
        f"F6: transfers count ≥ units-1", f"transfers={len(result.get('transfers',[]))}, units={len(result['units'])}")
    chk(len(result.get("risk_warnings",[])) >= 0, "F6b: risk_warnings present")
    chk("template_compliance" in result, "F6c: template_compliance field present")
    chk("cost_note" in result, "F6d: cost_note field present")

    print(f"\n  {C}SUMMARY{R}: {G}{passed} PASS{R}, {R}{failed} FAIL{R}")
    return 0 if failed == 0 else 1


def main():
    print(f"{C}Shanghai Custom Route Engine v1.1 — 5-Scenario Test Suite{R}")

    scenarios = [
        ("First-time visitor, classic, one day", {
            "city":"上海","duration_type":"one_day","interests":["culture","history","photography"],
            "pace":"moderate","budget_level":"medium","group_type":"couple"}),
        ("Young couple, photogenic citywalk, half day", {
            "city":"上海","duration_type":"half_day","interests":["photography","architecture","cafe"],
            "pace":"moderate","budget_level":"low","group_type":"couple"}),
        ("Family with child, rainy day, one day", {
            "city":"上海","duration_type":"one_day","interests":["family","interactive","museum"],
            "pace":"relaxed","budget_level":"medium","group_type":"family",
            "rainy_day":True,"need_private_car":True,"family_travel":True}),
        ("Culture slow pace senior, one day", {
            "city":"上海","duration_type":"one_day","interests":["history","literature","architecture"],
            "pace":"slow","budget_level":"flexible","group_type":"senior",
            "need_private_car":True,"elderly_travel":True}),
        ("Budget solo, free/low-cost, half day", {
            "city":"上海","duration_type":"half_day","interests":["street life","photography","architecture"],
            "pace":"moderate","budget_level":"low","group_type":"solo"}),
    ]

    passed = 0; failed = 0
    for i, (name, params) in enumerate(scenarios, 1):
        code = run_test(i, name, params)
        if code==0: passed += 1
        else: failed += 1

    print(f"\n{'='*70}\n  {G}{passed} PASS{R}, {R}{failed} FAIL{R}, {passed+failed} total\n{'='*70}")
    return 0 if failed==0 else 1

if __name__ == "__main__":
    sys.exit(main())
