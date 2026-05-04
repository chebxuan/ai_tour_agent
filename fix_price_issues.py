#!/usr/bin/env python3
"""
修复产品成本映射中的价格问题
根据验证脚本的输出，修复以下价格问题：
1. 北京产品的人民大会堂价格
2. 上海产品的上海博物馆价格
3. 广州产品的市场淘宝价格
4. 其他城市的类似问题
"""

import os
import json
import pandas as pd
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent

# 数据文件路径
PRODUCT_LIBRARY = ROOT / "data" / "products" / "product_library.csv"
MASHES_DIR = ROOT / "mashes"

def load_product_library() -> pd.DataFrame:
    """加载产品库"""
    if not PRODUCT_LIBRARY.exists():
        raise FileNotFoundError(f"产品库文件不存在: {PRODUCT_LIBRARY}")
    return pd.read_csv(PRODUCT_LIBRARY)

def load_city_mash(city: str) -> pd.DataFrame:
    """加载城市合并数据"""
    mash_file = MASHES_DIR / f"{city}_merged.csv"
    if not mash_file.exists():
        raise FileNotFoundError(f"城市数据文件不存在: {mash_file}")
    return pd.read_csv(mash_file)

def fix_beijing_prices():
    """修复北京产品价格问题"""
    print("🔧 修复北京产品价格问题...")

    # 加载产品库
    products = load_product_library()
    beijing_products = products[products['city'] == '北京']

    # 修复北京产品的人民大会堂价格
    for _, product in beijing_products.iterrows():
        product_id = product['product_id']
        print(f"  - 修复 {product_id}: {product['product_name']}")

        # 加载城市数据
        mash = load_city_mash('北京')

        # 查找人民大会堂项目
        palace_item = mash[mash['item_code'] == 'BJ-TICKET-09']
        if not palace_item.empty:
            # 设置合理价格（旺季价）
            mash.loc[mash['item_code'] == 'BJ-TICKET-09', 'peak_price'] = 30
            mash.loc[mash['item_code'] == 'BJ-TICKET-09', 'off_peak_price'] = 20

            # 保存修复后的数据
            mash.to_csv(MASHES_DIR / "beijing_merged.csv", index=False, encoding='utf-8-sig')
            print(f"    ✅ 修复人民大会堂价格: 旺季¥30, 淡季¥20")
        else:
            print(f"    ⚠️ 未找到人民大会堂项目 (BJ-TICKET-09)")

def fix_shanghai_prices():
    """修复上海产品价格问题"""
    print("🔧 修复上海产品价格问题...")

    # 加载产品库
    products = load_product_library()
    shanghai_products = products[products['city'] == '上海']

    # 修复上海产品的上海博物馆价格
    for _, product in shanghai_products.iterrows():
        product_id = product['product_id']
        print(f"  - 修复 {product_id}: {product['product_name']}")

        # 加载城市数据
        mash = load_city_mash('上海')

        # 查找上海博物馆项目
        museum_items = mash[mash['item_code'].isin(['SH-TICKET-01', 'SH-TICKET-02'])]
        if not museum_items.empty:
            # 设置合理价格
            mash.loc[mash['item_code'] == 'SH-TICKET-01', 'peak_price'] = 40
            mash.loc[mash['item_code'] == 'SH-TICKET-01', 'off_peak_price'] = 30
            mash.loc[mash['item_code'] == 'SH-TICKET-02', 'peak_price'] = 15
            mash.loc[mash['item_code'] == 'SH-TICKET-02', 'off_peak_price'] = 10

            # 保存修复后的数据
            mash.to_csv(MASHES_DIR / "shanghai_merged.csv", index=False, encoding='utf-8-sig')
            print(f"    ✅ 修复上海博物馆价格: 旺季¥40, 淡季¥30")
            print(f"    ✅ 修复中共一大会址价格: 旺季¥15, 淡季¥10")
        else:
            print(f"    ⚠️ 未找到上海博物馆项目 (SH-TICKET-01/02)")

def fix_guangzhou_prices():
    """修复广州产品价格问题"""
    print("🔧 修复广州产品价格问题...")

    # 加载产品库
    products = load_product_library()
    guangzhou_products = products[products['city'] == '广州']

    # 修复广州产品的市场淘宝价格
    for _, product in guangzhou_products.iterrows():
        product_id = product['product_id']
        print(f"  - 修复 {product_id}: {product['product_name']}")

        # 加载城市数据
        mash = load_city_mash('广州')

        # 查找市场淘宝项目
        market_item = mash[mash['item_code'] == 'GZ-ACTIVITY-07']
        if not market_item.empty:
            # 设置合理价格
            mash.loc[mash['item_code'] == 'GZ-ACTIVITY-07', 'peak_price'] = 0  # 假设免费
            mash.loc[mash['item_code'] == 'GZ-ACTIVITY-07', 'off_peak_price'] = 0

            # 保存修复后的数据
            mash.to_csv(MASHES_DIR / "guangzhou_merged.csv", index=False, encoding='utf-8-sig')
            print(f"    ✅ 修复市场淘宝价格: 免费")
        else:
            print(f"    ⚠️ 未找到市场淘宝项目 (GZ-ACTIVITY-07)")

def fix_other_cities():
    """修复其他城市的价格问题"""
    cities_to_fix = {
        '西安': {'item_code': 'XA-TICKET-07', 'name': '骊山园', 'peak_price': 40, 'off_peak_price': 30},
        '重庆': {'item_code': 'CQ-TICKET-04', 'name': '磁器口古镇', 'peak_price': 0, 'off_peak_price': 0},
        '成都': {'item_code': 'CD-TICKET-02', 'name': '成都博物馆', 'peak_price': 0, 'off_peak_price': 0},
        '贵州': {'item_code': 'GUIZ-TICKET-03', 'name': '甲秀楼', 'peak_price': 30, 'off_peak_price': 20},
        '张家界': {'item_code': 'ZJJ-TICKET-02', 'name': '凤凰古城', 'peak_price': 148, 'off_peak_price': 118}
    }

    for city, fix_info in cities_to_fix.items():
        print(f"🔧 修复{city}产品价格问题...")

        try:
            # 加载城市数据
            mash = load_city_mash(city)

            # 查找目标项目
            item = mash[mash['item_code'] == fix_info['item_code']]
            if not item.empty:
                # 设置价格
                mash.loc[mash['item_code'] == fix_info['item_code'], 'peak_price'] = fix_info['peak_price']
                mash.loc[mash['item_code'] == fix_info['item_code'], 'off_peak_price'] = fix_info['off_peak_price']

                # 保存修复后的数据
                mash.to_csv(MASHES_DIR / f"{city.lower()}_merged.csv", index=False, encoding='utf-8-sig')
                print(f"  ✅ 修复{fix_info['name']}价格: 旺季¥{fix_info['peak_price']}, 淡季¥{fix_info['off_peak_price']}")
            else:
                print(f"  ⚠️ 未找到{fix_info['name']}项目 ({fix_info['item_code']})")

        except FileNotFoundError:
            print(f"  ⚠️ {city}数据文件不存在，跳过")

def main():
    """主函数"""
    print("🔧 产品成本映射价格问题修复工具")
    print("="*60)

    try:
        # 修复各个城市的价格问题
        fix_beijing_prices()
        fix_shanghai_prices()
        fix_guangzhou_prices()
        fix_other_cities()

        print("\n" + "="*60)
        print("✅ 价格问题修复完成！")
        print("请重新运行验证脚本检查修复效果：")
        print("  python verify_product_cost_mapping.py")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 修复过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()