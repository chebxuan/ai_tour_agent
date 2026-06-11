# Hexa Blueprint - 入境游 AI 运营辅助系统

## 项目定位

Hexa Blueprint 是一个面向入境游业务链路的结构化规则引擎系统。  
目标不是做单次问答，而是把销售到交付的关键中间对象标准化，让推荐、报价、行程展示都可以持续复用与审计。

核心链路：

`LeadJSON → CandidateProductsJSON → PricingResultJSON → Markdown 行程单`

## 当前实现状态（2026-06-07）

### 标准产品匹配链路（已稳定）
- 仅保留 v2 API，v1 和 Coze 集成已移除。
- 已实现 **Streamlit Web UI**（`streamlit_app.py`），含标准行程生成、上海半定制路线、付款管理三个 Tab。
- 已实现 **`/api/v2/full_chain`** 一键全链路接口：product-match → pricing → Markdown 输出（含 day_plans + Highlights + 报价表）。
- 已实现 **供应商付款管理看板**，三列 Kanban（待处理/已支付/已存档），支持筛选搜索和状态流转。
- 已有多城市端到端回归测试（10/10 城市通过）。

### 🆕 上海 MVP 半定制路线生成器

**数据底座：**
- 35 个上海体验单元 + 12 个人群画像 + 12 个路线模板 + 99 条市内交通边
- 上海成本库从 28 项扩展到 38 项，21/35 体验单元已通过 `cost_item_code` 接入 `cost_engine` 报价

**引擎能力（`engines/custom_route_engine.py`）：**
- 标签打分（兴趣关键词直击 0.45/hit + 画像标签匹配 0.30/hit + 人群适配 ±0.35 + 预算硬约束）
- 模板驱动编排（12 个模板按 required_unit_types + preferred_areas 驱动选点）
- 全链路交通检查（每对相邻节点查 transport edge，未知交通按 25min 保守估算计入总时长）
- 辅助点规则（Romeo's Balcony / Peace Hotel / 教堂等 6 个点不能独立成线，必须搭配锚点）
- 模板硬性业务规则（First-timer 强制含 classic anchor、Romantic 必须有 dining+夜景、Budget 半日 ≥2 units）
- Water Town 模板需显式命中 `water_town/canal/zhujiajiao` 才选中，不被通用 photography 误触发

**验证状态：**
- 5 场景核心逻辑测试：**5/5 PASS**（F1-F6 六个维度全覆盖）
- 315 场景排列组合矩阵：55 条唯一路线指纹，5 个兴趣集各产出不同路线
- `/api/v2/custom-route` 端点 + Streamlit UI 端到端可用

**当前阶段：** MVP/原型。模板选择与画像路由已可区分不同客户画像，半天场景多样性受限于 35 单元池大小。非生产系统。
- 说明文档：[docs/custom_route_mvp.md](docs/custom_route_mvp.md)
- 排列组合报告：[data/custom/matrix_315_results.txt](data/custom/matrix_315_results.txt)

## 目录概览（现状）

