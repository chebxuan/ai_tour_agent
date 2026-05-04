#!/usr/bin/env python3
# cli_app.py - 交互式城市行程规划工具
# 基于问卷收集用户需求，调用引擎生成行程推荐和费用计算
# 支持多城市：北京、上海、广州、重庆、西安、阳朔、张家界、贵州、云南、成都

import sys
import os
import json
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from survey_architect import get_beijing_survey
from engines.product_engine import get_product_recommendation
from engines.cost_engine import calculate_total_cost
from engines.city_config import list_available_cities, get_city_code_prefix


def get_city_description(city: str) -> str:
    """
    获取城市描述
    """
    city_descriptions = {
        "北京": "皇城文化，胡同风情，历史古都",
        "上海": "魔都魅力，都市风情，时尚之都",
        "广州": "食在广州，粤式文化，美食天堂",
        "重庆": "山城特色，火锅之都，魔幻地形",
        "西安": "古都风韵，历史名城，兵马俑故乡",
        "阳朔": "山水甲天下，田园风光，喀斯特地貌",
        "张家界": "奇峰异石，仙境画卷，阿凡达取景地",
        "贵州": "贵州风情，山水风光，民族村寨",
        "云南": "七彩云南，民族风情，四季如春",
        "成都": "天府之国，美食之都，悠闲生活"
    }
    return city_descriptions.get(city, "魅力之都，精彩无限")


def show_cities_description():
    """显示城市详细描述"""
    print("\n" + "="*60)
    print("🏙️ 城市详细介绍")
    print("="*60)
    print("\n🌟 各城市特色介绍：")
    print("-"*40)
    print("🏛️  北京 - 皇城文化，胡同风情")
    print("  - 故宫、长城、天安门等历史遗迹")
    print("  - 烤鸭、涮肉等传统美食")
    print("  - 四季分明，每个季节都有独特魅力")
    print()
    print("🌃  上海 - 魔都魅力，都市风情")
    print("  - 外滩、东方明珠等现代地标")
    print("  - 小笼包、本帮菜等特色美食")
    print("  - 时尚与传统完美融合的国际大都市")
    print()
    print("🍜  广州 - 食在广州，粤式文化")
    print("  - 美食之都，粤菜发源地")
    print("  - 早茶文化，茶楼林立")
    print("  - 商贸发达，历史悠久")
    print()
    print("🔥  重庆 - 山城特色，火锅之都")
    print("  - 立体城市，山势起伏")
    print("  - 火锅文化，麻辣鲜香")
    print("  - 夜生活丰富，充满活力")
    print()
    print("🏺  西安 - 古都风韵，历史名城")
    print("  - 兵马俑、大雁塔等古迹")
    print("  - 回民街美食，肉夹馍、凉皮")
    print("  - 十三朝古都，文化底蕴深厚")
    print()
    print("🏞️  阳朔 - 山水甲天下，田园风光")
    print("  - 漓江风光，山水画卷")
    print("  - 阳朔西街，异国风情")
    print("  - 田园生活，悠闲自在")
    print()
    print("⛰️  张家界 - 奇峰异石，仙境画卷")
    print("  - 阿凡达取景地，自然奇观")
    print("  - 玻璃栈道，刺激体验")
    print("  - 民族风情，土家文化")
    print()
    print("🌿  贵州 - 贵州风情，山水风光")
    print("  - 黄果树瀑布，自然奇观")
    print("  - 苗族侗族，民族风情")
    print("  - 酸辣口味，特色美食")
    print()
    print("🌈  云南 - 七彩云南，民族风情")
    print("  - 昆明四季如春，春城之美")
    print("  - 25个少数民族，文化多元")
    print("  - 丽江古城，大理洱海")
    print()
    print("🐼  成都 - 天府之国，美食之都")
    print("  - 大熊猫基地，国宝故乡")
    print("  - 火锅、串串、川菜美食")
    print("  - 茶馆文化，悠闲生活")
    print("-"*40)
    print("\n💡 选择提示：")
    print("  • 首次旅游建议选择北京、上海等热门城市")
    print("  • 喜欢自然风光可选张家界、阳朔")
    print("  • 美食爱好者推荐广州、成都")
    print("  • 历史文化爱好者推荐西安")
    print("="*60)


