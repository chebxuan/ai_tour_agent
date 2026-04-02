# cli_app.py
# 职责：纯终端交互主程序，串联问卷→匹配→输出
# 运行方式：python cli_app.py
# 输入：用户在终端的数字选择
# 输出：完整的产品行程单（打印到终端）

import json
import os
import time
from survey_architect import get_beijing_survey
from product_engine import get_product_recommendation

# ── 可选：AI润色功能（如果没有API Key可以跳过）──────────────────
# 如果你想跳过AI润色，把 USE_AI_POLISH 设为 False
USE_AI_POLISH = True

def init_ai_client():
    """初始化AI客户端，失败则返回None"""
    if not USE_AI_POLISH:
        return None, None
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        model = "qwen-turbo"
        return client, model
    except Exception as e:
        print(f"[提示] AI客户端初始化失败，将跳过润色功能: {e}")
        return None, None

# ── 工具函数 ──────────────────────────────────────────────────────

def print_separator(char="─", length=50):
    print(char * length)

# cli_app.py 中替换 ask_question 函数

def ask_question(step_data, step_num, total):
    """支持选择题和文字输入题两种模式"""
    print_separator()
    print(f"\n【第 {step_num} 步 / 共 {total} 步】")
    print(f"\n  {step_data['question']}\n")

    # ── 文字输入模式（第2题人数）────────────────────────────────
    if step_data.get('input_type') == 'text':
        while True:
            raw = input("  请输入 (格式: 成人,儿童,老人): ").strip()
            try:
                parts = [int(x.strip()) for x in raw.split(',')]
                if len(parts) == 3:
                    adults, children, seniors = parts
                    print(f"\n  ✓ 已记录：成人 {adults} 人 | "
                          f"儿童 {children} 人 | 老人 {seniors} 人")
                    return {
                        "adults":   adults,
                        "children": children,
                        "seniors":  seniors
                    }
                else:
                    print("  ✗ 请输入3个数字，用逗号分隔，例如：2,1,0")
            except ValueError:
                print("  ✗ 格式错误，请输入数字，例如：2,0,0")

    # ── 选择题模式（其余步骤）───────────────────────────────────
    options = step_data.get('options', [])
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt['text']}")
    print()
    while True:
        try:
            choice = input("  请输入选项编号: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                selected = options[idx]
                print(f"\n  ✓ 已选择：{selected['text']}")
                return selected['weight']
            else:
                print(f"  ✗ 请输入 1 到 {len(options)} 之间的数字")
        except ValueError:
            print("  ✗ 请输入有效数字")

def collect_intent(survey):
    """
    遍历所有问卷步骤，汇总用户意图
    输入: survey List[Dict]
    输出: user_intent Dict
    """
    user_intent = {}
    total = len(survey)
    for idx, step_data in enumerate(survey, start=1):
        weight = ask_question(step_data, idx, total)
        # 将每一步的weight合并到总意图中
        user_intent.update(weight)
    return user_intent

def display_product(product, user_intent, ai_client=None, ai_model=None):
    """
    格式化输出产品信息到终端
    """
    print_separator("═")
    print("\n🗺️  HEXA BLUEPRINT™ — 您的专属北京行程")
    print_separator("═")

    print(f"\n📋 产品名称：{product['product_name']}")
    print(f"📅 行程天数：{product['days']} 天")

    # ── 每日行程 ──────────────────────────────────────────────────
    print_separator()
    print("\n📍 每日行程：\n")
    itinerary = product.get('itinerary', '')
    # 按换行分割，逐行打印（更易读）
    for line in itinerary.split('\n'):
        line = line.strip()
        if line:
            print(f"   {line}")

    # ── 常规项目 ──────────────────────────────────────────────────
    print_separator()
    print("\n✅ 常规包含项目：\n")
    regular = product.get('regular_items', '')
    for item in regular.split(','):
        item = item.strip()
        if item:
            print(f"   • {item}")

    # ── 可选项目 ──────────────────────────────────────────────────
    print_separator()
    print("\n⭐ 可选升级项目：\n")
    optional = product.get('optional_items', '')
    recommended = product.get('recommended_optional', '')
    for item in optional.split(','):
        item = item.strip()
        if not item:
            continue
        if item == recommended:
            # 高亮推荐项
            print(f"   ★ {item}  ← 根据您的兴趣，特别推荐！")
        else:
            print(f"   ○ {item}")

    # ── AI 润色 ───────────────────────────────────────────────────
    print_separator()
    if ai_client:
        print("\n💡 是否需要 AI 为行程加上有温度的小标题？(y/n): ", end="")
        choice = input().strip().lower()
        if choice == 'y':
            print("\n  正在生成... 请稍候...\n")
            polish_itinerary(
                product['itinerary'],
                ai_client,
                ai_model
            )
    else:
        print("\n[提示] AI润色功能未启用。如需启用，请配置 OPENAI_API_KEY。")

    print_separator("═")
    print("\n✈️  感谢使用 Hexa Blueprint™！祝您旅途愉快。")
    print_separator("═")

# cli_app.py 中新增 display_cost 函数

def display_cost(cost_result):
    """格式化输出报价单"""
    s = cost_result['summary']

    print_separator("═")
    print("\n💰  HEXA BLUEPRINT™ — 费用估算")
    print_separator("═")

    # ── 人员摘要 ─────────────────────────────────────────────────
    print(f"\n  👥 出行人员：成人 {s['adults']} 人",
          end="")
    if s['children'] > 0:
        print(f" | 儿童 {s['children']} 人", end="")
    if s['seniors'] > 0:
        print(f" | 老人 {s['seniors']} 人", end="")
    print(f"\n  📅 行程天数：{s['days']} 天",
          f"| 季节：{'旺季' if s['is_peak'] else '淡季'}")

    # ── 门票/活动明细 ────────────────────────────────────────────
    print_separator()
    print("\n  🎫 门票 & 活动\n")
    for item in cost_result['ticket_activity']['breakdown']:
        if item['line_total'] == 0:
            print(f"     {item['name']:<20} 免费")
        else:
            print(f"     {item['name']:<20} "
                  f"¥{item['unit_price']:>6.0f}/人 × "
                  f"{item['adults']}成人"
                  + (f"+{item['children']}儿童"
                     if item['children'] else "")
                  + f"  = ¥{item['line_total']:.0f}")
    print(f"\n     小计：¥{cost_result['ticket_activity']['subtotal']:.0f}")

    # ── 酒店 ─────────────────────────────────────────────────────
    h = cost_result['hotel']
    print_separator()
    print(f"\n  🏨 酒店\n")
    print(f"     {h['hotel_code']:<20} "
          f"¥{h['hotel_price']:.0f}/间/晚 × "
          f"{h['rooms']}间 × {h['nights']}晚"
          f"  = ¥{h['subtotal']:.0f}")

    # ── 交通 ─────────────────────────────────────────────────────
    t = cost_result['transport']
    print_separator()
    print(f"\n  🚗 交通\n")
    print(f"     包车 ({t['car_code']})  "
          f"¥{t['car_daily_price']:.0f}/天 × "
          f"{t['days']}天  = ¥{t['car_subtotal']:.0f}")
    if t['transfer_code']:
        print(f"     接送 ({t['transfer_code']})  "
              f"¥{t['transfer_price']:.0f}/次 × "
              f"{t['transfer_times']}次  = ¥{t['transfer_subtotal']:.0f}")

    # ── 导游 ─────────────────────────────────────────────────────
    g = cost_result['guide']
    if g['subtotal'] > 0:
        print_separator()
        print(f"\n  👤 导游\n")
        print(f"     {g['guide_name']:<20} "
              f"¥{g['daily_price']:.0f}/天 × "
              f"{g['days']}天  = ¥{g['subtotal']:.0f}")

    # ── 总计 ─────────────────────────────────────────────────────
    print_separator("═")
    print(f"\n  💵 团费总计：        ¥{s['grand_total']:.0f}")
    print(f"  👤 人均费用：        ¥{s['per_person']:.0f}")
    print_separator("═")
    print("\n  ⚠️  注：以上为参考估价，不含餐饮及个人消费。")
    print("      可选项目（如梨园京剧、涮肉等）未计入，如需添加请告知。\n")


def polish_itinerary(itinerary, client, model):
    """
    调用AI对行程进行润色
    输入: 行程字符串, AI客户端, 模型名
    输出: 打印润色后的文本
    """
    prompt = f"""
你是 Hexa China Tours 的资深旅行顾问。
请将以下北京行程，按照"宜家风格"重新排版：
- 给每一天加上一个有温度、有画面感的中文小标题（10字以内）
- 保持内容不变，只优化呈现形式
- 语言简洁、直接、充满专业感

行程内容：
{itinerary}
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        polished = response.choices[0].message.content.strip()
        print("  🎨 AI 润色版本：\n")
        print_separator()
        for line in polished.split('\n'):
            print(f"  {line}")
        print_separator()
    except Exception as e:
        print(f"  [润色失败] {e}")

# ── 主程序 ────────────────────────────────────────────────────────

def main():
    # 全局变量：总步骤数（供 ask_question 使用）
    global total_steps

    print_separator("═")
    print("  🗺️  欢迎使用 Hexa Blueprint™ 北京行程定制系统")
    print("  输入数字编号进行选择，按回车确认")
    print_separator("═")

    # Step 1: 加载问卷
    survey = get_beijing_survey()
    total_steps = len(survey)

    # Step 2: 收集用户意图
    print("\n  正在为您构建专属问卷...\n")
    time.sleep(0.5)  # 轻微延迟，提升仪式感
    user_intent = collect_intent(survey)

    # Step 3: 匹配产品
    print_separator()
    print("\n  正在匹配最适合您的产品...")
    time.sleep(0.5)
    product = get_product_recommendation(user_intent)

    # Step 4: 处理错误
    if product.get('error'):
        print(f"\n  ✗ 匹配失败：{product['error']}")
        print("  请检查您的选择后重试。")
        return

    # Step 5: 初始化AI（可选）
    ai_client, ai_model = init_ai_client()

    # Step 6: 展示结果
    display_product(product, user_intent, ai_client, ai_model)

    # Step 7: 计算成本
    from cost_engine import calculate_total_cost
    cost_result = calculate_total_cost(product, user_intent)
    display_cost(cost_result)

if __name__ == "__main__":
    main()