```text
.
├── api_main.py                    # FastAPI 主应用
├── cli_app.py                     # CLI 交互工具（独立的问卷+匹配+报价 demo）
├── streamlit_app.py               # Web UI（Streamlit），通过 HTTP 调用 API
├── survey_architect.py            # 北京问卷模板
├── engines/                       # 核心引擎
│   ├── city_config.py             # 城市配置（代码前缀、成本库路径、折扣规则）
│   ├── product_engine.py          # 产品匹配（城市+天数，CSV 查表）
│   ├── cost_engine.py             # 报价计算（门票/酒店/交通/导游）
│   ├── custom_route_engine.py     # 🆕 上海半定制路线引擎（标签匹配+区域聚类+交通检查）
│   ├── payment_tracker.py         # 供应商付款管理 CRUD
│   ├── narrative_engine.py        # 城市叙事引擎（City Walk 路线生成，独立模块）
│   └── merge_city_products.py     # 数据工程工具（按类型 CSV → 按城市合并）
├── data/                          # 数据资产
│   ├── products/
│   │   ├── product_library.csv    # 产品真源（21 个产品，10 城市）
│   │   ├── products.normalized.json  # 标准化产品库（含 day_plans 结构化行程）
│   │   ├── attraction_highlights.json  # 景点 Highlights（Route/attractions 映射）
│   │   └── services/              # 服务目录源文件
│   │       └── mashes/            # 按城市合并的成本真源（10 个 CSV）
│   ├── custom/                    # 半定制路线数据（上海 MVP）
│   │   ├── shanghai_experience_units.csv   # 上海体验最小单元库（35条，21条已映射成本编码）
│   │   ├── shanghai_transport_edges.csv    # 市内点对点交通关系（99条）
│   │   ├── customer_profile_tags.csv       # 客户画像标签（12个）
│   │   └── shanghai_route_templates.json   # 路线模板（12个）
│   ├── citywalk/
│   │   └── narratives_v2.csv
│   └── pois/
│       └── beijing_updates.csv
├── docs/
│   ├── logs/工作日志.md
│   └── prompts/*.md
├── scripts/
│   └── normalize_product_library.py
├── test_multi_city.py
├── test_optional_items.py
└── schemas.py                     # Pydantic 模型定义
```

## API 概览（全部 v2）

### 行程与报价

- `GET /api/v2/cities` — 城市列表
- `POST /api/v2/product-match` — 标准产品匹配（21 产品）
- `POST /api/v2/pricing` — 报价计算
- `POST /api/v2/full_chain` — **一键全链路**（product-match → pricing → Markdown 行程单）
- `POST /api/v2/custom-route` 🆕 — **上海半定制路线**（POI 编排 → 部分接入 cost_engine → Markdown）
- `GET /api/v2/item-names` — 项目编号 → 名称查询

### 付款管理

- `GET /api/v2/payments` — 付款列表/筛选
- `POST /api/v2/payments` — 创建付款条目
- `GET /api/v2/payments/{id}` — 付款详情
- `PUT /api/v2/payments/{id}` — 更新付款
- `PATCH /api/v2/payments/{id}/status` — 状态流转（待处理→已支付→已存档）
- `DELETE /api/v2/payments/{id}` — 删除付款
- `GET /api/v2/payments/suppliers` — 供应商列表（自动补全）
- `GET /api/v2/payments/stats` — 看板统计

## 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
```

### 2) 配置环境变量（.env）

```bash
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
GAODE_API_KEY=your_gaode_key
API_KEY=hexa-tour-2024
```

### 3) 启动 API

```bash
uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
```

### 4) 启动 CLI

```bash
python cli_app.py
```

### 5) 启动 Web UI（Streamlit）

```bash
streamlit run streamlit_app.py
```

浏览器访问 `http://localhost:8501`，在侧边栏填写客户需求后一键生成行程与报价。

## 数据策略

- 产品真源：`data/products/product_library.csv`
- 成本真源：`data/products/services/mashes/*.csv`
- 原则：优先修源数据，不通过 runtime alias 掩盖数据问题

## 数据库架构

系统数据分为四个层次，各自承担不同角色：

### 1. 产品库 — 产品定义层

**文件**：`data/products/product_library.csv`

定义可销售产品的完整信息。21 个产品覆盖 10 个城市：

| 城市 | 产品数 | 产品 |
|------|--------|------|
| 北京 | 3 | 经典2日 / 深度3日 / 全景4日 |
| 上海 | 3 | 精华2日 / 江南3日 / 乐园4日 |
| 重庆 | 3 | 山城2日 / 山水3日 / 山水5日(含游轮) |
| 西安 | 2 | 古都2日 / 盛唐3日 |
| 阳朔 | 2 | 山水2日 / 深度3日 |
| 张家界 | 2 | 奇景2日 / 全景3日 |
| 广州 | 3 | 商都1日 / 经典2日 / 历史文化3日 |
| 贵州 | 1 | 民族风情4日 |
| 云南 | 1 | 彩云之境5日 |
| 成都 | 1 | 悠闲2日 |

