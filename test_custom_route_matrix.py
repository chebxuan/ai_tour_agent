"""
排列组合测试：覆盖 duration × interests × pace × budget × group 的典型组合
检查不同输入是否产出不同路线，重复出现率，评分分布和预算约束
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engines.custom_route_engine import generate_route

# ── 参数网格 ──
DURATIONS  = ["one_day", "half_day"]
INTEREST_SETS = [
    ("culture", "history", "photography"),          # 经典观光
    ("photography", "architecture", "cafe"),         # 拍照打卡
    ("history", "literature", "garden"),             # 文化深度
    ("family", "museum", "interactive"),             # 亲子
    ("street life", "photography", "architecture"),  # 预算街拍
]
PACES  = ["moderate", "relaxed", "fast"]
BUDGETS = ["medium", "low", "flexible"]
GROUPS  = ["couple", "family", "solo", "senior"]

# ── 生成有意义组合（全排列=360太冗余，聚焦差异化路径）──
cases = []
for dur in DURATIONS:
    for ints in INTEREST_SETS:
        for pace in PACES:
            for bud in BUDGETS:
                for grp in GROUPS:
                    # 跳过逻辑矛盾
                    if bud == "low" and dur == "one_day" and pace == "fast":
                        continue  # 低预算全天快节奏 = 矛盾
                    if grp == "senior" and pace == "fast":
                        continue  # 长者快节奏 = 矛盾
                    cases.append((dur, ints, pace, bud, grp))

print(f"运行 {len(cases)} 个场景...\n")

results = []
fingerprints = Counter()

for dur, ints, pace, bud, grp in cases:
    r = generate_route(
        city="上海", duration_type=dur,
        interests=list(ints), pace=pace, budget_level=bud,
        group_type=grp, rainy_day=False, need_private_car=False,
        family_travel=(grp == "family"), elderly_travel=(grp == "senior"),
    )

    uids     = tuple(u["unit_id"] for u in r.get("units", []))
    title    = r.get("title_en", "")
    template = r.get("template_id", "")
    profile  = r.get("target_profile_summary", "").split("'")[1] if "'" in r.get("target_profile_summary","") else "?"
    activity = r.get("activity_min", 0)
    transit  = r.get("transit_min", 0)
    cost     = r.get("estimated_cost_rmb", 0)
    tc       = r.get("template_compliance", {})
    sat_ratio = len(tc.get("satisfied_types",[])) / max(len(tc.get("required_types",[])), 1)

    fingerprints[uids] += 1

    results.append({
        "dur": dur, "ints": ",".join(ints[:3]), "pace": pace, "bud": bud, "grp": grp,
        "profile": profile, "template": template, "title": title[:60],
        "units": len(uids), "uids": uids, "act": activity, "tr": transit,
        "cost": int(cost), "ratio": sat_ratio,
    })

# ── 输出 ──
print(f"{'#':>3} {'Dur':>4} {'Interests':>38s} {'Pace':>7s} {'Bud':>7s} {'Grp':>6s} | {'Pro':>5s} {'Tmpl':>8s} | u A+T=TTL | ¥cost | t%")
print("-" * 140)

for i, r in enumerate(results, 1):
    tag = "⚠️" if r["ratio"] < 0.75 else "  "
    print(f"{i:3d} {r['dur']:>4} {r['ints']:>38s} {r['pace']:7s} {r['bud']:7s} {r['grp']:6s} | {r['profile']:5s} {r['template']:8s} | {r['units']} {r['act']}+{r['tr']}={r['act']+r['tr']} | {r['cost']:>5d} | {r['ratio']:.0%} {tag}")

# ── 统计 ──
print(f"\n{'='*140}")
unique_routes = len(set(fp for fp, cnt in fingerprints.items() if cnt > 0))
duplicate_routes = sum(cnt - 1 for fp, cnt in fingerprints.items() if cnt > 1)
print(f"唯一路线指纹: {unique_routes}  |  重复出现: {duplicate_routes} 次（不同输入产出相同路线）")
print(f"总场景数: {len(results)}")

# 重复详情
print(f"\n🔁 重复路线指纹（出现 >5 次）:")
for fp, cnt in fingerprints.most_common(20):
    if cnt >= 3:
        uids_str = " → ".join(fp[:4])
        examples = [r for r in results if r["uids"] == fp][:3]
        inputs = "; ".join(f"{e['dur'][:2]}|{e['ints'][:25]}|{e['pace'][:2]}|{e['bud'][:2]}|{e['grp'][:2]}" for e in examples)
        print(f"  {cnt:2d}×  {uids_str[:80]}")
        print(f"       inputs: {inputs}")

# 图像匹配分布
profiles = Counter(r["profile"] for r in results)
print(f"\n📊 画像分布: {profiles.most_common()}")

# 模板分布
templates = Counter(r["template"] for r in results)
print(f"📊 模板分布: {templates.most_common()}")

# 预算约束
low_budget = [r for r in results if r["bud"] == "low"]
over_budget = [r for r in low_budget if r["cost"] > 50]
print(f"\n💰 低预算超支: {len(over_budget)}/{len(low_budget)} (>{50})" + ("" if not over_budget else f" — max={max(r['cost'] for r in over_budget)}"))

# 成本分布
for bud in ["low", "medium", "flexible"]:
    costs = [r["cost"] for r in results if r["bud"] == bud]
    if costs:
        print(f"  {bud}: cost range ¥{min(costs)}-¥{max(costs)}, avg ¥{sum(costs)//len(costs)}")