def get_city_survey(city: str) -> List[Dict]:
    """
    根据城市生成问卷
    基于北京的问卷模板，动态替换城市相关选项
    """
    city_code = get_city_code_prefix(city)

    if city == "北京":
        return get_beijing_survey()

    survey = [
        {
            "step": 1,
            "question": f"您计划游览{city}几天？",
            "options": []
        },
        {
            "step": 2,
            "question": "请输入同行人数（直接输入数字，用逗号分隔）\n  格式：成人数,儿童数(12岁以下),老人数(65岁以上)\n  示例：2,1,0 表示2个成人+1个小孩",
            "input_type": "text",
            "field": "traveler_counts",
            "options": []
        },
        {
            "step": 3,
            "question": "出行季节？（影响部分景点票价）",
            "options": [
                {"text": "旺季（4月-10月）", "weight": {"is_peak": True}},
                {"text": "淡季（11月-3月）", "weight": {"is_peak": False}}
            ]
        },
        {
            "step": 4,
            "question": "是否需要英文导游？",
            "options": [
                {"text": "需要全程英文导游", "weight": {"guide": f"{city_code}-GUIDE-01"}},
                {"text": "不需要导游（自由行）", "weight": {"guide": None}}
            ]
        },
        {
            "step": 5,
            "question": "酒店档次偏好？",
            "options": []
        },
        {
            "step": 6,
            "question": "请输入需要住宿几晚？（可输入 0）",
            "input_type": "integer",
            "field": "hotel_nights",
            "min": 0,
            "options": []
        },
        {
            "step": 7,
            "question": "是否需要接送服务？",
            "options": []
        },
        {
            "step": 8,
            "question": "请输入接送次数？（如只接机填 1，接机+送机填 2，可输入 0）",
            "input_type": "integer",
            "field": "transfer_times",
            "min": 0,
            "options": []
        },
        {
            "step": 9,
            "question": "请输入需要包车几天？（如全程无需包车可填 0）",
            "input_type": "integer",
            "field": "car_days",
            "min": 0,
            "options": []
        }
    ]

    survey[0]["options"] = [
        {"text": "1天", "weight": {"city": city, "days": 1}},
        {"text": "2天", "weight": {"city": city, "days": 2}},
        {"text": "3天", "weight": {"city": city, "days": 3}},
        {"text": "4天", "weight": {"city": city, "days": 4}},
        {"text": "5天", "weight": {"city": city, "days": 5}},
    ]

    survey[4]["options"] = [
        {"text": f"经济型（{city_code}-HOTEL-01）", "weight": {"hotel": f"{city_code}-HOTEL-01"}},
        {"text": f"舒适型（{city_code}-HOTEL-02）", "weight": {"hotel": f"{city_code}-HOTEL-02"}},
        {"text": f"精品型（{city_code}-HOTEL-03）", "weight": {"hotel": f"{city_code}-HOTEL-03"}}
    ]

    survey[6]["options"] = [
        {"text": "需要接机/接站", "weight": {"transfer": f"{city_code}-TRANS-03"}},
        {"text": "不需要接送", "weight": {"transfer": None}}
    ]

    return survey


def display_survey(survey: List[Dict]):
    """显示问卷"""
    print("\n" + "="*60)
    print("📋 旅游需求问卷")
    print("="*60)
    print("💡 请根据您的旅行需求选择或填写以下问题")
    print("🔄 您随时可以输入 'help' 查看帮助")
    print("❌ 如需退出，请输入 'exit'")
    print("="*60)

    for step in survey:
        print(f"\n【第{step['step']}题】{step['question']}")

        # 添加问题类型标识
        if step.get("help_text"):
            print(f"💡 {step.get('help_text')}")

        if step.get("input_type") in {"text", "integer"}:
            print("  ✍️ 请在此输入您的回答")
        elif step.get("options"):
            for i, option in enumerate(step["options"], 1):
                # 为选项添加图标
                icon = "🎯" if i == 1 else "📍"
                print(f"  {icon} {i}. {option['text']}")

        # 添加进度提示
        total_steps = len(survey)
        print(f"   📊 进度: {step['step']}/{total_steps}")


