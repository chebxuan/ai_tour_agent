#!/usr/bin/env python3
"""
补充缺失坐标：使用Nominatim API补充缺失的坐标
"""
import pandas as pd
import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def fill_missing_coordinates(input_csv, output_csv):
    """
    补充缺失的坐标

    Args:
        input_csv: 输入CSV文件路径
        output_csv: 输出CSV文件路径
    """
    print("=" * 60)
    print("🔧 补充缺失坐标")
    print("=" * 60)

    # 读取CSV
    df = pd.read_csv(input_csv)
    print(f"\n📂 读取文件: {input_csv}")
    print(f"   总地标数: {len(df)}")

    # 找出缺失坐标的地标
    missing_coords = df[df['latitude'].isna() | df['longitude'].isna()].copy()
    print(f"   缺失坐标: {len(missing_coords)}个")

    if len(missing_coords) == 0:
        print(f"\n✅ 没有缺失坐标的地标")
        return

    # 初始化地理编码器
    print(f"\n🔍 初始化地理编码器 (Nominatim)")
    geolocator = Nominatim(user_agent="city_walk_fill_missing")

    # 添加速率限制（1次/秒）
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # 补充坐标
    print(f"\n📍 开始补充坐标...")
    print(f"   预计时间: {len(missing_coords)} 秒")

    success_count = 0

    for idx, row in missing_coords.iterrows():
        landmark_name = row['地标名称']
        address = row['地址']
        region = row['区域']

        # 组合搜索地址
        search_query = f"{landmark_name}, {address}, {region}, 上海"

        try:
            # 调用地理编码
            location = geocode(search_query)

            if location:
                # 更新坐标
                df.loc[idx, 'latitude'] = location.latitude
                df.loc[idx, 'longitude'] = location.longitude
                success_count += 1
                print(f"   ✅ [{success_count}/{len(missing_coords)}] {landmark_name}: {location.latitude:.6f}, {location.longitude:.6f}")
            else:
                print(f"   ⚠️  [{success_count+1}/{len(missing_coords)}] {landmark_name}: 未找到")

        except Exception as e:
            print(f"   ❌ {landmark_name}: 错误 - {str(e)}")

        # 速率限制
        time.sleep(1)

        # 进度显示
        if (success_count + 1) % 5 == 0:
            print(f"   进度: {success_count}/{len(missing_coords)}")

    # 保存结果
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')

    print(f"\n" + "=" * 60)
    print(f"✅ 坐标补充完成")
    print(f"=" * 60)
    print(f"成功补充: {success_count}个")
    print(f"仍然缺失: {len(missing_coords) - success_count}个")

    # 统计
    total_valid = df['latitude'].notna().sum()
    print(f"\n📊 最终统计:")
    print(f"   总地标数: {len(df)}")
    print(f"   有效坐标: {total_valid} ({total_valid/len(df)*100:.1f}%)")
    print(f"   无效坐标: {len(df) - total_valid} ({(len(df) - total_valid)/len(df)*100:.1f}%)")

    print(f"\n💾 已保存到: {output_csv}")

    return df


if __name__ == "__main__":
    import sys

    # 获取文件路径
    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
    else:
        input_csv = "city_narratives_wgs84_coords.csv"

    if len(sys.argv) > 2:
        output_csv = sys.argv[2]
    else:
        output_csv = "city_narratives_complete_coords.csv"

    # 检查文件是否存在
    if not os.path.exists(input_csv):
        print(f"❌ 文件不存在: {input_csv}")
        sys.exit(1)

    # 补充坐标
    df = fill_missing_coordinates(input_csv, output_csv)

    # 重新生成地图
    if df is not None:
        print(f"\n下一步: 重新生成地图")
        print(f"  python scripts/visualize_map.py {output_csv} shanghai_landmarks_map.html")
