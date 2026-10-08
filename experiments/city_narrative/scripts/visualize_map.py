#!/usr/bin/env python3
"""
可视化脚本：使用Folium生成交互式地图（包含AntPath动态连线）
"""
import pandas as pd
import folium
import os
from folium import plugins
from folium.plugins import AntPath


def visualize_landmarks(csv_file, output_html):
    """
    生成交互式地图

    Args:
        csv_file: CSV文件路径（包含经纬度）
        output_html: 输出HTML文件路径
    """
    print("=" * 60)
    print("🗺️  开始生成交互式地图")
    print("=" * 60)

    # 读取CSV
    df = pd.read_csv(csv_file)

    print(f"\n📂 读取文件: {csv_file}")
    print(f"   总地标数: {len(df)}")

    # 检查坐标
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        print(f"\n❌ 文件缺少经纬度字段")
        print(f"   请先运行: python scripts/add_coordinates.py")
        return

    # 过滤有效坐标
    valid_df = df[df['latitude'].notna() & df['longitude'].notna()]
    invalid_count = len(df) - len(valid_df)

    if invalid_count > 0:
        print(f"\n⚠️  {invalid_count} 个地标缺少坐标，将被跳过")

    print(f"   有效坐标: {len(valid_df)}个")

    if len(valid_df) == 0:
        print(f"\n❌ 没有有效的坐标数据")
        return

    # 计算中心点
    center_lat = valid_df['latitude'].mean()
    center_lon = valid_df['longitude'].mean()

    print(f"\n📍 地图中心点: {center_lat:.6f}, {center_lon:.6f}")

    # 创建地图（使用OpenStreetMap，避免高德API访问问题）
    print(f"\n🎨 创建地图...")
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    )

    # 定义颜色映射
    color_map = {
        '历史': 'blue',
        '味觉': 'red',
        '购物': 'green',
        '视觉': 'orange',
        '放空': 'purple',
        '功能': 'gray',
        '体验': 'pink'
    }

    # 添加地标点位
    print(f"   添加地标点位...")
    for idx, row in valid_df.iterrows():
        # 支持中英文列名
        landmark_type = row.get('node_type') or row.get('类型', '')
        landmark_name = row.get('node_name') or row.get('地标名称', '')
        address = row.get('address') or row.get('地址', '')
        brief_intro = row.get('brief_intro') or row.get('简介', '')
        dwell_time = row.get('dwell_time_min') or row.get('停留时间(分钟)', '')
        weight = row.get('sequence_weight') or row.get('路线权重', '')

        # 选择颜色
        color = color_map.get(landmark_type, 'gray')

        # 构建弹窗内容
        popup_content = f"""
        <div style="font-family: Arial, sans-serif; width: 300px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">{landmark_name}</h4>
            <p style="margin: 5px 0; color: #666;">
                <strong>类型：</strong>{landmark_type}
            </p>
            <p style="margin: 5px 0; color: #666;">
                <strong>地址：</strong>{address}
            </p>
            <p style="margin: 5px 0; color: #666;">
                <strong>简介：</strong>{brief_intro}
            </p>
            <p style="margin: 5px 0; color: #666;">
                <strong>停留时间：</strong>{dwell_time}分钟
            </p>
            <p style="margin: 5px 0; color: #666;">
                <strong>路线权重：</strong>{weight}
            </p>
        </div>
        """

        # 添加标记
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=350),
            tooltip=landmark_name,
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)

    # 添加图例
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px;
                left: 50px;
                width: 150px;
                height: auto;
                z-index:9999;
                font-size:14px;
                background-color:white;
                border:2px solid grey;
                border-radius:5px;
                padding: 10px;">
    <p style="margin: 0 0 10px 0; font-weight: bold;">地标类型</p>
    '''
    for landmark_type, color in color_map.items():
        legend_html += f'''
        <p style="margin: 5px 0;">
            <i class="fa fa-circle" style="color:{color}"></i>
            {landmark_type}
        </p>
        '''
    legend_html += '</div>'

    m.get_root().html.add_child(folium.Element(legend_html))

    # 添加缩放控制
    plugins.Fullscreen().add_to(m)

    # 添加小地图
    plugins.MiniMap().add_to(m)

    # 保存地图
    print(f"   保存地图...")
    m.save(output_html)

    print(f"\n" + "=" * 60)
    print(f"✅ 地图生成完成")
    print(f"=" * 60)
    print(f"💾 已保存到: {output_html}")
    print(f"\n📊 统计信息:")
    print(f"   总地标数: {len(df)}")
    print(f"   显示地标数: {len(valid_df)}")
    print(f"   隐藏地标数: {invalid_count}")

    # 按类型统计
    type_col = 'node_type' if 'node_type' in valid_df.columns else '类型'
    type_stats = valid_df[type_col].value_counts()
    print(f"\n📈 类型分布:")
    for landmark_type, count in type_stats.items():
        print(f"   {landmark_type}: {count}个")

    # 按区域统计
    region_col = 'region' if 'region' in valid_df.columns else '区域'
    region_stats = valid_df[region_col].value_counts()
    print(f"\n📍 区域分布:")
    for region, count in region_stats.items():
        print(f"   {region}: {count}个")

    print(f"\n💡 使用说明:")
    print(f"   1. 双击 {output_html} 文件在浏览器中打开")
    print(f"   2. 点击地标查看详细信息")
    print(f"   3. 使用鼠标滚缩放")
    print(f"   4. 拖动地图移动视图")
    
    # ===== 添加 AntPath 动态连线 =====
    print(f"\n🛤️  添加区域路线连线...")
        
    # 颜色映射（不同区域用不同颜色）
    region_colors = {
        '武康路-安福路': '#FF6B6B',
        '外滩-圆明园路': '#4ECDC4',
        '豫园-老城厢': '#45B7D1',
        '衡山路-复兴西路': '#96CEB4',
        '南京西路-静安寺': '#FFEAA7',
        '新天地-马当路': '#DDA0DD',
        '愚园路 (长宁段)': '#98D8C8',
        '苏州河 (静安/黄浦段)': '#F7DC6F'
    }
        
    # 按区域分组并连线
    region_col = 'region' if 'region' in valid_df.columns else '区域'
    dwell_col = 'dwell_time_min' if 'dwell_time_min' in valid_df.columns else '停留时间(分钟)'
    weight_col = 'sequence_weight' if 'sequence_weight' in valid_df.columns else '路线权重'
        
    route_warnings = []  # 体感预警列表
        
    for region, group in valid_df.groupby(region_col):
        # 按权重排序
        sorted_group = group.sort_values(by=weight_col, ascending=True)
            
        # 提取坐标序列
        path_points = sorted_group[['latitude', 'longitude']].values.tolist()
            
        # 计算区域总时长
        if dwell_col in sorted_group.columns:
            total_duration = sorted_group[dwell_col].sum()
        else:
            total_duration = len(sorted_group) * 15  # 默认每个地标15分钟
            
        # 获取颜色
        color = region_colors.get(region, '#666666')
            
        # 添加 AntPath 动态连线
        AntPath(
            locations=path_points,
            dash_array=[1, 10],
            delay=1000,
            color=color,
            pulse_color='white',
            weight=3,
            opacity=0.7,
            tooltip=f"{region} 推荐路线 ({len(sorted_group)}个地标, {total_duration:.0f}分钟)"
        ).add_to(m)
            
        print(f"   ✅ {region}: {len(sorted_group)}个地标, {total_duration:.0f}分钟")
            
        # 体感预警（超过4小时）
        if total_duration > 240:
            warning_msg = f"⚠️ {region}: 总时长 {total_duration/60:.1f}小时，建议分拆为多条路线"
            route_warnings.append(warning_msg)
        
    print(f"\n📊 路线统计:")
    print(f"   共生成 {len(valid_df.groupby(region_col))} 条区域路线")
        
    # 输出体感预警
    if route_warnings:
        print(f"\n⚠️  体感预警:")
        for warning in route_warnings:
            print(f"   {warning}")
    else:
        print(f"\n✅ 所有区域路线时长合理（≤4小时）")

    return m


def add_heatmap(csv_file, map_obj):
    """
    添加热力图层
    """
    print(f"\n🔥 添加热力图层...")

    df = pd.read_csv(csv_file)
    valid_df = df[df['latitude'].notna() & df['longitude'].notna()]

    # 准备热力数据
    heat_data = [[row['latitude'], row['longitude']] for idx, row in valid_df.iterrows()]

    # 添加热力图层
    plugins.HeatMap(heat_data, name='热力图').add_to(map_obj)

    # 添加图层控制
    folium.LayerControl().add_to(map_obj)

    print(f"   ✅ 热力图层已添加")


if __name__ == "__main__":
    import sys

    # 获取文件路径
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = "city_narratives_with_coords.csv"

    if len(sys.argv) > 2:
        output_html = sys.argv[2]
    else:
        output_html = "shanghai_landmarks_map.html"

    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"❌ 文件不存在: {csv_file}")
        print(f"\n请先运行坐标补全脚本:")
        print(f"  python scripts/add_coordinates.py")
        sys.exit(1)

    # 生成交互式地图
    m = visualize_landmarks(csv_file, output_html)

    # 可选：添加热力图层
    if m:
        add_heatmap(csv_file, m)

        # 重新保存（包含热力图层）
        m.save(output_html)
        print(f"\n💾 已更新地图文件（包含热力图层）")
