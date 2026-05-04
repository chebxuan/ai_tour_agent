"""
Hexa Blueprint™ API - 多城市行程规划服务
FastAPI 版本，用于扣子(Coze)智能体集成

运行方式:
    uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload

环境变量:
    API_KEY: API 认证密钥 (必需)

作者: Hexa China Tours
版本: 2.1.0
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from engines.city_config import list_available_cities
from engines.cost_engine import calculate_total_cost, load_cost_db
from engines.delivery_engine import build_delivery_draft
from engines.plan_engine import build_plan_object
from engines.product_engine import get_product_recommendation
from schemas import (
    CandidateProductsJSON,
    ConfirmedClientInfoJSON,
    ContactInfo,
    DeliveryDraftObject,
    LeadIntent,
    LeadJSON,
    PassengerMix,
    PlanObject,
    PricingResultJSON,
    ProductCandidate,
    ProductCandidateReason,
    ProductReference,
    SelectedProduct,
    TravelWindow,
)
from survey_architect import get_beijing_survey

# 加载环境变量
load_dotenv()

ROOT = Path(__file__).resolve().parent
NORMALIZED_PRODUCTS_JSON = ROOT / "data" / "products" / "products.normalized.json"
HIGHLIGHTS_JSON = ROOT / "data" / "products" / "attraction_highlights.json"


# ── Load highlights data ──

def load_highlights_data() -> Dict[str, Any]:
    if HIGHLIGHTS_JSON.exists():
        return json.loads(HIGHLIGHTS_JSON.read_text(encoding="utf-8"))
    return {}


# ── FastAPI 应用初始化 ───────────────────────────────────────────

def get_servers():
    """根据环境变量或默认值返回 servers 配置"""
    public_url = os.getenv("PUBLIC_URL", "")
    if public_url:
        return [{"url": public_url, "description": "Public server"}]
    return [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://your-domain.loca.lt", "description": "Localtunnel (update with your actual URL)"},
    ]


app = FastAPI(
    title="Hexa Blueprint™ API",
    description="多城市旅游行程规划与报价服务",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=get_servers(),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Key 认证 ─────────────────────────────────────────────────

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("请设置环境变量 API_KEY，用于 API 认证")


async def verify_api_key(x_api_key: str = Header(..., description="API 认证密钥")):
    """验证 API Key"""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
        )
    return x_api_key


# ── Pydantic 数据模型 ────────────────────────────────────────────

class SurveyStepOption(BaseModel):
    """问卷选项"""

    text: str = Field(..., description="选项文本")
    weight: Dict[str, Any] = Field(..., description="权重映射")


class SurveyStep(BaseModel):
    """问卷步骤"""

    question: str = Field(..., description="问题文本")
    options: Optional[List[SurveyStepOption]] = Field(None, description="选项列表")
    input_type: str = Field("choice", description="输入类型: choice/text")


class SurveyResponse(BaseModel):
    """问卷响应"""

    survey: List[SurveyStep]
    total_steps: int
    version: str = "1.0.0"


class UserIntentRequest(BaseModel):
    """用户意图请求"""

    city: str = Field("北京", description="目标城市")
    days: int = Field(..., ge=1, le=7, description="行程天数")
    persona: str = Field("standard", description="用户画像: family/couple/solo/senior")
    has_child: bool = Field(False, description="是否带儿童")
    interest: Optional[str] = Field(None, description="兴趣标签")
    adults: int = Field(2, ge=1, description="成人数量")
    children: int = Field(0, ge=0, description="儿童数量")
    seniors: int = Field(0, ge=0, description="老人数量")
    is_peak: bool = Field(True, description="是否旺季")
    guide: Optional[str] = Field(None, description="导游代码")
    hotel: Optional[str] = Field(None, description="酒店代码")
    hotel_nights: int = Field(0, ge=0, description="酒店入住晚数")
    transfer: Optional[str] = Field(None, description="接送代码")
    transfer_times: int = Field(0, ge=0, description="接送次数")
    car_days: int = Field(0, ge=0, description="包车天数")
    selected_optional: List[str] = Field(default_factory=list, description="用户选择的可选项目代码列表")
    recommend_optional: Optional[str] = Field(None, description="推荐可选项")


class ProductInfo(BaseModel):
    """产品信息"""

    product_name: str
    days: int
    itinerary: str
    regular_items: str
    optional_items: str
    recommended_optional: str


class ProductResponse(BaseModel):
    """产品推荐响应"""

    success: bool
    data: Optional[ProductInfo] = None
    error: Optional[str] = None
    timestamp: str


class CostSummary(BaseModel):
    """费用汇总"""

    product_name: str
    days: int
    city: str
    adults: int
    children: int
    seniors: int
    total_people: int
    is_peak: bool
    hotel_nights: int
    car_days: int
    transfer_times: int
    regular_items_count: Optional[int] = 0
    optional_items_count: Optional[int] = 0
    grand_total: float
    per_person: float


class CostBreakdown(BaseModel):
    """费用明细项"""

    code: str
    name: str
    unit_price: float
    adults: int
    children: int
    seniors: int
    line_total: float
    note: str


class TicketActivityCost(BaseModel):
    """门票活动费用"""

    breakdown: List[CostBreakdown]
    subtotal: float


class HotelCost(BaseModel):
    """酒店费用"""

    hotel_code: Optional[str]
    hotel_name: Optional[str] = None
    hotel_price: float
    rooms: int
    nights: int
    subtotal: float


class TransportCost(BaseModel):
    """交通费用"""

    car_code: Optional[str]
    car_daily_price: float
    car_days: int
    car_subtotal: float
    transfer_code: Optional[str]
    transfer_price: float
    transfer_times: int
    transfer_subtotal: float
    subtotal: float


class GuideCost(BaseModel):
    """导游费用"""

    guide_code: Optional[str]
    guide_name: Optional[str]
    daily_price: float
    days: int
    subtotal: float


class CostResponse(BaseModel):
    """费用计算响应"""

    success: bool
    summary: Optional[CostSummary] = None
    ticket_activity: Optional[TicketActivityCost] = None
    hotel: Optional[HotelCost] = None
    transport: Optional[TransportCost] = None
    guide: Optional[GuideCost] = None
    error: Optional[str] = None
    timestamp: str


class CompleteRequest(BaseModel):
    """一键完成请求"""

    intent: UserIntentRequest


class CompleteResponse(BaseModel):
    """一键完成响应"""

    success: bool
    product: Optional[ProductInfo] = None
    cost: Optional[CostResponse] = None
    error: Optional[str] = None
    timestamp: str


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    timestamp: str


class ProductMatchRequest(BaseModel):
    lead: LeadJSON


class PricingRequestV2(BaseModel):
    lead: LeadJSON
    selected_product_id: str = Field(..., description="Selected product id from normalized product library")
    is_peak: bool = Field(True, description="Whether current quote is peak season")
    guide_code: Optional[str] = Field(None, description="Guide service code")
    hotel_code: Optional[str] = Field(None, description="Hotel service code")
    hotel_nights: Optional[int] = Field(None, ge=0)
    transfer_code: Optional[str] = Field(None, description="Transfer service code")
    transfer_times: int = Field(0, ge=0)
    car_days: Optional[int] = Field(None, ge=0)
    selected_optional_item_codes: List[str] = Field(default_factory=list)


class PlanRequestV2(BaseModel):
    lead: LeadJSON
    selected_product_ids: List[str] = Field(..., min_length=1, description="Ordered selected product ids")
    selected_optional_item_codes: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Optional item codes keyed by product id",
    )
    selection_notes: List[str] = Field(default_factory=list)
    custom_adjustments: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Manual adjustment notes keyed by product id",
    )


# ── v2 helper functions ──────────────────────────────────────────

def load_normalized_product_payload() -> Dict[str, Any]:
    if not NORMALIZED_PRODUCTS_JSON.exists():
        raise FileNotFoundError(
            f"Normalized product library not found: {NORMALIZED_PRODUCTS_JSON}. "
            "Please run scripts/normalize_product_library.py first."
        )
    return json.loads(NORMALIZED_PRODUCTS_JSON.read_text(encoding="utf-8"))


def load_normalized_products() -> List[Dict[str, Any]]:
    return load_normalized_product_payload().get("products", [])


def build_query_summary_from_lead(lead: LeadJSON) -> str:
    cities = ", ".join(lead.intent.destination_cities) if lead.intent.destination_cities else "destination TBD"
    trip_days = f"{lead.intent.trip_days}-day" if lead.intent.trip_days else "flexible-length"
    passenger_parts = []
    if lead.passenger_mix.adults:
        passenger_parts.append(f"{lead.passenger_mix.adults} adults")
    if lead.passenger_mix.children:
        passenger_parts.append(f"{lead.passenger_mix.children} children")
    if lead.passenger_mix.seniors:
        passenger_parts.append(f"{lead.passenger_mix.seniors} seniors")
    passengers = ", ".join(passenger_parts) if passenger_parts else "passenger mix unspecified"
    interests = ", ".join(lead.intent.interests[:3]) if lead.intent.interests else "general interests"
    return f"{passengers} planning a {trip_days} trip in {cities} with focus on {interests}."


def score_product_for_lead(product: Dict[str, Any], lead: LeadJSON) -> ProductCandidate:
    requested_cities = set(lead.intent.destination_cities)
    trip_days = lead.intent.trip_days
    interests = [value.lower() for value in lead.intent.interests]
    travel_style = [value.lower() for value in lead.intent.travel_style]
    must_have = [value.lower() for value in lead.intent.must_have]
    avoid = [value.lower() for value in lead.intent.avoid]

    score = 0.0
    matched_interests: List[str] = []
    matched_constraints: List[str] = []
    warnings: List[str] = []

    product_city = product.get("city", "")
    product_days = int(product.get("duration_days", 0) or 0)
    searchable_text = " ".join(
        [
            product.get("product_name", ""),
            product.get("itinerary_text", ""),
            " ".join(product.get("regular_items", [])),
            " ".join(product.get("optional_items", [])),
        ]
    ).lower()

    if requested_cities:
        if product_city in requested_cities:
            score += 0.45
            matched_constraints.append(f"destination={product_city}")
        else:
            warnings.append("city does not exactly match requested destination")
    else:
        score += 0.15
        warnings.append("destination not explicitly specified in lead")

    if trip_days:
        if product_days == trip_days:
            score += 0.30
            matched_constraints.append(f"trip_days={trip_days}")
        elif abs(product_days - trip_days) == 1:
            score += 0.15
            matched_constraints.append(f"near_duration_match={product_days}")
            warnings.append("duration differs by 1 day from requested trip length")
        else:
            warnings.append("duration fit is weak")
    else:
        score += 0.10
        warnings.append("trip length not explicitly specified")

    for token in interests + travel_style + must_have:
        if token and token in searchable_text and token not in matched_interests:
            matched_interests.append(token)
            score += 0.05

    for token in avoid:
        if token and token in searchable_text:
            warnings.append(f"contains potentially avoided element: {token}")
            score -= 0.05

    if lead.passenger_mix.children > 0:
        matched_constraints.append("family_travel")
    if lead.passenger_mix.seniors > 0:
        matched_constraints.append("senior_travel")
    if lead.intent.need_private_car:
        matched_constraints.append("private_car_requested")
    if lead.intent.need_guide:
        matched_constraints.append("guide_requested")

    score = max(0.0, min(round(score, 2), 1.0))
    fit_label = "high" if score >= 0.75 else "medium" if score >= 0.45 else "low"

    rationale_parts = []
    if requested_cities and product_city in requested_cities:
        rationale_parts.append(f"matches requested city {product_city}")
    if trip_days and product_days == trip_days:
        rationale_parts.append("exact duration match")
    elif trip_days and abs(product_days - trip_days) == 1:
        rationale_parts.append("near duration match")
    if matched_interests:
        rationale_parts.append(f"interest overlap: {', '.join(matched_interests[:3])}")
    if not rationale_parts:
        rationale_parts.append("basic fallback candidate based on available product data")

    return ProductCandidate(
        rank=1,
        product=ProductReference(
            product_id=product.get("product_id", ""),
            city=product_city,
            product_name=product.get("product_name", ""),
            duration_days=product_days or 1,
            daily_itinerary=product.get("itinerary_text", ""),
        ),
        match_score=score,
        fit_label=fit_label,
        regular_item_codes=product.get("regular_item_codes", []),
        optional_item_codes=product.get("optional_item_codes", []),
        reason=ProductCandidateReason(
            matched_interests=matched_interests,
            matched_constraints=matched_constraints,
            warnings=warnings,
            rationale="; ".join(rationale_parts),
        ),
    )


def build_candidates_from_lead(lead: LeadJSON) -> CandidateProductsJSON:
    products = load_normalized_products()
    requested_cities = set(lead.intent.destination_cities)

    filtered_products = [
        product for product in products if not requested_cities or product.get("city") in requested_cities
    ]
    if not filtered_products:
        filtered_products = products

    candidates = [score_product_for_lead(product, lead) for product in filtered_products]
    candidates.sort(key=lambda item: item.match_score, reverse=True)

    top_candidates = candidates[:3]
    for index, candidate in enumerate(top_candidates, start=1):
        candidate.rank = index

    recommended_product_id = top_candidates[0].product.product_id if top_candidates else None

    return CandidateProductsJSON(
        lead_id=lead.lead_id,
        city_scope=lead.intent.destination_cities,
        query_summary=build_query_summary_from_lead(lead),
        candidates=top_candidates,
        recommended_product_id=recommended_product_id,
        generated_by="agent_1_product_matcher",
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )


def get_normalized_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    for product in load_normalized_products():
        if product.get("product_id") == product_id:
            return product
    return None


def build_user_intent_from_pricing_request(request: PricingRequestV2, product: Dict[str, Any]) -> Dict[str, Any]:
    lead = request.lead
    return {
        "lead_id": lead.lead_id,
        "city": product.get("city"),
        "days": product.get("duration_days"),
        "adults": lead.passenger_mix.adults,
        "children": lead.passenger_mix.children,
        "seniors": lead.passenger_mix.seniors,
        "is_peak": request.is_peak,
        "guide": request.guide_code,
        "need_guide": lead.intent.need_guide,
        "need_private_car": lead.intent.need_private_car,
        "hotel": request.hotel_code,
        "hotel_nights": request.hotel_nights if request.hotel_nights is not None else max(int(product.get("duration_days", 1)) - 1, 0),
        "transfer": request.transfer_code,
        "transfer_times": request.transfer_times,
        "car_days": request.car_days if request.car_days is not None else int(product.get("duration_days", 1)),
        "selected_optional": request.selected_optional_item_codes,
        "recommend_optional": None,
    }


def build_selected_products_from_plan_request(request: PlanRequestV2) -> List[SelectedProduct]:
    selected_products: List[SelectedProduct] = []
    for product_id in request.selected_product_ids:
        product = get_normalized_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"未找到产品: {product_id}")

        option_codes = request.selected_optional_item_codes.get(product_id, [])
        optional_lookup = {
            code: name for code, name in zip(product.get("optional_item_codes", []), product.get("optional_items", []))
        }

        selected_optional_items = [
            {
                "code": code,
                "name": optional_lookup.get(code),
                "selected": True,
            }
            for code in option_codes
        ]

        selected_products.append(
            SelectedProduct(
                product=ProductReference(
                    product_id=product.get("product_id", ""),
                    city=product.get("city", ""),
                    product_name=product.get("product_name", ""),
                    duration_days=int(product.get("duration_days", 1) or 1),
                    daily_itinerary=product.get("itinerary_text", ""),
                ),
                selection_reason=None,
                regular_item_codes=product.get("regular_item_codes", []),
                selected_optional_items=selected_optional_items,
                custom_adjustments=request.custom_adjustments.get(product_id, []),
            )
        )
    return selected_products


def format_itinerary_markdown(
    lead: LeadJSON,
    product_match: CandidateProductsJSON,
    pricing: Optional[PricingResultJSON],
    plan: Optional[PlanObject],
    delivery: Optional[DeliveryDraftObject],
) -> str:
    """将全链路输出格式化为可发送客户的 Markdown 路书
    对齐 05-模版路书.md 格式：标题 → 客户信息 → 提醒 → 行程表 → 酒店/交通/联系人 → 报价 → 备注
    """
    lines: List[str] = []
    top = product_match.candidates[0] if product_match.candidates else None
    product_name = top.product.product_name if top else "Custom Trip"
    customer_name = lead.contact.full_name or lead.contact.nationality or "Traveler"

    # ── Title & Client Info ──
    lines.append(f"# {product_name}")
    lines.append("")
    lines.append(f"**For:** {customer_name}")
    pax = lead.passenger_mix
    pax_parts = [f"{pax.adults} Adult(s)"]
    if pax.children:
        pax_parts.append(f"{pax.children} Child(ren)")
    if pax.seniors:
        pax_parts.append(f"{pax.seniors} Senior(s)")
    lines.append(f"**Travelers:** {', '.join(pax_parts)}")
    if lead.travel_window.start_date:
        lines.append(f"**Travel Dates:** {lead.travel_window.start_date}")
    if lead.intent.interests:
        lines.append(f"**Interests:** {', '.join(lead.intent.interests)}")
    lines.append("")

    # ── Product Info ──
    if top:
        lines.append("## 产品信息 Product Information")
        lines.append("")
        lines.append(f"| 字段 Field | 内容 Value |")
        lines.append(f"|-----------|-----------|")
        lines.append(f"| **产品编号 Product ID** | {top.product.product_id} |")
        lines.append(f"| **产品名称 Product Name** | {top.product.product_name} |")
        lines.append(f"| **行程天数 Duration** | {top.product.duration_days} 天 Days |")
        if top.product.daily_itinerary:
            itinerary_text = top.product.daily_itinerary.replace("\n", "<br>")
            lines.append(f"| **每日行程 Daily Itinerary** | {itinerary_text} |")
        lines.append("")

    # ── Welcome & Emergency ──
    lines.append("Thanks for travelling with Hexa! To help you get ready, we have put together this itinerary with your daily schedule, accommodation, local contacts and all the essential details for your trip. If you have any question, please feel free to contact us.")
    lines.append("")

    # ── Kindly Note (从 delivery.global_reminders 提取) ──
    if delivery and delivery.global_reminders:
        lines.append("### 温馨提示 Kindly note:")
        lines.append("")
        for reminder in delivery.global_reminders:
            lines.append(f"- {reminder.content}")
        lines.append("")

    # ── Day-by-Day Itinerary — Bilingual operations format ──
    highlights_data = load_highlights_data()
    city_h = highlights_data.get(lead.intent.destination_cities[0], {}) if lead.intent.destination_cities else {}
    product_id = top.product.product_id if top else ""
    day_routes = city_h.get("product_days", {}).get(product_id, {})
    all_routes = city_h.get("routes", {})

    if plan and plan.day_plans:
        lines.append("## 每日行程 Day-by-Day Itinerary")
        lines.append("")
        for day in plan.day_plans:
            day_num = day.day_number
            date_str = f" ({day.date})" if day.date else ""
            route_key = day_routes.get(str(day_num))
            route = all_routes.get(route_key) if route_key else None

            # Day header — bilingual
            lines.append(f"### 第{day_num}天 Day {day_num}{date_str}")
            if route and route.get("title"):
                lines.append(f"*{route['title']}*")
            lines.append("")

            # Activities grouped by time period
            morning_acts: List[str] = []
            afternoon_acts: List[str] = []
            evening_acts: List[str] = []
            for act in day.activities:
                if not act.included:
                    continue
                entry = act.title
                if act.notes:
                    first = act.notes[0]
                    if "optional" in first.lower():
                        entry = f"{entry} (可选 Optional)"
                if act.time_slot == "morning":
                    morning_acts.append(entry)
                elif act.time_slot == "afternoon":
                    afternoon_acts.append(entry)
                elif act.time_slot == "evening":
                    evening_acts.append(entry)
                else:
                    morning_acts.append(entry)

            if morning_acts:
                lines.append("🌅 **上午 Morning**")
                for a in morning_acts:
                    lines.append(f"▪ {a}")
                lines.append("")
            if afternoon_acts:
                lines.append("☀️ **下午 Afternoon**")
                for a in afternoon_acts:
                    lines.append(f"▪ {a}")
                lines.append("")
            if evening_acts:
                lines.append("🌙 **晚上 Evening**")
                for a in evening_acts:
                    lines.append(f"▪ {a}")
                lines.append("")

            # Attractions — compact inline list (removed redundant Highlight of the Day)
            if route and route.get("attractions"):
                lines.append("🏛 **景点 Highlights**")
                for attr in route["attractions"]:
                    name = attr.get("name", "")
                    duration = attr.get("duration", "")
                    desc = attr.get("description", "")
                    parts = [f"▪ **{name}**"]
                    if duration:
                        parts.append(f"({duration})")
                    if desc:
                        parts.append(f"— {desc}")
                    lines.append(" ".join(parts))
                lines.append("")

            # Transport notes
            if day.transport_notes:
                lines.append("🚗 **交通 Transport**")
                for note in day.transport_notes:
                    lines.append(f"▪ {note}")
                lines.append("")

            # Separator between days
            lines.append("---")
            lines.append("")

    elif delivery:
        # Fallback: use delivery table if no plan available
        itinerary_section = next(
            (s for s in delivery.sections if s.section_type == "itinerary_table"),
            None,
        )
        if itinerary_section and itinerary_section.rows:
            lines.append("## 每日行程 Day-by-Day Itinerary")
            lines.append("")
            lines.append("| 日期 Date | 时段 Period | 地点 Location | 活动 Activities | 提醒 Reminders |")
            lines.append("|------|--------|----------|------------|---------------------|")
            for row in itinerary_section.rows:
                date = row.date_label or ""
                time = row.time_range or ""
                loc = row.city or ""
                act = row.activity_title or ""
                reminders = "; ".join(r.content for r in row.reminders) if row.reminders else ""
                if len(reminders) > 80:
                    reminders = reminders[:77] + "..."
                lines.append(f"| {date} | {time} | {loc} | {act} | {reminders} |")
            lines.append("")

    # ── Hotel Stays ──
    if delivery:
        hotel_section = next(
            (s for s in delivery.sections if s.section_type == "hotel"),
            None,
        )
        if hotel_section:
            lines.append("## 住宿 Accommodation")
            lines.append("")
            lines.append(hotel_section.content or "Hotel details to be confirmed.")
            lines.append("")

    # ── Transport Arrangements ──
    if delivery:
        transport_section = next(
            (s for s in delivery.sections if s.section_type == "transport"),
            None,
        )
        if transport_section and transport_section.content:
            lines.append("## 交通 Transport Arrangements")
            lines.append("")
            lines.append(transport_section.content)
            lines.append("")

    # ── Key Contacts ──
    if delivery:
        contacts_section = next(
            (s for s in delivery.sections if s.section_type == "contacts"),
            None,
        )
        if contacts_section and contacts_section.rows:
            first_row = contacts_section.rows[0]
            if first_row.contacts:
                lines.append("## 主要联系人 Key Contacts")
                lines.append("")
                # Check if there are city-specific contacts by looking for per-city rows
                city_contacts = False
                for row in contacts_section.rows:
                    if row.city and row.contacts:
                        city_contacts = True
                        lines.append(f"### {row.city}")
                        lines.append("")
                        for c in row.contacts:
                            phone_str = f" — {c.phone}" if c.phone else ""
                            role_str = f" ({c.role})" if c.role and c.role != "Key Contacts" else ""
                            lines.append(f"- **{c.name}**{role_str}{phone_str}")
                        lines.append("")
                if not city_contacts:
                    # Global contacts as a simple list
                    for c in first_row.contacts:
                        phone_str = f" — {c.phone}" if c.phone else ""
                        role_str = f" ({c.role})" if c.role else ""
                        lines.append(f"- **{c.name}**{role_str}{phone_str}")
                    lines.append("")

    # ── Optional Add-ons ──
    if top and top.optional_item_codes:
        lines.append("### 可选项目 Optional Add-ons")
        lines.append("")
        # Load cost DB to get human-readable names
        _opt_db = load_cost_db(city=top.product.city) if top.product.city else {}
        for code in top.optional_item_codes:
            name = _opt_db.get(code, {}).get("name") or code
            lines.append(f"- {name} ({code})")
        lines.append("")

    # ── Cost Breakdown (replaces old Pricing Summary) ──
    if pricing and pricing.summary:
        lines.append("## 费用明细 Cost Breakdown")
        lines.append("")
        lines.append(f"_{pricing.summary.product_name} — {pricing.summary.city}_")
        season_label = "旺季 Peak Season" if pricing.summary.is_peak else "淡季 Off-Peak Season"
        lines.append(f"_{pricing.summary.adults} 成人 Adult(s) | {pricing.summary.children} 儿童 Child(ren) | {pricing.summary.seniors} 老人 Senior(s) | {season_label}_")
        lines.append("")

        # Group line items by category
        category_order = ["ticket_activity", "guide", "transport", "hotel", "other"]
        cat_labels = {
            "ticket_activity": "🎫 门票活动 Tickets & Activities",
            "guide": "👩‍💼 导游 Guide",
            "transport": "🚗 交通 Transport",
            "hotel": "🏨 住宿 Hotel",
            "other": "📦 其他 Other",
        }

        for cat in category_order:
            items = [li for li in pricing.line_items if li.category == cat]
            if not items:
                continue
            lines.append(f"### {cat_labels.get(cat, cat)}")
            lines.append("")
            lines.append("| 编号 Code | 项目 Item | 单价 Unit Price | 数量 Qty | 小计 Subtotal |")
            lines.append("|-----------|-----------|----------------|----------|---------------|")
            for item in items:
                code = item.code or ""
                name = item.name
                unit_price = f"¥{item.unit_price:,.0f}" if item.unit_price else "—"
                qty = f"{item.quantity:.0f}" if item.quantity else "—"
                subtotal = f"¥{item.subtotal:,.0f}" if item.subtotal else "—"
                lines.append(f"| {code} | {name} | {unit_price} | {qty} | {subtotal} |")
            cat_sub = pricing.category_subtotals.get(cat, 0)
            if cat_sub > 0:
                lines.append(f"| | **小计 Subtotal** | | | **¥{cat_sub:,.2f}** |")
            lines.append("")

        # Grand total
        lines.append("### 费用汇总 Summary")
        lines.append("")
        lines.append(f"| | 金额 Amount (RMB) |")
        lines.append(f"|---|------------------|")
        lines.append(f"| **总计 Grand Total** | **¥{pricing.summary.grand_total:,.2f}** |")
        lines.append(f"| **人均 Per Person** | **¥{pricing.summary.per_person:,.2f}** |")
        lines.append(f"| **人数 Total People** | {pricing.summary.total_people} |")
        if pricing.summary.hotel_nights > 0:
            lines.append(f"| **住宿晚数 Hotel Nights** | {pricing.summary.hotel_nights} |")
        if pricing.summary.car_days > 0:
            lines.append(f"| **用车天数 Car Days** | {pricing.summary.car_days} |")
        lines.append("")
        lines.append(f"_*以上价格为{season_label}价格。餐饮不含，除非特别说明。Pricing based on {season_label}. Meals not included unless specified above._")
        lines.append("")

    # ── Important Notes ──
    if delivery:
        notes_section = next(
            (s for s in delivery.sections if s.section_type == "notes"),
            None,
        )
        if notes_section and notes_section.content:
            lines.append("## 重要提示 Important Notes")
            lines.append("")
            lines.append(notes_section.content)
            lines.append("")

    # ── Footer ──
    lines.append("---")
    lines.append("_由 Hexa Blueprint™ AI Travel Copilot 生成 · Generated by Hexa Blueprint™ AI Travel Copilot_")
    lines.append("")

    return "\n".join(lines)


def build_lead_from_full_chain_request(req: FullChainRequest) -> LeadJSON:
    """从简化请求构建 LeadJSON"""
    lead_id = f"lead_{uuid4().hex[:8]}"
    start_date = None
    if req.travel_date:
        try:
            start_date = datetime.strptime(req.travel_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    if start_date is None:
        start_date = datetime.utcnow().date()
    return LeadJSON(
        lead_id=lead_id,
        contact=ContactInfo(nationality="International"),
        travel_window=TravelWindow(
            start_date=start_date,
            flexible_days=0,
        ),
        passenger_mix=PassengerMix(
            adults=req.adults,
            children=req.children,
            seniors=req.seniors,
        ),
        intent=LeadIntent(
            destination_cities=[req.city],
            trip_days=req.days,
            interests=req.interests,
            travel_style=["private"],
            need_guide=req.need_guide,
            need_private_car=req.need_private_car,
        ),
    )


# ── API 端点 ─────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
async def root():
    """根路径 - 服务状态检查"""
    return HealthResponse(
        status="running",
        version="2.1.0",
        timestamp=datetime.now().isoformat(),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        version="2.1.0",
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/v1/cities", response_model=Dict[str, Any])
async def get_cities(api_key: str = Depends(verify_api_key)):
    """获取支持的城市列表"""
    try:
        cities = list_available_cities()
        return {
            "success": True,
            "cities": cities,
            "count": len(cities),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取城市列表失败: {str(e)}",
        )


@app.get("/api/v1/survey", response_model=SurveyResponse)
async def get_survey(api_key: str = Depends(verify_api_key)):
    """获取问卷数据"""
    try:
        survey_data = get_beijing_survey()
        return SurveyResponse(survey=survey_data, total_steps=len(survey_data), version="1.0.0")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问卷加载失败: {str(e)}",
        )


@app.post("/api/v1/recommend", response_model=ProductResponse)
async def get_recommendation(intent: UserIntentRequest, api_key: str = Depends(verify_api_key)):
    """获取产品推荐"""
    try:
        user_intent = intent.model_dump()
        product = get_product_recommendation(user_intent)

        if product.get("error"):
            return ProductResponse(success=False, error=product["error"], timestamp=datetime.now().isoformat())

        return ProductResponse(
            success=True,
            data=ProductInfo(**product),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        return ProductResponse(success=False, error=f"推荐失败: {str(e)}", timestamp=datetime.now().isoformat())


@app.post("/api/v1/cost", response_model=CostResponse)
async def calculate_cost(intent: UserIntentRequest, api_key: str = Depends(verify_api_key)):
    """计算行程费用"""
    try:
        user_intent = intent.model_dump()
        product = get_product_recommendation(user_intent)

        if product.get("error"):
            return CostResponse(success=False, error=product["error"], timestamp=datetime.now().isoformat())

        cost_result = calculate_total_cost(product, user_intent)
        if not cost_result.get("success", True):
            return CostResponse(
                success=False,
                summary=CostSummary(**cost_result["summary"]),
                ticket_activity=TicketActivityCost(**cost_result["ticket_activity"]),
                hotel=HotelCost(**cost_result["hotel"]),
                transport=TransportCost(**cost_result["transport"]),
                guide=GuideCost(**cost_result["guide"]),
                error=cost_result.get("error"),
                timestamp=datetime.now().isoformat(),
            )

        summary_payload = dict(cost_result["summary"])
        summary_payload["regular_items_count"] = len(cost_result.get("regular_item_codes", []))
        summary_payload["optional_items_count"] = len(cost_result.get("selected_optional_item_codes", []))

        return CostResponse(
            success=True,
            summary=CostSummary(**summary_payload),
            ticket_activity=TicketActivityCost(**cost_result["ticket_activity"]),
            hotel=HotelCost(**cost_result["hotel"]),
            transport=TransportCost(**cost_result["transport"]),
            guide=GuideCost(**cost_result["guide"]),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        return CostResponse(success=False, error=f"费用计算失败: {str(e)}", timestamp=datetime.now().isoformat())


@app.post("/api/v1/complete", response_model=CompleteResponse)
async def complete_planning(request: CompleteRequest, api_key: str = Depends(verify_api_key)):
    """一键完成行程规划"""
    try:
        user_intent = request.intent.model_dump()
        product = get_product_recommendation(user_intent)

        if product.get("error"):
            return CompleteResponse(success=False, error=product["error"], timestamp=datetime.now().isoformat())

        cost_result = calculate_total_cost(product, user_intent)
        summary_payload = dict(cost_result["summary"])
        summary_payload["regular_items_count"] = len(cost_result.get("regular_item_codes", []))
        summary_payload["optional_items_count"] = len(cost_result.get("selected_optional_item_codes", []))

        return CompleteResponse(
            success=cost_result.get("success", True),
            product=ProductInfo(**product),
            cost=CostResponse(
                success=cost_result.get("success", True),
                summary=CostSummary(**summary_payload),
                ticket_activity=TicketActivityCost(**cost_result["ticket_activity"]),
                hotel=HotelCost(**cost_result["hotel"]),
                transport=TransportCost(**cost_result["transport"]),
                guide=GuideCost(**cost_result["guide"]),
                error=cost_result.get("error"),
                timestamp=datetime.now().isoformat(),
            ),
            error=cost_result.get("error"),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        return CompleteResponse(success=False, error=f"规划失败: {str(e)}", timestamp=datetime.now().isoformat())


@app.post("/api/v2/product-match", response_model=CandidateProductsJSON)
async def match_products_v2(request: ProductMatchRequest, api_key: str = Depends(verify_api_key)):
    """Agent 1 风格产品匹配接口"""
    try:
        return build_candidates_from_lead(request.lead)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"产品匹配失败: {str(e)}",
        )


@app.post("/api/v2/pricing", response_model=PricingResultJSON)
async def calculate_pricing_v2(request: PricingRequestV2, api_key: str = Depends(verify_api_key)):
    """PricingResultJSON 风格报价接口"""
    try:
        product = get_normalized_product_by_id(request.selected_product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"未找到产品: {request.selected_product_id}")

        user_intent = build_user_intent_from_pricing_request(request, product)
        pricing_result = calculate_total_cost(product, user_intent)
        return PricingResultJSON(**pricing_result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报价计算失败: {str(e)}",
        )


@app.post("/api/v2/plan", response_model=PlanObject)
async def build_plan_v2(request: PlanRequestV2, api_key: str = Depends(verify_api_key)):
    """Agent 3 风格方案骨架接口"""
    try:
        selected_products = build_selected_products_from_plan_request(request)
        normalized_products = load_normalized_products()
        plan_object = build_plan_object(
            lead=request.lead,
            selected_products=selected_products,
            normalized_products=normalized_products,
        )
        if request.selection_notes:
            plan_object.planning_notes.extend(request.selection_notes)
        return plan_object
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"方案生成失败: {str(e)}",
        )


# ── 飞书 API 扩展接口（预留）──────────────────────────────────────

class DeliveryRequestV2(BaseModel):
    plan: PlanObject
    confirmed_client_info: Optional[ConfirmedClientInfoJSON] = None
    language: str = Field("en", description="Output language for the delivery draft")


class FullChainRequest(BaseModel):
    """一键全链路请求 — 简化输入，内部串联 product → pricing → plan → delivery"""

    city: str = Field("北京", description="目标城市")
    days: int = Field(..., ge=1, le=10, description="行程天数")
    adults: int = Field(2, ge=1, description="成人数量")
    children: int = Field(0, ge=0, description="儿童数量")
    seniors: int = Field(0, ge=0, description="老人数量")
    is_peak: bool = Field(True, description="是否旺季")
    interests: List[str] = Field(default_factory=lambda: ["history", "culture"], description="兴趣标签")
    need_guide: bool = Field(False, description="是否需要导游")
    need_private_car: bool = Field(True, description="是否需要包车")
    selected_optional_item_codes: List[str] = Field(default_factory=list, description="用户选择的 optional 项目编号")
    travel_date: Optional[str] = Field(None, description="Travel start date (YYYY-MM-DD)")


class FullChainResponse(BaseModel):
    """一键全链路响应"""

    success: bool
    lead: Optional[LeadJSON] = None
    product_match: Optional[CandidateProductsJSON] = None
    pricing: Optional[PricingResultJSON] = None
    plan: Optional[PlanObject] = None
    delivery: Optional[DeliveryDraftObject] = None
    itinerary_markdown: str = ""
    error: Optional[str] = None
    generated_at: str = ""


@app.post("/api/v2/delivery", response_model=DeliveryDraftObject)
async def build_delivery_v2(request: DeliveryRequestV2, api_key: str = Depends(verify_api_key)):
    """Agent 4 风格交付草稿生成接口"""
    try:
        return build_delivery_draft(
            plan=request.plan,
            confirmed_client_info=request.confirmed_client_info,
            language=request.language,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"交付草稿生成失败: {str(e)}",
        )


@app.post("/api/v2/full_chain", response_model=FullChainResponse)
async def full_chain_v2(request: FullChainRequest, api_key: str = Depends(verify_api_key)):
    """一键全链路接口：简化输入 → 产品匹配 → 报价 → 方案 → 交付 + Markdown

    输入只需城市、天数、人数等基本信息，内部自动串联 v2 四接口。
    输出包含各阶段结构化 JSON 和可直接发送客户的 Markdown 行程。
    """
    generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    partial = FullChainResponse(success=False, generated_at=generated_at)

    try:
        # 1. Build Lead
        lead = build_lead_from_full_chain_request(request)
        partial.lead = lead

        # 2. Product Match
        try:
            product_match = build_candidates_from_lead(lead)
            partial.product_match = product_match
        except Exception as e:
            partial.error = f"产品匹配失败: {str(e)}"
            return partial

        if not product_match.candidates:
            partial.error = "未找到匹配产品"
            return partial

        top_product_id = product_match.recommended_product_id
        top_candidate = product_match.candidates[0]

        # 3. Pricing
        try:
            product = get_normalized_product_by_id(top_product_id)
            hotel_nights = max(int(product.get("duration_days", 1)) - 1, 0) if product else max(request.days - 1, 0)
            # Auto-assign guide code when guide is requested but no specific code given
            guide_code = None
            if request.need_guide:
                from engines.city_config import get_city_code_prefix
                city_prefix = get_city_code_prefix(request.city)
                guide_code = f"{city_prefix}-GUIDE-01" if city_prefix else None
            pricing_request = PricingRequestV2(
                lead=lead,
                selected_product_id=top_product_id,
                is_peak=request.is_peak,
                guide_code=guide_code,
                hotel_nights=hotel_nights,
                car_days=request.days,
                transfer_times=2,
                selected_optional_item_codes=request.selected_optional_item_codes,
            )
            user_intent = build_user_intent_from_pricing_request(pricing_request, product or {})
            pricing_result = calculate_total_cost(product or {}, user_intent)
            partial.pricing = PricingResultJSON(**pricing_result)
        except Exception as e:
            partial.error = f"报价计算失败: {str(e)}"
            return partial

        # 4. Plan
        try:
            plan_request = PlanRequestV2(
                lead=lead,
                selected_product_ids=[top_product_id],
                selected_optional_item_codes={
                    top_product_id: request.selected_optional_item_codes
                },
            )
            selected_products = build_selected_products_from_plan_request(plan_request)
            normalized_products = load_normalized_products()
            plan_object = build_plan_object(
                lead=lead,
                selected_products=selected_products,
                normalized_products=normalized_products,
            )
            partial.plan = plan_object
        except Exception as e:
            partial.error = f"方案生成失败: {str(e)}"
            return partial

        # 5. Delivery
        try:
            delivery_request = DeliveryRequestV2(plan=plan_object)
            delivery_draft = build_delivery_draft(
                plan=plan_object,
                confirmed_client_info=None,
                language="en",
            )
            partial.delivery = delivery_draft
        except Exception as e:
            partial.error = f"交付生成失败: {str(e)}"
            return partial

        # 6. Format Markdown
        partial.itinerary_markdown = format_itinerary_markdown(
            lead=lead,
            product_match=product_match,
            pricing=partial.pricing,
            plan=partial.plan,
            delivery=partial.delivery,
        )

        partial.success = True
        partial.generated_at = generated_at
        return partial

    except Exception as e:
        partial.error = f"全链路执行失败: {str(e)}"
        return partial


# ── Item Names Lookup ─────────────────────────────────────────────


class ItemNamesResponse(BaseModel):
    success: bool
    items: Dict[str, str] = Field(default_factory=dict, description="Map of item code → display name")
    error: Optional[str] = None


@app.get("/api/v2/item-names", response_model=ItemNamesResponse)
async def get_item_names(
    city: str = "北京",
    codes: str = "",
    api_key: str = Depends(verify_api_key),
):
    """通过项目编号获取人类可读名称"""
    try:
        db = load_cost_db(city=city)
        code_list = [c.strip() for c in codes.split(",") if c.strip()]
        result = {}
        for code in code_list:
            item = db.get(code)
            if item:
                result[code] = item.get("name") or code
            else:
                result[code] = code
        return ItemNamesResponse(success=True, items=result)
    except Exception as e:
        return ItemNamesResponse(success=False, error=str(e))


# ── 飞书 API 扩展接口（预留）──────────────────────────────────────

class FeishuWebhookRequest(BaseModel):
    """飞书 Webhook 请求"""

    challenge: Optional[str] = Field(None, description="飞书验证挑战")
    token: Optional[str] = Field(None, description="验证 Token")
    type: Optional[str] = Field(None, description="事件类型")
    event: Optional[Dict[str, Any]] = Field(None, description="事件数据")


class FeishuWebhookResponse(BaseModel):
    """飞书 Webhook 响应"""

    challenge: Optional[str] = None
    message: str = "ok"


@app.post("/api/v1/feishu/webhook", response_model=FeishuWebhookResponse)
async def feishu_webhook(request: FeishuWebhookRequest):
    """飞书机器人 Webhook 接口（预留）"""
    if request.challenge:
        return FeishuWebhookResponse(challenge=request.challenge)
    return FeishuWebhookResponse(message="收到飞书事件")


@app.post("/api/v1/feishu/card", response_model=Dict[str, Any])
async def feishu_card_template(intent: UserIntentRequest, api_key: str = Depends(verify_api_key)):
    """飞书卡片模板接口（预留）"""
    try:
        user_intent = intent.model_dump()
        product = get_product_recommendation(user_intent)

        if product.get("error"):
            return {"success": False, "error": product["error"]}

        cost_result = calculate_total_cost(product, user_intent)
        grand_total = cost_result.get("summary", {}).get("grand_total", 0)

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🗺️ {product['product_name']}"},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**行程天数:** {product['days']} 天\n**团费总计:** ¥{grand_total:.0f}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**每日行程:**\n{product['itinerary']}",
                    },
                },
            ],
        }

        return {"success": True, "card": card}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 错误处理 ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"服务器内部错误: {str(exc)}",
            "timestamp": datetime.now().isoformat(),
        },
    )


# ── 启动入口 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
