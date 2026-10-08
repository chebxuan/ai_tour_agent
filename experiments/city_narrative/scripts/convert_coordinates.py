#!/usr/bin/env python3
"""
坐标转换脚本：将高德GCJ-02坐标转换为WGS-84坐标
"""
import pandas as pd
import math
from typing import Tuple


def gcj02_to_wgs84(lat: float, lon: float) -> Tuple[float, float]:
    """
    将GCJ-02（高德坐标）转换为WGS-84（GPS坐标）

    Args:
        lat: 纬度（GCJ-02）
        lon: 经度（GCJ-02）

    Returns:
        (纬度, 经度) (WGS-84)
    """
    # 常量
    pi = 3.1415926535897932384626
    a = 6378245.0  # 长半轴
    ee = 0.00669342162296594323  # 扁率

    def transformlat(lat, lon):
        ret = -100.0 + 2.0 * lat + 3.0 * lon + 0.2 * lon * lon + \
              0.1 * lat * lon + 0.2 * math.sqrt(abs(lat))
        ret += (20.0 * math.sin(6.0 * lat * pi) + 20.0 *
                math.sin(2.0 * lat * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lon * pi) + 40.0 *
                math.sin(lon / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lon / 12.0 * pi) + 320 *
                math.sin(lon * pi / 30.0)) * 2.0 / 3.0
        return ret

    def transformlon(lat, lon):
        ret = 300.0 + lat + 2.0 * lon + 0.1 * lat * lat + \
              0.1 * lat * lon + 0.1 * math.sqrt(abs(lat))
        ret += (20.0 * math.sin(6.0 * lat * pi) + 20.0 *
                math.sin(2.0 * lat * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * pi) + 40.0 *
                math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lat / 12.0 * pi) + 300.0 *
                math.sin(lat / 30.0 * pi)) * 2.0 / 3.0
        return ret

    dlat = transformlat(lat - 35.0, lon - 105.0)
    dlon = transformlon(lat - 35.0, lon - 105.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglon = lon + dlon

    return (lat * 2 - mglat, lon * 2 - mglon)


def convert_coordinates(input_csv, output_csv):
    """
    将CSV中的GCJ-02坐标转换为WGS-84坐标

    Args:
        input_csv: 输入CSV文件路径（GCJ-02坐标）
        output_csv: 输出CSV文件路径（WGS-84坐标）
    """
    print("=" * 60)
    print("🔄 开始坐标转换（GCJ-02 → WGS-84）")
    print("=" * 60)

    # 读取CSV
    df = pd.read_csv(input_csv)
    print(f"\n📂 读取文件: {input_csv}")
    print(f"   总地标数: {len(df)}")

    # 检查坐标字段
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        print(f"\n❌ 文件缺少经纬度字段")
        return

    # 转换坐标
    print(f"\n📍 转换坐标...")

    wgs84_latitudes = []
    wgs84_longitudes = []

    for idx, row in df.iterrows():
        if pd.notna(row['latitude']) and pd.notna(row['longitude']):
            lat = row['latitude']
            lon = row['longitude']

            # 转换坐标
            wgs84_lat, wgs84_lon = gcj02_to_wgs84(lat, lon)

            wgs84_latitudes.append(wgs84_lat)
            wgs84_longitudes.append(wgs84_lon)

            if (idx + 1) % 50 == 0:
                print(f"   进度: {idx+1}/{len(df)}")
        else:
            wgs84_latitudes.append(None)
            wgs84_longitudes.append(None)

    # 更新坐标
    df['latitude'] = wgs84_latitudes
    df['longitude'] = wgs84_longitudes

    # 保存结果
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')

    print(f"\n" + "=" * 60)
    print(f"✅ 坐标转换完成")
    print(f"=" * 60)
    print(f"💾 已保存到: {output_csv}")

    print(f"\n📊 坐标对比（示例）:")
    print(f"   GCJ-02: {df['latitude'].iloc[0]:.6f}, {df['longitude'].iloc[0]:.6f}")
    print(f"   WGS-84: {wgs84_latitudes[0]:.6f}, {wgs84_longitudes[0]:.6f}")

    print(f"\n💡 说明:")
    print(f"   - 原始坐标: GCJ-02（高德坐标系）")
    print(f"   - 转换后坐标: WGS-84（国际标准坐标系）")
    print(f"   - 用途: 用于Google Maps、OpenStreetMap等")
    print(f"   - 偏移: 约几十米，纠偏后更准确")

    return df


if __name__ == "__main__":
    import sys
    import os

    # 获取文件路径
    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
    else:
        input_csv = "city_narratives_amap_coords.csv"

    if len(sys.argv) > 2:
        output_csv = sys.argv[2]
    else:
        output_csv = "city_narratives_wgs84_coords.csv"

    # 检查文件是否存在
    if not os.path.exists(input_csv):
        print(f"❌ 文件不存在: {input_csv}")
        print(f"\n请先运行高德API坐标补全脚本:")
        print(f"  python scripts/add_coordinates_amap.py <API_Key>")
        sys.exit(1)

    # 转换坐标
    convert_coordinates(input_csv, output_csv)

    print(f"\n下一步: 运行可视化脚本")
    print(f"  python scripts/visualize_map.py {output_csv} shanghai_landmarks_map.html")
