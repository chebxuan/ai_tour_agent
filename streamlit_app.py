"""
Hexa Blueprint™ — Travel Copilot Streamlit Frontend
一键生成可发送客户的行程与报价

运行方式:
    streamlit run streamlit_app.py
"""

import json
import os
from typing import Any, Dict, List

import requests
import streamlit as st

# ── 配置 ──────────────────────────────────────────────────────

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "hexa-tour-2024")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


# ── API 交互 ───────────────────────────────────────────────────

def api_get_cities() -> List[str]:
    try:
        resp = requests.get(f"{API_BASE}/api/v1/cities", headers=HEADERS, timeout=5)
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

# ── 主输出区 ──────────────────────────────────────────────────

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

        # ── 产品信息 ──
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

        # ── 行程 Markdown ──
        st.markdown("## 📅 行程草稿")
        md = result.get("itinerary_markdown", "")
        st.markdown(md)

        st.divider()

        # ── 报价概览 ──
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

        # ── 原始 JSON 调试 ──
        with st.expander("🔧 原始数据（Debug）"):
            # 精简展示，去掉冗长的 markdown
            debug = dict(result)
            st.json(debug)
    else:
        st.error(f"❌ 生成失败：{result.get('error', '未知错误')}")

else:
    # 默认展示帮助信息
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
