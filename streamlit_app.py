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


def api_custom_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    """调用上海半定制路线 API"""
    resp = requests.post(
        f"{API_BASE}/api/v2/custom-route",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )
    return resp.json()


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
    page_title="Travel Copilot",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("✈️ Inbound Travel AI Copilot")
st.caption("面向入境游运营：一键生成可发送客户的行程与报价")

# ── 侧边栏输入 ────────────────────────────────────────────────

with st.sidebar:
    st.header("📋 客户需求")

    cities = api_get_cities()
    city = st.selectbox("目的地城市", cities, index=0)

    days = st.number_input("行程天数", min_value=1, max_value=10, value=2)

    st.subheader("人数构成")
    col1, col2, col3 = st.columns(3)
    with col1:
        adults = st.number_input("成人", min_value=1, max_value=10, value=2)
    with col2:
        children = st.number_input("儿童", min_value=0, max_value=10, value=0)
    with col3:
        seniors = st.number_input("老人", min_value=0, max_value=10, value=0)

    is_peak = st.checkbox("旺季价格", value=True)

    col_a, col_b = st.columns(2)
    with col_a:
        need_guide = st.checkbox("需要导游", value=False)
    with col_b:
        need_car = st.checkbox("需要包车", value=True)

    interests = st.text_input("兴趣标签（逗号分隔）", value="history, culture")

    travel_date = st.date_input("出行日期", value=None, help="客户出行起始日期（可选）")

    # ── 动态获取可选项目 ──
    st.subheader("可选项目")
    product_info = api_get_product_options(city, days)
    optional_codes = product_info.get("optional_codes", [])

    # 获取可选项目的人类可读名称
    optional_names = product_info.get("optional_names", {})
    selected_optional = []
    if optional_codes:
        selected_optional = st.multiselect(
            "选择 optional 项目",
            options=optional_codes,
            default=[],
            format_func=lambda code: optional_names.get(code, code),
        )
    elif product_info.get("product_name"):
        st.caption("该产品无可选项目")
    else:
        st.caption("加载中...")

    generate_btn = st.button("🚀 生成行程", type="primary", use_container_width=True)

# ── Tabs ──────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["✈️ 行程生成", "🏙️ 上海半定制", "💳 付款管理"])

# ==================================================================
# Tab 1: 行程生成 (existing functionality)
# ==================================================================

with tab1:
    if generate_btn:
        with st.spinner("正在生成行程，请稍候..."):
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

            result = api_full_chain(payload)

        if result.get("success"):
            st.success("✅ 行程生成成功！")

            pm = result.get("product_match", {})
            candidates = pm.get("candidates", [])
            if candidates:
                prod = candidates[0].get("product", {})
                with st.container():
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("产品编号", prod.get("product_id", ""))
                    with col_b:
                        st.metric("产品名称", prod.get("product_name", ""))
                    with col_c:
                        st.metric("行程天数", f"{prod.get('duration_days', '')} 天")
                    if prod.get("daily_itinerary"):
                        st.caption(f"📋 每日行程：{prod['daily_itinerary'].replace(chr(10), ' | ')}")
                st.divider()

            st.markdown("## 📅 行程草稿")
            md = result.get("itinerary_markdown", "")
            st.markdown(md)

            st.divider()

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

            with st.expander("🔧 原始数据（Debug）"):
                debug = dict(result)
                st.json(debug)
        else:
            st.error(f"❌ 生成失败：{result.get('error', '未知错误')}")

    else:
        st.info("👈 请在左侧填写客户需求，然后点击「生成行程」")

        with st.expander("💡 使用说明"):
            st.markdown("""
            ### 使用流程
            1. 选择**目的地城市**和**行程天数**
            2. 填写**人数构成**（成人/儿童/老人）
            3. 选择**兴趣标签**和**可选项目**
            4. 点击「生成行程」按钮

            ### 输出内容
            - **行程草稿**：可直接复制发送客户的 Markdown 文本
            - **报价概览**：总价、人均、分类明细
            - **原始数据**：完整链路 JSON（用于 Debug）

            ### 支持的城市
            """ + ", ".join(cities))

        with st.expander("📋 示例输入"):
            st.markdown("""
            ```
            城市: 北京
            天数: 2
            人数: 2 成人
            兴趣: history, culture
            ```
            """)


