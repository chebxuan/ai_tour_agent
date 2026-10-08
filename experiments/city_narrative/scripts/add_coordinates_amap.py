#!/usr/bin/env python3
"""
坐标补全脚本：使用高德地图API获取真实坐标
需要先在高德开放平台申请API Key
"""
import pandas as pd
import time
import requests
from typing import Optional, Tuple


def geocode_address(address: str, api_key: str, city: str = "上海") -> Optional[Tuple[float, float]]:
    """
    使用高德API获取地址的经纬度
    
    尝试多种搜索策略：
    1. 完整地址搜索
    2. 地标名称+城市搜索
    3. 简化地址搜索
    """
    url = "https://restapi.amap.com/v3/geocode/geo"
    
    # 策略1: 完整地址
    params = {"key": api_key, "address": address, "city": city, "output": "json"}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data['status'] == '1' and data['geocodes']:
            location = data['geocodes'][0]['location']
            lon, lat = location.split(',')
            return float(lat), float(lon)
    except Exception as e:
        print(f"      ❌ API调用错误: {e}")
        return None
    
    return None


def geocode_landmark(name: str, address: str, region: str, api_key: str) -> Optional[Tuple[float, float]]:
    """
    智能地标坐标查询，尝试多种搜索组合
    """
    # 搜索策略列表（按优先级）
    search_queries = []
    
    # 如果地址包含具体门牌号，优先使用
    if address and any(c.isdigit() for c in address):
        search_queries.append(f"{address}, 上海")
        search_queries.append(f"{name}, {address}, 上海")
    
    # 使用地标名称+区域
    if region:
        search_queries.append(f"{name}, {region}, 上海")
    
    # 纯地标名称搜索
    search_queries.append(f"{name}, 上海")
    search_queries.append(name)
    
    # 尝试所有策略
    for query in search_queries:
        result = geocode_address(query, api_key)
        if result:
            return result
    
    return None


def add_coordinates_with_amap(input_csv, output_csv, api_key):
    """
    使用高德API为地标补全真实坐标

    Args:
        input_csv: 输入CSV文件路径
        output_csv: 输出CSV文件路径
        api_key: 高德API Key
    """
    print("=" * 60)
    print("🗺️  开始使用高德API补全真实坐标")
    print("=" * 60)

    # 读取CSV
    df = pd.read_csv(input_csv)
    print(f"\n📂 读取文件: {input_csv}")
    print(f"   总地标数: {len(df)}")

    # 检查API Key
    if not api_key or api_key == "YOUR_AMAP_API_KEY":
        print(f"\n❌ 请提供有效的高德API Key")
        print(f"   获取方式: https://lbs.amap.com/")
        return

    # 补全坐标
    print(f"\n📍 开始补全坐标...")
    print(f"   预计时间: {len(df)} 秒 ({len(df)/60:.1f} 分钟)")
    print(f"   ⚠️  注意: 高德API有频率限制（免费版：2000次/天）")

    latitudes = []
    longitudes = []
    success_count = 0
    fail_count = 0
    fail_landmarks = []

    for idx, row in df.iterrows():
        # 支持中英文列名
        landmark_name = row.get('node_name') or row.get('地标名称') or row.get('name', '')
        address = row.get('address') or row.get('地址') or ''
        region = row.get('region') or row.get('区域') or ''

        # 使用智能查询（尝试多种搜索策略）
        result = geocode_landmark(landmark_name, address, region, api_key)

        if result:
            latitudes.append(result[0])
            longitudes.append(result[1])
            success_count += 1
            print(f"   ✅ [{idx+1}/{len(df)}] {landmark_name}: {result[0]:.6f}, {result[1]:.6f}")
        else:
            latitudes.append(None)
            longitudes.append(None)
            fail_count += 1
            fail_landmarks.append(landmark_name)
            print(f"   ⚠️  [{idx+1}/{len(df)}] {landmark_name}: 未找到坐标")

        # 速率限制（1次/秒，避免触发API限制）
        time.sleep(1)

        # 进度显示
        if (idx + 1) % 10 == 0:
            print(f"   进度: {idx+1}/{len(df)} ({(idx+1)/len(df)*100:.0f}%)")

    # 添加坐标到DataFrame
    df['latitude'] = latitudes
    df['longitude'] = longitudes

    # 保存结果
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')

    print(f"\n" + "=" * 60)
    print(f"✅ 坐标补全完成")
    print(f"=" * 60)
    print(f"成功: {success_count}个 ({success_count/len(df)*100:.1f}%)")
    print(f"失败: {fail_count}个 ({fail_count/len(df)*100:.1f}%)")

    if fail_count > 0:
        print(f"\n⚠️  以下地标未能获取坐标:")
        for landmark in fail_landmarks:
            print(f"   - {landmark}")

    print(f"\n💾 已保存到: {output_csv}")
    print(f"\n📊 API使用情况:")
    print(f"   本次调用: {len(df)} 次")
    print(f"   剩余额度: 2000 - {len(df)} = {2000 - len(df)} 次（每天重置）")

    return df


