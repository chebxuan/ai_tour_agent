# product_engine.py
# 职责：从CSV匹配产品，并根据兴趣推荐可选项
# 输入：user_intent Dict
# 输出：产品信息 Dict

import pandas as pd
import os

def get_product_recommendation(user_intent):
    """
    输入: user_intent = {
        "city": "北京",
        "days": 2,
        "style": "经典",
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
        base_path = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(
            base_path,
            "Product Logic Library_final_updated.csv"
        )
        df = pd.read_csv(csv_path)

        # --- 第一步：城市 + 天数硬过滤 ---
        target_city = str(user_intent.get('city', ''))
        target_days = int(user_intent.get('days', 0))

        mask = (
            (df['城市 (City)'] == target_city) &
            (df['行程天数 (Duration)'] == target_days)
        )
        results = df[mask]

        if results.empty:
            return {
                "error": f"未找到匹配产品。"
                         f"城市: {target_city}, 天数: {target_days}天"
            }

        # --- 第二步：风格关键词匹配（匹配不上则取第一个） ---
        style_keyword = str(user_intent.get('style', ''))
        style_match = results[
            results['产品名称 (ProductName)'].str.contains(
                style_keyword, na=False
            )
        ]
        target_product = (
            style_match.iloc[0]
            if not style_match.empty
            else results.iloc[0]
        )

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
            "recommended_optional": highlight_optional
        }

    except Exception as e:
        return {"error": f"读取错误: {str(e)}"}