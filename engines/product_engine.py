# product_engine.py
# 职责：从CSV匹配产品，并根据兴趣推荐可选项
# 输入：user_intent Dict
# 输出：产品信息 Dict

import csv
import os
from .city_config import list_available_cities

def get_product_recommendation(user_intent):
    """
    输入: user_intent = {
        "city": "北京",
        "days": 2,
        "persona": "family",
        "has_child": True,
        "interest": "history",
        "recommend_optional": "梨园京剧"
    }
    输出: {
        "product_name": str,
        "days": int,
        "itinerary": str,
        "regular_items": str,
        "optional_items": str,
        "recommended_optional": str  ← 根据兴趣推荐的可选项
    }
    """
    try:
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "data",
            "products",
            "product_library.csv"
        )
        
        # 使用csv模块读取，更好地处理换行符
        products = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            # 使用QUOTE_MINIMAL来处理包含换行符的字段
            reader = csv.DictReader(f, quotechar='"', skipinitialspace=True)
            for row in reader:
                products.append(row)
        
        # --- 第一步：城市 + 天数硬过滤 ---
        target_city = str(user_intent.get('city', ''))
        target_days = int(user_intent.get('days', 0))

        # 验证城市是否 supported
        available_cities = list_available_cities()
        if target_city not in available_cities:
            return {
                "error": f"不支持的城市: {target_city}。可用城市: {', '.join(available_cities)}"
            }

        # 过滤匹配的产品
        results = [
            p for p in products
            if p.get('城市 (City)') == target_city 
            and p.get('行程天数 (Duration)') == str(target_days)
        ]

        if not results:
            return {
                "error": f"未找到匹配产品。"
                         f"城市: {target_city}, 天数: {target_days}天"
            }

        # --- 第二步：取第一个匹配产品（城市+天数唯一确定产品） ---
        target_product = results[0]

        # --- 第三步：推荐可选项 ---
        optional_items = str(
            target_product.get('可选项目 (Optional Items)', '')
        )
        recommended_optional = user_intent.get('recommend_optional', '')

        # 检查用户感兴趣的可选项是否真的在这个产品里
        if recommended_optional and recommended_optional in optional_items:
            highlight_optional = recommended_optional
        else:
            # 如果不在，就取第一个可选项作为推荐
            first_optional = (
                optional_items.split(',')[0].strip()
                if optional_items else "暂无"
            )
            highlight_optional = first_optional

        return {
            "product_name": target_product['产品名称 (ProductName)'],
            "days": int(target_product['行程天数 (Duration)']),
            "itinerary": target_product['每日行程 (Daily Itinerary)'],
            "regular_items": target_product['常规项目 (Regular Items)'],
            "optional_items": optional_items,
            "recommended_optional": highlight_optional,
            "city": target_city,  # 添加城市信息
            # 添加项目编号列表（用于费用计算）
            "常规项目项目编号列表": target_product.get('常规项目项目编号列表', ''),
            "可选项目项目编号列表": target_product.get('可选项目项目编号列表', '')
        }

    except Exception as e:
        return {"error": f"读取错误: {str(e)}"}