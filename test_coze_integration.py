#!/usr/bin/env python3
# test_coze_integration.py - 测试Coze集成功能
# 模拟Coze Agent调用API的过程

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
from cli_app import get_city_survey


class CozeAPITester:
    """Coze API测试器"""

    def __init__(self):
        self.session_id = f"session_{os.getpid()}"
        self.user_id = "test_user"

    def log_message(self, role: str, message: str):
        """记录对话消息"""
        print(f"\n[{role}] {message}")

    def simulate_coze_agent_workflow(self):
        """模拟Coze Agent工作流程"""
        print("="*70)
        print("🤖 Coze Agent 集成测试")
        print("="*70)

        # 1. 会话开始
        self.trigger_session_start()

        # 2. 问候用户
        self.greet_user()

        # 3. 收集用户需求
        user_intent = self.collect_user_requirements()

        # 4. 获取产品推荐
        product_recommendation = self.get_recommendations(user_intent)

        # 5. 计算费用
        cost_result = self.calculate_costs(product_recommendation)

        # 6. 显示结果
        self.display_plan(user_intent, product_recommendation, cost_result)

        # 7. 会话结束
        self.trigger_plan_completed(user_intent, cost_result)

    def trigger_session_start(self):
        """触发会话开始事件"""
        print("\n🔄 触发会话开始事件...")
        print(f"   - 用户ID: {self.user_id}")
        print(f"   - 会话ID: {self.session_id}")

    def greet_user(self):
        """问候用户"""
        print("\n👋 欢迎使用智能旅游规划助手！")
        print("我是您的专属旅游顾问，将帮您规划完美的行程。")
        print("\n请告诉我您想去哪里旅游？")

    def collect_user_requirements(self) -> Dict[str, Any]:
        """收集用户需求"""
        print("\n" + "-"*60)
        print("📋 收集您的旅游需求")
        print("-"*60)

        # 模拟用户选择
        cities = list_available_cities()
        city = cities[0]  # 选择北京作为示例

        print(f"🏙️ 您选择了：{city}")

        # 生成问卷
        survey = get_city_survey(city)

        # 模拟用户回答
        user_intent = {
            "city": city,
            "days": 3,
            "adults": 2,
            "children": 1,
            "seniors": 0,
            "is_peak": True,
            "hotel": f"{get_city_code_prefix(city)}-HOTEL-02",
            "transfer": None,
            "car_days": 1,
            "transfer_times": 2,
            "selected_optional": []
        }

        print(f"\n📝 您的需求：")
        print(f"   - 城市：{city}")
        print(f"   - 天数：{user_intent['days']}天")
        print(f"   - 人数：{user_intent['adults']}成人，{user_intent['children']}儿童")
        print(f"   - 季节：{'旺季' if user_intent['is_peak'] else '淡季'}")
        print(f"   - 住宿：舒适型")
        print(f"   - 交通：包车1天，接送2次")

        return user_intent

    def get_recommendations(self, user_intent: Dict[str, Any]) -> Dict[str, Any]:
        """获取产品推荐"""
        print("\n🚀 正在为您推荐产品...")

        try:
            product = get_product_recommendation(user_intent)

            if product.get("error"):
                print(f"❌ 推荐失败：{product['error']}")
                return {}

            print("✅ 产品推荐成功！")
            print(f"📦 产品名称：{product.get('product_name', 'N/A')}")
            print(f"🎯 可选项目：{product.get('optional_items', '无')}")

            return product

        except Exception as e:
            print(f"❌ API调用失败：{str(e)}")
            return {}

    def calculate_costs(self, product_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """计算费用"""
        print("\n💰 正在计算费用...")

        try:
            cost_result = calculate_total_cost(product_recommendation)
            total_cost = cost_result.get("summary", {}).get("total_cost", 0)

            print(f"✅ 费用计算完成！")
            print(f"💵 总费用：¥{total_cost:,.2f}")

            return cost_result

        except Exception as e:
            print(f"❌ 费用计算失败：{str(e)}")
            return {}

    def display_plan(self, user_intent: Dict[str, Any],
                    product_recommendation: Dict[str, Any],
                    cost_result: Dict[str, Any]):
        """显示行程计划"""
        print("\n" + "="*70)
        print("🎉 您的专属行程计划")
        print("="*70)

        # 基本信息展示
        summary = cost_result.get("summary", {})
        print(f"\n📋 【行程摘要】")
        print("-"*50)
        print(f"🏷️  产品名称: {summary.get('product_name', 'N/A')}")
        print(f"🌆 城市: {summary.get('city', 'N/A')}")
        print(f"📅 行程天数: {summary.get('days', 0)} 天")
        print(f"👥 总人数: {summary.get('total_people', 0)} 人 "
              f"(成人:{summary.get('adults', 0)} | "
              f"儿童:{summary.get('children', 0)} | "
              f"老人:{summary.get('seniors', 0)})")
        print(f"🌸 出行季节: {'🌸 旺季' if summary.get('is_peak') else '❄️ 淡季'}")

        # 费用概览
        print(f"\n💰 【费用概览】")
        print("-"*30)
        total_cost = summary.get('total_cost', 0)
        print(f"  💵 总费用: ¥{total_cost:,.2f}")

        if summary.get('total_people', 0) > 0:
            per_person_cost = total_cost / summary.get('total_people', 0)
            print(f"  👥 人均费用: ¥{per_person_cost:,.2f}")

        # 项目统计
        regular_count = summary.get('regular_items_count', 0)
        optional_count = summary.get('optional_items_count', 0)
        print(f"\n📊 【项目统计】")
        print(f"  ✅ 常规项目: {regular_count} 个")
        print(f"  🎯 可选项目: {optional_count} 个")

        print("\n🎯 Coze Agent已为您完成行程规划！")

    def trigger_plan_completed(self, user_intent: Dict[str, Any],
                              cost_result: Dict[str, Any]):
        """触发行程完成事件"""
        print("\n🔄 触发行程完成事件...")

        summary = cost_result.get("summary", {})
        total_cost = summary.get('total_cost', 0)

        print(f"   - 规划城市：{user_intent.get('city', 'N/A')}")
        print(f"   - 总费用：¥{total_cost:,.2f}")
        print(f"   - 会话结束")

        print("\n" + "="*70)
        print("✅ Coze集成测试完成！")
        print("🌟 您的专属行程已生成")
        print("="*70)


def test_api_endpoints():
    """测试各个API端点"""
    print("\n🧪 测试API端点...")

    tester = CozeAPITester()

    # 测试1：获取城市列表
    print("\n1. 测试 list_available_cities")
    cities = list_available_cities()
    print(f"   返回城市数量：{len(cities)}")
    print(f"   前3个城市：{cities[:3]}")

    # 测试2：生成问卷
    print("\n2. 测试 get_city_survey")
    survey = get_city_survey("北京")
    print(f"   问卷题目数量：{len(survey)}")
    print(f"   第一题：{survey[0]['question']}")

    # 测试3：产品推荐
    print("\n3. 测试 get_product_recommendation")
    user_intent = {
        "city": "北京",
        "days": 3,
        "adults": 2,
        "children": 1,
        "seniors": 0,
        "is_peak": True,
        "hotel": "BJ-HOTEL-02",
        "transfer": None,
        "car_days": 1,
        "transfer_times": 2,
        "selected_optional": []
    }
    product = get_product_recommendation(user_intent)
    print(f"   推荐成功：{'✅' if not product.get('error') else '❌'}")

    # 测试4：费用计算
    print("\n4. 测试 calculate_total_cost")
    if product and not product.get('error'):
        cost = calculate_total_cost(product, user_intent)
        print(f"   计算成功：{'✅' if cost else '❌'}")
    else:
        print("   跳过测试（产品推荐失败）")
        print("   ❌")

    if cost:
        total_cost = cost.get("summary", {}).get("total_cost", 0)
        print(f"   总费用：¥{total_cost:,.2f}")


def main():
    """主函数"""
    print("🔧 Coze集成测试工具")
    print("="*50)

    # 选择测试模式 - 默认运行API端点测试
    print("\n自动选择：API端点独立测试")
    test_api_endpoints()
    print("\n✅ API端点测试完成")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")