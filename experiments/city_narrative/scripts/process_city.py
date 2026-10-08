#!/usr/bin/env python3
"""
一键处理脚本：从原始笔记提取地标并生成CSV数据库

使用方法：
1. 准备数据文件（JSON格式）
2. 运行脚本：python scripts/process_city.py 数据文件名.json
3. 输出：city_narratives.csv（数据库）、city_landmarks.json（完整数据）
"""
import json
import os
import sys
import re


def extract_data(input_file):
    """
    从原始JSON文件提取数据（处理换行符和中文引号）
    """
    print(f"📂 读取文件: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"   文件大小: {len(content)} 字符")

    # 提取所有regions
    regions = []

    # 定义区域数据
    region_names = [
        "武康路-安福路", "外滩-圆明园路", "豫园-老城厢",
        "衡山路-复兴西路", "南京西路-静安寺", "新天地-马当路",
        "愚园路", "苏州河"
    ]

    for i, region_name in enumerate(region_names, 1):
        # 查找区域
        start_marker = f'"id": {i},'
        end_marker = f'"id": {i+1},' if i < len(region_names) else None

        start_idx = content.find(start_marker)
        if start_idx == -1:
            continue

        if end_marker:
            end_idx = content.find(end_marker, start_idx)
        else:
            end_idx = len(content)

        if end_idx == -1:
            end_idx = len(content)

        region_content = content[start_idx:end_idx]

        # 提取笔记
        notes = []
        search_idx = 0

        while True:
            content_start = region_content.find('"content":', search_idx)
            if content_start == -1:
                break

            quote_start = region_content.find('"', content_start + 10)
            if quote_start == -1:
                break

            quote_end = region_content.find('"\n', quote_start + 1)
            if quote_end == -1:
                quote_end = region_content.find('"', quote_start + 1)

            if quote_end != -1:
                note_content = region_content[quote_start + 1:quote_end]
                notes.append({
                    "id": len(notes) + 1,
                    "title": f"笔记{len(notes) + 1}",
                    "content": note_content
                })
                search_idx = quote_end + 1
            else:
                break

        if notes:
            regions.append({
                "id": i,
                "name": region_name,
                "notes": notes
            })
            print(f"   ✅ {region_name}: {len(notes)} 条笔记")

    return regions


def process_regions(regions):
    """
    处理所有区域，提取地标
    """
    import sys
    sys.path.insert(0, os.path.join(os.getenv('COZE_WORKSPACE_PATH', '.'), 'src'))

    from graphs.nodes.narrative_analysis_node import narrative_analysis_node
    from graphs.state import NarrativeAnalysisInput
    from langgraph.runtime import Runtime
    from coze_coding_utils.runtime_ctx.context import Context, new_context

    all_landmarks = []

    for region in regions:
        print(f"\n📍 处理区域: {region['name']}")
        region_landmarks = []

        for note in region['notes']:
            print(f"   📝 笔记 {note['id']}: {note['title'][:30]}...")

            input_state = NarrativeAnalysisInput(raw_content=note['content'])
            config = {
                'metadata': {
                    'llm_cfg': os.path.join(os.getenv('COZE_WORKSPACE_PATH', '.'), 'config/narrative_analysis_cfg.json')
                }
            }

            ctx = new_context(method="batch_process")
            runtime = Runtime[Context](context=ctx)

            try:
                result = narrative_analysis_node(input_state, config, runtime)
                analysis_result = result.analysis_result

                if isinstance(analysis_result, dict):
                    if 'nodes' in analysis_result:
                        nodes = analysis_result['nodes']
                        for node in nodes:
                            node['region_id'] = region['id']
                            node['region_name'] = region['name']
                        region_landmarks.extend(nodes)
                        print(f"      ✅ 提取了 {len(nodes)} 个节点")
            except Exception as e:
                print(f"      ❌ 处理失败: {e}")

        # 去重
        unique_nodes = []
        seen_names = set()
        for node in region_landmarks:
            if node.get('node_name') not in seen_names:
                seen_names.add(node['node_name'])
                unique_nodes.append(node)

        all_landmarks.extend(unique_nodes)
        print(f"   📊 去重后: {len(unique_nodes)} 个地标")

    return all_landmarks


def save_results(landmarks, csv_file, json_file):
    """
    保存结果
    """
    import pandas as pd

    # 保存CSV
    df = pd.DataFrame(landmarks)

    # 展开嵌套字段
    if 'fact_sheet' in df.columns:
        fact_df = pd.json_normalize(df['fact_sheet'])
        fact_df.columns = [f'fact_{col}' for col in fact_df.columns]
        df = pd.concat([df.drop('fact_sheet', axis=1), fact_df], axis=1)

    if 'walking_logic' in df.columns:
        walk_df = pd.json_normalize(df['walking_logic'])
        walk_df.columns = [f'walk_{col}' for col in walk_df.columns]
        df = pd.concat([df.drop('walking_logic', axis=1), walk_df], axis=1)

    # 重命名列（中文化）
    column_mapping = {
        'node_name': '地标名称',
        'address': '地址',
        'node_type': '类型',
        'tags': '标签',
        'region_id': '区域ID',
        'region_name': '区域',
        'note_id': '来源笔记',
        'fact_brief_intro': '简介',
        'fact_practical_info': '实用信息',
        'fact_recommended_action': '推荐动作',
        'walk_dwell_time_min': '停留时间(分钟)',
        'walk_sequence_weight': '路线权重'
    }

    df.rename(columns=column_mapping, inplace=True)

    # 保存CSV（UTF-8 without BOM，避免Excel显示问题）
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')

    print(f"\n💾 CSV已保存: {csv_file}")
    print(f"   总地标数: {len(df)}")

    # 保存JSON
    import json
    output_data = {
        'summary': {
            'total_landmarks': len(landmarks),
            'regions': list(set(l['region_name'] for l in landmarks))
        },
        'landmarks': landmarks
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"💾 JSON已保存: {json_file}")


def main():
    """
    主函数
    """
    print("=" * 60)
    print("🚀 城市地标提取工具")
    print("=" * 60)

    # 获取输入文件
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = 'assets/shanghai_regions_template.json'

    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        print("\n使用方法:")
        print("  python scripts/process_city.py 数据文件名.json")
        print("\n示例:")
        print("  python scripts/process_city.py assets/shanghai_regions_template.json")
        return

    # 提取数据
    regions = extract_data(input_file)

    if not regions:
        print("❌ 未找到区域数据")
        return

    # 处理地标
    landmarks = process_regions(regions)

    if not landmarks:
        print("❌ 未提取到地标")
        return

    # 保存结果
    csv_file = 'city_narratives.csv'
    json_file = 'city_landmarks.json'

    save_results(landmarks, csv_file, json_file)

    print("\n" + "=" * 60)
    print("✅ 处理完成！")
    print("=" * 60)
    print("\n📊 输出文件:")
    print(f"  - {csv_file} (数据库)")
    print(f"  - {json_file} (完整数据)")
    print("\n💡 提示:")
    print("  - CSV文件可直接在Excel中打开")
    print("  - CSV文件可导入数据库")
    print("  - JSON文件可用于API或前端")


if __name__ == "__main__":
    main()
