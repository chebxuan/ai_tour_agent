# 项目结构

## 目录结构

```
.
├── assets/                              # 资源文件
│   └── shanghai_regions_template.json   # 数据模板
├── config/                              # 配置文件
│   └── narrative_analysis_cfg.json      # LLM 配置
├── scripts/                             # 脚本
│   ├── process_city.py                  # 一键处理脚本
│   ├── add_coordinates_amap.py          # 高德API坐标补全
│   ├── convert_coordinates.py           # 坐标纠偏
│   └── visualize_map.py                 # 地图生成
├── src/                                 # 源代码
│   ├── graphs/                          # 工作流编排
│   │   ├── state.py                     # 状态定义
│   │   ├── graph.py                     # 主图编排
│   │   └── nodes/                       # 节点实现
│   │       └── narrative_analysis_node.py
│   ├── storage/                         # 存储
│   ├── tools/                           # 工具函数
│   └── utils/                           # 工具类
├── docs/                                # 文档
│   ├── QUICK_START.md                   # 快速开始
│   ├── GET_REAL_COORDINATES_QUICK.md    # 坐标获取指南
│   ├── VISUALIZATION_QUICK_GUIDE.md     # 可视化指南
│   └── PROJECT_STRUCTURE.md             # 本文件
├── AGENTS.md                            # 项目架构
├── README.md                            # 项目说明
├── city_narratives.csv                  # CSV 数据库
├── shanghai_landmarks.json              # JSON 完整数据
├── shanghai_landmarks_map.html          # 交互式地图
├── pyproject.toml                       # 项目配置
└── requirements.txt                     # Python 依赖
```

## 核心文件说明

### 输入文件
- `assets/shanghai_regions_template.json` - 数据模板

### 输出文件
- `city_narratives.csv` - CSV 数据库（192个地标）
- `shanghai_landmarks.json` - JSON 完整数据（192个地标）
- `shanghai_landmarks_map.html` - 交互式地图（143个标记）

### 核心脚本
- `scripts/process_city.py` - 一键处理，提取地标
- `scripts/add_coordinates_amap.py` - 高德API获取坐标
- `scripts/convert_coordinates.py` - GCJ-02转WGS-84
- `scripts/visualize_map.py` - 生成交互式地图

### 核心代码
- `src/graphs/nodes/narrative_analysis_node.py` - LLM提取节点
- `src/graphs/state.py` - 状态定义
- `src/graphs/graph.py` - 工作流编排

### 配置文件
- `config/narrative_analysis_cfg.json` - LLM配置（豆包模型）

### 文档文件
- `README.md` - 项目说明
- `AGENTS.md` - 项目架构
- `docs/QUICK_START.md` - 快速开始
- `docs/GET_REAL_COORDINATES_QUICK.md` - 坐标获取指南
- `docs/VISUALIZATION_QUICK_GUIDE.md` - 可视化指南

## 快速定位

### 想了解项目？
→ 查看 `README.md` 和 `AGENTS.md`

### 想快速上手？
→ 查看 `docs/QUICK_START.md`

### 想修改LLM逻辑？
→ 查看 `src/graphs/nodes/narrative_analysis_node.py`

### 想调整LLM提示词？
→ 查看 `config/narrative_analysis_cfg.json`

### 想处理自己的数据？
→ 参考 `assets/shanghai_regions_template.json`，运行 `scripts/process_city.py`

### 想获取真实坐标？
→ 查看 `docs/GET_REAL_COORDINATES_QUICK.md`，运行 `scripts/add_coordinates_amap.py`

### 想生成地图？
→ 查看 `docs/VISUALIZATION_QUICK_GUIDE.md`，运行 `scripts/visualize_map.py`
