# Hexa Blueprint - 入境游 AI 运营辅助系统

## 项目定位

Hexa Blueprint 是一个面向入境游业务链路的结构化 AI 系统。  
目标不是做单次问答，而是把销售到交付的关键中间对象标准化，让推荐、报价、行程和交付都可以持续复用与审计。

核心链路：

`LeadJSON -> CandidateProductsJSON -> PricingResultJSON -> PlanObject -> DeliveryDraftObject`

## 当前实现状态（2026-04-29）

- 已实现 v1 与 v2 API 并存，v2 覆盖 product-match/pricing/plan/delivery/full_chain。
- 已实现 **Streamlit Web UI**（`streamlit_app.py`），运营人员可直接填写需求一键生成行程与报价。
- 已实现 **`/api/v2/full_chain`** 一键全链路接口，简化输入，串联四接口 + Markdown 输出。
- 已实现 4 个业务 Agent Prompt（产品匹配、报价解释、行程编排、交付生成）。
- 已修复产品库与成本库主映射，映射类硬错误清零。
- 已有多城市端到端测试脚本。

## 目录概览（现状）

```text
.
├── api_main.py                    # FastAPI 主应用
├── cli_app.py                     # CLI 交互工具
├── streamlit_app.py               # Web UI（Streamlit）
├── survey_architect.py            # 问卷模块
├── engines/                       # 核心引擎
│   ├── city_config.py
│   ├── product_engine.py
│   ├── cost_engine.py
│   ├── plan_engine.py
│   ├── delivery_engine.py
│   ├── narrative_engine.py
│   └── merge_city_products.py
├── data/                          # 数据资产
│   ├── products/
│   │   ├── product_library.csv    # 产品真源
│   │   ├── products.normalized.json
│   │   └── services/              # 服务目录源文件
│   │       └── mashes/            # 按城市合并的成本真源
│   ├── citywalk/
│   │   └── narratives_v2.csv
│   └── pois/
│       └── beijing_updates.csv
├── docs/
│   ├── logs/工作日志.md
│   ├── prompts/*.md
│   ├── openapi/*.json
│   └── schemas/coze_plugin.json
├── coze_agent_prompt.md
├── coze_plugin_schema.json
├── scripts/
│   └── normalize_product_library.py
├── test_coze_integration.py
├── test_multi_city.py
├── test_optional_items.py
├── verify_product_cost_mapping.py
└── schemas.py                     # Pydantic 模型定义
```

## API 概览

### v1（兼容接口）

- `GET /api/v1/cities`
- `GET /api/v1/survey`
- `POST /api/v1/recommend`
- `POST /api/v1/cost`
- `POST /api/v1/complete`
- `POST /api/v1/feishu/webhook`
- `POST /api/v1/feishu/card`

### v2（结构化接口）

- `POST /api/v2/product-match` — 产品匹配
- `POST /api/v2/pricing` — 报价计算
- `POST /api/v2/plan` — 方案编排
- `POST /api/v2/delivery` — 交付生成
- `POST /api/v2/full_chain` — **一键全链路**（简化输入，串联四接口 + Markdown 输出）

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

**标准化副本**：`data/products/products.normalized.json` — 由 `scripts/normalize_product_library.py` 生成，供 v2 API 运行时消费。

### 2. 服务目录 — 维护编辑层

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

### 3. 成本库 — 运行时真源

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

### 4. 城市叙事 & POI 数据 — 内容增强层

- **城市漫步**：`data/citywalk/narratives_v2.csv` — 上海城市漫步节点 167 个，覆盖 6 条故事线
- **POI 数据**：`data/pois/beijing_updates.csv` — 北京景点元数据（主题分类、建议时长、标签等）

### 5. 文档模板 — 输出质量目标

`data/products/` 目录下存放了 Hexa 业务侧实际使用的交付模板和参考文档。这些文件定义了系统输出的质量目标——**Plan Structuring 和 Delivery Composition 应尽量接近这些人工制作的交付物水准**。