def get_help_text(step: Dict) -> str:
    """获取问题的帮助文本"""
    help_texts = {
        "traveler_counts": """
📝 人数输入格式：
• 2        → 2个成人
• 2,1,0    → 2个成人+1个儿童+0个老人
• 1,2      → 1个成人+2个儿童（老人数为0）""",
        "hotel_nights": """
🏨 住宿晚数建议：
• 1天行程 → 0晚（当日往返）
• 2天行程 → 1晚
• 3天行程 → 2晚
• 以此类推...""",
        "transfer_times": """
🚗 接送次数说明：
• 1        → 只接机/接站
• 2        → 接机+返程接送
• 3        → 接机+返程+送站
- 2        → 接机+送机
- 0        → 不需要接送
- 更多    → 根据实际需求""",
        "car_days": """
包车天数说明：
- 0        → 不需要包车
- 1        → 包车1天
- 2        → 包车2天
- 更多    → 根据行程安排"""
    }

    field = step.get("field")
    if field in help_texts:
        return help_texts[field]
    return ""


def handle_user_commands(user_input: str) -> Dict[str, str]:
    """
    处理用户命令
    返回: {"command": 命令类型, "message": 提示信息}
    """
    user_input = user_input.strip().lower()

    command_map = {
        "help": {
            "type": "help",
            "message": """📚 可用命令：
• help - 显示帮助信息
• exit - 退出程序
• restart - 重新开始问卷
• cities - 查看支持的城市列表
• skip - 跳过当前问题（如适用）
"""
        },
        "exit": {
            "type": "exit",
            "message": "👋 感谢使用，再见！"
        },
        "restart": {
            "type": "restart",
            "message": "🔄 重新开始问卷..."
        },
        "cities": {
            "type": "cities",
            "message": """🏙️ 支持的城市列表：
• 北京 - 皇城文化，胡同风情
• 上海 - 魔都魅力，都市风情
• 广州 - 食在广州，粤式文化
• 重庆 - 山城特色，火锅之都
• 西安 - 古都风韵，历史名城
• 阳朔 - 山水甲天下，田园风光
• 张家界 - 奇峰异石，仙境画卷
• 贵州 - 贵州风情，山水风光
• 云南 - 七彩云南，民族风情
• 成都 - 天府之国，美食之都"""
        },
        "skip": {
            "type": "skip",
            "message": "⏭️ 已跳过当前问题"
        }
    }

    for cmd, cmd_info in command_map.items():
        if user_input == cmd:
            return cmd_info

    return {"type": "invalid", "message": f"❌ 未知命令 '{user_input}'。输入 'help' 查看可用命令"}


