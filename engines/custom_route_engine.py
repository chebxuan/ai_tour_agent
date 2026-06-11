"""
Custom Route Engine — 上海 MVP 半定制路线生成引擎 v1.1

职责：
  1. 加载上海体验单元库 / 交通关系表 / 客户画像 / 路线模板
  2. 根据客户需求 → 画像匹配 → 标签打分 → 模板约束 → 交通检查 → 输出 RoutePlanJSON

修复（v1.0 → v1.1）：
  - 模板 required_unit_types 真正参与编排（支持 unit_type + primary_tags 双匹配）
  - 所有相邻节点查交通 edge，计入 transit_min
  - budget_level / pace 在画像匹配和打分中生效
  - 低预算路线设置硬成本上限
  - 输出 transfers 数组、indoor_outdoor/rainy_day_friendly 字段
  - cost_item_code 已入 CSV；API 层可据此部分接入 cost_engine，engine 层仍保留体验单元估算价
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
CUSTOM_DIR = ROOT / "data" / "custom"

UNITS_CSV = CUSTOM_DIR / "shanghai_experience_units.csv"
EDGES_CSV = CUSTOM_DIR / "shanghai_transport_edges.csv"
TAGS_CSV = CUSTOM_DIR / "customer_profile_tags.csv"
TEMPLATES_JSON = CUSTOM_DIR / "shanghai_route_templates.json"


# ============================================================
# Data classes
# ============================================================

@dataclass
class ExperienceUnit:
    unit_id: str
    city: str
    area: str
    name_cn: str
    name_en: str
    unit_type: str
    primary_tags: List[str] = field(default_factory=list)
    secondary_tags: List[str] = field(default_factory=list)
    suitable_for: List[str] = field(default_factory=list)
    avoid_for: List[str] = field(default_factory=list)
    duration_min: int = 0
    opening_hours: str = ""
    best_time_slot: str = ""
    indoor_outdoor: str = "outdoor"
    rainy_day_friendly: bool = False
    family_friendly: bool = True
    elderly_friendly: bool = True
    booking_required: bool = False
    estimated_cost_rmb: float = 0.0
    cost_item_code: str = ""        # ← 将来接入 cost_engine 用
    supplier_needed: bool = False
    supplier_type: str = ""
    monetization_type: str = ""
    social_heat_score: int = 0
    source_note: str = ""
    operational_risk: str = ""
    description_en: str = ""
    host_story_en: str = ""
    fit_score: float = 0.0
    score_reasons: List[str] = field(default_factory=list)


@dataclass
class TransportEdge:
    from_unit_id: str
    from_area: str
    to_unit_id: str
    to_area: str
    distance_km: float = 0.0
    walk_min: int = 0
    taxi_min: int = 0
    metro_min: int = 0
    recommended_mode: str = ""
    transfer_difficulty: str = "Low"
    elderly_friendly: bool = True
    rainy_day_risk: str = "LOW"
    notes: str = ""


@dataclass
class CustomerProfile:
    tag_id: str
    tag_name: str
    description: str
    positive_unit_tags: List[str] = field(default_factory=list)
    negative_unit_tags: List[str] = field(default_factory=list)
    pacing_preference: str = "moderate"
    budget_preference: str = "medium"
    commercial_note: str = ""


@dataclass
class RouteTemplate:
    template_id: str
    template_name: str
    duration_type: str
    target_profile_tags: List[str] = field(default_factory=list)
    required_unit_types: List[str] = field(default_factory=list)
    preferred_areas: List[str] = field(default_factory=list)
    pacing_rule: str = ""
    commercial_rule: str = ""
    route_story_angle: str = ""


# ============================================================
# Safe parsing helpers
# ============================================================

def safe_int(val: str, default: int = 0) -> int:
    if not val or val.strip().upper() == "N/A":
        return default
    try: return int(val)
    except (ValueError, TypeError): return default

def safe_float(val: str, default: float = 0.0) -> float:
    if not val or val.strip().upper() == "N/A":
        return default
    try: return float(val)
    except (ValueError, TypeError): return default

def parse_csv_tags(raw: str) -> List[str]:
    if not raw: return []
    raw = raw.strip().strip('"')
    return [t.strip() for t in raw.split(",") if t.strip()]

def _parse_bool(val: str) -> bool:
    return val.strip().upper() == "TRUE"


# ============================================================
# I/O
# ============================================================

def load_experience_units(city: str = "上海") -> List[ExperienceUnit]:
    units: List[ExperienceUnit] = []
    with open(UNITS_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("city", "") != city: continue
            units.append(ExperienceUnit(
                unit_id=row.get("unit_id",""),
                city=row.get("city",""),
                area=row.get("area",""),
                name_cn=row.get("name_cn",""),
                name_en=row.get("name_en",""),
                unit_type=row.get("unit_type",""),
                primary_tags=parse_csv_tags(row.get("primary_tags","")),
                secondary_tags=parse_csv_tags(row.get("secondary_tags","")),
                suitable_for=parse_csv_tags(row.get("suitable_for","")),
                avoid_for=parse_csv_tags(row.get("avoid_for","")),
                duration_min=safe_int(row.get("duration_min","0")),
                opening_hours=row.get("opening_hours",""),
                best_time_slot=row.get("best_time_slot",""),
                indoor_outdoor=row.get("indoor_outdoor","outdoor"),
                rainy_day_friendly=_parse_bool(row.get("rainy_day_friendly","FALSE")),
                family_friendly=_parse_bool(row.get("family_friendly","TRUE")),
                elderly_friendly=_parse_bool(row.get("elderly_friendly","TRUE")),
                booking_required=_parse_bool(row.get("booking_required","FALSE")),
                estimated_cost_rmb=safe_float(row.get("estimated_cost_rmb","0")),
                cost_item_code=row.get("cost_item_code","").strip(),
                supplier_needed=row.get("supplier_needed","No").strip().lower()=="yes",
                supplier_type=row.get("supplier_type",""),
                monetization_type=row.get("monetization_type",""),
                social_heat_score=safe_int(row.get("social_heat_score","0")),
                source_note=row.get("source_note",""),
                operational_risk=row.get("operational_risk",""),
                description_en=row.get("description_en",""),
                host_story_en=row.get("host_story_en",""),
            ))
    return units

def load_transport_edges() -> List[TransportEdge]:
    edges: List[TransportEdge] = []
    with open(EDGES_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            edges.append(TransportEdge(
                from_unit_id=row.get("from_unit_id",""),
                from_area=row.get("from_area",""),
                to_unit_id=row.get("to_unit_id",""),
                to_area=row.get("to_area",""),
                distance_km=safe_float(row.get("distance_km","0")),
                walk_min=safe_int(row.get("walk_min","0")),
                taxi_min=safe_int(row.get("taxi_min","0")),
                metro_min=safe_int(row.get("metro_min","0")),
                recommended_mode=row.get("recommended_mode",""),
                transfer_difficulty=row.get("transfer_difficulty","Low"),
                elderly_friendly=_parse_bool(row.get("elderly_friendly","TRUE")),
                rainy_day_risk=row.get("rainy_day_risk","LOW"),
                notes=row.get("notes",""),
            ))
    return edges

def load_customer_profiles() -> List[CustomerProfile]:
    profiles: List[CustomerProfile] = []
    with open(TAGS_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            profiles.append(CustomerProfile(
                tag_id=row.get("tag_id",""),
                tag_name=row.get("tag_name",""),
                description=row.get("description",""),
                positive_unit_tags=parse_csv_tags(row.get("positive_unit_tags","")),
                negative_unit_tags=parse_csv_tags(row.get("negative_unit_tags","")),
                pacing_preference=row.get("pacing_preference","moderate"),
                budget_preference=row.get("budget_preference","medium"),
                commercial_note=row.get("commercial_note",""),
            ))
    return profiles

def load_route_templates() -> List[RouteTemplate]:
    data = json.loads(TEMPLATES_JSON.read_text(encoding="utf-8"))
    return [RouteTemplate(
        template_id=i.get("template_id",""),
        template_name=i.get("template_name",""),
        duration_type=i.get("duration_type",""),
        target_profile_tags=i.get("target_profile_tags",[]),
        required_unit_types=i.get("required_unit_types",[]),
        preferred_areas=i.get("preferred_areas",[]),
        pacing_rule=i.get("pacing_rule",""),
        commercial_rule=i.get("commercial_rule",""),
        route_story_angle=i.get("route_story_angle",""),
    ) for i in data.get("templates",[])]


# ============================================================
# Unified type matching — 支持 unit_type + primary_tags 双匹配
# ============================================================

def _unit_matches_type(unit: ExperienceUnit, type_name: str) -> bool:
    """判断一个体验单元是否匹配模板要求的某个类型。
    匹配逻辑：
      - 直接匹配 unit_type（大小写不敏感）
      - 匹配 primary_tags 中的任意标签（大小写不敏感）
      - 匹配 secondary_tags 中的任意标签
    这使得模板可以写 "museum"、"city_walk"、"cafe" 等非 unit_type 的值，
    只要单元的 primary_tags 中包含对应关键词即可。
    """
    tl = type_name.lower()
    if unit.unit_type.lower() == tl: return True
    for t in unit.primary_tags:
        if tl in t.lower() or t.lower() == tl: return True
    for t in unit.secondary_tags:
        if tl in t.lower() or t.lower() == tl: return True
    return False


# ============================================================
# Profile matching — 加入 budget_level 强制路由
# ============================================================

def match_profile_to_tag(profiles: List[CustomerProfile],
                         interests: List[str],
                         pace: str,
                         budget_level: str,
                         group_type: str) -> Tuple[CustomerProfile, float]:
    """根据客户兴趣/节奏/预算/人群匹配最佳画像。
    budget_level='low' 时强制加权 TAG-08（Budget-conscious）。
    经典通用兴趣（culture/history/photography）向 TAG-01（First-timer）倾斜。"""
    best_profile = profiles[0]
    best_score = -999.0

    # 判断是否是"经典通用"兴趣
    classic_interests = {"culture", "history", "photography", "sightseeing", "iconic", "landmark", "cityscape"}
    niche_interests = {"cafe", "vintage", "art_gallery", "concept_store", "speakeasy",
                       "street_food", "nightlife", "wellness", "cycling", "literature"}
    is_classic_profile = any(i.lower() in classic_interests for i in interests) and \
                         not any(i.lower() in niche_interests for i in interests)

    for profile in profiles:
        score = 0.0

        # 经典通用 → TAG-01 加分
        if is_classic_profile and profile.tag_id == "TAG-01":
            score += 0.6

        # 兴趣关键词匹配
        profile_text = (profile.tag_name + " " + profile.description).lower()
        for interest in interests:
            if interest.lower() in profile_text:
                score += 0.3

        # 节奏匹配
        if pace == profile.pacing_preference:
            score += 0.2

        # 人群类型匹配
        if group_type.lower() in profile.tag_name.lower():
            score += 0.25

        # 预算匹配 — 强制路由
        if budget_level == "low" and profile.tag_id == "TAG-08":
            score += 0.8   # 强力加权
        elif budget_level == "low" and profile.budget_preference == "low":
            score += 0.3
        elif budget_level == "medium" and profile.budget_preference in ("medium","flexible"):
            score += 0.15

        # 正向标签命中
        pos_hits = sum(1 for tag in profile.positive_unit_tags
                       if any(i.lower() in tag.lower() for i in interests))
        score += pos_hits * 0.1

        if score > best_score:
            best_score = score
            best_profile = profile

    return best_profile, best_score


# ============================================================
# Unit scoring — 预算硬约束
# ============================================================

def score_unit(unit: ExperienceUnit, profile: CustomerProfile,
               interests: List[str], pace: str, budget_level: str,
               group_type: str, rainy_day: bool,
               family_travel: bool, elderly_travel: bool) -> float:
    """计算体验单元匹配度。高区分度版本：
      - 标签匹配 ×0.35/hit（强信号）
      - 兴趣关键词直击 primary_tags（+0.5/hit）
      - group_type 匹配 suitable_for/avoid_for（±0.4）
      - pace 影响时长偏好
    """
    score = 0.0
    reasons: List[str] = []

    # ── 1. 兴趣直击（最强信号）──
    all_tags_lower = set(t.lower() for t in unit.primary_tags + unit.secondary_tags)
    for kw in interests:
        kw_lower = kw.lower()
        # 精确包含匹配
        for tag in all_tags_lower:
            if kw_lower in tag or tag in kw_lower:
                score += 0.45
                reasons.append(f"interest:{kw}≈{tag}")
                break

    # ── 2. 画像标签匹配 ──
    all_tags = set(unit.primary_tags + unit.secondary_tags)
    positive = set(profile.positive_unit_tags)
    negative = set(profile.negative_unit_tags)
    pos_hits = all_tags & positive
    neg_hits = all_tags & negative
    if pos_hits:
        score += len(pos_hits) * 0.30
        reasons.append(f"+tags:{','.join(sorted(pos_hits)[:3])}")
    if neg_hits:
        score -= len(neg_hits) * 0.25
        reasons.append(f"-tags:{','.join(sorted(neg_hits)[:2])}")

    # ── 3. 社交热度 ──
    score += unit.social_heat_score * 0.04

    # ── 4. 氛围适配 ──
    # group_type 匹配 suitable_for / avoid_for
    suitable_lower = [s.strip().lower() for s in unit.suitable_for]
    avoid_lower = [s.strip().lower() for s in unit.avoid_for]
    grp_lower = group_type.lower()
    grp_map = {"couple": "couple", "family": "family", "solo": "solo", "senior": "senior",
               "solo": "独自旅行", "senior": "长者"}

    if any(grp_lower in s or s in grp_lower for s in suitable_lower):
        score += 0.3; reasons.append(f"suits:{group_type}")
    if any(grp_lower in a or a in grp_lower for a in avoid_lower):
        score -= 0.35; reasons.append(f"avoids:{group_type}")

    # 特殊人群：长者慢行过滤
    if group_type == "senior":
        if not unit.elderly_friendly:
            score -= 0.5
        if unit.duration_min > 150:
            score -= 0.2
    if group_type == "family" and unit.family_friendly:
        score += 0.15

    # ── 5. 天气 ──
    if rainy_day:
        if unit.rainy_day_friendly: score += 0.3; reasons.append("rainy_ok")
        else: score -= 0.35; reasons.append("rainy_bad")

    # ── 6. 基础人群适配 ──
    if family_travel:
        if unit.family_friendly: score += 0.12
        else: score -= 0.3
    if elderly_travel:
        if unit.elderly_friendly: score += 0.12
        else: score -= 0.3

    # ── 7. 节奏偏好 ──
    if pace == "slow":
        if unit.duration_min > 120: score -= 0.15; reasons.append("too_long_slow")
        if unit.duration_min <= 60: score += 0.15; reasons.append("short_works_slow")
    elif pace == "fast":
        if unit.duration_min <= 30: score += 0.12
        if unit.duration_min > 180: score -= 0.15; reasons.append("too_long_fast")

    # ── 8. 预算 ──
    if budget_level == "low":
        if unit.estimated_cost_rmb == 0:
            score += 0.35; reasons.append("free")
        elif unit.estimated_cost_rmb <= 50:
            score += 0.10
        else:
            score -= 0.45; reasons.append("expensive_for_budget")

    # ── 9. 运营风险 ──
    if unit.operational_risk and unit.operational_risk.lower() not in ("none",""):
        score -= 0.1

    unit.fit_score = round(max(0.0, score), 2)
    unit.score_reasons = reasons
    return unit.fit_score


# ============================================================
# Scoring + filtering pipeline
# ============================================================

def filter_and_rank(units: List[ExperienceUnit], profile: CustomerProfile,
                    duration_type: str, interests: List[str], pace: str,
                    budget_level: str, group_type: str,
                    rainy_day: bool, family_travel: bool, elderly_travel: bool) -> List[ExperienceUnit]:
    max_total_min = 480 if duration_type == "one_day" else 240
    for unit in units:
        score_unit(unit, profile, interests, pace, budget_level, group_type, rainy_day, family_travel, elderly_travel)
        if unit.duration_min > max_total_min:
            unit.fit_score = 0.0
            unit.score_reasons.append("duration_exceeds_limit")
    return sorted(units, key=lambda u: u.fit_score, reverse=True)


# ============================================================
# Transport helpers
# ============================================================

def find_edge(edges: List[TransportEdge], a: str, b: str) -> Optional[TransportEdge]:
    for e in edges:
        if (e.from_unit_id==a and e.to_unit_id==b) or (e.from_unit_id==b and e.to_unit_id==a):
            return e
    return None

def estimate_transit_min(edge: Optional[TransportEdge], need_private_car: bool) -> int:
    """根据 edge 和用车情况估算交通耗时"""
    if not edge:
        return 25  # 默认 25min（未知 edge 的保守估计）
    if need_private_car or edge.recommended_mode.upper().startswith("TAXI") or edge.recommended_mode.upper().startswith("CAR"):
        return edge.taxi_min or max(edge.walk_min, 10)
    if edge.walk_min <= 25:
        return edge.walk_min
    return edge.taxi_min or edge.metro_min or edge.walk_min


# ============================================================
# Route Plan Builder — 核心编排
# ============================================================

def select_route_units(
    ranked_units: List[ExperienceUnit],
    template: RouteTemplate,
    edges: List[TransportEdge],
    profile: CustomerProfile,
    duration_type: str,
    budget_level: str,
    group_type: str,
    rainy_day: bool,
    need_private_car: bool,
    elderly_travel: bool,
) -> Tuple[List[ExperienceUnit], List[Dict], List[str]]:
    """按模板+人群规则选择路线节点。v1.2: group-aware fill"""
    if duration_type == "one_day": base_min = 480
    else: base_min = 240
    if profile.pacing_preference == "slow": base_min = int(base_min * 0.75)
    meal_buffer = 90 if duration_type == "one_day" else 60
    max_activity_min = base_min - meal_buffer
    max_transit_min = 90 if duration_type == "one_day" else 45
    max_cost = 99999
    if budget_level == "low" and duration_type == "half_day": max_cost = 50
    elif budget_level == "low": max_cost = 150

    selected, selected_ids, transfers = [], set(), []
    total_activity, total_transit, total_cost = 0, 0, 0.0
    satisfied_types: set = set()
    logic: List[str] = []
    preferred_areas = template.preferred_areas or []
    required_types = template.required_unit_types or []

    def _fits(u): return (u.fit_score > 0.05 and u.unit_id not in selected_ids
                          and total_activity + u.duration_min <= max_activity_min
                          and total_cost + u.estimated_cost_rmb <= max_cost)
    def _add(u, edge, reason):
        nonlocal total_activity, total_cost, total_transit
        transit_add = estimate_transit_min(edge, need_private_car)
        selected.append(u); selected_ids.add(u.unit_id)
        total_activity += u.duration_min; total_cost += u.estimated_cost_rmb
        total_transit += transit_add
        satisfied_types.update(rt for rt in required_types if _unit_matches_type(u, rt))
        # 只记录有前一个单元的 transfer（锚点不产生 transfer）
        if len(selected) >= 2:
            prev = selected[-2]
            transfers.append({"from": prev.unit_id, "to": u.unit_id,
                "from_area": prev.area, "to_area": u.area,
                "mode": edge.recommended_mode if edge else "unknown",
                "transit_min": transit_add, "has_edge": edge is not None,
                "risk": "No edge data — estimated 25min" if not edge else (edge.notes or "")})
        logic.append(reason)

    # ── Rule 1: Pick anchor ──
    anchor_keywords = ["sightseeing", "garden", "architecture", "museum", "temple"]
    anchor_type = None
    for kw in anchor_keywords:
        for rt in required_types:
            if kw in rt.lower(): anchor_type = rt; break
        if anchor_type: break
    if not anchor_type and required_types: anchor_type = required_types[0]

    anchor = None
    for u in ranked_units:
        if not _fits(u): continue
        area_ok = any(pa in u.area for pa in preferred_areas) if preferred_areas else True
        if area_ok and (not anchor_type or _unit_matches_type(u, anchor_type)):
            anchor = u; break
    if not anchor:
        for u in ranked_units:
            if not _fits(u): continue
            if u.unit_type == "sightseeing": anchor = u; break
    if anchor:
        _add(anchor, None, f"Anchor: {anchor.name_en} ({anchor.area}, fit={anchor.fit_score})")

    # ── Rule 2: Group-aware fill ──
    grp_fills = {
        "couple": ["photo_spot","dining","free_experience","activity"],
        "family": ["activity","free_experience","dining","photo_spot"],
        "solo":   ["free_experience","photo_spot","dining","activity"],
        "senior": ["free_experience","dining","photo_spot","activity"],
    }
    fills = grp_fills.get(group_type, ["photo_spot","free_experience","dining"])
    max_units = 4 if duration_type=="one_day" else 3
    for ft in fills:
        if len(selected) >= max_units: break
        for u in ranked_units:
            if not _fits(u): continue
            if _unit_matches_type(u, ft):
                prev = selected[-1]
                e = find_edge(edges, prev.unit_id, u.unit_id)
                tb = estimate_transit_min(e, need_private_car)
                if total_transit + tb <= max_transit_min:
                    _add(u, e, f"Add[{group_type}]: {u.name_en} ({u.unit_type}, {u.area}, +{tb}min)")
                break

    # ── Rule 3: Dining for one_day ──
    if duration_type == "one_day" and len(selected) < max_units:
        for u in ranked_units:
            if not _fits(u): continue
            if _unit_matches_type(u, "dining") or u.unit_type=="dining":
                prev = selected[-1]
                e = find_edge(edges, prev.unit_id, u.unit_id)
                tb = estimate_transit_min(e, need_private_car)
                if total_transit + tb <= max_transit_min:
                    _add(u, e, f"Dining: {u.name_en} ({u.best_time_slot}, Y{u.estimated_cost_rmb})")
                    break

    # ── Rule 4: Floor-fill to minimum unit count ──
    min_units = 3 if duration_type=="one_day" else 2
    while len(selected) < min_units:
        best, best_edge, best_tb, best_score = None, None, 0, -99
        for u in ranked_units:
            if not _fits(u): continue
            area_bonus = 0.5 if u.area in {x.area for x in selected} else 0
            s = u.fit_score + area_bonus
            if s > best_score:
                prev = selected[-1]
                e = find_edge(edges, prev.unit_id, u.unit_id)
                tb = estimate_transit_min(e, need_private_car)
                if total_transit + tb <= max_transit_min:
                    best_score, best, best_edge, best_tb = s, u, e, tb
        if best is None: break
        _add(best, best_edge, f"Floor: {best.name_en} ({best.unit_type}, {best.area}, +{best_tb}min)")

    # ── Rule 5: Rain filter ──
    if rainy_day:
        before = len(selected)
        selected = [u for u in selected if u.rainy_day_friendly]
        kept_ids = {u.unit_id for u in selected}
        transfers = [t for t in transfers if t.get("from","") in kept_ids and t["to"] in kept_ids]
        logic.append(f"Rain: {len(selected)}/{before} units kept")

    # ── Rule 6: Elderly-slow filter ──
    if elderly_travel and profile.pacing_preference=="slow":
        before = len(selected)
        selected = [u for u in selected if u.elderly_friendly and u.duration_min <= 150]
        logic.append(f"Elderly-slow: {len(selected)}/{before} units")

    for t in transfers: t["total_transit_so_far"] = total_transit

    # ── 辅助点规则: 这类 POI 不能独立成线，必须搭配锚点 ──
    SUPPLEMENTARY_IDS = {"SH-012", "SH-032", "SH-023", "SH-014", "SH-031", "SH-019"}
    # 检查: 如果 selected 中仅含辅助点 + photo_spot + free_experience，缺少 sightseeing/activity
    has_anchor = any(u.unit_type in ("sightseeing","activity") and u.unit_id not in SUPPLEMENTARY_IDS for u in selected)
    supp_only = all(u.unit_id in SUPPLEMENTARY_IDS for u in selected) if selected else False
    if not has_anchor and len(selected) > 0:
        logic.append("⚠️ Route composed of supplementary-only POIs — adding anchor enforcement")
        # 强制替换最后一个辅助点为高优先级锚点
        for u in ranked_units:
            if u.fit_score <= 0.1: continue
            if u.unit_id in selected_ids: continue
            if u.unit_type == "sightseeing" and u.unit_id not in SUPPLEMENTARY_IDS:
                if total_activity - selected[-1].duration_min + u.duration_min <= max_activity_min:
                    logic.append(f"Suppl→Anchor swap: {selected[-1].name_en} → {u.name_en}")
                    selected[-1] = u
                    break

    # ── 模板硬性业务规则 ──
    # 1. 首次客 (SH-TPL-01/02/03) 必须有经典上海锚点 (Bund/Yu Garden/Oriental Pearl/Shanghai Museum)
    CLASSIC_IDS = {"SH-001", "SH-005", "SH-002", "SH-018", "SH-003"}
    if template.template_id in ("SH-TPL-01", "SH-TPL-03") and not any(u.unit_id in CLASSIC_IDS for u in selected):
        logic.append("⚠️ First-timer template without classic anchor — injecting Bund")
        for u in ranked_units:
            if u.unit_id in CLASSIC_IDS and u.unit_id not in selected_ids:
                if total_activity + u.duration_min <= max_activity_min:
                    _add(u, find_edge(edges, selected[-1].unit_id, u.unit_id) if selected else None,
                         f"First-timer rule: +{u.name_en}")
                    break

    # 2. 浪漫夜 (SH-TPL-06) 至少 1 night_view + 1 dining + 1 nightlife
    if template.template_id == "SH-TPL-06":
        night_count = sum(1 for u in selected if "Night View" in (u.primary_tags or []) or "Nightlife" in (u.primary_tags or []) or u.best_time_slot == "evening")
        dine_count = sum(1 for u in selected if u.unit_type == "dining")
        if dine_count == 0:
            for u in ranked_units:
                if u.unit_type == "dining" and u.unit_id not in selected_ids:
                    if total_activity + u.duration_min <= max_activity_min:
                        _add(u, find_edge(edges, selected[-1].unit_id, u.unit_id), f"Romantic dining rule: +{u.name_en}")
                        break
        if night_count == 0:
            logic.append("⚠️ Romantic template missing night activity")

    # 3. 预算半日 (SH-TPL-05) ≥2 units
    if template.template_id == "SH-TPL-05" and len(selected) < 2:
        logic.append(f"Budget rule: min 2 units required, currently {len(selected)}")

    return selected, transfers, logic


def assess_risks(units: List[ExperienceUnit], transfers: List[Dict], profile: CustomerProfile,
                 budget_level: str, rainy_day: bool, duration_type: str,
                 need_private_car: bool, elderly_travel: bool) -> List[str]:
    risks: List[str] = []
    total_cost = sum(u.estimated_cost_rmb for u in units)
    total_activity = sum(u.duration_min for u in units)
    total_transit = sum(t.get("transit_min", 0) for t in transfers)

    # 交通 — 未知 edge
    unknown_edges = [t for t in transfers if not t.get("has_edge")]
    if unknown_edges:
        pairs = [f"{t['from']}→{t['to']}" for t in unknown_edges]
        risks.append(f"No transport edge data for: {', '.join(pairs)}—transit times are estimates. Verify manually.")

    # 高难度交通
    hard_transfers = [t for t in transfers if t.get("risk") and "high" in t.get("risk","").lower()]
    if hard_transfers:
        risks.append(f"High-difficulty transfers detected—confirm with client or arrange private car.")

    # 超时
    total_min = total_activity + total_transit + (90 if duration_type=="one_day" else 60)
    max_ok = 540 if duration_type=="one_day" else 270
    if total_min > max_ok:
        risks.append(f"Total route time ~{total_min}min may exceed limit ({max_ok}min)—consider dropping 1 unit.")

    # 低预算超支
    if budget_level == "low" and total_cost > 50:
        risks.append(f"Estimated cost ¥{total_cost:.0f} exceeds low-budget target (≤¥50).")

    # 雨天户外
    if rainy_day:
        outdoor_count = sum(1 for u in units if u.indoor_outdoor == "outdoor")
        if outdoor_count > 0:
            risks.append(f"{outdoor_count} outdoor unit(s) in rainy route—provide umbrella or indoor alternatives.")

    # 老人
    if elderly_travel:
        not_friendly = [u.name_en for u in units if not u.elderly_friendly]
        if not_friendly:
            risks.append(f"Units not elderly-friendly: {', '.join(not_friendly)}—confirm client mobility.")

    # 需预约
    booking_units = [u.name_en for u in units if u.booking_required]
    if booking_units:
        risks.append(f"Booking required: {', '.join(booking_units)}—confirm availability before committing.")

    # 运营风险
    for u in units:
        if u.operational_risk and u.operational_risk.lower() not in ("none",""):
            risks.append(f"{u.name_en}: {u.operational_risk}")

    return risks


def generate_customization_options(units: List[ExperienceUnit],
                                    template: RouteTemplate) -> List[Dict[str, str]]:
    options: List[Dict[str, str]] = []
    if template.duration_type == "one_day":
        options.append({"type":"add_dinner","description":"Add Bund-view dinner (¥200-500/p)","cost_impact":"+¥200-500/p"})
    options.append({"type":"add_guide","description":"Add English-speaking guide (¥1200-1500/day)","cost_impact":"+¥1200-1500/group"})
    if not any(u.unit_type=="activity" for u in units):
        options.append({"type":"add_cruise","description":"Huangpu River night cruise (¥286/p)","cost_impact":"+¥286/p"})
    return options


# ============================================================
# Main Entry Point
# ============================================================

def generate_route(
    city: str = "上海",
    duration_type: str = "one_day",
    interests: Optional[List[str]] = None,
    travel_style: Optional[List[str]] = None,
    pace: str = "moderate",
    budget_level: str = "medium",
    group_type: str = "couple",
    rainy_day: bool = False,
    need_private_car: bool = False,
    family_travel: bool = False,
    elderly_travel: bool = False,
) -> Dict[str, Any]:
    """主入口：生成上海半定制路线"""

    all_units = load_experience_units(city)
    edges = load_transport_edges()
    profiles = load_customer_profiles()
    templates = load_route_templates()

    if not all_units:
        return {"error": f"No experience units found for {city}", "success": False}

    interests = interests or ["culture"]
    travel_style = travel_style or []

    # 1. 匹配画像（budget_level 参与）
    profile, profile_score = match_profile_to_tag(profiles, interests, pace, budget_level, group_type)

    # 2. 选择模板 — 优先 primary match，Water Town 需显式触发
    candidates = [t for t in templates if profile.tag_id in t.target_profile_tags and t.duration_type == duration_type]
    # SH-TPL-08 (Water Town) 需要 interests 命中 water_town/canal/zhujiajiao/escape/nature 或 need_private_car=True
    water_town_keywords = {"water town", "canal", "zhujiajiao", "escape", "countryside", "day trip", "nature"}
    has_water_town_intent = any(kw.lower() in " ".join(interests).lower() for kw in water_town_keywords)
    candidates = [t for t in candidates
                  if t.template_id != "SH-TPL-08" or has_water_town_intent or need_private_car]
    if not candidates:
        candidates = [t for t in templates if t.duration_type == duration_type]
        candidates = [t for t in candidates
                      if t.template_id != "SH-TPL-08" or has_water_town_intent or need_private_car]
    # 按 primary 优先排序
    candidates.sort(key=lambda t: 0 if t.target_profile_tags and t.target_profile_tags[0] == profile.tag_id else 1)
    template: RouteTemplate = candidates[0] if candidates else templates[0]

    # 3. 打分 + 排序
    ranked = filter_and_rank(all_units, profile, duration_type, interests, pace,
                             budget_level, group_type,
                             rainy_day, family_travel, elderly_travel)

    # 4. 模板驱动编排
    selected, transfers, route_logic = select_route_units(
        ranked, template, edges, profile, duration_type, budget_level,
        group_type, rainy_day, need_private_car, elderly_travel,
    )

    # 5. 统计
    total_activity = sum(u.duration_min for u in selected)
    total_transit = sum(t.get("transit_min",0) for t in transfers)
    total_duration = total_activity + total_transit + (90 if duration_type=="one_day" else 60)
    total_cost = sum(u.estimated_cost_rmb for u in selected)
    risks = assess_risks(selected, transfers, profile, budget_level, rainy_day, duration_type,
                         need_private_car, elderly_travel)
    custom_options = generate_customization_options(selected, template)

    # 6. 交通摘要
    has_cross = any(t.get("risk") and "high" in t["risk"].lower() for t in transfers)
    recommended_transport = "Private car + walking" if (has_cross or need_private_car) else "Walking + metro"

    # 7. 模板合规报告
    satisfied_types = set()
    for u in selected:
        for rt in template.required_unit_types:
            if _unit_matches_type(u, rt):
                satisfied_types.add(rt)
    unsatisfied = [rt for rt in template.required_unit_types if rt not in satisfied_types]

    return {
        "success": True,
        "route_id": f"SH-CUSTOM-{duration_type.replace('_','-')}-{profile.tag_id.replace('TAG-','')}",
        "city": city,
        "title_en": template.route_story_angle,
        "template_id": template.template_id,
        "template_name": template.template_name,
        "target_profile_summary": f"Matched '{profile.tag_name}' (score={profile_score:.2f})",
        "duration_type": duration_type,
        "total_duration_min": total_duration,
        "activity_min": total_activity,
        "transit_min": total_transit,
        "estimated_cost_rmb": round(total_cost, 0),
        "cost_note": "Estimated from experience unit data. API layer can partially price mapped cost_item_code values via cost_engine; unmapped units remain estimate-only.",
        "budget_level_applied": budget_level,
        "recommended_transport": recommended_transport,
        "units": [{
            "sequence": i+1,
            "unit_id": u.unit_id,
            "name_en": u.name_en,
            "name_cn": u.name_cn,
            "area": u.area,
            "unit_type": u.unit_type,
            "duration_min": u.duration_min,
            "estimated_cost_rmb": u.estimated_cost_rmb,
            "cost_item_code": u.cost_item_code or None,
            "indoor_outdoor": u.indoor_outdoor,
            "rainy_day_friendly": u.rainy_day_friendly,
            "elderly_friendly": u.elderly_friendly,
            "fit_score": u.fit_score,
            "description_en": u.description_en[:200] if u.description_en else "",
        } for i, u in enumerate(selected)],
        "transfers": transfers,
        "template_compliance": {
            "required_types": template.required_unit_types,
            "satisfied_types": sorted(satisfied_types),
            "unsatisfied_types": unsatisfied,
        },
        "route_logic": route_logic,
        "risk_warnings": risks,
        "customization_options": custom_options,
        "commercial_notes": profile.commercial_note,
        "generated_by": "custom_route_engine v1.1 (Shanghai MVP)",
    }