每行包含：产品编号、城市、天数、每日行程、常规/可选项目名称及项目编号列表。

**标准化副本**：`data/products/products.normalized.json` — 由 `scripts/normalize_product_library.py` 生成，包含结构化 `day_plans`（每日活动列表 + item_codes），供 v2 API 运行时消费。

### 2. 景点 Highlights — 内容增强层

**文件**：`data/products/attraction_highlights.json`

按城市组织的 Route → 景点描述映射，每个产品按天数映射到对应 Route。`format_itinerary_markdown()` 直接读取此文件，为每日行程附加景点 Highlights（名称、时长、描述）。

### 3. 服务目录 — 维护编辑层

**文件**：`data/products/services/*.csv`

按服务类型组织的原始价格目录，共 5 类：

| 文件 | 内容 | 用途 |
|------|------|------|
| `产品服务_TICKET_ACTIVITY_门票活动.csv` | 门票 + 活动价格明细 | 景点、体验项目标价 |
| `产品服务_TRANS_车辆.csv` | 车辆接送价格 | 包车、接送机、打车 |
| `产品服务_GUIDE_导游.csv` | 英文导游价格 | 导游日薪、深度讲解 |
| `产品服务_OTHER_其他.csv` | 酒店 + 附加服务 | 住宿、司导补贴 |
| `产品服务_REC_推荐.csv` | 推荐餐饮参考价 | 餐饮推荐（不含在成本内） |

这一层是**按类型组织**的维护入口，方便统一调整某类服务的价格。

### 4. 成本库 — 运行时真源

**文件**：`data/products/services/mashes/*.csv`

按城市合并的成本数据，各城市一个文件。每条记录包含服务项目编号、名称、单价（淡季/旺季）等信息。

```
data/products/services/mashes/
├── 北京_merged.csv    ├── 上海_merged.csv    ├── 广州_merged.csv
├── 重庆_merged.csv    ├── 西安_merged.csv    ├── 阳朔_merged.csv
├── 张家界_merged.csv  ├── 贵州_merged.csv    ├── 云南_merged.csv
└── 成都_merged.csv
```

这一层是**按城市组织**的运行时视图，`cost_engine.py` 直接从各城市 mash 读取数据计算报价。

### 数据关系图

```
产品库 (product_library.csv)              服务目录 (services/*.csv)
        │                                         │
        │  normalize_product_library.py            │  merge_city_products.py
        ▼                                         ▼
  products.normalized.json               成本库 (mashes/*.csv)
  （day_plans + item_codes）                    │
        │                                      │
        │  product_match                       │  load_cost_db()
        ▼                                      ▼
  CandidateProductsJSON ────────────→ cost_engine.calculate_total_cost()
        │                                      │
        │                                      ▼
        │                              PricingResultJSON
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
               attraction_highlights.json
                       │
                       ▼
              format_itinerary_markdown()
              （day_plans + Highlights + 报价表）
```

## 引擎职责

| 引擎 | 角色 | 消费数据 |
|------|------|----------|
| `product_engine.py` | 城市+天数查表匹配（21 固定产品） | `product_library.csv` |
| `cost_engine.py` | 门票/酒店/交通/导游费用计算 | `mashes/*.csv` |
| `custom_route_engine.py` 🆕 | 上海半定制路线：标签匹配+区域聚类+交通检查+时长控制 → RoutePlanJSON | `data/custom/shanghai_*.csv/json` |
| `city_config.py` | 城市代码前缀、成本库路径、折扣规则 | 纯配置 |
| `payment_tracker.py` | 供应商付款 CRUD + 看板统计 | `data/payments.json` |
| `narrative_engine.py` | City Walk 探索地图生成（独立模块，未接入主链路） | `data/citywalk/narratives_v2.csv` |
| `merge_city_products.py` | 数据工程：按类型 CSV → 按城市合并 CSV（手动运行） | `services/*.csv` |