def collect_answers(survey: List[Dict]) -> Dict[str, Any]:
    """收集用户回答"""
    user_intent = {}

    for step in survey:
        step_num = step["step"]
        input_type = step.get("input_type")
        question = step["question"]

        print(f"\n【第{step_num}题】{question}")
        help_text = get_help_text(step)
        if help_text:
            print(f"\n💡 帮助：{help_text}")

        if input_type == "text":
            while True:
                try:
                    answer = input("\n请输入: ").strip()
                    if not answer:
                        print("  ❌ 输入不能为空，请重新输入")
                        continue

                    # 处理用户命令
                    if answer.lower() in ["help", "exit", "restart", "cities", "skip"]:
                        cmd_result = handle_user_commands(answer.lower())
                        print(f"\n{cmd_result['message']}")

                        if cmd_result["type"] == "exit":
                            sys.exit(0)
                        elif cmd_result["type"] == "restart":
                            return {"restart": True}
                        elif cmd_result["type"] == "skip":
                            if step.get("field"):
                                user_intent[step.get("field")] = "skipped"
                                break
                            else:
                                print("\n❌ 跳过选项不可用")
                                continue

                    if step.get("field") == "traveler_counts":
                        # 处理人数输入
                        parts = [x.strip() for x in answer.split(",")]
                        if len(parts) == 1:
                            adults = int(parts[0])
                            children = 0
                            seniors = 0
                        elif len(parts) == 3:
                            adults, children, seniors = map(int, parts)
                        else:
                            print("  ❌ 格式错误，请输入：成人数,儿童数,老人数")
                            continue

                        if adults < 1 or children < 0 or seniors < 0:
                            print("  ❌ 人数不能为负数，且成人数量至少为1")
                            continue

                        total_people = adults + children + seniors
                        if total_people > 20:
                            print("  ⚠️ 人数过多，请联系客服团队处理")
                            continue

                        user_intent["adults"] = adults
                        user_intent["children"] = children
                        user_intent["seniors"] = seniors
                        print(f"  ✅ 已记录：{adults}成人+{children}儿童+{seniors}老人")
                        break
                    else:
                        # 其他文本输入
                        user_intent[step.get("field")] = answer
                        break

                except ValueError:
                    print("  ❌ 请输入有效的数字")
                except KeyboardInterrupt:
                    print("\n\n👋 已取消操作")
                    sys.exit(0)

        elif input_type == "integer":
            field = step.get("field")
            minimum = step.get("min", 0)
            maximum = step.get("max", None)

            while True:
                try:
                    answer = input("\n请输入数字: ").strip()
                    if answer == "":
                        print("  ❌ 输入不能为空")
                        continue

                    # 处理用户命令
                    if answer.lower() in ["help", "exit", "restart", "cities", "skip"]:
                        cmd_result = handle_user_commands(answer.lower())
                        print(f"\n{cmd_result['message']}")

                        if cmd_result["type"] == "exit":
                            sys.exit(0)
                        elif cmd_result["type"] == "restart":
                            return {"restart": True}
                        elif cmd_result["type"] == "skip":
                            if field:
                                user_intent[field] = "skipped"
                                break
                            else:
                                print("\n❌ 跳过选项不可用")
                                continue

                    value = int(answer)
                    if value < minimum:
                        print(f"  ❌ 请输入大于或等于 {minimum} 的数字")
                        continue
                    if maximum and value > maximum:
                        print(f"  ❌ 请输入小于或等于 {maximum} 的数字")
                        continue

                    user_intent[field] = value
                    print(f"  ✅ 已记录：{value}")
                    break
                except ValueError:
                    print("  ❌ 请输入有效的整数")
                except KeyboardInterrupt:
                    print("\n\n👋 已取消操作")
                    sys.exit(0)

        elif step.get("options"):
            print("\n可选选项：")
            for i, option in enumerate(step["options"], 1):
                icon = "🎯" if i == 1 else "📍"
                print(f"  {icon} {i}. {option['text']}")

            while True:
                try:
                    answer = input("\n请选择选项编号 (输入0查看帮助): ").strip()

                    # 处理用户命令
                    if answer.lower() in ["help", "exit", "restart", "cities", "skip"]:
                        cmd_result = handle_user_commands(answer.lower())
                        print(f"\n{cmd_result['message']}")

                        if cmd_result["type"] == "exit":
                            sys.exit(0)
                        elif cmd_result["type"] == "restart":
                            return {"restart": True}
                        elif cmd_result["type"] == "skip":
                            # 为选项类型的字段提供默认值
                            if "days" in str(step.get("options", [])):
                                user_intent["days"] = 1
                            elif "hotel" in str(step.get("options", [])):
                                user_intent["hotel"] = "skipped"
                            elif "transfer" in str(step.get("options", [])):
                                user_intent["transfer"] = None
                            print("  ⏭️ 已跳过，使用默认值")
                            break
                        continue

                    if answer == "0":
                        print("\n💡 提示：请输入选项前的数字编号")
                        print("示例：输入1选择第一个选项，输入2选择第二个选项")
                        continue

                    idx = int(answer) - 1

                    if 0 <= idx < len(step["options"]):
                        selected_option = step["options"][idx]
                        user_intent.update(selected_option["weight"])
                        print(f"  ✅ 已选择：{selected_option['text']}")
                        break
                    else:
                        print(f"  ❌ 选项编号无效，请输入1-{len(step['options'])}之间的数字")

                except ValueError:
                    print("  ❌ 请输入有效的数字")
                except KeyboardInterrupt:
                    print("\n\n👋 已取消操作")
                    sys.exit(0)

    return user_intent


def display_result(product: Dict, cost_result: Dict):
    """显示结果"""
    print("\n" + "="*60)
    print("🎉 行程规划结果")
    print("="*60)

    # 产品信息
    print("\n📦 【产品信息】")
    print(f"🌟 产品名称: {product.get('product_name', 'N/A')}")
    print(f"📅 行程天数: {product.get('days', 'N/A')} 天")
    print(f"📍 目的地: {product.get('city', 'N/A')}")

    # 行程概览
    itinerary = product.get('itinerary', '')
    if itinerary:
        print("\n🗓️ 【行程概览】")
        for line in itinerary.split('\n'):
            line = line.strip()
            if line:
                print(f"  • {line}")

    # 项目列表
    regular_items = product.get('regular_items', '')
    optional_items = product.get('optional_items', '')

    if regular_items:
        print(f"\n✅ 【常规项目】{regular_items}")
    if optional_items:
        print(f"🎯 【可选项目】{optional_items}")

    # 使用增强显示函数
    display_enhanced_result(user_intent, cost_result)

    return user_intent, cost_result