# ==================================================================
# Tab 2: 上海半定制路线 (Custom Route MVP)
# ==================================================================

with tab2:
    if "custom_route_result" not in st.session_state:
        st.session_state.custom_route_result = None
    if "custom_route_payload" not in st.session_state:
        st.session_state.custom_route_payload = None

    st.subheader("🏙️ 上海半定制路线生成器")
    st.caption("基于 POI 最小单元 + 人群画像 + 交通规则的半定制路线编排（与固定 21 产品链路并行）")

    col_left, col_right = st.columns(2)

    with col_left:
        custom_duration = st.selectbox(
            "路线时长", ["one_day", "half_day"],
            format_func=lambda x: "全天 (One Day)" if x == "one_day" else "半天 (Half Day)",
            key="custom_dur"
        )

        custom_interests = st.multiselect(
            "兴趣标签",
            ["history", "culture", "photography", "architecture", "food", "cafe",
             "shopping", "street life", "museum", "garden", "night view", "literature"],
            default=["culture", "photography"],
            key="custom_int"
        )

        custom_pace = st.selectbox(
            "节奏偏好",
            ["moderate", "relaxed", "fast"],
            format_func=lambda x: {"moderate": "适中 Moderate", "relaxed": "慢节奏 Relaxed", "fast": "快节奏 Fast"}[x],
            key="custom_pace"
        )

    with col_right:
        custom_budget = st.selectbox(
            "预算等级",
            ["medium", "low", "flexible"],
            format_func=lambda x: {"medium": "中等 Medium", "low": "低预算 Budget", "flexible": "灵活 Flexible"}[x],
            key="custom_budget"
        )

        custom_group = st.selectbox(
            "人群类型",
            ["couple", "family", "solo", "senior"],
            format_func=lambda x: {"couple": "情侣 Couple", "family": "家庭 Family", "solo": "独自 Solo", "senior": "长者 Senior"}[x],
            key="custom_group"
        )

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        custom_adults = st.number_input("成人", 1, 10, 2, key="custom_adult")
    with col_b:
        custom_children = st.number_input("儿童", 0, 10, 0, key="custom_child")
    with col_c:
        custom_seniors = st.number_input("老人", 0, 10, 0, key="custom_senior")
    with col_d:
        pass

    col_x, col_y, col_z = st.columns(3)
    with col_x:
        custom_rain = st.checkbox("🌧️ 雨天模式", value=False, key="custom_rain")
    with col_y:
        custom_car = st.checkbox("🚗 包车", value=False, key="custom_car")
    with col_z:
        custom_guide = st.checkbox("🎓 英文导游", value=False, key="custom_guide")

    custom_is_peak = st.checkbox("旺季价格", value=True, key="custom_peak")

    custom_btn = st.button("🎨 生成半定制路线", type="primary", use_container_width=True, key="custom_btn")

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

            render_hr_demo_card(route, pricing, payload)

            # 路线概览
            with st.container():
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("路线标题", route.get("title_en", "")[:25] + "..." if len(route.get("title_en", "")) > 25 else route.get("title_en", ""))
                with c2:
                    total_min = route.get("total_duration_min", 0)
                    st.metric("总时长", f"{total_min}min ({total_min//60}h{total_min%60}m)")
                with c3:
                    st.metric("活动时间", f"{route.get('activity_min', 0)}min")
                with c4:
                    st.metric("交通时间", f"{route.get('transit_min', 0)}min")

            st.divider()

            # 路线卡片
            st.subheader("🗺️ 推荐路线")
            units = route.get("units", [])
            for u in units:
                cost_label = f"💰 ¥{u['estimated_cost_rmb']:.0f}" if u['estimated_cost_rmb'] > 0 else "🆓 Free"
                tags = []
                if u.get("indoor_outdoor") == "indoor": tags.append("🏠 Indoor")
                elif u.get("indoor_outdoor") == "outdoor": tags.append("🌳 Outdoor")
                if u.get("rainy_day_friendly"): tags.append("☔ OK")
                if u.get("elderly_friendly"): tags.append("👴 OK")
                tag_str = " · ".join(tags) if tags else ""

                with st.expander(
                    f"{u['sequence']}. {u['name_en']} ({u['name_cn']}) — {u['duration_min']}min {cost_label}",
                    expanded=(u['sequence'] <= 3)
                ):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.caption(f"📍 {u['area']}  |  {u['unit_type']}  |  fit={u['fit_score']:.1f}")
                        if tag_str: st.caption(tag_str)
                        if u.get("description_en"): st.write(u["description_en"][:300])
                    with col_b:
                        if u.get("cost_item_code"):
                            st.caption(f"Mash: {u['cost_item_code']}")
                        else:
                            st.caption("No mash mapping")

            # 交通
            transfers = route.get("transfers", [])
            if transfers:
                st.subheader("🚗 交通 Transfers")
                for t in transfers:
                    icon = "✅" if t.get("has_edge") else "⚠️"
                    st.caption(
                        f"{icon} {t.get('from_area','')} → {t.get('to_area','')} : "
                        f"{t.get('mode','')} ~{t.get('transit_min',0)}min"
                        + (f" — {t.get('risk','')}" if t.get('risk') else "")
                    )

            st.divider()

            # 报价
            st.subheader("💵 报价明细")
            if pricing and pricing.get("success"):
                summary = pricing.get("summary", {})
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("总价", f"¥{summary.get('grand_total', 0):,.0f}")
                with c2: st.metric("人均", f"¥{summary.get('per_person', 0):,.0f}")
                with c3: st.metric("人数", f"{summary.get('total_people', 0)}")

                line_items = pricing.get("line_items", [])
                if line_items:
                    st.caption("费用分类明细：")
                    for li in line_items:
                        st.caption(
                            f"  {li.get('category',''):>16s} | {li.get('name',''):20s} | "
                            f"¥{li.get('unit_price',0):>6.0f} × {li.get('quantity',0):.0f} = "
                            f"¥{li.get('subtotal',0):>8.0f}"
                        )
            else:
                st.metric("估算成本", f"¥{route.get('estimated_cost_rmb', 0):.0f}")
                st.caption(f"_{route.get('cost_note', '')}_")

            # 逻辑与风险
            st.divider()
            with st.expander("🔍 编排逻辑与风险", expanded=False):
                logic = route.get("route_logic", [])
                if logic:
                    st.markdown("**编排逻辑：**")
                    for step in logic:
                        st.caption(f"→ {step}")

                risks = route.get("risk_warnings", [])
                if risks:
                    st.markdown("**风险提示：**")
                    for r in risks:
                        st.warning(r)

                tc = route.get("template_compliance", {})
                if tc:
                    st.caption(f"模板合规: {tc.get('satisfied_types',[])} ✓  /  未满足: {tc.get('unsatisfied_types',[])}")

            # 模板信息
            with st.expander("📋 匹配详情", expanded=False):
                st.caption(f"匹配画像: {route.get('target_profile_summary', '')}")
                st.caption(f"使用模板: {route.get('template_name', '')} ({route.get('template_id', '')})")
                st.caption(f"推荐交通: {route.get('recommended_transport', '')}")

            # Markdown 预览
            st.divider()
            st.subheader("📄 Markdown 行程单预览")
            md = result.get("itinerary_markdown", "")
            st.markdown(md)

        else:
            st.error(f"❌ 生成失败: {result.get('error', 'Unknown error')}")
    else:
        st.info("设置上方条件后点击「生成半定制路线」，生成成功后会出现一张适合发给 HR 的演示摘要卡。")


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

    # ── Load data ──
    stats_data = api_get_payment_stats()
    stats = stats_data.get("stats", {}) if stats_data.get("success") else {}

    # ── Stats Row ──
    st.markdown("### 📊 看板概览")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("⏳ 待处理", stats.get("pending_count", 0),
                  delta=f"¥{stats.get('pending_amount', 0):,.0f}")
    with c2:
        st.metric("✅ 已支付", stats.get("paid_count", 0),
                  delta=f"¥{stats.get('paid_amount', 0):,.0f}")
    with c3:
        st.metric("📦 已存档", stats.get("archived_count", 0),
                  delta=f"¥{stats.get('archived_amount', 0):,.0f}")
    with c4:
        overdue = stats.get("overdue_count", 0)
        st.metric("⚠️ 逾期", overdue if overdue else "无",
                  delta=f"¥{stats.get('overdue_amount', 0):,.0f}" if overdue else None,
                  delta_color="inverse")
    with c5:
        st.metric("📋 总计", stats.get("total_count", 0))
    st.divider()

    # ── Filter Bar ──
    st.markdown("### 🔍 筛选条件")
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
        if st.button("➕ 新建付款", type="primary", use_container_width=True):
            st.session_state.show_payment_form = True
            st.session_state.edit_payment_id = None
            st.rerun()

    # ── Create / Edit Payment Form ──
    if st.session_state.show_payment_form:
        st.markdown("---")
        is_edit = st.session_state.edit_payment_id is not None
        st.markdown(f"### {'✏️ 编辑付款' if is_edit else '➕ 新建付款'}")

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
                submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
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
            with st.expander(f"📄 付款详情: {p.get('payment_id')} — {p.get('supplier_name')}", expanded=True):
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
                        if st.button("✅ 标记已支付", key=f"pay_{p['payment_id']}"):
                            api_update_payment_status(p["payment_id"], "paid")
                            st.rerun()
                with col_db:
                    if p.get("status") in ("pending", "paid"):
                        if st.button("📦 存档", key=f"arch_{p['payment_id']}"):
                            api_update_payment_status(p["payment_id"], "archived")
                            st.rerun()
                with col_dc:
                    if st.button("❌ 关闭", key=f"cls_{p['payment_id']}"):
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
    st.markdown("### 📋 看板")
    kanban1, kanban2, kanban3 = st.columns(3)

    def render_card(p: Dict[str, Any]) -> None:
        """Render a single payment card."""
        pid = p.get("payment_id", "")
        status_text = {"pending": "⏳ 待处理", "paid": "✅ 已支付", "archived": "📦 已存档"}.get(p.get("status"), "")
        overdue = p.get("status") == "pending" and p.get("due_date") and p["due_date"] < datetime.now().strftime("%Y-%m-%d")

        with st.container(border=True):
            st.markdown(f"**{p.get('supplier_name', '')}**")
            st.caption(f"ID: {pid} | {status_text}")
            st.metric("金额", f"¥{p.get('total_amount', 0):,.0f}")
            if p.get("due_date"):
                due_label = f"⚠️ 截止: {p['due_date']}" if overdue else f"📅 截止: {p['due_date']}"
                st.caption(due_label)
            if p.get("booking_id"):
                st.caption(f"Booking: {p['booking_id']}")

            if p.get("status") == "pending":
                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    if st.button("✅ 支付", key=f"kpay_{pid}", use_container_width=True):
                        api_update_payment_status(pid, "paid")
                        st.rerun()
                with c_act2:
                    if st.button("📦 存档", key=f"karch_{pid}", use_container_width=True):
                        api_update_payment_status(pid, "archived")
                        st.rerun()
            elif p.get("status") == "paid":
                if st.button("📦 存档", key=f"karch2_{pid}", use_container_width=True):
                    api_update_payment_status(pid, "archived")
                    st.rerun()

            if st.button("📝 详情/编辑", key=f"kedit_{pid}", use_container_width=True):
                st.session_state.edit_payment_id = pid
                st.rerun()

    with kanban1:
        st.subheader(f"⏳ 待处理 ({len(pending_list)})")
        if not pending_list:
            st.caption("暂无待处理付款")
        for p in pending_list:
            render_card(p)

    with kanban2:
        st.subheader(f"✅ 已支付 ({len(paid_list)})")
        if not paid_list:
            st.caption("暂无已支付付款")
        for p in paid_list:
            render_card(p)

    with kanban3:
        st.subheader(f"📦 已存档 ({len(archived_list)})")
        if not archived_list:
            st.caption("暂无已存档付款")
        for p in archived_list:
            render_card(p)
