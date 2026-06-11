"""
POI Registry — 最小单元库数据模型与加载层

六类最小单元：
  anchor    — 锚点景点（故宫、长城），当天的"主角"
  experience — 文化体验（汉服、京剧），差异化来源
  freebie   — 免费节点（公园、建筑外观），零成本填缝剂
  meal      — 餐饮（烤鸭、涮肉），时间锚点+体验载体
  rest      — 休憩点（咖啡馆、书店），节奏缓冲
  service   — 服务单元（包车、导游、酒店），参与报价不参与编排

设计原则：
  - 所有单元共享 BaseUnit 基础字段
  - 每类有各自扩展字段，不强行统一
  - 以 JSON 文件为真源（data/pois/{city}_pois.json），代码只定义 Schema + 加载
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
POIS_DIR = ROOT / "data" / "pois"

# ── Category literal ───────────────────────────────────────────────

UnitCategory = Literal["anchor", "experience", "freebie", "meal", "rest", "service"]
TimeSlot = Literal["morning", "afternoon", "evening", "lunch", "dinner", "flexible"]
IndoorOutdoor = Literal["indoor", "outdoor", "mixed"]
MealPeriod = Literal["breakfast", "lunch", "dinner", "snack", "any"]


# ============================================================
# Base Unit — 所有最小单元的公共字段
# ============================================================


class BaseUnit(BaseModel):
    """所有最小单元的基础字段"""

    unit_id: str = Field(..., description="唯一标识，格式: {城市代码}-{类别}-{序号}，如 BJ-ANC-001")
    city: str = Field(..., description="所属城市")
    category: UnitCategory = Field(..., description="单元类别")
    name: str = Field(..., description="中文名称")
    name_en: str = Field("", description="英文名称")

    # ── 时间维度 ──
    duration_min: int = Field(..., ge=0, description="建议停留时长（分钟）")
    duration_min_min: int = Field(0, ge=0, description="最短停留（赶时间模式）")
    duration_max_min: int = Field(0, ge=0, description="最长停留（深度体验模式）")

    # ── 时段约束 ──
    preferred_slot: TimeSlot = Field("flexible", description="推荐时段")
    opening_start: str = Field("", description="开放起始时间，如 08:30。空字符串=无时间限制")
    opening_end: str = Field("", description="开放结束时间，如 17:00")
    closed_days: List[str] = Field(default_factory=list, description="闭馆日，如 ['Monday']")
    peak_season_note: str = Field("", description="旺季特殊说明")

    # ── 空间维度 ──
    lat: float = Field(0.0, description="纬度")
    lng: float = Field(0.0, description="经度")
    area: str = Field("", description="城市内区域，如'东城区'。同区域POI优先同天编排")
    indoor_outdoor: IndoorOutdoor = Field("outdoor")

    # ── 天气约束 ──
    is_rainy_friendly: bool = Field(True, description="雨天是否适合")
    is_hot_weather_friendly: bool = Field(True, description="高温是否适合")

    # ── 人群适配 ──
    is_family_friendly: bool = Field(True, description="是否适合家庭（带小孩）")
    is_senior_friendly: bool = Field(True, description="是否适合老人")
    min_age: int = Field(0, ge=0, description="最低年龄限制，0=不限")

    # ── 成本维度 ──
    unit_price_adult: float = Field(0.0, ge=0, description="成人单价（RMB）")
    unit_price_child: float = Field(0.0, ge=0, description="儿童单价（RMB）")
    unit_price_senior: float = Field(0.0, ge=0, description="老人单价（RMB）")
    is_free: bool = Field(False, description="是否免费")

    # ── 标签与关联 ──
    tags: List[str] = Field(default_factory=list, description="标签，如 ['世界遗产', '建筑美学', '摄影']")
    theme: str = Field("", description="叙事主题，如 Imperial_Life / City_Walk / Modern_China")
    related_units: List[str] = Field(default_factory=list, description="天然关联的POI ID列表")
    incompatible_units: List[str] = Field(default_factory=list, description="互斥的POI ID列表（不宜同天上午）")

    # ── 体验强度 ──
    energy_level: int = Field(1, ge=1, le=5, description="体力强度 1-5。1=轻松，5=高强度")
    crowd_level: int = Field(1, ge=1, le=5, description="拥挤程度 1-5。1=冷门，5=人山人海")
    uniqueness_score: int = Field(1, ge=1, le=5, description="独特性 1-5。区别于'大众景点'的程度")


# ============================================================
# 各类扩展字段
# ============================================================


class AnchorUnit(BaseUnit):
    """锚点景点 — 当天的'主角'"""

    category: Literal["anchor"] = "anchor"  # type: ignore[assignment]
    is_must_see: bool = Field(False, description="首次来此城市是否必去。True=engine优先选择")
    requires_reservation: bool = Field(False, description="是否需要预约（故宫/国博）")
    advance_days: int = Field(0, ge=0, description="提前几天可预约")
    ticket_item_code: str = Field("", description="对应成本库 item_code，如 BJ-TICKET-05。空=无需门票")


class ExperienceUnit(BaseUnit):
    """文化体验 — 差异化来源"""

    category: Literal["experience"] = "experience"  # type: ignore[assignment]
    requires_min_people: int = Field(1, ge=1, description="最少需要几人")
    max_people_per_session: int = Field(20, ge=1, description="单场最多容纳人数")
    requires_guide: bool = Field(False, description="是否需要导游翻译陪同")
    language_support: List[str] = Field(default_factory=lambda: ["EN", "ZH"], description="支持语言")
    item_code: str = Field("", description="对应成本库 item_code")


class FreebieUnit(BaseUnit):
    """免费节点 — 零成本文化体验"""

    category: Literal["freebie"] = "freebie"  # type: ignore[assignment]
    best_time_note: str = Field("", description="最佳体验时间描述，如'清晨本地人打太极时最有氛围'")
    photo_score: int = Field(1, ge=1, le=5, description="出片指数 1-5")


class MealUnit(BaseUnit):
    """餐饮 — 时间锚点 + 体验载体"""

    category: Literal["meal"] = "meal"  # type: ignore[assignment]
    cuisine_type: str = Field("", description="菜系，如'北京菜' / '川菜' / '小吃'")
    meal_period: MealPeriod = Field("any", description="适用餐段")
    price_per_person_range: str = Field("", description="人均价格区间，如'50-100'")
    is_social: bool = Field(False, description="是否有社交属性（如涮肉=是，快餐=否）")
    item_code: str = Field("", description="对应成本库 item_code，空=不计入报价（客人自理）")


class RestUnit(BaseUnit):
    """休憩点 — 节奏缓冲"""

    category: Literal["rest"] = "rest"  # type: ignore[assignment]
    has_wifi: bool = Field(False)
    has_restroom: bool = Field(False)
    item_code: str = Field("", description="对应成本库 item_code，空=客人自理")


class ServiceUnit(BaseUnit):
    """服务单元 — 参与报价但不参与每日行程编排"""

    category: Literal["service"] = "service"  # type: ignore[assignment]
    service_type: Literal["transport", "guide", "hotel", "transfer"] = Field(..., description="服务类型")
    unit_type: str = Field("day", description="计价单位：day / time / night")
    max_people: int = Field(6, ge=1, description="最大服务人数")
    item_code: str = Field("", description="对应成本库 item_code")


# ── Union type for loading ──

PoiUnit = AnchorUnit | ExperienceUnit | FreebieUnit | MealUnit | RestUnit | ServiceUnit


# ============================================================
# Category resolver — 按 category 字段路由到正确的 Pydantic 类
# ============================================================

CATEGORY_CLASS_MAP: Dict[str, type[BaseUnit]] = {
    "anchor": AnchorUnit,
    "experience": ExperienceUnit,
    "freebie": FreebieUnit,
    "meal": MealUnit,
    "rest": RestUnit,
    "service": ServiceUnit,
}


def parse_poi_unit(raw: Dict[str, Any]) -> BaseUnit:
    """根据 category 字段解析为对应的 Pydantic 子类"""
    cat = raw.get("category", "")
    cls = CATEGORY_CLASS_MAP.get(cat)
    if cls is None:
        raise ValueError(f"Unknown POI category: {cat}. Must be one of {list(CATEGORY_CLASS_MAP.keys())}")
    return cls(**raw)


# ============================================================
# I/O — 按城市加载/保存
# ============================================================


def load_city_pois(city: str) -> List[BaseUnit]:
    """加载指定城市的所有 POI"""
    filepath = POIS_DIR / f"{city}_pois.json"
    if not filepath.exists():
        return []
    data = json.loads(filepath.read_text(encoding="utf-8"))
    return [parse_poi_unit(item) for item in data.get("pois", [])]


def save_city_pois(city: str, pois: List[BaseUnit]) -> None:
    """保存指定城市的 POI 到 JSON"""
    POIS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "city": city,
        "version": "1.0.0",
        "count": len(pois),
        "pois": [p.model_dump(exclude_none=True) for p in pois],
    }
    filepath = POIS_DIR / f"{city}_pois.json"
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_available_poi_cities() -> List[str]:
    """列出已有 POI 数据的城市"""
    if not POIS_DIR.exists():
        return []
    cities: List[str] = []
    for f in sorted(POIS_DIR.glob("*_pois.json")):
        city = f.stem.replace("_pois", "")
        cities.append(city)
    return cities


def get_pois_by_category(pois: List[BaseUnit], category: UnitCategory) -> List[BaseUnit]:
    """按类别筛选"""
    return [p for p in pois if p.category == category]


def get_pois_by_area(pois: List[BaseUnit], area: str) -> List[BaseUnit]:
    """按区域筛选"""
    return [p for p in pois if p.area == area]


def get_pois_by_tag(pois: List[BaseUnit], tag: str) -> List[BaseUnit]:
    """按标签筛选"""
    return [p for p in pois if tag in p.tags]
