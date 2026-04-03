import json
import os
import time
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o-mini"

# 定义 Primary Tag 库
TAG_LIBRARY = [
    "皇家权力", "祭祀礼仪", "皇家园林", "边塞雄关", "藏传佛教", "国家地标",
    "国家门面", "伟人缅怀", "文化沉浸", "老城记忆", "俯瞰全城", "双奥地标",
    "饕餮京味", "国宴美食", "夜色胡同", "艺术表演"
]

# 系统提示词
SYSTEM_PROMPT = f"""
你是一个资深的旅行规划分析师。你的任务是分析用户的原始需求，并将其映射到特定的 primary_tag 权重。

输入变量：
User_Input: {{用户输入的内容}}
Tag_Library: {TAG_LIBRARY}

逻辑要求：
识别核心动机：从 User_Input 中提取 2-3 个最相关的 primary_tag 并赋予 0-1 之间的权重。
识别硬约束：提取天数、同行人（老人/小孩）、预算（经济/豪华）。

输出格式：严格 JSON。

输出示例：
{{
  "intent": {{"皇家权力": 0.9, "老城记忆": 0.7}},
  "constraints": {{"days": 1, "has_child": true, "budget": "luxury"}},
  "style_preference": "depth_exploration"
}}
"""

def intent_parser(user_input, max_retries=3):
    """
    意图解析器：将用户输入解析为结构化JSON。
    
    Args:
        user_input (str): 用户的自然语言输入。
    
    Returns:
        dict: 解析后的JSON字典。
    """
    content = ""
    for attempt in range(max_retries):
        try:
            # 构造消息
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User_Input: {user_input}"}
            ]
            
            # 调用 LLM
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1  # 保持一致性
            )
            
            # 解析响应
            content = response.choices[0].message.content.strip()
            
            # 尝试解析为JSON
            result = json.loads(content)
            return result
        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"Rate limit hit, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return {"error": "Rate limit exceeded after retries", "raw_response": content}
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response as JSON", "raw_response": content}

# 测试示例
if __name__ == "__main__":
    test_input = "带小孩看历史，一天时间，预算中等"
    result = intent_parser(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))