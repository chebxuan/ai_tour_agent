# narrative_engine.py
# 城市叙事引擎 - 生成有节奏感的 City Walk 路线
# 输入: storyline, duration_min
# 输出: Discovery Map JSON

import csv
import json
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class CityNode:
    """城市叙事节点"""
    node_id: str
    city: str
    storyline: str
    node_name: str
    node_type: str
    description: str
    lat: float
    lng: float
    dwell_time_min: int
    serendipity_tip: str
    host_story: str


@dataclass
class WalkSegment:
    """步行段信息"""
    distance_m: int
    estimated_min: int
    route_hint: str


@dataclass
class DiscoveryNode:
    """探索地图中的节点（含顺序和步行信息）"""
    sequence: int
    node_id: str
    node_name: str
    node_type: str
    description: str
    lat: float
    lng: float
    dwell_time_min: int
    serendipity_tip: str
    walk_to_next: Optional[WalkSegment] = None


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间距离（米）"""
    R = 6371000  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def load_nodes(csv_path: str = "data/citywalk/narratives.csv") -> List[CityNode]:
    """从 CSV 加载所有节点"""
    nodes = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat, lng = map(float, row['lat_long'].split(','))
            nodes.append(CityNode(
                node_id=row['node_id'],
                city=row['city'],
                storyline=row['storyline'],
                node_name=row['node_name'],
                node_type=row['node_type'],
                description=row['description'],
                lat=lat,
                lng=lng,
                dwell_time_min=int(row['dwell_time_min']),
                serendipity_tip=row['serendipity_tip'],
                host_story=row['host_story']
            ))
    return nodes


def filter_by_storyline(nodes: List[CityNode], storyline: str) -> List[CityNode]:
    """筛选指定故事线的节点"""
    return [n for n in nodes if n.storyline == storyline]


def cluster_by_proximity(nodes: List[CityNode], max_distance_m: float = 500) -> List[CityNode]:
    """
    基于地理位置聚类，剔除离群点
    使用简单的连通分量算法
    """
    if len(nodes) <= 1:
        return nodes

    # 构建邻接表（距离 < max_distance_m 的节点相连）
    n = len(nodes)
    adj = defaultdict(list)
    for i in range(n):
        for j in range(i + 1, n):
            dist = haversine_distance(
                nodes[i].lat, nodes[i].lng,
                nodes[j].lat, nodes[j].lng
            )
            if dist <= max_distance_m:
                adj[i].append(j)
                adj[j].append(i)

    # 找最大连通分量
    visited = [False] * n
    max_component = []

    def dfs(start: int, component: List[int]):
        visited[start] = True
        component.append(start)
        for neighbor in adj[start]:
            if not visited[neighbor]:
                dfs(neighbor, component)

    for i in range(n):
        if not visited[i]:
            component = []
            dfs(i, component)
            if len(component) > len(max_component):
                max_component = component

    return [nodes[i] for i in max_component]


def calculate_rhythm_score(sequence: List[CityNode]) -> float:
    """
    计算序列的节奏分数
    - 避免连续相同类型（惩罚）
    - 视觉打卡/历史锚点在中后段有奖励（高潮节点）
    - 起点和终点类型合理有奖励
    """
    if len(sequence) <= 1:
        return 1.0

    score = 1.0
    n = len(sequence)

    # 1. 惩罚连续相同类型
    for i in range(n - 1):
        if sequence[i].node_type == sequence[i + 1].node_type:
            score -= 0.15

    # 2. 高潮节点位置奖励（视觉打卡/历史锚点在中后段）
    climax_types = {'视觉打卡', '历史锚点'}
    for i, node in enumerate(sequence):
        if node.node_type in climax_types:
            position = i / (n - 1)  # 0.0 ~ 1.0
            if 0.4 <= position <= 0.8:  # 中后段是理想位置
                score += 0.1
            elif position < 0.3:  # 太早出现，略减分
                score -= 0.05

    # 3. 起点和终点类型奖励
    good_start_types = {'过渡节点', '历史锚点'}
    good_end_types = {'味觉停留', '视觉打卡', '过渡节点'}

    if sequence[0].node_type in good_start_types:
        score += 0.05
    if sequence[-1].node_type in good_end_types:
        score += 0.05

    return max(0.0, min(1.0, score))


def generate_route_hint(from_node: CityNode, to_node: CityNode) -> str:
    """生成步行路线提示"""
    # 计算方向
    delta_lat = to_node.lat - from_node.lat
    delta_lng = to_node.lng - from_node.lng

    # 简单方向判断
    directions = []
    if abs(delta_lat) > abs(delta_lng):
        directions.append('向北' if delta_lat > 0 else '向南')
    else:
        directions.append('向东' if delta_lng > 0 else '向西')

    direction = ''.join(directions)

    # 根据节点类型生成提示
    hints = [
        f"沿{direction}步行，留意{from_node.node_type.replace('节点', '').replace('停留', '')}的氛围",
        f"{direction}前行，途中可能会经过一些有趣的小店",
        f"慢慢{direction}走，感受这条街的{random.choice(['梧桐树影', '老建筑韵味', '街角风景'])}",
    ]

    return random.choice(hints)


def sequence_nodes(nodes: List[CityNode], duration_min: int) -> Tuple[List[DiscoveryNode], Dict]:
    """
    排序与编排节点
    使用贪心算法 + 局部搜索优化节奏
    """
    if not nodes:
        return [], {"error": "没有可用节点"}

    # 1. 基于距离构建初始路径（最近邻贪心）
    def build_greedy_path(start_idx: int) -> List[CityNode]:
        unvisited = set(range(len(nodes)))
        path = [nodes[start_idx]]
        unvisited.remove(start_idx)
        current = start_idx

        while unvisited:
            # 找最近的未访问节点
            nearest = min(unvisited,
                         key=lambda i: haversine_distance(
                             nodes[current].lat, nodes[current].lng,
                             nodes[i].lat, nodes[i].lng
                         ))
            path.append(nodes[nearest])
            unvisited.remove(nearest)
            current = nearest

        return path

    # 2. 尝试多个起点，选择节奏最好的
    best_path = None
    best_score = -1

    for start_idx in range(min(len(nodes), 5)):  # 尝试前5个作为起点
        path = build_greedy_path(start_idx)
        score = calculate_rhythm_score(path)

        # 简单局部优化：尝试交换相邻节点改善节奏
        improved = True
        while improved and len(path) > 2:
            improved = False
            for i in range(len(path) - 1):
                # 尝试交换 i 和 i+1
                new_path = path[:i] + [path[i+1], path[i]] + path[i+2:]
                new_score = calculate_rhythm_score(new_path)
                if new_score > score:
                    path = new_path
                    score = new_score
                    improved = True
                    break

        if score > best_score:
            best_score = score
            best_path = path

    # 3. 根据时长限制截断（如果必要）
    total_dwell = sum(n.dwell_time_min for n in best_path)
    # 估算步行时间（假设步行速度 3km/h = 50m/min）
    walk_time = 0
    for i in range(len(best_path) - 1):
        dist = haversine_distance(
            best_path[i].lat, best_path[i].lng,
            best_path[i+1].lat, best_path[i+1].lng
        )
        walk_time += dist / 50  # 分钟

    total_time = total_dwell + walk_time

    # 如果超时，尝试移除一些节点（优先保留节奏好的）
    while total_time > duration_min * 1.2 and len(best_path) > 3:
        # 找可以移除的节点（非高潮节点）
        removable = [i for i, n in enumerate(best_path)
                    if n.node_type not in {'视觉打卡', '历史锚点'}]
        if not removable:
            removable = list(range(1, len(best_path) - 1))  # 不能移除首尾

        if removable:
            # 移除后节奏最好的
            best_remove = min(removable,
                            key=lambda i: calculate_rhythm_score(
                                best_path[:i] + best_path[i+1:]
                            ))
            best_path = best_path[:best_remove] + best_path[best_remove+1:]

            # 重新计算时间
            total_dwell = sum(n.dwell_time_min for n in best_path)
            walk_time = sum(
                haversine_distance(
                    best_path[i].lat, best_path[i].lng,
                    best_path[i+1].lat, best_path[i+1].lng
                ) / 50
                for i in range(len(best_path) - 1)
            )
            total_time = total_dwell + walk_time
        else:
            break

    # 4. 构建 DiscoveryNode 列表
    discovery_nodes = []
    total_distance = 0

    for i, node in enumerate(best_path):
        walk_segment = None
        if i < len(best_path) - 1:
            dist = haversine_distance(
                node.lat, node.lng,
                best_path[i+1].lat, best_path[i+1].lng
            )
            total_distance += dist
            walk_segment = WalkSegment(
                distance_m=int(dist),
                estimated_min=int(dist / 50) + 1,
                route_hint=generate_route_hint(node, best_path[i+1])
            )

        discovery_nodes.append(DiscoveryNode(
            sequence=i + 1,
            node_id=node.node_id,
            node_name=node.node_name,
            node_type=node.node_type,
            description=node.description,
            lat=node.lat,
            lng=node.lng,
            dwell_time_min=node.dwell_time_min,
            serendipity_tip=node.serendipity_tip,
            walk_to_next=walk_segment
        ))

    # 5. 节奏分析
    rhythm_pattern = [n.node_type for n in best_path]
    climax_types = {'视觉打卡', '历史锚点'}
    climax_positions = [i for i, n in enumerate(best_path) if n.node_type in climax_types]

    pacing_analysis = {
        "rhythm_pattern": rhythm_pattern,
        "climax_position": f"节点{climax_positions[0]+1}/{len(best_path)}" if climax_positions else "无",
        "flow_score": round(best_score, 2),
        "total_dwell_min": int(total_dwell),
        "total_walk_min": int(walk_time)
    }

    return discovery_nodes, pacing_analysis


def generate_discovery_map(storyline: str, duration_min: int = 120) -> Dict:
    """
    生成探索地图
    主入口函数
    """
    # 1. 加载数据
    all_nodes = load_nodes()

    # 2. 筛选故事线
    storyline_nodes = filter_by_storyline(all_nodes, storyline)
    if not storyline_nodes:
        return {
            "success": False,
            "error": f"未找到故事线: {storyline}"
        }

    # 3. 地理位置聚类
    clustered_nodes = cluster_by_proximity(storyline_nodes)
    if len(clustered_nodes) < 3:
        return {
            "success": False,
            "error": f"故事线节点不足（聚类后只有{len(clustered_nodes)}个）"
        }

    # 4. 排序与编排
    discovery_nodes, pacing_analysis = sequence_nodes(clustered_nodes, duration_min)

    # 5. 构建输出
    total_distance = sum(
        n.walk_to_next.distance_m for n in discovery_nodes if n.walk_to_next
    )
    total_time = pacing_analysis["total_dwell_min"] + pacing_analysis["total_walk_min"]

    # 获取城市信息
    city = discovery_nodes[0].lat if discovery_nodes else ""

    return {
        "success": True,
        "storyline": storyline,
        "city": storyline_nodes[0].city if storyline_nodes else "",
        "total_duration_min": total_time,
        "total_distance_m": int(total_distance),
        "node_count": len(discovery_nodes),
        "nodes": [
            {
                "sequence": n.sequence,
                "node_id": n.node_id,
                "node_name": n.node_name,
                "node_type": n.node_type,
                "description": n.description,
                "lat": n.lat,
                "lng": n.lng,
                "dwell_time_min": n.dwell_time_min,
                "serendipity_tip": n.serendipity_tip,
                "walk_to_next": asdict(n.walk_to_next) if n.walk_to_next else None
            }
            for n in discovery_nodes
        ],
        "pacing_analysis": pacing_analysis
    }


# 测试入口
if __name__ == "__main__":
    # 测试生成武康路探索地图
    result = generate_discovery_map("武康路的老洋房故事", duration_min=120)
    print(json.dumps(result, ensure_ascii=False, indent=2))
