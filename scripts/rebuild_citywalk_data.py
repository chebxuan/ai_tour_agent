#!/usr/bin/env python3
# rebuild_citywalk_data.py
# 城市叙事数据重构脚本
# 功能：读取原始地标数据，按故事线重组，优化节点排序，生成统计报告

import csv
import os
import sys
from collections import defaultdict, Counter
from typing import List, Dict, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


# ── 故事线映射配置 ─────────────────────────────────────────────

STORYLINE_MAPPING = {
    "武康路-安福路": "武康安福：多巴胺生活家",
    "愚园路 (长宁段)": "愚园路上：电台与弄堂往事",
    "苏州河 (静安/黄浦段)": "苏河彼岸：工业遗存与影像",
    "衡山路-复兴西路": "衡复乐章：梧桐树下的变奏",
    "新天地-马当路": "城市经典：B面上海",
    "豫园-老城厢": "城市经典：B面上海",
    "南京西路-静安寺": "城市经典：B面上海",
    "外滩-圆明园路": "城市经典：B面上海",
}

# 节点类型映射（统一命名）
NODE_TYPE_MAPPING = {
    "视觉": "视觉打卡",
    "味觉": "味觉停留",
    "历史": "历史锚点",
    "文化": "过渡节点",
    "购物": "购物发现",
    "互动": "互动体验",
}

# 节奏优化规则：连续相同类型节点的最大数量
MAX_CONSECUTIVE_SAME_TYPE = 2


def load_raw_data(csv_path: str) -> List[Dict]:
    """读取原始CSV数据"""
    nodes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.append(row)
    
    print(f"✅ 读取原始数据: {len(nodes)} 个节点")
    return nodes


def map_storyline(region: str) -> str:
    """根据region映射到storyline"""
    return STORYLINE_MAPPING.get(region, "待定：其他路线")


def map_node_type(node_type: str) -> str:
    """映射节点类型到统一命名"""
    return NODE_TYPE_MAPPING.get(node_type, node_type)


def parse_dwell_time(time_str: str) -> int:
    """解析停留时间为整数"""
    try:
        return int(time_str.strip())
    except:
        return 15  # 默认15分钟


def check_is_free(practical_info: str) -> bool:
    """检查是否免费"""
    if not practical_info:
        return False
    return "免费" in practical_info or "无门票" in practical_info


def group_by_storyline(nodes: List[Dict]) -> Dict[str, List[Dict]]:
    """按故事线分组节点"""
    grouped = defaultdict(list)
    
    for node in nodes:
        region = node.get('region', '')
        storyline = map_storyline(region)
        
        # 构建新节点数据
        new_node = {
            'node_name': node.get('node_name', '').strip(),
            'address': node.get('address', '').strip(),
            'node_type_original': node.get('node_type', '').strip(),
            'node_type': map_node_type(node.get('node_type', '').strip()),
            'region': region.strip(),
            'storyline': storyline,
            'brief_intro': node.get('brief_intro', '').strip(),
            'practical_info': node.get('practical_info', '').strip(),
            'recommended_action': node.get('recommended_action', '').strip(),
            'dwell_time_min': parse_dwell_time(node.get('dwell_time_min', '15')),
            'sequence_weight': float(node.get('sequence_weight', '0')),
            'tags': node.get('tags', '').strip(),
            'is_free': check_is_free(node.get('practical_info', ''))
        }
        
        grouped[storyline].append(new_node)
    
    return grouped


def optimize_rhythm(nodes: List[Dict]) -> List[Dict]:
    """
    优化节点节奏
    规则：如果连续3个节点都是视觉类型，尝试在中间插入味觉或休息节点
    """
    if len(nodes) < 3:
        return nodes
    
    # 先按sequence_weight降序排列
    nodes.sort(key=lambda x: x['sequence_weight'], reverse=True)
    
    optimized = []
    i = 0
    
    while i < len(nodes):
        optimized.append(nodes[i])
        
        # 检查连续3个视觉节点
        if (i >= 2 and 
            optimized[-1]['node_type'] == '视觉打卡' and
            optimized[-2]['node_type'] == '视觉打卡' and
            optimized[-3]['node_type'] == '视觉打卡'):
            
            # 查找后面是否有味觉或文化节点可以插入
            insert_node = None
            insert_idx = None
            
            for j in range(i + 1, len(nodes)):
                if nodes[j]['node_type'] in ['味觉停留', '过渡节点']:
                    insert_node = nodes[j]
                    insert_idx = j
                    break
            
            # 如果找到，插入到当前位置
            if insert_node:
                optimized.insert(-1, insert_node)
                nodes.pop(insert_idx)
                # 调整i，因为插入了一个节点
                i -= 1
        
        i += 1
    
    return optimized


