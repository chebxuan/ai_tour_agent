#!/usr/bin/env python3
# test_optional_items.py
# 测试可选项目选择和费用计算功能

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.product_engine import get_product_recommendation
from engines.cost_engine import calculate_total_cost


def test_with_optional_items():
    """测试带可选项目的费用计算"""
    print("="*80)
    print("🧪 测试：可选项目选择和费用计算")
    print("="*80)
    
    # 测试案例1：北京2日游，不选择可选项目
    print("\n【测试1】北京2日游 - 不选择可选项目")
    print("-" * 80)
    
    user_intent_1 = {
        "city": "北京",
        "days": 2,
        "adults": 2,
        "children": 1,
        "seniors": 0,
        "is_peak": True,
        "selected_optional": []  # 不选择任何可选项目
    }
    
    product_1 = get_product_recommendation(user_intent_1)
    print(f"产品: {product_1.get('product_name')}")
    print(f"常规项目: {product_1.get('regular_items')}")
    print(f"可选项目: {product_1.get('optional_items')}")
    
    cost_1 = calculate_total_cost(product_1, user_intent_1)
    summary_1 = cost_1.get('summary', {})
    print(f"\n费用汇总:")
    print(f"  常规项目数: {summary_1.get('regular_items_count', 0)}")
    print(f"  可选项目数: {summary_1.get('optional_items_count', 0)}")
    print(f"  总价: ¥{summary_1.get('grand_total', 0):.2f}")
    print(f"  人均: ¥{summary_1.get('per_person', 0):.2f}")
    
    # 测试案例2：北京2日游，选择所有可选项目
    print("\n\n【测试2】北京2日游 - 选择所有可选项目")
    print("-" * 80)
    
    # 获取可选项目编码
    optional_codes_raw = product_1.get('可选项目项目编号列表', '') or ''
    optional_codes = [c.strip() for c in optional_codes_raw.split(',') if c.strip()]
    
    user_intent_2 = {
        "city": "北京",
        "days": 2,
        "adults": 2,
        "children": 1,
        "seniors": 0,
        "is_peak": True,
        "selected_optional": optional_codes  # 选择所有可选项目
    }
    
    product_2 = get_product_recommendation(user_intent_2)
    cost_2 = calculate_total_cost(product_2, user_intent_2)
    summary_2 = cost_2.get('summary', {})
    
    print(f"产品: {product_2.get('product_name')}")
    print(f"选择的可选项目: {optional_codes}")
    print(f"\n费用汇总:")
    print(f"  常规项目数: {summary_2.get('regular_items_count', 0)}")
    print(f"  可选项目数: {summary_2.get('optional_items_count', 0)}")
    print(f"  总价: ¥{summary_2.get('grand_total', 0):.2f}")
    print(f"  人均: ¥{summary_2.get('per_person', 0):.2f}")
    
    # 显示可选项目的费用明细
    ticket_2 = cost_2.get('ticket_activity', {})
    print(f"\n门票活动费用明细:")
    for item in ticket_2.get('breakdown', []):
        if item.get('line_total', 0) > 0:
            code = item.get('code', '')
            if code in optional_codes:
                print(f"  🎯 [可选] {item['name']}: ¥{item['line_total']:.2f}")
            else:
                print(f"  ✅ [常规] {item['name']}: ¥{item['line_total']:.2f}")
    
    # 测试案例3：上海2日游，选择部分可选项目
    print("\n\n【测试3】上海2日游 - 选择部分可选项目")
    print("-" * 80)
    
    user_intent_3 = {
        "city": "上海",
        "days": 2,
        "adults": 2,
        "children": 0,
        "seniors": 1,
        "is_peak": True,
        "selected_optional": []  # 先获取产品
    }
    
    product_3 = get_product_recommendation(user_intent_3)
    print(f"产品: {product_3.get('product_name')}")
    print(f"可选项目: {product_3.get('optional_items')}")
    
    # 获取可选项目编码，只选择第一个
    optional_codes_raw_3 = product_3.get('可选项目项目编号列表', '') or ''
    optional_codes_3 = [c.strip() for c in optional_codes_raw_3.split(',') if c.strip()]
    
    if optional_codes_3:
        selected_3 = [optional_codes_3[0]]  # 只选择第一个
        user_intent_3['selected_optional'] = selected_3
        
        cost_3 = calculate_total_cost(product_3, user_intent_3)
        summary_3 = cost_3.get('summary', {})
        
        print(f"选择的可选项目: {selected_3}")
        print(f"\n费用汇总:")
        print(f"  常规项目数: {summary_3.get('regular_items_count', 0)}")
        print(f"  可选项目数: {summary_3.get('optional_items_count', 0)}")
        print(f"  总价: ¥{summary_3.get('grand_total', 0):.2f}")
        print(f"  人均: ¥{summary_3.get('per_person', 0):.2f}")
    
    # 对比总结
    print("\n" + "="*80)
    print("📊 对比总结")
    print("="*80)
    print(f"\n北京2日游（2成1童）:")
    print(f"  无可选项目: ¥{summary_1.get('grand_total', 0):.2f} (人均¥{summary_1.get('per_person', 0):.2f})")
    print(f"  有可选项目: ¥{summary_2.get('grand_total', 0):.2f} (人均¥{summary_2.get('per_person', 0):.2f})")
    if summary_1.get('grand_total', 0) > 0:
        diff = summary_2.get('grand_total', 0) - summary_1.get('grand_total', 0)
        print(f"  差额: ¥{diff:.2f} (可选项目费用)")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    test_with_optional_items()
