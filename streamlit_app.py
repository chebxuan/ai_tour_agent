"""
Hexa Blueprint™ — Travel Copilot Streamlit Frontend
一键生成可发送客户的行程与报价

运行方式:
    streamlit run streamlit_app.py
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import requests
import streamlit as st

# ── 配置 ──────────────────────────────────────────────────────

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "hexa-tour-2024")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


# ── HR 演示视图辅助 ─────────────────────────────────────────────

def _demo_duration_label(duration_type: str) -> str:
    return "全天路线" if duration_type == "one_day" else "半天路线"


def _demo_price_summary(pricing: Dict[str, Any], route: Dict[str, Any]) -> Dict[str, Any]:
    if pricing and pricing.get("success"):
        summary = pricing.get("summary", {})
        return {
            "grand_total": summary.get("grand_total", 0),
            "per_person": summary.get("per_person", 0),
            "total_people": summary.get("total_people", 0),
        }
    return {
        "grand_total": route.get("estimated_cost_rmb", 0),
        "per_person": 0,
        "total_people": 0,
    }


def render_hr_demo_card(
    route: Dict[str, Any],
    pricing: Dict[str, Any],
    request_payload: Dict[str, Any],
) -> None:
    """一屏截图友好的 HR 演示摘要。"""
    units = route.get("units", [])
    transfers = route.get("transfers", [])
    price = _demo_price_summary(pricing, route)
    route_names = " → ".join([u.get("name_cn") or u.get("name_en", "") for u in units[:4]])
    tags = ", ".join(request_payload.get("interests", []))
    total_min = int(route.get("total_duration_min", 0) or 0)
    hours = f"{total_min // 60}h{total_min % 60}m" if total_min else "-"
    mapped_count = sum(1 for u in units if u.get("cost_item_code"))
    warning_count = len(route.get("risk_warnings", []))

    st.markdown(
        """
        <style>
        .hr-demo-card {
            border: 1px solid #ead9d6;
            background: linear-gradient(180deg, #fffafa 0%, #ffffff 62%);
            border-radius: 14px;
            padding: 24px 28px;
            margin: 8px 0 22px;
            box-shadow: 0 8px 24px rgba(30, 41, 59, 0.06);
        }
        .hr-demo-eyebrow {
            color: #f05a54;
            font-weight: 700;
            font-size: 14px;
            letter-spacing: .02em;
            margin-bottom: 6px;
        }
        .hr-demo-title {
            color: #272b3a;
            font-size: 34px;
            font-weight: 800;
            line-height: 1.18;
            margin-bottom: 8px;
        }
        .hr-demo-subtitle {
            color: #6b7280;
            font-size: 16px;
            margin-bottom: 18px;
        }
        .hr-demo-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 16px 0;
        }
        .hr-demo-metric {
            background: #f7f7fb;
            border-radius: 10px;
            padding: 12px 14px;
        }
        .hr-demo-label {
            color: #7a7f8d;
            font-size: 13px;
            margin-bottom: 4px;
        }
        .hr-demo-value {
            color: #272b3a;
            font-size: 22px;
            font-weight: 800;
            line-height: 1.15;
        }
        .hr-demo-section-title {
            color: #272b3a;
            font-size: 15px;
            font-weight: 800;
            margin-top: 16px;
            margin-bottom: 7px;
        }
        .hr-demo-route {
            color: #2f3443;
            background: #fff;
            border: 1px solid #ececf2;
            border-radius: 10px;
            padding: 12px 14px;
            font-size: 17px;
            font-weight: 700;
        }
        .hr-demo-note {
            color: #626978;
            font-size: 14px;
            line-height: 1.55;
        }
        .hr-demo-pill {
            display: inline-block;
            background: #fff1f0;
            color: #d9473f;
            border-radius: 999px;
            padding: 4px 10px;
            margin-right: 8px;
            margin-top: 6px;
            font-size: 13px;
            font-weight: 700;
        }
        @media (max-width: 900px) {
            .hr-demo-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .hr-demo-title { font-size: 28px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="hr-demo-card">
            <div class="hr-demo-eyebrow">HR DEMO SNAPSHOT · AI Travel Ops Copilot</div>
            <div class="hr-demo-title">上海半定制路线生成器</div>
            <div class="hr-demo-subtitle">
                输入客户画像后，系统自动完成画像匹配、POI 编排、交通检查、成本报价，并生成可发送客户的行程草稿。
            </div>
            <div>
                <span class="hr-demo-pill">{_demo_duration_label(request_payload.get("duration_type", ""))}</span>
                <span class="hr-demo-pill">兴趣: {tags or "culture"}</span>
                <span class="hr-demo-pill">人群: {request_payload.get("group_type", "-")}</span>
                <span class="hr-demo-pill">预算: {request_payload.get("budget_level", "-")}</span>
            </div>
            <div class="hr-demo-grid">
                <div class="hr-demo-metric">
                    <div class="hr-demo-label">推荐时长</div>
                    <div class="hr-demo-value">{hours}</div>
                </div>
                <div class="hr-demo-metric">
                    <div class="hr-demo-label">路线节点</div>
                    <div class="hr-demo-value">{len(units)} 个</div>
                </div>
                <div class="hr-demo-metric">
                    <div class="hr-demo-label">总价 / 人均</div>
                    <div class="hr-demo-value">¥{price["grand_total"]:,.0f} / ¥{price["per_person"]:,.0f}</div>
                </div>
                <div class="hr-demo-metric">
                    <div class="hr-demo-label">成本映射</div>
                    <div class="hr-demo-value">{mapped_count}/{len(units)}</div>
                </div>
            </div>
            <div class="hr-demo-section-title">生成路线</div>
            <div class="hr-demo-route">{route_names or "等待生成路线"}</div>
            <div class="hr-demo-section-title">技术亮点</div>
            <div class="hr-demo-note">
                35 个上海体验单元 + {len(transfers)} 段交通关系参与编排；报价接入城市 mashes 成本库；
                自动输出模板合规、交通风险和运营可审核说明。当前风险提示 {warning_count} 条。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── API 交互 ───────────────────────────────────────────────────

def api_get_cities() -> List[str]:
    try:
        resp = requests.get(f"{API_BASE}/api/v2/cities", headers=HEADERS, timeout=5)
        data = resp.json()
        return data.get("cities", [])
    except Exception:
        return ["北京", "上海", "广州", "重庆", "西安", "阳朔", "张家界", "贵州", "云南", "成都"]


def api_llm_status() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{API_BASE}/api/llm/status", headers=HEADERS, timeout=5)
        return resp.json()
    except Exception:
        return {
            "configured": False,
            "message": "无法读取 LLM 状态。表单生成仍可使用。",
        }


def api_record_human_approval(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(
        f"{API_BASE}/api/v2/human-approval",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )
    return resp.json()


def api_get_product_options(city: str, days: int) -> Dict[str, Any]:
    """获取产品的 optional item codes 以及名称映射"""
    try:
        payload = {
            "lead": {
                "lead_id": "preview",
                "contact": {"nationality": "International"},
                "travel_window": {},
                "passenger_mix": {"adults": 2},
                "intent": {
                    "destination_cities": [city],
                    "trip_days": days,
                },
            }
        }
        resp = requests.post(
            f"{API_BASE}/api/v2/product-match",
            json=payload,
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            prod = candidates[0]["product"]
            codes = candidates[0].get("optional_item_codes", [])
            # Fetch names for these codes
            names = {}
            if codes:
                try:
                    nr = requests.get(
                        f"{API_BASE}/api/v2/item-names",
                        params={"city": city, "codes": ",".join(codes)},
                        headers=HEADERS,
                        timeout=5,
                    )
                    ndata = nr.json()
                    if ndata.get("success"):
                        names = ndata.get("items", {})
                except Exception:
                    pass
            return {
                "product_name": prod.get("product_name", ""),
                "product_id": prod.get("product_id", ""),
                "duration_days": prod.get("duration_days", days),
                "daily_itinerary": prod.get("daily_itinerary", ""),
                "optional_codes": codes,
                "optional_names": names,
                "regular_codes": candidates[0].get("regular_item_codes", []),
            }
    except Exception:
        pass
    return {"product_name": "", "product_id": "", "duration_days": days, "daily_itinerary": "", "optional_codes": [], "optional_names": {}, "regular_codes": []}


def api_full_chain(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(
        f"{API_BASE}/api/v2/full_chain",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )
    return resp.json()


def api_lead_full_chain(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(
        f"{API_BASE}/api/v2/lead-full-chain",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )
    return resp.json()


def api_lead_text_full_chain(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(
        f"{API_BASE}/api/v2/lead-text-full-chain",
        json=payload,
        headers=HEADERS,
        timeout=75,
    )
    return resp.json()


def api_parse_lead(raw_text: str) -> Dict[str, Any]:
    resp = requests.post(
        f"{API_BASE}/api/lead/parse",
        json={"raw_text": raw_text, "source_channel": "streamlit"},
        headers=HEADERS,
        timeout=45,
    )
    return resp.json()


def api_custom_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    """调用上海半定制路线 API"""
    resp = requests.post(
        f"{API_BASE}/api/v2/custom-route",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )
    return resp.json()


def apply_lead_to_standard_form(lead: Dict[str, Any], cities: List[str]) -> None:
    intent = lead.get("intent", {})
    passenger_mix = lead.get("passenger_mix", {})
    destination_cities = intent.get("destination_cities") or []
    selected_city = destination_cities[0] if destination_cities else None

    if selected_city in cities:
        st.session_state.standard_city = selected_city
    if intent.get("trip_days"):
        st.session_state.standard_days = int(intent["trip_days"])

    st.session_state.standard_adults = int(passenger_mix.get("adults") or 1)
    st.session_state.standard_children = int(passenger_mix.get("children") or 0)
    st.session_state.standard_seniors = int(passenger_mix.get("seniors") or 0)

    interests = intent.get("interests") or []
    if interests:
        st.session_state.standard_interests = ", ".join(interests)

    if isinstance(intent.get("need_guide"), bool):
        st.session_state.standard_need_guide = intent["need_guide"]

    need_private_car = intent.get("need_private_car")
    st.session_state.standard_lead_parse_note = ""
    if isinstance(need_private_car, bool):
        st.session_state.standard_need_car = need_private_car
    elif need_private_car is None:
        st.session_state.standard_lead_parse_note = "私家车需求未确认，请运营人工确认后再生成报价。"


# ── 付款管理 API ───────────────────────────────────────────────

def api_get_payments(**filters) -> Dict[str, Any]:
    params = {k: v for k, v in filters.items() if v}
    resp = requests.get(f"{API_BASE}/api/v2/payments", params=params, headers=HEADERS, timeout=10)
    return resp.json()


def api_create_payment(data: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(f"{API_BASE}/api/v2/payments", json=data, headers=HEADERS, timeout=10)
    return resp.json()


def api_update_payment(payment_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.put(f"{API_BASE}/api/v2/payments/{payment_id}", json=data, headers=HEADERS, timeout=10)
    return resp.json()


def api_update_payment_status(payment_id: str, status: str) -> Dict[str, Any]:
    resp = requests.patch(f"{API_BASE}/api/v2/payments/{payment_id}/status", json={"status": status}, headers=HEADERS, timeout=10)
    return resp.json()


def api_delete_payment(payment_id: str) -> Dict[str, Any]:
    resp = requests.delete(f"{API_BASE}/api/v2/payments/{payment_id}", headers=HEADERS, timeout=10)
    return resp.json()


def api_get_suppliers() -> Dict[str, Any]:
    resp = requests.get(f"{API_BASE}/api/v2/payments/suppliers", headers=HEADERS, timeout=10)
    return resp.json()


def api_get_payment_stats() -> Dict[str, Any]:
    resp = requests.get(f"{API_BASE}/api/v2/payments/stats", headers=HEADERS, timeout=10)
    return resp.json()


# ── 页面 ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Travel Ops Copilot",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #17202a;
        --muted: #667085;
        --line: #e5e7eb;
        --panel: #ffffff;
        --soft: #f7f8fa;
        --accent: #2f6f73;
        --accent-soft: #e8f2f1;
        --warn-soft: #fff7ed;
    }
    .block-container {
        max-width: 1220px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3, p, li, div, label {
        letter-spacing: 0;
    }
    h1 {
        font-size: 30px !important;
        line-height: 1.25 !important;
        margin-bottom: 0.2rem !important;
        color: var(--ink);
    }
    h2 {
        font-size: 22px !important;
        margin-top: 0.4rem !important;
        color: var(--ink);
    }
    h3 {
        font-size: 18px !important;
        color: var(--ink);
    }
    [data-testid="stCaptionContainer"] {
        color: var(--muted);
        font-size: 14px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid var(--line);
        position: sticky;
        top: 0;
        z-index: 5;
        background: #fff;
        padding-top: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0 18px;
        font-weight: 650;
        color: #475467;
        border-radius: 0;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent);
        border-bottom: 2px solid var(--accent);
    }
    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 13px;
    }
    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 24px;
        font-weight: 760;
    }
    div[data-testid="stForm"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 18px 18px 10px;
        background: var(--panel);
    }
    div[data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
    }
    .app-title {
        display: flex;
        justify-content: space-between;
        gap: 24px;
        align-items: flex-end;
        margin-bottom: 16px;
    }
    .app-title h1 {
        margin: 0 !important;
    }
    .app-kicker {
        color: var(--accent);
        font-size: 13px;
        font-weight: 760;
        margin-bottom: 4px;
    }
    .app-subtitle {
        color: var(--muted);
        font-size: 15px;
        margin-top: 5px;
    }
    .page-head {
        margin: 18px 0 18px;
        padding: 18px 20px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fff;
    }
    .page-head-title {
        font-size: 21px;
        font-weight: 780;
        color: var(--ink);
        margin-bottom: 4px;
    }
    .page-head-copy {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.55;
        max-width: 860px;
    }
    .panel-title {
        font-size: 16px;
        color: var(--ink);
        font-weight: 760;
        margin: 4px 0 12px;
    }
    .soft-panel {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px 18px;
        background: var(--soft);
        margin-bottom: 14px;
    }
    .route-step {
        border-left: 3px solid var(--accent);
        padding: 10px 14px;
        margin: 10px 0;
        background: #fff;
        border-radius: 0 8px 8px 0;
        border-top: 1px solid var(--line);
        border-right: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
    }
    .route-step-title {
        font-weight: 750;
        color: var(--ink);
        font-size: 16px;
    }
    .route-step-meta {
        color: var(--muted);
        font-size: 13px;
        margin-top: 3px;
    }
    .route-step-desc {
        color: #344054;
        font-size: 14px;
        line-height: 1.55;
        margin-top: 8px;
    }
    .small-pill {
        display: inline-block;
        border: 1px solid #d8e7e5;
        background: var(--accent-soft);
        color: #20585b;
        border-radius: 999px;
        padding: 3px 9px;
        margin: 0 6px 6px 0;
        font-size: 12px;
        font-weight: 650;
    }
    .empty-state {
        border: 1px dashed #cfd6dd;
        border-radius: 8px;
        padding: 28px;
        background: #fbfcfd;
        color: var(--muted);
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-title">
      <div>
        <div class="app-kicker">AI Travel Ops Copilot</div>
        <h1>入境游运营工作台</h1>
        <div class="app-subtitle">把询单、报价、行程草稿和供应商付款放进同一个可审核流程。</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Tabs ──────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["行程生成", "上海半定制", "付款管理"])

# ==================================================================
# Tab 1: 行程生成 (existing functionality)
# ==================================================================

with tab1:
    if "standard_route_result" not in st.session_state:
        st.session_state.standard_route_result = None
    if "standard_lead_parse_result" not in st.session_state:
        st.session_state.standard_lead_parse_result = None
    if "standard_lead_parse_note" not in st.session_state:
        st.session_state.standard_lead_parse_note = ""

    st.markdown(
        """
        <div class="page-head">
          <div class="page-head-title">标准产品行程生成</div>
          <div class="page-head-copy">
            适合北京等标准线路：输入客户人数、天数和偏好后，系统匹配现有产品，计算报价，并生成可继续编辑的行程草稿。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    input_col, output_col = st.columns([0.38, 0.62], gap="large")

    with input_col:
        st.markdown('<div class="panel-title">客户需求</div>', unsafe_allow_html=True)
        cities = api_get_cities()
        with st.expander("AI 解析客户原文", expanded=False):
            llm_status = api_llm_status()
            llm_ready = bool(llm_status.get("configured"))
            if llm_ready:
                st.caption(f"LLM 已配置：{llm_status.get('model', '')}")
            else:
                st.info("LLM 未配置：AI 解析不可用，但下方表单生成、产品匹配和报价仍可使用。")

            raw_lead_text = st.text_area(
                "客户原文",
                height=130,
                placeholder="例如：We are two adults visiting Shanghai for 2 days. Private car is optional...",
            )
            parse_col, direct_col = st.columns(2)
            with parse_col:
                parse_clicked = st.button("解析为 LeadJSON", use_container_width=True, disabled=not llm_ready)
            with direct_col:
                direct_clicked = st.button("解析并直接生成", type="primary", use_container_width=True, disabled=not llm_ready)

            if parse_clicked or direct_clicked:
                if not raw_lead_text.strip():
                    st.warning("请先粘贴客户原文")
                elif parse_clicked:
                    with st.spinner("正在解析客户需求..."):
                        parsed = api_parse_lead(raw_lead_text.strip())
                    st.session_state.standard_lead_parse_result = parsed
                    if parsed.get("success") and parsed.get("lead"):
                        apply_lead_to_standard_form(parsed["lead"], cities)
                        st.success("已解析，并预填到下方表单。请人工确认后再生成报价。")
                    else:
                        st.error(parsed.get("error", "解析失败"))
                else:
                    with st.spinner("正在解析客户原文，并生成行程与报价..."):
                        result = api_lead_text_full_chain(
                            {
                                "raw_text": raw_lead_text.strip(),
                                "source_channel": "streamlit",
                                "is_peak": st.session_state.get("standard_is_peak", True),
                                "selected_optional_item_codes": st.session_state.get("standard_selected_optional", []),
                            }
                        )
                    st.session_state.standard_route_result = result
                    if result.get("lead"):
                        st.session_state.standard_lead_parse_result = {
                            "success": True,
                            "lead": result["lead"],
                            "generated_at": result.get("generated_at", ""),
                        }
                        apply_lead_to_standard_form(result["lead"], cities)
                    if result.get("success"):
                        st.success("已完成解析、匹配、报价和风险检查")
                    else:
                        st.error(result.get("error", "生成失败"))

            parsed_result = st.session_state.standard_lead_parse_result
            if parsed_result and parsed_result.get("lead"):
                st.json(parsed_result["lead"])
                if st.button("用解析结果一键生成行程与报价", type="primary", use_container_width=True):
                    lead = parsed_result["lead"]
                    with st.spinner("正在用 LeadJSON 跑产品匹配、报价和风险检查..."):
                        st.session_state.standard_route_result = api_lead_full_chain(
                            {
                                "lead": lead,
                                "is_peak": st.session_state.get("standard_is_peak", True),
                                "selected_optional_item_codes": st.session_state.get("standard_selected_optional", []),
                            }
                        )
                    if st.session_state.standard_route_result.get("success"):
                        st.success("已根据解析结果生成行程与报价")
                    else:
                        st.error(st.session_state.standard_route_result.get("error", "生成失败"))
            if st.session_state.standard_lead_parse_note:
                st.warning(st.session_state.standard_lead_parse_note)

        default_city = st.session_state.get("standard_city", cities[0] if cities else "北京")
        city_index = cities.index(default_city) if default_city in cities else 0
        with st.form("standard_route_form"):
            city = st.selectbox("目的地城市", cities, index=city_index, key="standard_city")
            days = st.number_input("行程天数", min_value=1, max_value=10, value=2, key="standard_days")

            person_a, person_b, person_c = st.columns(3)
            with person_a:
                adults = st.number_input("成人", min_value=1, max_value=10, value=2, key="standard_adults")
            with person_b:
                children = st.number_input("儿童", min_value=0, max_value=10, value=0, key="standard_children")
            with person_c:
                seniors = st.number_input("老人", min_value=0, max_value=10, value=0, key="standard_seniors")

            interests = st.text_input(
                "兴趣标签",
                value="history, culture",
                help="用英文逗号分隔，例如 history, culture",
                key="standard_interests",
            )
            travel_date = st.date_input("出行日期", value=None, help="可选")

            opt_a, opt_b, opt_c = st.columns(3)
            with opt_a:
                is_peak = st.checkbox("旺季价格", value=True, key="standard_is_peak")
            with opt_b:
                need_guide = st.checkbox("需要导游", value=False, key="standard_need_guide")
            with opt_c:
                need_car = st.checkbox("需要包车", value=True, key="standard_need_car")

            product_info = api_get_product_options(city, days)
            optional_codes = product_info.get("optional_codes", [])
            optional_names = product_info.get("optional_names", {})
            selected_optional = []
            if optional_codes:
                selected_optional = st.multiselect(
                    "可选项目",
                    options=optional_codes,
                    default=[],
                    format_func=lambda code: optional_names.get(code, code),
                    key="standard_selected_optional",
                )
            elif product_info.get("product_name"):
                st.caption("该产品暂无可选项目")
            else:
                st.caption("暂未加载到可选项目")

            generate_btn = st.form_submit_button("生成行程与报价", type="primary", use_container_width=True)

        st.markdown(
            """
            <div class="soft-panel">
              <div class="panel-title">适用场景</div>
              <div class="page-head-copy">
                固定产品、快速询价、销售初稿。需要深度换点或城市内体验组合时，建议使用“上海半定制”。
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with output_col:
        if generate_btn:
            with st.spinner("正在匹配产品、计算报价和生成行程草稿..."):
                interest_list = [i.strip() for i in interests.split(",") if i.strip()]
                payload = {
                    "city": city,
                    "days": days,
                    "adults": adults,
                    "children": children,
                    "seniors": seniors,
                    "is_peak": is_peak,
                    "need_guide": need_guide,
                    "need_private_car": need_car,
                    "interests": interest_list or ["history", "culture"],
                    "selected_optional_item_codes": selected_optional,
                }
                if travel_date:
                    payload["travel_date"] = travel_date.strftime("%Y-%m-%d")
                st.session_state.standard_route_result = api_full_chain(payload)

        result = st.session_state.standard_route_result

        if result and result.get("success"):
            st.success("行程已生成")

            pm = result.get("product_match", {})
            candidates = pm.get("candidates", [])
            if candidates:
                prod = candidates[0].get("product", {})
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("产品编号", prod.get("product_id", ""))
                with col_b:
                    st.metric("产品名称", prod.get("product_name", ""))
                with col_c:
                    st.metric("天数", f"{prod.get('duration_days', '')} 天")
                if prod.get("daily_itinerary"):
                    st.caption(f"每日行程：{prod['daily_itinerary'].replace(chr(10), ' | ')}")

            pricing = result.get("pricing", {})
            summary = pricing.get("summary", {})
            if summary:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总价", f"¥{summary['grand_total']:,.0f}")
                with col2:
                    st.metric("人均", f"¥{summary['per_person']:,.0f}")
                with col3:
                    st.metric("人数", f"{summary['total_people']}人")
                with col4:
                    label = "旺季" if summary.get("is_peak") else "淡季"
                    st.metric("季节", label)

            risk_check = result.get("risk_check") or {}
            risk_issues = risk_check.get("issues") or []
            if risk_issues:
                st.markdown("### 风险检查")
                if risk_check.get("human_review_required"):
                    st.warning("该行程需要人工复核")
                for issue in risk_issues:
                    severity = issue.get("severity", "warning")
                    message = f"{issue.get('code', '')}: {issue.get('message', '')}"
                    if severity == "blocking":
                        st.error(message)
                    elif severity == "info":
                        st.info(message)
                    else:
                        st.warning(message)

            st.markdown("### 行程草稿")
            md = result.get("itinerary_markdown", "")
            st.markdown(md)

            delivery_draft = result.get("delivery_draft") or {}
            if delivery_draft:
                st.markdown("### 销售邮件草稿")
                st.text_input("邮件标题", value=delivery_draft.get("subject", ""))
                st.markdown(delivery_draft.get("body_markdown", ""))

            with st.expander("原始数据", expanded=False):
                debug = dict(result)
                st.json(debug)

            st.markdown("### 人工确认")
            approval_notes = st.text_input("确认备注", value="", placeholder="例如：报价已核对，私家车另行确认")
            if st.button("人工确认通过", use_container_width=True):
                lead = result.get("lead") or {}
                approval = api_record_human_approval(
                    {
                        "lead_id": lead.get("lead_id"),
                        "approved": True,
                        "reviewer": "streamlit_operator",
                        "notes": approval_notes,
                    }
                )
                if approval.get("success"):
                    st.success("已记录 HumanApproved 节点")
                else:
                    st.error("人工确认记录失败")
        elif result:
            st.error(f"生成失败：{result.get('error', '未知错误')}")
        else:
            st.markdown(
                """
                <div class="empty-state">
                  左侧填写客户需求后生成结果。这里会显示产品匹配、价格、人均费用和行程草稿。
                </div>
                """,
                unsafe_allow_html=True,
            )


# ==================================================================
# Tab 2: 上海半定制路线 (Custom Route MVP)
# ==================================================================

with tab2:
    if "custom_route_result" not in st.session_state:
        st.session_state.custom_route_result = None
    if "custom_route_payload" not in st.session_state:
        st.session_state.custom_route_payload = None

    st.markdown(
        """
        <div class="page-head">
          <div class="page-head-title">上海半定制路线</div>
          <div class="page-head-copy">
            适合客户只给出偏好、预算和节奏时快速生成路线初稿。它不替代标准 21 产品，而是用体验单元补足“换点、半日、雨天、老人、情侣拍照”等场景。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    form_col, note_col = st.columns([0.7, 0.3], gap="large")

    with form_col:
        with st.form("custom_route_form"):
            row1_a, row1_b, row1_c = st.columns(3)
            with row1_a:
                custom_duration = st.selectbox(
                    "路线时长", ["one_day", "half_day"],
                    format_func=lambda x: "全天" if x == "one_day" else "半天",
                    key="custom_dur",
                )
            with row1_b:
                custom_group = st.selectbox(
                    "人群类型",
                    ["couple", "family", "solo", "senior"],
                    format_func=lambda x: {"couple": "情侣", "family": "家庭", "solo": "独自", "senior": "长者"}[x],
                    key="custom_group",
                )
            with row1_c:
                custom_pace = st.selectbox(
                    "节奏偏好",
                    ["moderate", "relaxed", "fast"],
                    format_func=lambda x: {"moderate": "适中", "relaxed": "慢节奏", "fast": "快节奏"}[x],
                    key="custom_pace",
                )

            custom_interests = st.multiselect(
                "兴趣标签",
                ["history", "culture", "photography", "architecture", "food", "cafe",
                 "shopping", "street life", "museum", "garden", "night view", "literature"],
                default=["culture", "photography"],
                key="custom_int",
            )

            row2_a, row2_b, row2_c, row2_d = st.columns(4)
            with row2_a:
                custom_budget = st.selectbox(
                    "预算等级",
                    ["medium", "low", "flexible"],
                    format_func=lambda x: {"medium": "中等", "low": "低预算", "flexible": "灵活"}[x],
                    key="custom_budget",
                )
            with row2_b:
                custom_adults = st.number_input("成人", 1, 10, 2, key="custom_adult")
            with row2_c:
                custom_children = st.number_input("儿童", 0, 10, 0, key="custom_child")
            with row2_d:
                custom_seniors = st.number_input("老人", 0, 10, 0, key="custom_senior")

            row3_a, row3_b, row3_c, row3_d = st.columns(4)
            with row3_a:
                custom_rain = st.checkbox("雨天模式", value=False, key="custom_rain")
            with row3_b:
                custom_car = st.checkbox("包车", value=False, key="custom_car")
            with row3_c:
                custom_guide = st.checkbox("英文导游", value=False, key="custom_guide")
            with row3_d:
                custom_is_peak = st.checkbox("旺季价格", value=True, key="custom_peak")

            custom_btn = st.form_submit_button("生成半定制路线", type="primary", use_container_width=True)

    with note_col:
        st.markdown(
            """
            <div class="soft-panel">
              <div class="panel-title">审核重点</div>
              <div class="page-head-copy">
                生成后重点看三件事：路线是否像客户会买的产品、交通是否过度跨区、报价是否进入成本库。
              </div>
            </div>
            <div class="soft-panel">
              <div class="panel-title">当前数据</div>
              <span class="small-pill">35 个体验单元</span>
              <span class="small-pill">12 个路线模板</span>
              <span class="small-pill">市内交通边</span>
              <span class="small-pill">部分成本映射</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if custom_btn:
        with st.spinner("正在编排路线 + 计算报价..."):
            payload = {
                "city": "上海",
                "duration_type": custom_duration,
                "interests": custom_interests or ["culture"],
                "pace": custom_pace,
                "budget_level": custom_budget,
                "group_type": custom_group,
                "adults": custom_adults,
                "children": custom_children,
                "seniors": custom_seniors,
                "is_peak": custom_is_peak,
                "rainy_day": custom_rain,
                "need_private_car": custom_car,
                "need_guide": custom_guide,
            }
            result = api_custom_route(payload)
            st.session_state.custom_route_result = result
            st.session_state.custom_route_payload = payload

    result = st.session_state.custom_route_result
    payload = st.session_state.custom_route_payload or {}

    if result:
        if result.get("success"):
            route = result.get("route", {})
            pricing = result.get("pricing", {})
            units = route.get("units", [])
            transfers = route.get("transfers", [])
            total_min = route.get("total_duration_min", 0)
            mapped_count = sum(1 for u in units if u.get("cost_item_code"))

            st.success("路线已生成")
            st.markdown(f"### {route.get('template_name', '推荐路线')}")
            st.caption(route.get("title_en", ""))

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("总时长", f"{total_min//60}h{total_min%60}m")
            with c2:
                st.metric("体验节点", f"{len(units)} 个")
            with c3:
                st.metric("交通时间", f"{route.get('transit_min', 0)} 分钟")
            with c4:
                st.metric("报价映射", f"{mapped_count}/{len(units)}")

            main_col, side_col = st.columns([0.64, 0.36], gap="large")

            with main_col:
                st.markdown('<div class="panel-title">推荐路线</div>', unsafe_allow_html=True)
                for u in units:
                    cost_label = f"¥{u['estimated_cost_rmb']:.0f}" if u["estimated_cost_rmb"] > 0 else "免费"
                    tags = []
                    if u.get("indoor_outdoor") == "indoor":
                        tags.append("室内")
                    elif u.get("indoor_outdoor") == "outdoor":
                        tags.append("室外")
                    if u.get("rainy_day_friendly"):
                        tags.append("雨天可用")
                    if u.get("elderly_friendly"):
                        tags.append("长者友好")
                    if u.get("cost_item_code"):
                        tags.append(f"成本码 {u['cost_item_code']}")
                    tag_html = "".join([f'<span class="small-pill">{tag}</span>' for tag in tags])
                    desc = (u.get("description_en") or "")[:260]
                    st.markdown(
                        f"""
                        <div class="route-step">
                          <div class="route-step-title">{u['sequence']}. {u['name_cn']} · {u['name_en']}</div>
                          <div class="route-step-meta">{u['area']} · {u['unit_type']} · {u['duration_min']} 分钟 · {cost_label}</div>
                          <div style="margin-top: 8px;">{tag_html}</div>
                          <div class="route-step-desc">{desc}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if transfers:
                    st.markdown('<div class="panel-title">交通衔接</div>', unsafe_allow_html=True)
                    for t in transfers:
                        status = "已匹配" if t.get("has_edge") else "需人工确认"
                        st.caption(
                            f"{t.get('from_area','')} → {t.get('to_area','')} · "
                            f"{t.get('mode','')} · 约 {t.get('transit_min',0)} 分钟 · {status}"
                        )

            with side_col:
                st.markdown('<div class="panel-title">报价</div>', unsafe_allow_html=True)
                if pricing and pricing.get("success"):
                    summary = pricing.get("summary", {})
                    st.metric("总价", f"¥{summary.get('grand_total', 0):,.0f}")
                    st.metric("人均", f"¥{summary.get('per_person', 0):,.0f}")
                    st.metric("人数", f"{summary.get('total_people', 0)} 人")

                    line_items = pricing.get("line_items", [])
                    if line_items:
                        with st.expander("费用明细", expanded=False):
                            for li in line_items:
                                st.caption(
                                    f"{li.get('name','')} · ¥{li.get('unit_price',0):,.0f} × "
                                    f"{li.get('quantity',0):.0f} = ¥{li.get('subtotal',0):,.0f}"
                                )
                else:
                    st.metric("估算成本", f"¥{route.get('estimated_cost_rmb', 0):.0f}")
                    st.caption(route.get("cost_note", ""))

                st.markdown('<div class="panel-title">审核提醒</div>', unsafe_allow_html=True)
                risks = route.get("risk_warnings", [])
                if risks:
                    for r in risks:
                        st.warning(r)
                else:
                    st.caption("暂无风险提示。")

                tc = route.get("template_compliance", {})
                if tc:
                    with st.expander("模板匹配", expanded=False):
                        st.caption(f"已满足：{tc.get('satisfied_types', [])}")
                        st.caption(f"未满足：{tc.get('unsatisfied_types', [])}")
                        st.caption(f"画像：{route.get('target_profile_summary', '')}")
                        st.caption(f"交通建议：{route.get('recommended_transport', '')}")

            with st.expander("编排过程", expanded=False):
                logic = route.get("route_logic", [])
                if logic:
                    for step in logic:
                        st.caption(step)
                else:
                    st.caption("暂无编排过程。")

            with st.expander("Markdown 行程单", expanded=False):
                md = result.get("itinerary_markdown", "")
                st.markdown(md)

        else:
            st.error(f"生成失败: {result.get('error', 'Unknown error')}")
    else:
        st.markdown(
            """
            <div class="empty-state">
              设置客户画像后生成路线。结果会显示路线节点、报价映射、交通衔接和人工审核提醒。
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==================================================================
# Tab 3: 供应商付款管理 (Payment Tracker)
# ==================================================================

with tab3:
    # ── Initialize session state ──
    if "show_payment_form" not in st.session_state:
        st.session_state.show_payment_form = False
    if "edit_payment_id" not in st.session_state:
        st.session_state.edit_payment_id = None
    if "payment_filter_status" not in st.session_state:
        st.session_state.payment_filter_status = "全部"
    if "payment_filter_supplier" not in st.session_state:
        st.session_state.payment_filter_supplier = ""
    if "payment_filter_search" not in st.session_state:
        st.session_state.payment_filter_search = ""

    st.markdown(
        """
        <div class="page-head">
          <div class="page-head-title">供应商付款管理</div>
          <div class="page-head-copy">
            跟踪待处理、已支付和已存档的供应商款项。适合运营每天查看付款状态、票据和关联订单。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load data ──
    stats_data = api_get_payment_stats()
    stats = stats_data.get("stats", {}) if stats_data.get("success") else {}

    # ── Stats Row ──
    st.markdown("### 看板概览")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("待处理", stats.get("pending_count", 0),
                  delta=f"¥{stats.get('pending_amount', 0):,.0f}")
    with c2:
        st.metric("已支付", stats.get("paid_count", 0),
                  delta=f"¥{stats.get('paid_amount', 0):,.0f}")
    with c3:
        st.metric("已存档", stats.get("archived_count", 0),
                  delta=f"¥{stats.get('archived_amount', 0):,.0f}")
    with c4:
        overdue = stats.get("overdue_count", 0)
        st.metric("逾期", overdue if overdue else "无",
                  delta=f"¥{stats.get('overdue_amount', 0):,.0f}" if overdue else None,
                  delta_color="inverse")
    with c5:
        st.metric("总计", stats.get("total_count", 0))
    st.divider()

    # ── Filter Bar ──
    st.markdown("### 筛选条件")
    fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 3, 2, 2])
    with fc1:
        status_filter = st.selectbox(
            "状态", ["全部", "pending", "paid", "archived"],
            key="payment_filter_status",
        )
    with fc2:
        supplier_filter = st.text_input("供应商", key="payment_filter_supplier")
    with fc3:
        search_input = st.text_input("搜索（编号/订单/客户）", key="payment_filter_search")
    with fc4:
        date_from = st.date_input("截止日期起", value=None)
    with fc5:
        date_to = st.date_input("截止日期止", value=None)

    st.divider()

    # ── New Payment Button ──
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("新建付款", type="primary", use_container_width=True):
            st.session_state.show_payment_form = True
            st.session_state.edit_payment_id = None
            st.rerun()

    # ── Create / Edit Payment Form ──
    if st.session_state.show_payment_form:
        st.markdown("---")
        is_edit = st.session_state.edit_payment_id is not None
        st.markdown(f"### {'编辑付款' if is_edit else '新建付款'}")

        # Pre-fill if editing
        prefill = {}
        if is_edit:
            detail_resp = requests.get(
                f"{API_BASE}/api/v2/payments/{st.session_state.edit_payment_id}",
                headers=HEADERS, timeout=10,
            ).json()
            if detail_resp.get("success") and detail_resp.get("payment"):
                prefill = detail_resp["payment"]

        with st.form("payment_form"):
            supplier_name = st.text_input(
                "供应商名称 *",
                value=prefill.get("supplier_name", ""),
                placeholder="输入供应商名称...",
            )
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                booking_id = st.text_input("Booking ID", value=prefill.get("booking_id", ""))
            with col_f2:
                related_order = st.text_input(
                    "关联客户订单",
                    value=prefill.get("related_customer_order", ""),
                )
            total_amount = st.number_input(
                "总金额 (¥)", min_value=0.0, step=100.0,
                value=float(prefill.get("total_amount", 0)),
            )
            col_f3, col_f4 = st.columns(2)
            with col_f3:
                due_date = st.date_input("截止日期", value=None)
            with col_f4:
                receipt_link = st.text_input(
                    "票据链接 (URL)",
                    value=prefill.get("receipt_link", ""),
                )
            notes = st.text_area("备注", value=prefill.get("notes", ""))

            st.caption("* 费用明细可在创建后编辑")

            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
                submitted = st.form_submit_button("保存", type="primary", use_container_width=True)
            with col_sub2:
                cancelled = st.form_submit_button("取消", use_container_width=True)

            if submitted and supplier_name.strip():
                data = {
                    "supplier_name": supplier_name.strip(),
                    "booking_id": booking_id or None,
                    "related_customer_order": related_order or None,
                    "total_amount": total_amount,
                    "due_date": due_date.strftime("%Y-%m-%d") if due_date else None,
                    "receipt_link": receipt_link or None,
                    "notes": notes or None,
                }
                if is_edit:
                    result = api_update_payment(st.session_state.edit_payment_id, data)
                else:
                    result = api_create_payment(data)
                if result.get("success"):
                    st.success("付款记录已保存！")
                else:
                    st.error(f"保存失败：{result.get('error', '未知错误')}")
                st.session_state.show_payment_form = False
                st.session_state.edit_payment_id = None
                st.rerun()

            if cancelled:
                st.session_state.show_payment_form = False
                st.session_state.edit_payment_id = None
                st.rerun()

    # ── Detail View ──
    if st.session_state.edit_payment_id and not st.session_state.show_payment_form:
        detail_resp = requests.get(
            f"{API_BASE}/api/v2/payments/{st.session_state.edit_payment_id}",
            headers=HEADERS, timeout=10,
        ).json()
        if detail_resp.get("success") and detail_resp.get("payment"):
            p = detail_resp["payment"]
            with st.expander(f"付款详情: {p.get('payment_id')} — {p.get('supplier_name')}", expanded=True):
                col_d1, col_d2, col_d3 = st.columns(3)
                with col_d1:
                    st.markdown(f"**付款编号:** {p.get('payment_id')}")
                    st.markdown(f"**供应商:** {p.get('supplier_name')}")
                    st.markdown(f"**金额:** ¥{p.get('total_amount', 0):,.0f}")
                with col_d2:
                    st.markdown(f"**状态:** {p.get('status')}")
                    st.markdown(f"**截止日期:** {p.get('due_date', '-')}")
                    st.markdown(f"**实际支付日:** {p.get('actual_payment_date', '-')}")
                with col_d3:
                    st.markdown(f"**Booking ID:** {p.get('booking_id', '-')}")
                    st.markdown(f"**客户订单:** {p.get('related_customer_order', '-')}")
                    st.markdown(f"**票据:** {p.get('receipt_link', '-')}")
                if p.get("notes"):
                    st.caption(f"备注: {p['notes']}")

                col_da, col_db, col_dc = st.columns(3)
                with col_da:
                    if p.get("status") == "pending":
                        if st.button("标记已支付", key=f"pay_{p['payment_id']}"):
                            api_update_payment_status(p["payment_id"], "paid")
                            st.rerun()
                with col_db:
                    if p.get("status") in ("pending", "paid"):
                        if st.button("存档", key=f"arch_{p['payment_id']}"):
                            api_update_payment_status(p["payment_id"], "archived")
                            st.rerun()
                with col_dc:
                    if st.button("关闭", key=f"cls_{p['payment_id']}"):
                        st.session_state.edit_payment_id = None
                        st.rerun()

    # ── Load filtered payments ──
    filter_kwargs = {}
    if status_filter != "全部":
        filter_kwargs["status"] = status_filter
    if supplier_filter.strip():
        filter_kwargs["supplier"] = supplier_filter.strip()
    if search_input.strip():
        filter_kwargs["search"] = search_input.strip()
    if date_from:
        filter_kwargs["date_from"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        filter_kwargs["date_to"] = date_to.strftime("%Y-%m-%d")

    payments_data = api_get_payments(**filter_kwargs)
    payments = payments_data.get("payments", [])

    # Split by status
    pending_list = [p for p in payments if p.get("status") == "pending"]
    paid_list = [p for p in payments if p.get("status") == "paid"]
    archived_list = [p for p in payments if p.get("status") == "archived"]

    # ── Kanban Board ──
    st.markdown("---")
    st.markdown("### 看板")
    kanban1, kanban2, kanban3 = st.columns(3)

    def render_card(p: Dict[str, Any]) -> None:
        """Render a single payment card."""
        pid = p.get("payment_id", "")
        status_text = {"pending": "待处理", "paid": "已支付", "archived": "已存档"}.get(p.get("status"), "")
        overdue = p.get("status") == "pending" and p.get("due_date") and p["due_date"] < datetime.now().strftime("%Y-%m-%d")

        with st.container(border=True):
            st.markdown(f"**{p.get('supplier_name', '')}**")
            st.caption(f"ID: {pid} | {status_text}")
            st.metric("金额", f"¥{p.get('total_amount', 0):,.0f}")
            if p.get("due_date"):
                due_label = f"逾期: {p['due_date']}" if overdue else f"截止: {p['due_date']}"
                st.caption(due_label)
            if p.get("booking_id"):
                st.caption(f"Booking: {p['booking_id']}")

            if p.get("status") == "pending":
                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    if st.button("支付", key=f"kpay_{pid}", use_container_width=True):
                        api_update_payment_status(pid, "paid")
                        st.rerun()
                with c_act2:
                    if st.button("存档", key=f"karch_{pid}", use_container_width=True):
                        api_update_payment_status(pid, "archived")
                        st.rerun()
            elif p.get("status") == "paid":
                if st.button("存档", key=f"karch2_{pid}", use_container_width=True):
                    api_update_payment_status(pid, "archived")
                    st.rerun()

            if st.button("详情/编辑", key=f"kedit_{pid}", use_container_width=True):
                st.session_state.edit_payment_id = pid
                st.rerun()

    with kanban1:
        st.subheader(f"待处理 ({len(pending_list)})")
        if not pending_list:
            st.caption("暂无待处理付款")
        for p in pending_list:
            render_card(p)

    with kanban2:
        st.subheader(f"已支付 ({len(paid_list)})")
        if not paid_list:
            st.caption("暂无已支付付款")
        for p in paid_list:
            render_card(p)

    with kanban3:
        st.subheader(f"已存档 ({len(archived_list)})")
        if not archived_list:
            st.caption("暂无已存档付款")
        for p in archived_list:
            render_card(p)
