#!/usr/bin/env python3
"""
演示数据生成脚本：基于区域中心点生成模拟坐标
注意：这是用于演示的模拟数据，真实坐标需要使用地理编码API获取
"""
import pandas as pd
import random
import os


def generate_demo_coordinates(input_csv, output_csv):
    """
    基于区域中心点生成模拟坐标

    Args:
        input_csv: 输入CSV文件路径
        output_csv: 输出CSV文件路径（包含模拟坐标）
    """
    print("=" * 60)
    print("🎨 生成演示坐标数据（模拟坐标）")
    print("=" * 60)

    # 读取CSV
    df = pd.read_csv(input_csv)
    print(f"\n📂 读取文件: {input_csv}")
    print(f"   总地标数: {len(df)}")

    # 上海各区域中心点（近似值）
    region_centers = {
        "武康路-安福路": (31.2068, 121.4377),
        "外滩-圆明园路": (31.2376, 121.4916),
        "豫园-老城厢": (31.2265, 121.4889),
        "衡山路-复兴西路": (31.2080, 121.4460),
        "南京西路-静安寺": (31.2270, 121.4460),
        "新天地-马当路": (31.2210, 121.4770),
        "愚园路 (长宁段)": (31.2150, 121.4350),
        "苏州河 (静安/黄浦段)": (31.2480, 121.4680)
    }

    # 生成模拟坐标
    print(f"\n📍 生成模拟坐标...")

    latitudes = []
    longitudes = []

    for idx, row in df.iterrows():
        region = row['区域']

        if region in region_centers:
            center_lat, center_lon = region_centers[region]

            # 在中心点附近随机偏移（约1公里范围）
            offset_lat = random.uniform(-0.01, 0.01)
            offset_lon = random.uniform(-0.01, 0.01)

            lat = center_lat + offset_lat
            lon = center_lon + offset_lon

            latitudes.append(round(lat, 6))
            longitudes.append(round(lon, 6))

            if (idx + 1) % 50 == 0:
                print(f"   进度: {idx+1}/{len(df)}")

    # 添加坐标到DataFrame
    df['latitude'] = latitudes
    df['longitude'] = longitudes

    # 保存结果
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')

    print(f"\n" + "=" * 60)
    print(f"✅ 模拟坐标生成完成")
    print(f"=" * 60)
    print(f"💾 已保存到: {output_csv}")

    print(f"\n⚠️  重要提示:")
    print(f"   - 这是模拟坐标，仅用于演示可视化功能")
    print(f"   - 真实坐标需要使用地理编码API获取")
    print(f"   - 建议在高德开放平台申请API Key")
    print(f"   - 使用 scripts/add_coordinates.py 获取真实坐标")

    return df


if __name__ == "__main__":
    import sys

    # 获取文件路径
    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
    else:
        input_csv = "city_narratives.csv"

    if len(sys.argv) > 2:
        output_csv = sys.argv[2]
    else:
        output_csv = "city_narratives_demo_coords.csv"

    # 检查文件是否存在
    if not os.path.exists(input_csv):
        print(f"❌ 文件不存在: {input_csv}")
        sys.exit(1)

    # 生成演示坐标
    generate_demo_coordinates(input_csv, output_csv)
