"""
Hexa Blueprint™ API - 多城市行程规划服务

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

from engines.city_config import list_available_cities, get_city_code_prefix
from engines.cost_engine import calculate_total_cost, load_cost_db
from engines.custom_route_engine import generate_route as generate_custom_route
from engines.payment_tracker import (
    create_payment,
    delete_payment,
    get_kanban_stats,
    get_payment,
    list_payments,
    load_cost_items_from_mashes,
    load_suppliers_from_mashes,
    update_payment,
    update_payment_status,
)

from schemas import (
    CandidateProductsJSON,
    ContactInfo,
    LeadIntent,
    LeadJSON,
    PassengerMix,
    PaymentCostItem,
    PaymentCreateRequest,
    PaymentDetailResponse,
    PaymentEntry,
    PaymentListResponse,
    PaymentStatsResponse,
    PaymentStatusUpdate,
    PaymentSuppliersResponse,
    PaymentUpdateRequest,
    PricingResultJSON,
    ProductCandidate,
    ProductCandidateReason,
    ProductReference,
    TravelWindow,
)

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


def format_itinerary_markdown(
    lead: LeadJSON,
    product_match: CandidateProductsJSON,
    pricing: Optional[PricingResultJSON],
    normalized_product: Optional[Dict[str, Any]] = None,
) -> str:
    """将全链路输出格式化为 Markdown 行程单
    结构：标题 → 产品信息 → 每日行程（day_plans + Highlights） → 可选项目 → 报价明细 → 提示
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
        lines.append("")

    # ── Day-by-Day Itinerary ──
    highlights_data = load_highlights_data()
    city_h = highlights_data.get(lead.intent.destination_cities[0], {}) if lead.intent.destination_cities else {}
    product_id = top.product.product_id if top else ""
    day_routes = city_h.get("product_days", {}).get(product_id, {})
    all_routes = city_h.get("routes", {})

    # 从 normalized product 或 itinerary_text 提取 day_plans
    day_plans_data = []
    if normalized_product:
        day_plans_data = normalized_product.get("day_plans", [])
    # fallback: 从 top.product.daily_itinerary 解析
    if not day_plans_data and top and top.product.daily_itinerary:
        for line in top.product.daily_itinerary.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # 格式: "Day 1: 景点A+景点B+..."
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0].strip().lower().startswith("day"):
                day_num_str = parts[0].strip().replace("Day ", "").replace("day ", "")
                try:
                    day_num = int(day_num_str)
                except ValueError:
                    day_num = len(day_plans_data) + 1
                act_names = [a.strip() for a in parts[1].split("+") if a.strip()]
                day_plans_data.append({"day_number": day_num, "activity_names": act_names})

    if day_plans_data:
        lines.append("## 每日行程 Day-by-Day Itinerary")
        lines.append("")
        for day in day_plans_data:
            day_num = day.get("day_number", len(lines))
            route_key = day_routes.get(str(day_num))
            route = all_routes.get(route_key) if route_key else None

            # Day header
            lines.append(f"### 第{day_num}天 Day {day_num}")
            if route and route.get("title"):
                lines.append(f"*{route['title']}*")
            lines.append("")

            # Activity list
            activity_names = day.get("activity_names", [])
            if activity_names:
                for act in activity_names:
                    marker = ""
                    if any(kw in act for kw in ["(可选)", "(建议)", "(推荐)"]):
                        marker = " *(可选 Optional)*"
                    clean = act
                    for kw in ["(可选)", "(建议)", "(推荐)"]:
                        clean = clean.replace(kw, "")
                    lines.append(f"▪ {clean.strip()}{marker}")
                lines.append("")

            # Highlights from attraction_highlights.json
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

            lines.append("---")
            lines.append("")

    # ── Optional Add-ons ──
    if top and top.optional_item_codes:
        lines.append("### 可选项目 Optional Add-ons")
        lines.append("")
        _opt_db = load_cost_db(city=top.product.city) if top.product.city else {}
        for code in top.optional_item_codes:
            name = _opt_db.get(code, {}).get("name") or code
            lines.append(f"- {name} ({code})")
        lines.append("")

    # ── Cost Breakdown ──
    if pricing and pricing.summary:
        lines.append("## 费用明细 Cost Breakdown")
        lines.append("")
        lines.append(f"_{pricing.summary.product_name} — {pricing.summary.city}_")
        season_label = "旺季 Peak Season" if pricing.summary.is_peak else "淡季 Off-Peak Season"
        lines.append(f"_{pricing.summary.adults} 成人 Adult(s) | {pricing.summary.children} 儿童 Child(ren) | {pricing.summary.seniors} 老人 Senior(s) | {season_label}_")
        lines.append("")

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

    # ── Notes ──
    lines.append("## 重要提示 Important Notes")
    lines.append("")
    lines.append("- Please carry your passport for attraction entry where required.")
    lines.append("- Meals are not included unless specified above.")
    lines.append("- Tipping is not mandatory but appreciated for good service.")
    lines.append("- Keep valuables secure in crowded areas.")
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