def display_enhanced_result(user_intent: Dict[str, Any], cost_result: Dict[str, Any]):
    """增强的结果显示函数"""
    print("\n" + "="*70)
    print("🎉 您的专属旅行方案已生成！")
    print("="*70)

    # 基本信息展示
    print("\n📋 【旅行摘要】")
    print("-"*50)
    summary = cost_result.get("summary", {})
    print(f"🏷️  产品名称: {summary.get('product_name', 'N/A')}")
    print(f"🌆 城市: {summary.get('city', 'N/A')}")
    print(f"📅 行程天数: {summary.get('days', 0)} 天")
    print(f"👥 总人数: {summary.get('total_people', 0)} 人 "
          f"(成人:{summary.get('adults', 0)} | "
          f"儿童:{summary.get('children', 0)} | "
          f"老人:{summary.get('seniors', 0)})")
    print(f"🌸 出行季节: {'🌸 旺季 (4-10月)' if summary.get('is_peak') else '❄️ 淡季 (11-3月)'}")
    print(f"🎒 行程类型: {'自助游' if summary.get('total_cost', 0) < 3000 else '跟团游'}")

    # 项目统计
    print("\n📊 【项目统计】")
    print("-"*30)
    regular_count = summary.get('regular_items_count', 0)
    optional_count = summary.get('optional_items_count', 0)
    print(f"  ✅ 常规项目: {regular_count} 个（已包含在费用中）")
    print(f"  🎯 可选项目: {optional_count} 个（您自由选择）")
    total_items = regular_count + optional_count
    print(f"  📦 项目总计: {total_items} 个")

    # 费用概览
    print("\n💰 【费用概览】")
    print("-"*30)
    total_cost = summary.get('total_cost', 0)
    print(f"  💵 总费用: ¥{total_cost:,.2f}")

    # 人均费用
    if summary.get('total_people', 0) > 0:
        per_person_cost = total_cost / summary.get('total_people', 0)
        print(f"  👥 人均费用: ¥{per_person_cost:,.2f}")

    # 价格等级
    if total_cost > 10000:
        price_level = "💎 高端奢华"
    elif total_cost > 5000:
        price_level = "⭐ 豪华精选"
    elif total_cost > 2000:
        price_level = "🌟 中档舒适"
    else:
        price_level = "💰 经济实惠"
    print(f"  🏷️ 价格等级: {price_level}")

    # 详细费用 breakdown
    print("\n🧾 【详细费用分解】")
    print("-"*60)

    # 门票活动费用
    ticket = cost_result.get("ticket_activity", {})
    if ticket.get('subtotal', 0) > 0:
        print(f"\n🎫 门票活动费用: ¥{ticket.get('subtotal', 0):.2f}")
        print("  └─ " + "─" * 45)
        for item in ticket.get('breakdown', []):
            if item.get('line_total', 0) > 0:
                print(f"  📍 {item['name']}")
                print(f"     💰 单价: ¥{item['unit_price']} × "
                      f"{item['adults']}成{item['children']}童{item['seniors']}老")
                print(f"     💸 小计: ¥{item['line_total']:.2f}")
                print()

    # 酒店住宿费用
    hotel = cost_result.get("hotel", {})
    if hotel.get('subtotal', 0) > 0:
        print(f"\n🏨 酒店住宿: ¥{hotel.get('subtotal', 0):.2f}")
        print("  └─ " + "─" * 45)
        print(f"  🏠 酒店名称: {hotel.get('hotel_name', 'N/A')}")
        print(f"  🛏️ 房间配置: {hotel.get('rooms', 0)} 间房 × {hotel.get('nights', 0)} 晚")
        print(f"  💡 住宿类型: {hotel.get('hotel_type', '标准间')}")
        print(f"  💰 每晚价格: ¥{hotel.get('hotel_price', 0)}")

    # 交通费用
    transport = cost_result.get("transport", {})
    if transport.get('subtotal', 0) > 0:
        print(f"\n🚗 交通费用: ¥{transport.get('subtotal', 0):.2f}")
        print("  └─ " + "─" * 45)
        if transport.get('car_code'):
            print(f"  🚙 包车服务:")
            print(f"     🚘 车型: {transport.get('car_name', 'N/A')}")
            print(f"     📅 包车天数: {transport.get('car_days', 0)} 天")
            print(f"     💰 包车费用: ¥{transport.get('car_subtotal', 0):.2f}")
        if transport.get('transfer_code'):
            print(f"  🚕 接送服务:")
            print(f"     🚙 车型: {transport.get('transfer_name', 'N/A')}")
            print(f"     📍 接送次数: {transport.get('transfer_times', 0)} 次")
            print(f"     💰 接送费用: ¥{transport.get('transfer_subtotal', 0):.2f}")

    # 导游费用
    guide = cost_result.get("guide", {})
    print(f"🌆 城市: {summary.get('city', 'N/A')}")
    print(f"📅 天数: {summary.get('days', 0)} 天")
    print(f"👥 人数: {summary.get('total_people', 0)} 人 "
          f"(成人:{summary.get('adults', 0)} "
          f"儿童:{summary.get('children', 0)} "
          f"老人:{summary.get('seniors', 0)})")
    print(f"🌸 季节: {'旺季' if summary.get('is_peak') else '淡季'}")

    regular_count = summary.get('regular_items_count', 0)
    optional_count = summary.get('optional_items_count', 0)
    print(f"\n📋 【项目统计】")
    print(f"  ✅ 常规项目: {regular_count} 个（已包含）")
    print(f"  🎯 可选项目: {optional_count} 个（您选择的）")

    # 详细费用
    print("\n--- 详细费用 ---")

    # 门票活动
    ticket = cost_result.get("ticket_activity", {})
    if ticket.get('subtotal', 0) > 0:
        print(f"\n🎫 门票活动: ¥{ticket.get('subtotal', 0):.2f}")
        for item in ticket.get('breakdown', []):
            if item.get('line_total', 0) > 0:
                print(f"  📍 {item['name']}")
                print(f"     ¥{item['unit_price']} × "
                      f"{item['adults']}成{item['children']}童{item['seniors']}老 "
                      f"= ¥{item['line_total']:.2f}")

    # 酒店住宿
    hotel = cost_result.get("hotel", {})
    if hotel.get('subtotal', 0) > 0:
        print(f"\n🏨 酒店住宿: ¥{hotel.get('subtotal', 0):.2f}")
        print(f"  📍 {hotel.get('hotel_name', 'N/A')}")
        print(f"  🏠 {hotel.get('rooms', 0)} 间 × {hotel.get('nights', 0)} 晚")
        print(f"  💰 ¥{hotel.get('hotel_price', 0)}/晚")

    # 交通费用
    transport = cost_result.get("transport", {})
    if transport.get('subtotal', 0) > 0:
        print(f"\n🚗 交通费用: ¥{transport.get('subtotal', 0):.2f}")
        if transport.get('car_code'):
            print(f"  🚙 包车: {transport.get('car_name', 'N/A')}")
            print(f"     {transport.get('car_days', 0)} 天 = ¥{transport.get('car_subtotal', 0):.2f}")
        if transport.get('transfer_code'):
            print(f"  🚕 接送: {transport.get('transfer_name', 'N/A')}")
            print(f"     {transport.get('transfer_times', 0)} 次 = ¥{transport.get('transfer_subtotal', 0):.2f}")

    # 导游费用
    guide = cost_result.get("guide", {})
    if guide.get('subtotal', 0) > 0:
        print(f"\n🎓 导游费用: ¥{guide.get('subtotal', 0):.2f}")
        print(f"  👨‍🏫 {guide.get('guide_name', 'N/A')}")
        print(f"     {guide.get('days', 0)} 天")

    # 费用汇总
    print("\n" + "="*60)
    print("💎 【费用汇总】")
    print("="*60)
    print(f"💵 总费用: ¥{summary.get('grand_total', 0):.2f}")
    print(f"👤 人均费用: ¥{summary.get('per_person', 0):.2f}")
    print(f"💱 货币单位: {summary.get('currency', 'RMB')}")

    # 添加保存提示
    print("\n💡 提示：请截图保存此行程，方便后续查看")
    print("🎯 如需修改行程，请重新运行程序")
    print("="*60)