## 核心脚本

- 全量自动验证：`bash scripts/auto_verify.sh` — 一键 normalize + test_multi_city + test_optional_items
- 标准化产品库：`python scripts/normalize_product_library.py` — 从 CSV 生成 `products.normalized.json`
- 多城市链路验证：`python test_multi_city.py`
- optional 项验证：`python test_optional_items.py`
- 🆕 上海半定制路线测试：`python test_custom_route_shanghai.py` — 5 个客户场景端到端验证

## 已知边界与后续优先级

### 已知边界

- 尚未覆盖国际机票实时搜索、签证自动化、支付订单财务系统。
- `projects 2/` 与主流程的关系仍需进一步模块化收敛（当前以并行方式存在）。
- `narrative_engine.py`（City Walk 路线生成）为独立模块，尚未接入主销售交付链路。
- 行程输出为 Markdown 格式，尚未对接 PDF/Canva/Word 渲染。

### 下一步（建议）

1. **全城市回归** — 用真实 Lead 覆盖 10 城市做 v2 full_chain 验证。
2. **输出质量增强** — 多语言输出（中/英）、行程描述丰富、Reminder 和 Contact 结构完善。
3. **Markdown → PDF 渲染** — 对接 Canva/Word/PDF 映射协议。
4. **数据治理自动化** — 变更产品库后自动 normalize + verify，清理重复资产。

### 版本标记

- 当前文档版本：`v2.1.0`
- 更新时间：`2026-06-07`

---

## 一句话说清楚这个项目

给入境游旅行社用的 AI 工具。填客户需求，自动匹配产品、算价格、生成中英双语行程单（day_plans + Highlights + 报价表）。同时提供供应商付款管理看板，跟踪待处理/已支付/已存档的付款条目。后端 Python FastAPI，前端 Streamlit，全部规则引擎，不调 AI。

### 快速启动

```bash
pip install -r requirements.txt
uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload     # 终端1
streamlit run streamlit_app.py                                # 终端2
```

浏览器打开 `http://localhost:8501`，侧边栏填城市/天数/人数，点「生成行程」出结果。

### 项目骨架

| 文件 | 作用 |
|------|------|
| `api_main.py` | API 服务，所有接口在这 |
| `streamlit_app.py` | Web 界面（标准行程 / 上海半定制 / 付款管理 三个 Tab） |
| `engines/product_engine.py` | 标准产品匹配（城市+天数查表） |
| `engines/cost_engine.py` | 报价计算（门票/酒店/交通/导游） |
| `engines/custom_route_engine.py` | 🆕 上海半定制路线引擎 |
| `engines/payment_tracker.py` | 付款管理引擎 |
| `data/products/product_library.csv` | 产品真源（21 产品 / 10 城市） |
| `data/products/products.normalized.json` | 标准化产品库（含 day_plans） |
| `data/products/attraction_highlights.json` | 景点 Highlights 映射 |
| `data/products/services/mashes/` | 成本真源（10 城市，上海已扩展到 38 项） |
| `data/custom/` | 🆕 半定制路线数据（体验单元/交通边/画像/模板） |
| `data/payments.json` | 付款数据存储 |
| `schemas.py` | 数据模型定义 |

### API 接口

- `POST /api/v2/full_chain` — **标准产品一键调用**，填城市/天数/人数，返回结构化 JSON + Markdown 行程单
- `POST /api/v2/custom-route` 🆕 — **上海半定制路线**，填兴趣/节奏/预算/人群，返回编排路线 + 报价 + Markdown 行程单
- 分步：`product-match` → `pricing`（标准链路）/ `custom-route`（半定制）
- 付款：完整的 CRUD + 三列看板统计

### 部署到公网

- **前端（Streamlit Cloud）**：https://aitouragent-39dajfvlpujbydigehbkhc.streamlit.app/
- **后端（Railway）**：https://hexa-blueprint-api-production.up.railway.app
- 部署指南见 [docs/deployment_guide.md](docs/deployment_guide.md)