def rebuild_data(nodes: List[Dict]) -> Dict[str, List[Dict]]:
    """重构数据：分组 + 排序 + 节奏优化"""
    # 1. 按故事线分组
    grouped = group_by_storyline(nodes)
    
    print(f"\n📊 故事线分布:")
    for storyline, story_nodes in grouped.items():
        print(f"  - {storyline}: {len(story_nodes)} 个节点")
    
    # 2. 对每个故事线进行排序和节奏优化
    optimized_groups = {}
    for storyline, story_nodes in grouped.items():
        print(f"\n⚙️  优化故事线: {storyline}")
        optimized_groups[storyline] = optimize_rhythm(story_nodes)
    
    return optimized_groups


def save_rebuilt_data(optimized_groups: Dict[str, List[Dict]], output_path: str):
    """保存重构后的数据"""
    # 定义输出字段
    fieldnames = [
        'node_name', 'address', 'node_type', 'storyline', 'region',
        'brief_intro', 'practical_info', 'is_free',
        'recommended_action', 'dwell_time_min', 'sequence_weight', 'tags',
        'node_type_original'
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        total_nodes = 0
        for storyline, nodes in optimized_groups.items():
            for node in nodes:
                writer.writerow(node)
                total_nodes += 1
    
    print(f"\n✅ 数据已保存: {output_path}")
    print(f"   总节点数: {total_nodes}")


def generate_statistics(optimized_groups: Dict[str, List[Dict]]):
    """生成统计报告"""
    print("\n" + "="*80)
    print("📊 故事线统计报告")
    print("="*80)
    
    total_nodes_all = 0
    total_duration_all = 0
    
    for storyline, nodes in optimized_groups.items():
        # 计算统计数据
        node_count = len(nodes)
        total_duration = sum(node['dwell_time_min'] for node in nodes)
        
        # 节点类型分布
        type_counter = Counter([node['node_type'] for node in nodes])
        
        print(f"\n{'─'*80}")
        print(f"📍 故事线: {storyline}")
        print(f"{'─'*80}")
        print(f"  节点数量: {node_count}")
        print(f"  总预测时长: {total_duration} 分钟 ({total_duration/60:.1f} 小时)")
        print(f"  平均停留时间: {total_duration/node_count:.0f} 分钟/节点")
        
        print(f"\n  节点类型分布:")
        for node_type, count in type_counter.most_common():
            percentage = (count / node_count) * 100
            bar = '█' * int(percentage / 5)
            print(f"    {node_type:10s}: {count:2d} ({percentage:5.1f}%) {bar}")
        
        # 免费景点统计
        free_count = sum(1 for node in nodes if node.get('is_free', False))
        if free_count > 0:
            print(f"\n  💰 免费景点: {free_count}/{node_count}")
        
        total_nodes_all += node_count
        total_duration_all += total_duration
    
    # 总体统计
    print(f"\n{'='*80}")
    print(f"📈 总体统计")
    print(f"{'='*80}")
    print(f"  故事线数量: {len(optimized_groups)}")
    print(f"  总节点数量: {total_nodes_all}")
    print(f"  总预测时长: {total_duration_all} 分钟 ({total_duration_all/60:.1f} 小时)")
    print(f"  平均每故事线: {total_nodes_all/len(optimized_groups):.0f} 个节点")
    print(f"{'='*80}\n")


def main():
    """主函数"""
    print("="*80)
    print("🌏 城市叙事数据重构工具")
    print("="*80)
    
    # 1. 确定路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)  # 项目根目录
    input_path = os.path.join(project_root, 'projects 2', 'city_narratives.csv')
    output_path = os.path.join(project_root, 'data', 'citywalk', 'narratives_v2.csv')
    
    # 检查输入文件
    if not os.path.exists(input_path):
        print(f"\n❌ 错误: 找不到输入文件 {input_path}")
        return 1
    
    # 2. 读取原始数据
    print(f"\n📂 输入文件: {input_path}")
    nodes = load_raw_data(input_path)
    
    # 3. 重构数据
    print(f"\n🔄 开始重构数据...")
    optimized_groups = rebuild_data(nodes)
    
    # 4. 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 5. 保存重构后的数据
    save_rebuilt_data(optimized_groups, output_path)
    
    # 6. 生成统计报告
    generate_statistics(optimized_groups)
    
    # 7. 输出后续建议
    print("💡 后续建议:")
    print("  1. 检查 narratives_v2.csv 中的节点排序是否符合预期")
    print("  2. 为 '待定：其他路线' 的节点分配更具体的故事线")
    print("  3. 补充缺失的 practical_info 信息")
    print("  4. 将 is_free=True 的景点在成本库中标记为免费")
    print("  5. 使用 narratives_v2.csv 更新 narrative_engine.py 的数据源")
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())
