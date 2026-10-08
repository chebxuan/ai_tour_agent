#!/usr/bin/env python3
"""
简化版地标提取脚本
使用标准 OpenAI API 替代 Coze 平台依赖
"""
import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化客户端（使用OpenAI兼容API，支持阿里云DashScope等）
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

if not api_key:
    print("❌ 错误: 请在 .env 文件中设置 OPENAI_API_KEY")
    print("   格式: OPENAI_API_KEY=你的API密钥")
    sys.exit(1)

if base_url:
    client = OpenAI(api_key=api_key, base_url=base_url)
    print(f"✅ 使用自定义API: {base_url}")
else:
    client = OpenAI(api_key=api_key)
    print("✅ 使用OpenAI官方API")

# 提取地标的系统提示词
SYSTEM_PROMPT = """你是一个专业的城市地标提取助手。请从用户提供的游记文本中提取所有**物理存在的地标实体**。

输出格式要求：
```json
{
  "nodes": [
    {
      "node_name": "地标名称（简洁，不含地址）",
      "address": "地址描述（尽可能详细，如'武康路安福路路口'或'新天地北里'）",
      "node_type": "类型：历史/味觉/购物/视觉/放空/文化",
      "fact_sheet": {
        "brief_intro": "一句话简介",
        "practical_info": "实用信息（门票/营业时间等）",
        "recommended_action": "推荐做什么"
      },
      "walking_logic": {
        "dwell_time_min": 建议停留分钟数,
        "sequence_weight": 路线顺序权重1-10
      },
      "tags": ["标签1", "标签2"]
    }
  ]
}
```

提取原则：
1. 只提取**物理存在的具体地点**（建筑、店铺、景点、餐厅等）
2. **必须是可以独立定位的单一地点**，排除：
   - 抽象概念（如"历史保护建筑群"、"西点店集群"）
   - 区域/路段（如"愚园支路P3至安西路"）
   - 活动/体验（如"拍照打卡点"）
3. 地址尽可能详细，从小红书笔记中提取：
   - ✅ "武康大楼"（知名地标，可独立定位）
   - ✅ "武康路安福路路口"（交叉路口，可定位）
   - ✅ "新天地北里"（商圈内的区域，可定位）
   - ❌ "武康路"（太宽泛，整条路）
   - ❌ "苏州河畔"（太宽泛，沿河区域）
4. 对于知名地标（如和平饭店、豫园），名称本身就足够定位
5. 对于小众店铺，尽量提取"路名+店名"（如"武康路老麦咖啡馆"）
6. 如果笔记中某个地点完全没有位置信息，**不要提取**
"""


def extract_landmarks_from_note(note_content, region_name):
    """从单条笔记提取地标"""
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "qwen-turbo"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"区域：{region_name}\n\n游记内容：\n{note_content}"}
            ],
            temperature=0.5,
            max_tokens=4000
        )
        
        # 解析JSON响应
        content = response.choices[0].message.content
        # 提取JSON部分（可能包含markdown代码块）
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content
            
        data = json.loads(json_str.strip())
        return data.get("nodes", [])
    except Exception as e:
        print(f"     ⚠️ 提取失败: {e}")
        return []


def process_regions(input_file):
    """处理所有区域"""
    print(f"📂 读取文件: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    regions = data.get("regions", [])
    print(f"   找到 {len(regions)} 个区域")
    
    all_landmarks = []
    
    for region in regions:
        print(f"\n📍 处理区域: {region['name']}")
        region_landmarks = []
        
        for note in region.get("notes", []):
            print(f"   📝 笔记 {note['id']}: {note['title'][:30]}...")
            landmarks = extract_landmarks_from_note(note['content'], region['name'])
            
            # 添加区域信息
            for lm in landmarks:
                lm['region'] = region['name']
                lm['source_note'] = note['title']
            
            region_landmarks.extend(landmarks)
            print(f"      ✅ 提取 {len(landmarks)} 个地标")
        
        all_landmarks.extend(region_landmarks)
        print(f"   📊 区域总计: {len(region_landmarks)} 个地标")
    
    return all_landmarks


def save_outputs(landmarks):
    """保存输出文件"""
    # 1. 保存JSON
    json_file = "shanghai_landmarks.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({"landmarks": landmarks}, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON已保存: {json_file} ({len(landmarks)} 个地标)")
    
    # 2. 保存CSV
    csv_file = "city_narratives.csv"
    import csv
    
    if landmarks:
        # 获取所有字段
        fieldnames = set()
        for lm in landmarks:
            fieldnames.update(lm.keys())
        
        # 扁平化嵌套字段
        flat_landmarks = []
        for lm in landmarks:
            flat = {
                "node_name": lm.get("node_name", ""),
                "address": lm.get("address", ""),
                "node_type": lm.get("node_type", ""),
                "region": lm.get("region", ""),
                "brief_intro": lm.get("fact_sheet", {}).get("brief_intro", ""),
                "practical_info": lm.get("fact_sheet", {}).get("practical_info", ""),
                "recommended_action": lm.get("fact_sheet", {}).get("recommended_action", ""),
                "dwell_time_min": lm.get("walking_logic", {}).get("dwell_time_min", ""),
                "sequence_weight": lm.get("walking_logic", {}).get("sequence_weight", ""),
                "tags": ", ".join(lm.get("tags", []))
            }
            flat_landmarks.append(flat)
        
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=flat_landmarks[0].keys())
            writer.writeheader()
            writer.writerows(flat_landmarks)
        print(f"💾 CSV已保存: {csv_file}")
    
    return json_file, csv_file


def main():
    if len(sys.argv) < 2:
        input_file = "assets/shanghai_regions_template.json"
    else:
        input_file = sys.argv[1]
    
    print("=" * 60)
    print("🚀 城市地标提取工具（简化版）")
    print("=" * 60)
    
    # 检查API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DOUBAO_API_KEY"):
        print("\n❌ 错误: 请设置环境变量 OPENAI_API_KEY 或 DOUBAO_API_KEY")
        print("   可在 .env 文件中添加：")
        print("   OPENAI_API_KEY=your_api_key")
        print("   或：")
        print("   DOUBAO_API_KEY=your_api_key")
        print("   DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3")
        return
    
    # 处理区域
    landmarks = process_regions(input_file)
    
    # 去重（按名称）
    seen = set()
    unique_landmarks = []
    for lm in landmarks:
        name = lm.get("node_name", "")
        if name and name not in seen:
            seen.add(name)
            unique_landmarks.append(lm)
    
    print(f"\n" + "=" * 60)
    print(f"📊 提取完成")
    print(f"   原始地标: {len(landmarks)} 个")
    print(f"   去重后: {len(unique_landmarks)} 个")
    print(f"   涉及区域: {len(set(lm.get('region') for lm in unique_landmarks))} 个")
    print("=" * 60)
    
    # 保存输出
    json_file, csv_file = save_outputs(unique_landmarks)
    
    print(f"\n✨ 下一步:")
    print(f"   1. 坐标补全: python scripts/add_coordinates_amap.py '你的API_Key'")
    print(f"   2. 坐标纠偏: python scripts/convert_coordinates.py {csv_file.replace('.csv', '_amap_coords.csv')}")
    print(f"   3. 生成地图: python scripts/visualize_map.py {csv_file.replace('.csv', '_wgs84_coords.csv')} map.html")


if __name__ == "__main__":
    main()