def validate_coordinates(csv_file):
    """
    验证坐标质量
    """
    print(f"\n" + "=" * 60)
    print(f"🔍 验证坐标质量")
    print(f"=" * 60)

    df = pd.read_csv(csv_file)

    # 统计
    total = len(df)
    valid = df['latitude'].notna().sum()
    invalid = df['latitude'].isna().sum()

    print(f"\n总地标数: {total}")
    print(f"有效坐标: {valid} ({valid/total*100:.1f}%)")
    print(f"无效坐标: {invalid} ({invalid/total*100:.1f}%)")

    if valid > 0:
        print(f"\n坐标范围:")
        print(f"  纬度: {df['latitude'].min():.6f} ~ {df['latitude'].max():.6f}")
        print(f"  经度: {df['longitude'].min():.6f} ~ {df['longitude'].max():.6f}")

        print(f"\n坐标中心点:")
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        print(f"  纬度: {center_lat:.6f}")
        print(f"  经度: {center_lon:.6f}")

        print(f"\n⚠️  注意: 这些坐标是GCJ-02（火星坐标）")
        print(f"   如需在Google Maps或OpenStreetMap中使用，需要转换为WGS-84坐标")

    return valid >= total * 0.8  # 至少80%成功


if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    
    # 加载.env文件
    load_dotenv()

    # 获取API Key（优先从.env读取GAODE_API_KEY，兼容AMAP_API_KEY）
    api_key = os.getenv("GAODE_API_KEY") or os.getenv("AMAP_API_KEY")
    
    # 命令行参数可覆盖
    if len(sys.argv) > 1 and sys.argv[1]:
        api_key = sys.argv[1]

    # 检查API Key
    if not api_key or api_key == "YOUR_AMAP_API_KEY":
        print("=" * 60)
        print("❌ 请提供高德API Key")
        print("=" * 60)
        print("\n推荐方法 - 在.env文件中配置:")
        print(f"  GAODE_API_KEY=你的高德API密钥")
        print(f"\n其他方法:")
        print(f"  命令行参数: python {sys.argv[0]} <你的API_Key>")
        print(f"  环境变量: export GAODE_API_KEY=<你的API_Key>")
        print("\n获取API Key:")
        print("  1. 访问: https://lbs.amap.com/")
        print("  2. 注册/登录")
        print("  3. 创建应用")
        print("  4. 获取Web服务API Key")
        sys.exit(1)
    else:
        print(f"✅ 已读取高德API Key: {api_key[:8]}...")

    # 获取文件路径
    if len(sys.argv) > 2:
        input_csv = sys.argv[2]
    else:
        input_csv = "city_narratives.csv"

    if len(sys.argv) > 3:
        output_csv = sys.argv[3]
    else:
        output_csv = "city_narratives_amap_coords.csv"

    # 检查文件是否存在
    if not os.path.exists(input_csv):
        print(f"❌ 文件不存在: {input_csv}")
        sys.exit(1)

    # 补全坐标
    df = add_coordinates_with_amap(input_csv, output_csv, api_key)

    # 验证坐标
    if validate_coordinates(output_csv):
        print(f"\n✅ 坐标质量良好，可以继续可视化")
        print(f"\n下一步: 运行可视化脚本")
        print(f"  python scripts/visualize_map.py {output_csv} shanghai_landmarks_map.html")
    else:
        print(f"\n⚠️  坐标质量较差，建议检查API Key或手动补充")