| 文件 | 用途 | 说明 |
|------|------|------|
| `01Product Menu_highlights.pdf` | 产品精选菜单 | 面向客户的高亮点产品概览，用于客户初步选择 |
| `02Product Menu_all_packages.pdf` | 完整产品目录 | 全量产品包清单，含各城市模块化产品的详细描述 |
| `03模版-产品介绍-自有产品.pdf` | 自有产品介绍 | 自营产品的详细介绍 PDF 模版，含行程和图片 |
| `03模版-产品介绍（合作）-其他地接社的已有产品.pdf` | 合作产品介绍 | 合作伙伴（地接社）产品的介绍模版 |
| `04报价单（暂定）.pdf` | 报价单模版 | Canva 报价单格式参考，含定价结构和利润率说明 |
| `05-模版路书.md` | 客户路书模版 | **最终交付物参考** — 完整的多日跨城路书 Markdown，含每日时间表、地点、联系人、注意事项（参见右侧样例） |
| `Hexa - Client Information Form.pdf` | 客户信息表 | 客户问卷信息收集表，用于 Lead Intake |    

> **路线图**：系统的 `DeliveryDraftObject` 和 `full_chain` Markdown 输出应逐步对齐 `05-模版路书.md` 格式。当前输出已覆盖行程与报价，后续需补充：联系人信息、应急提醒、交通衔接说明、多城市衔接段落。

### 数据关系图

```
产品库 (product_library.csv)              服务目录 (services/*.csv)
        │                                         │
        │  item_codes 关联                        │ 按城市合并
        ▼                                         ▼
  products.normalized.json               成本库 (mashes/*.csv)
        │                                         │
        └─────────────┬───────────────────────────┘
                      ▼
              运行时引擎 (cost_engine / plan_engine / delivery_engine)
```

## 核心脚本

- 全量自动验证：`bash scripts/auto_verify.sh` — 一键 normalize + test_multi_city + test_optional_items
- 标准化产品库：`python scripts/normalize_product_library.py` — 从 CSV 生成 `products.normalized.json`
- 多城市链路验证：`python test_multi_city.py`
- optional 项验证：`python test_optional_items.py`
- Coze 集成验证：`python test_coze_integration.py`

## 已知边界与后续优先级

### 已知边界

- 尚未覆盖国际机票实时搜索、签证自动化、支付订单财务系统。
- `projects 2/` 与主流程的关系仍需进一步模块化收敛（当前以并行方式存在）。
- 城市叙事能力已具备基础文件与引擎，但与主销售交付链路尚未完全闭环。

### 下一步（建议）

1. **全城市回归** — 用真实 lead 覆盖 10 城市做 v2 四接口串联验证。
2. **输出质量增强** — 多语言输出（中/英）、行程描述丰富、Reminder 和 Contact 结构完善。
3. **交付模板渲染** — 定义 `DeliveryDraftObject` 到 Canva/Word/PDF 的映射协议。
4. **数据治理自动化** — 变更产品库后自动 normalize + verify，清理重复资产。

### 版本标记

- 当前文档版本：`v1.1.0`
- 更新时间：`2026-04-29`

---

## 一句话说清楚这个项目

给入境游旅行社用的 AI 工具。填客户需求，自动匹配产品、算价格、生成中英双语行程单和报价单。后端 Python FastAPI，前端 Streamlit，全部规则引擎，不调 AI。

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
| `streamlit_app.py` | Web 界面，填表单出结果 |
| `engines/` | 核心逻辑（匹配产品/算价格/排行程/生成文档） |
| `data/products/` | 产品库 CSV + 服务价格 CSV |
| `schemas.py` | 数据模型定义 |

### API 接口

- `POST /api/v2/full_chain` — **一键调用**，填城市/天数/人数，返回行程 Markdown + 报价表
- 分步：`product-match` → `pricing` → `plan` → `delivery`

### 部署到公网

参见 [docs/deployment_guide.md](docs/deployment_guide.md)：GitHub + Railway（后端）+ Streamlit Cloud（前端），全部免费。
