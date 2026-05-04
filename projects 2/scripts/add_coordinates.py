#!/usr/bin/env python3
"""
坐标补全脚本：使用免费的Nominatim API（OpenStreetMap）
无需API Key，但有频率限制（1次/秒）
"""
import pandas as pd
import time
import os
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def add_coordinates(input_csv, output_csv):
    """
    为CSV文件中的地标地址补全经纬度坐标

    Args:
        input_csv: 输入CSV文件路径
        output_csv: 输出CSV文件路径（包含经纬度）
    """
    print("=" * 60)
    print("🗺️  开始补全经纬度坐标")
    print("=" * 60)

    # 读取CSV
    df = pd.read_csv(input_csv)
    print(f"\n📂 读取文件: {input_csv}")
    print(f"   总地标数: {len(df)}")

    # 检查是否已有坐标
    if 'latitude' in df.columns and 'longitude' in df.columns:
        print(f"\n✅ 文件已包含坐标字段")
        print(f"   已有坐标的地标: {df['latitude'].notna().sum()}个")
        return

    # 初始化地理编码器
    print(f"\n🔍 初始化地理编码器 (Nominatim - 免费服务)")
    geolocator = Nominatim(user_agent="city_walk_extractor")

    # 添加速率限制（1次/秒）
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # 补全坐标
    print(f"\n📍 开始补全坐标...")
    print(f"   预计时间: {len(df)} 秒 ({len(df)/60:.1f} 分钟)")

    latitudes = []
    longitudes = []
    success_count = 0
    fail_count = 0
    fail_landmarks = []

    for idx, row in df.iterrows():
        landmark_name = row['地标名称']
        address = row['地址']
        region = row['区域']

        # 组合搜索地址（提高准确度）
        search_query = f"{landmark_name}, {address}, {region}, 上海"

        try:
            # 调用地理编码
            location = geocode(search_query)

            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
                success_count += 1
                print(f"   ✅ [{idx+1}/{len(df)}] {landmark_name}: {location.latitude:.6f}, {location.longitude:.6f}")
            else:
                latitudes.append(None)
                longitudes.append(None)
                fail_count += 1
                fail_landmarks.append(landmark_name)
                print(f"   ⚠️  [{idx+1}/{len(df)}] {landmark_name}: 未找到坐标")

        except Exception as e:
            latitudes.append(None)
            longitudes.append(None)
            fail_count += 1
            fail_landmarks.append(landmark_name)
            print(f"   ❌ [{idx+1}/{len(df)}] {landmark_name}: 错误 - {str(e)}")

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

    return valid >= total * 0.8  # 至少80%成功


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
        output_csv = "city_narratives_with_coords.csv"

    # 检查文件是否存在
    if not os.path.exists(input_csv):
        print(f"❌ 文件不存在: {input_csv}")
        sys.exit(1)

    # 补全坐标
    df = add_coordinates(input_csv, output_csv)

    # 验证坐标
    if validate_coordinates(output_csv):
        print(f"\n✅ 坐标质量良好，可以继续可视化")
    else:
        print(f"\n⚠️  坐标质量较差，建议手动补充")