@app.get("/api/v2/cities", response_model=Dict[str, Any])
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


class FullChainRequest(BaseModel):
    """一键全链路请求 — 简化输入，内部串联 product → pricing，输出行程 + Highlights + 报价"""

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
    itinerary_markdown: str = ""
    error: Optional[str] = None
    generated_at: str = ""


@app.post("/api/v2/full_chain", response_model=FullChainResponse)
async def full_chain_v2(request: FullChainRequest, api_key: str = Depends(verify_api_key)):
    """一键全链路接口：简化输入 → 产品匹配 → 报价 + Markdown 行程单

    输入只需城市、天数、人数等基本信息，内部自动串联 product-match + pricing。
    输出包含结构化 JSON 和可直接发送客户的 Markdown 行程（day_plans + Highlights + 报价表）。
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

        # 3. Pricing
        try:
            product = get_normalized_product_by_id(top_product_id)
            hotel_nights = max(int(product.get("duration_days", 1)) - 1, 0) if product else max(request.days - 1, 0)
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

        # 4. Format Markdown（直接使用 normalized product day_plans + highlights + pricing）
        partial.itinerary_markdown = format_itinerary_markdown(
            lead=lead,
            product_match=product_match,
            pricing=partial.pricing,
            normalized_product=product,
        )

        partial.success = True
        partial.generated_at = generated_at
        return partial

    except Exception as e:
        partial.error = f"全链路执行失败: {str(e)}"
        return partial


# ── Custom Route (上海 MVP 半定制路线) ────────────────────────────


class CustomRouteRequest(BaseModel):
    """上海半定制路线请求"""

    city: str = Field("上海", description="目标城市（目前仅支持上海）")
    duration_type: str = Field("one_day", description="半天还是全天: half_day / one_day")
    interests: List[str] = Field(default_factory=lambda: ["culture"], description="兴趣标签")
    pace: str = Field("moderate", description="节奏: relaxed / moderate / fast")
    budget_level: str = Field("medium", description="预算: low / medium / flexible")
    group_type: str = Field("couple", description="人群: couple / family / solo / senior")
    adults: int = Field(2, ge=1, description="成人数量")
    children: int = Field(0, ge=0, description="儿童数量")
    seniors: int = Field(0, ge=0, description="老人数量")
    is_peak: bool = Field(True, description="是否旺季")
    rainy_day: bool = Field(False, description="是否雨天")
    need_private_car: bool = Field(False, description="是否包车")
    need_guide: bool = Field(False, description="是否需要导游")


class CustomRouteResponse(BaseModel):
    """半定制路线响应"""

    success: bool
    route: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    itinerary_markdown: str = ""
    error: Optional[str] = None


@app.post("/api/v2/custom-route", response_model=CustomRouteResponse)
async def build_custom_route(request: CustomRouteRequest, api_key: str = Depends(verify_api_key)):
    """上海半定制路线：兴趣匹配 → POI 编排 → 报价 → Markdown 行程单"""
    try:
        # 1. 调用 custom_route_engine 生成路线
        route = generate_custom_route(
            city=request.city,
            duration_type=request.duration_type,
            interests=request.interests,
            pace=request.pace,
            budget_level=request.budget_level,
            group_type=request.group_type,
            rainy_day=request.rainy_day,
            need_private_car=request.need_private_car,
            family_travel=request.children > 0,
            elderly_travel=request.seniors > 0,
        )

        if not route.get("success"):
            return CustomRouteResponse(success=False, error=route.get("error", "路线生成失败"))

        # 2. 提取选中的 cost_item_code 接入 cost_engine 报价
        selected_units = route.get("units", [])
        cost_item_codes = [
            u.get("cost_item_code") for u in selected_units
            if u.get("cost_item_code")
        ]

        # 构建最小产品 dict（模拟 cost_engine 需要的 product 格式）
        product = {
            "city": request.city,
            "days": 1,
            "product_name": route.get("title_en", f"Custom {request.city} Route"),
            "常规项目项目编号列表": ", ".join(cost_item_codes),
            "regular_item_codes": cost_item_codes,
        }

        # 自动推断 hotel/guide/car 编码
        prefix = get_city_code_prefix(request.city)
        user_intent = {
            "city": request.city,
            "days": 1,
            "adults": request.adults,
            "children": request.children,
            "seniors": request.seniors,
            "is_peak": request.is_peak,
            "guide": f"{prefix}-GUIDE-01" if request.need_guide else None,
            "need_guide": request.need_guide,
            "hotel": f"{prefix}-HOTEL-01" if request.duration_type == "one_day" else None,
            "hotel_nights": 1 if request.duration_type == "one_day" else 0,
            "transfer": f"{prefix}-TRANS-03" if request.need_private_car else None,
            "transfer_times": 2 if request.need_private_car else 0,
            "car_days": 1 if request.need_private_car else 0,
            "need_private_car": request.need_private_car,
            "selected_optional": [],
        }

        try:
            pricing_result = calculate_total_cost(product, user_intent)
        except Exception as e:
            pricing_result = {
                "success": False,
                "error": f"报价计算失败: {str(e)}",
                "summary": {"grand_total": route.get("estimated_cost_rmb", 0), "per_person": 0, "total_people": request.adults + request.children + request.seniors},
            }

        # 3. 生成 Markdown 行程单
        md = _format_custom_route_markdown(route, pricing_result, request)

        return CustomRouteResponse(
            success=True,
            route=route,
            pricing=pricing_result if pricing_result.get("success") else None,
            itinerary_markdown=md,
        )

    except Exception as e:
        return CustomRouteResponse(success=False, error=f"半定制路线生成失败: {str(e)}")


def _format_custom_route_markdown(
    route: Dict[str, Any],
    pricing: Dict[str, Any],
    request: CustomRouteRequest,
) -> str:
    """将 custom_route 输出格式化为 Markdown 行程单"""
    lines: List[str] = []

    title = route.get("title_en", "Custom Shanghai Route")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Profile:** {route.get('target_profile_summary', '')}")
    lines.append(f"**Duration:** {route.get('duration_type', '')}  |  "
                 f"**Pace:** {request.pace}  |  **Budget:** {request.budget_level}")
    lines.append(f"**Travelers:** {request.adults} Adult(s)" +
                 (f" + {request.children} Child(ren)" if request.children else "") +
                 (f" + {request.seniors} Senior(s)" if request.seniors else ""))
    if request.rainy_day:
        lines.append(f"**Weather Note:** 🌧️ Rainy day — indoor-focused route")
    lines.append("")

    # 路线节点
    lines.append("## 推荐路线 Route Plan")
    lines.append("")
    units = route.get("units", [])
    for u in units:
        seq = u.get("sequence", 0)
        name = u.get("name_en", "")
        name_cn = u.get("name_cn", "")
        area = u.get("area", "")
        dur = u.get("duration_min", 0)
        cost = u.get("estimated_cost_rmb", 0)
        cost_label = f"¥{cost:.0f}" if cost > 0 else "Free"
        desc = u.get("description_en", "")[:150]
        lines.append(f"### {seq}. {name} ({name_cn})")
        lines.append(f"📍 {area}  |  ⏱ {dur}min  |  💰 {cost_label}")
        if desc:
            lines.append(f"_{desc}_")
        lines.append("")

    # 交通
    transfers = route.get("transfers", [])
    if transfers:
        lines.append("## 交通 Transfers")
        lines.append("")
        for t in transfers:
            mode = t.get("mode", "unknown")
            tmin = t.get("transit_min", 0)
            from_area = t.get("from_area", "")
            to_area = t.get("to_area", "")
            has_edge = "✅" if t.get("has_edge") else "⚠️ estimated"
            lines.append(f"- **{from_area} → {to_area}**: {mode} ~{tmin}min {has_edge}")
        lines.append("")

    # 报价
    if pricing and pricing.get("success"):
        summary = pricing.get("summary", {})
        lines.append("## 报价 Pricing")
        lines.append("")
        season_label = "Peak Season" if request.is_peak else "Off-Peak Season"
        lines.append(f"_{request.adults} Adult(s) | {season_label} | "
                     f"{'with guide' if request.need_guide else 'no guide'} | "
                     f"{'private car' if request.need_private_car else 'metro/walk'}_")
        lines.append("")

        line_items = pricing.get("line_items", [])
        if line_items:
            lines.append("| Category | Item | Unit Price | Qty | Subtotal |")
            lines.append("|----------|------|-----------|-----|----------|")
            for li in line_items:
                lines.append(f"| {li.get('category','')} | {li.get('name','')} | ¥{li.get('unit_price',0):,.0f} | {li.get('quantity',0):.0f} | ¥{li.get('subtotal',0):,.0f} |")

        lines.append("")
        lines.append(f"| | **Grand Total** | | | **¥{summary.get('grand_total', 0):,.2f}** |")
        lines.append(f"| | **Per Person** | | | **¥{summary.get('per_person', 0):,.2f}** |")
        lines.append("")
    else:
        lines.append("## 报价 Pricing")
        lines.append("")
        lines.append(f"**Estimated Total:** ¥{route.get('estimated_cost_rmb', 0):.0f}")
        lines.append(f"_Note: {route.get('cost_note', '')}_")
        lines.append("")

    # 逻辑与风险
    logic = route.get("route_logic", [])
    if logic:
        lines.append("## 编排逻辑 Route Logic")
        lines.append("")
        for step in logic:
            lines.append(f"- {step}")
        lines.append("")

    risks = route.get("risk_warnings", [])
    if risks:
        lines.append("## 注意事项 Risk Warnings")
        lines.append("")
        for r in risks:
            lines.append(f"- ⚠️ {r}")
        lines.append("")

    # 定制选项
    options = route.get("customization_options", [])
    if options:
        lines.append("## 可定制项 Customization Options")
        lines.append("")
        for opt in options:
            lines.append(f"- **{opt.get('type')}**: {opt.get('description')} ({opt.get('cost_impact', '')})")
        lines.append("")

    lines.append("---")
    lines.append("_Generated by Hexa Blueprint™ Custom Route Engine (Shanghai MVP)_")
    return "\n".join(lines)


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


# ── Supplier Payment Management (Kanban) ────────────────────────────


@app.get("/api/v2/payments", response_model=PaymentListResponse)
async def list_payments_endpoint(
    supplier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
):
    """List and filter payments with kanban stats."""
    try:
        payments = list_payments(
            supplier=supplier,
            status=status,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        stats = get_kanban_stats()
        return PaymentListResponse(
            success=True,
            payments=[PaymentEntry(**p) for p in payments],
            total_count=len(payments),
            stats=stats,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"付款列表查询失败: {str(e)}",
        )


@app.post("/api/v2/payments", response_model=PaymentDetailResponse)
async def create_payment_endpoint(
    request: PaymentCreateRequest,
    api_key: str = Depends(verify_api_key),
):
    """Create a new payment entry."""
    try:
        payment = create_payment(request.model_dump())
        return PaymentDetailResponse(success=True, payment=PaymentEntry(**payment))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建付款失败: {str(e)}",
        )


@app.get("/api/v2/payments/suppliers", response_model=PaymentSuppliersResponse)
async def get_suppliers_endpoint(api_key: str = Depends(verify_api_key)):
    """Get all supplier names and cost items from mashes data."""
    try:
        suppliers = load_suppliers_from_mashes()
        cost_items = load_cost_items_from_mashes()
        return PaymentSuppliersResponse(
            success=True, suppliers=suppliers, cost_items=cost_items
        )
    except Exception as e:
        return PaymentSuppliersResponse(success=False, error=str(e))


@app.get("/api/v2/payments/stats", response_model=PaymentStatsResponse)
async def get_payment_stats_endpoint(api_key: str = Depends(verify_api_key)):
    """Get kanban aggregate statistics."""
    try:
        stats = get_kanban_stats()
        return PaymentStatsResponse(success=True, stats=stats)
    except Exception as e:
        return PaymentStatsResponse(success=False, error=str(e))


@app.get("/api/v2/payments/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment_endpoint(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Get a single payment by ID."""
    payment = get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到付款记录: {payment_id}",
        )
    return PaymentDetailResponse(success=True, payment=PaymentEntry(**payment))


@app.put("/api/v2/payments/{payment_id}", response_model=PaymentDetailResponse)
async def update_payment_endpoint(
    payment_id: str,
    request: PaymentUpdateRequest,
    api_key: str = Depends(verify_api_key),
):
    """Update a payment entry (does not change status)."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    payment = update_payment(payment_id, updates)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到付款记录: {payment_id}",
        )
    return PaymentDetailResponse(success=True, payment=PaymentEntry(**payment))


@app.patch("/api/v2/payments/{payment_id}/status", response_model=PaymentDetailResponse)
async def update_payment_status_endpoint(
    payment_id: str,
    request: PaymentStatusUpdate,
    api_key: str = Depends(verify_api_key),
):
    """Update only the payment status (pending -> paid -> archived)."""
    try:
        payment = update_payment_status(payment_id, request.status)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到付款记录: {payment_id}",
            )
        return PaymentDetailResponse(success=True, payment=PaymentEntry(**payment))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"状态更新失败: {str(e)}",
        )


@app.delete("/api/v2/payments/{payment_id}")
async def delete_payment_endpoint(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Delete a payment entry."""
    deleted = delete_payment(payment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到付款记录: {payment_id}",
        )
    return {"success": True, "message": f"已删除付款记录: {payment_id}"}


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
