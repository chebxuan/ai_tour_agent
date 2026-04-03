import streamlit as st
import json
from survey_architect import generate_survey, client, model
from product_engine import get_product_recommendation

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 核心修改：统一使用 DashScope 接口
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), # 确保环境变量里存的是阿里的 SK
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
model = "qwen-turbo" # 使用通义千问模型

st.set_page_config(page_title="Hexa Blueprint™ AI", page_icon="🗺️")

st.title("🗺️ Hexa Blueprint™ 定制系统")

# 初始化 Session State
if 'survey' not in st.session_state:
    with st.spinner("AI 正在为您构建动态问卷..."):
        st.session_state.survey = generate_survey()
    st.session_state.answers = []
    st.session_state.step = 0

survey = st.session_state.survey
current_step = st.session_state.step

if current_step < len(survey):
    step_data = survey[current_step]
    st.subheader(f"Step {current_step + 1}")
    st.write(step_data['question'])

    # --- 修改前的代码 ---
# options = step_data['options']
# choice_text = st.radio("选择您的偏好：", [opt['text'] for opt in options])

# --- 修改后的防御性代码 ---
    options = step_data.get('options', [])
    if not options:
        st.error("问卷数据异常：未找到选项 (options)")
        st.stop()

# 自动兼容不同的键名：尝试获取 'text', 'Text' 或第一个键的值
    def get_option_text(opt):
        return opt.get('text') or opt.get('Text') or list(opt.values())[0]

    option_labels = [get_option_text(opt) for opt in options]
    choice_text = st.radio("选择您的偏好：", option_labels)
    if st.button("确认"):
        # 获取选中选项的完整 weight 字典
        selected_weight = next(opt['weight'] for opt in options if opt['text'] == choice_text)
        st.session_state.answers.append(selected_weight)
        st.session_state.step += 1
        st.rerun()
else:
    # 问卷结束：逻辑汇总
    st.success("偏好采集完成！正在生成产品推荐...")

    user_intent = {"city": None, "days": None, "style": None}
    for ans in st.session_state.answers:
        if isinstance(ans, dict):
            if ans.get("city"):
                user_intent["city"] = ans["city"]
            if ans.get("days"):
                user_intent["days"] = ans["days"]
            if ans.get("style"):
                user_intent["style"] = ans["style"]
            # 兼容加入 CITY/DAYS/STYLE 在 weight 里
            if ans.get("weight") and isinstance(ans["weight"], dict):
                user_intent["city"] = user_intent["city"] or ans["weight"].get("city")
                user_intent["days"] = user_intent["days"] or ans["weight"].get("days")
                user_intent["style"] = user_intent["style"] or ans["weight"].get("style")

    # 最低条件必须有city+days
    if not user_intent["city"] or not user_intent["days"]:
        st.error("未检测到城市或天数，请返回问卷重新选择。")
    else:
        product = get_product_recommendation(user_intent)

        if not product or product.get("error"):
            st.error("未找到匹配产品，请调整您的偏好后重试。")
        else:
            st.subheader(product.get("product_name", "未知产品"))
            st.info(product.get("itinerary", "每日行程暂无"))

            regular = product.get("regular_items")
            optional = product.get("optional_items")
            if regular:
                st.write(f"常规项目：{regular}")
            if optional:
                st.warning(f"可选项目 (Optional)：{optional}")

            # 选装：用 AI 重新润色每日行程，宜家风格 + 温度小标题
            if st.button("极致润色：按宜家风格重排并加小标题"):
                prompt = (
                    "这是我们的成熟产品行程，请按照宜家风格重新排版，并给每一天加上一个有温度的小标题。\n" +
                    product.get("itinerary", "")
                )
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.9
                    )
                    ai_text = response.choices[0].message.content.strip()
                    st.success("AI 润色完成：")
                    st.text(ai_text)
                except Exception as e:
                    st.error(f"AI 润色失败：{e}")

    if st.button("重新生成问卷"):
        st.session_state.clear()
        st.rerun()