def show_help():
    """显示帮助信息"""
    print("\n" + "="*60)
    print("❓ 【使用指南】")
    print("="*60)
    print("\n📋 系统功能：")
    print("  • 根据您的需求推荐最适合的旅游产品")
    print("  • 计算详细的费用明细")
    print("  • 生成个性化的行程规划")
    print("\n🎯 使用方法：")
    print("  1. 选择您想去的城市")
    print("  2. 回答简单的问卷问题")
    print("  3. 选择您喜欢的可选项目")
    print("  4. 获取详细的行程和报价")
    print("\n💡 小贴士：")
    print("  • 旺季（4月-10月）价格较高，景点较多")
    print("  • 淡季（11月-3月）价格优惠，游客较少")
    print("  • 包车建议选择舒适型，适合长途旅行")
    print("  • 导游服务能让您的体验更加深入")
    print("\n📞 客服支持：")
    print("  • 如需人工服务，请工作时间联系客服")
    print("  • 紧急情况：400-123-4567")
    print("\n输入 'h' 查看此帮助，输入 'q' 退出程序")
    print("="*60)


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🌏 城市旅游智能平台 - 行程规划系统")
    print("="*70)
    print("\n🎉 欢迎使用智能旅游规划系统！")
    print("🤖 我将根据您的需求为您推荐最适合的旅游产品")
    print("💡 提示：输入 'help' 查看使用指南，输入 'exit' 退出程序")
    print("="*70)

    while True:
        try:
            print("\n" + "🚀"*25)
            print("开始您的专属旅程规划...")
            print("🚀"*25 + "\n")

            # 选择城市
            print("\n" + "-"*60)
            print("🏙️ 第一步：选择您想去的城市")
            print("-"*60)
            cities = list_available_cities()

            print("🌟 热门推荐城市：")
            for i, city in enumerate(cities[:3], 1):
                prefix = get_city_code_prefix(city)
                desc = get_city_description(city)
                print(f"  🎯 {i}. {city} - {desc} ({prefix})")

            print("\n🌍 其他城市：")
            for i, city in enumerate(cities[3:], 4):
                prefix = get_city_code_prefix(city)
                print(f"  📍 {i}. {city} ({prefix})")

            while True:
                try:
                    choice = input("\n👉 请选择城市编号 (输入0查看城市列表): ").strip()

                    # 处理命令
                    if choice.lower() == 'help':
                        show_help()
                        continue
                    elif choice.lower() == 'exit':
                        print("\n👋 感谢使用，再见！")
                        return
                    elif choice.lower() in ['cities', 'city']:
                        show_cities_description()
                        continue

                    if choice == "0":
                        print("\n" + "="*60)
                        print("🏙️ 支持的城市详细列表")
                        print("="*60)
                        for city in cities:
                            prefix = get_city_code_prefix(city)
                            desc = get_city_description(city)
                            print(f"  🌟 {city} - {desc} ({prefix})")
                        continue

                    idx = int(choice) - 1
                    if 0 <= idx < len(cities):
                        city = cities[idx]
                        print(f"\n✅ 已选择城市: {city}")
                        print(f"📍 正在为您准备 {city} 的专属问卷...")
                        break
                    else:
                        print(f"  ❌ 请输入1-{len(cities)}之间的数字")

                except ValueError:
                    print("  ❌ 请输入有效的数字")

            # 生成并显示问卷
            survey = get_city_survey(city)
            display_survey(survey)

            # 收集用户回答
            print("\n💫 正在收集您的需求...")
            user_intent = collect_answers(survey)

            # 如果用户选择重启，跳过后续处理
            if isinstance(user_intent, dict) and user_intent.get("restart"):
                print("\n🔄 重新开始...\n")
                continue

            # 调用行程规划引擎
            print("\n🚀 正在为您规划行程...")
            print("⏳ 请稍候，这可能需要几秒钟...")

            try:
                product_recommendation = get_product_recommendation(user_intent)
                cost_result = calculate_total_cost(product_recommendation)

                # 显示结果
                display_results(user_intent, product_recommendation, cost_result)

                # 添加成功提示
                print("\n🎉 您的专属行程已生成完毕！")

            except Exception as e:
                print(f"\n❌ 生成行程时出现错误：{str(e)}")
                print("💡 建议：请检查输入信息是否正确，或联系客服")
                continue

            # 询问是否继续
            print("\n" + "="*70)
            print("🔄 下一步操作？")
            print("="*70)
            print("1. 继续规划新行程")
            print("2. 查看使用指南")
            print("3. 退出系统")

            while True:
                choice = input("\n👉 请选择 (1/2/3): ").strip().lower()
                if choice in ['1', 'y', 'yes', '继续']:
                    print("\n🔄 开始新的行程规划...\n")
                    break
                elif choice in ['2', 'h', 'help', '帮助']:
                    show_help()
                    continue
                elif choice in ['3', 'n', 'no', 'exit', '退出', 'q']:
                    print("\n" + "="*70)
                    print("👋 感谢使用智能旅游规划系统！")
                    print("🌟 祝您旅途愉快！")
                    print("📱 保存好您的行程，随时查看")
                    print("="*70)
                    return
                else:
                    print("  ❌ 请输入 1(继续)、2(帮助) 或 3(退出)")

        except KeyboardInterrupt:
            print("\n\n👋 操作已取消，感谢使用！")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ 系统出现错误：{str(e)}")
            print("💡 建议：请重新运行程序")
            continue

    survey = get_city_survey(city)

    display_survey(survey)
    print("\n" + "-"*60)
    print("请依次回答以上问题")
    print("-"*60)

    user_intent = collect_answers(survey)
    user_intent["city"] = city

    print("\n⏳ 正在为您匹配最佳产品...")
    product = get_product_recommendation(user_intent)

    if product.get("error"):
        print(f"\n❌ 产品推荐失败: {product['error']}")
        return 1

    optional_items = product.get('optional_items', '')
    optional_codes_raw = product.get('可选项目项目编号列表', '') or ''
    optional_codes = [c.strip() for c in optional_codes_raw.split(',') if c.strip()]

    if optional_items and optional_codes:
        print(f"\n{'='*60}")
        print("🎯 可选项目选择")
        print(f"{'='*60}")
        print(f"\n本产品提供以下可选项目：")

        optional_item_names = [item.strip() for item in optional_items.split(',') if item.strip()]
        for i, (name, code) in enumerate(zip(optional_item_names, optional_codes), 1):
            print(f"  {i}. {name} ({code})")

        print(f"\n请选择您想要添加的可选项目（输入编号，多个项目用逗号分隔）")
        print(f"例如：1,3 表示选择第1和第3个项目")
        print(f"直接回车表示不添加任何可选项目")

        while True:
            try:
                choice = input(f"\n您的选择: ").strip()
                if not choice:
                    user_intent["selected_optional"] = []
                    break

                selected_indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip()]

                if all(0 <= idx < len(optional_codes) for idx in selected_indices):
                    selected_codes = [optional_codes[idx] for idx in selected_indices]
                    user_intent["selected_optional"] = selected_codes

                    selected_names = [optional_item_names[idx] for idx in selected_indices]
                    print(f"✅ 已选择: {', '.join(selected_names)}")
                    break
                else:
                    print(f"❌ 选项编号无效，请输入1-{len(optional_codes)}之间的数字")

            except ValueError:
                print(f"❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n👋 已取消操作")
                sys.exit(0)
    else:
        print(f"\nℹ️  本产品没有可选项目")
        user_intent["selected_optional"] = []

    print("\n⏳ 正在计算费用...")
    cost_result = calculate_total_cost(product, user_intent)

    if cost_result.get("error"):
        print(f"\n❌ 费用计算失败: {cost_result['error']}")
        validation_errors = cost_result.get("validation_issues", [])
        for issue in validation_errors:
            print(f"  - {issue}")
        return 1

    display_result(product, cost_result)

    while True:
        try:
            choice = input("\n🔄 是否继续查询其他城市？(y/n) [默认n]: ").strip().lower()
            if choice in ['y', 'yes']:
                main()
                return 0
            elif choice in ['n', 'no', '']:
                print("\n👋 感谢使用城市旅游智能平台！祝您旅途愉快！\n")
                return 0
            else:
                print("❌ 请输入 y 或 n")
        except KeyboardInterrupt:
            print("\n\n👋 感谢使用城市旅游智能平台！祝您旅途愉快！\n")
            return 0


if __name__ == "__main__":
    exit(main())
