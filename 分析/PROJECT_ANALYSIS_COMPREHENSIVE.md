# 城市旅游智能平台（Hexa Blueprint）项目完整分析（详细版）

**分析日期**：2026-04-28  
**项目位置**：`/Users/gengchenxuan/Downloads/Master-Retrieval-Augmented-Generation-RAG-Systems-main`  
**分析基线**：结合 `docs/logs/工作日志.md`（重点 4/27、4/28）与 `PRD_执行路线.md`（v1.0.1）

---

## 📋 一、项目总览

本项目当前可视为一个“**双层并行架构**”：

1. **主业务链路层（生产主路径）**：围绕入境游业务对象，完成从 Lead 到 Delivery 的结构化闭环；
2. **数据管道层（能力孵化路径）**：在 `projects 2/` 内进行城市叙事、地标抽取、坐标增强与地图可视化。

### 1.1 当前阶段结论

- 主链路 `LeadJSON -> CandidateProductsJSON -> PricingResultJSON -> PlanObject -> DeliveryDraftObject` 已可跑通；
- v2 四接口（product-match/pricing/plan/delivery）已落地并可独立调用；
- 数据真源策略已明确并在 4/27 日志中确认：
  - 产品真源：`data/products/product_library.csv`
  - 成本真源：`mashes/*.csv`
- 当前主要风险从“功能缺失”转为“**文件重复、路径口径不一致、并行模块边界不清晰**”。

---

## 🗂️ 二、目录结构详解（现状）

### 2.1 根目录关键入口

| 文件 | 作用 | 当前状态 |
|---|---|---|
| `api_main.py` | FastAPI 服务入口（v1+v2） | 核心运行中 |
| `cli_app.py` | 交互式命令行工具 | 核心运行中 |
| `survey_architect.py` | 问卷生成 | 运行中 |
| `schemas.py` | 结构化对象 schema | v2 依赖 |
| `readme.md` | 项目说明（已刷新） | 当前文档基线 |
| `PRD_执行路线.md` | 执行 PRD（v1.0.1） | 当前策略基线 |

### 2.2 核心引擎目录 `engines/`

| 文件 | 主要职责 | 关键依赖 |
|---|---|---|
| `product_engine.py` | 产品推荐匹配 | `data/products/product_library.csv` |
| `cost_engine.py` | 成本计算与报价汇总 | `mashes/*.csv` + `city_config.py` |
| `plan_engine.py` | PlanObject 构建 | v2 Plan 接口 |
| `delivery_engine.py` | DeliveryDraftObject 构建 | v2 Delivery 接口 |
| `city_config.py` | 城市映射、折扣规则、成本库路径 | `mashes/*.csv` |
| `narrative_engine.py` | 城市叙事路线编排 | `data/citywalk/narratives.csv` |
| `merge_city_products.py` | 服务明细合并脚本 | `data/products/services/*` |

### 2.3 数据目录

#### A. 主链路核心数据（业务数据库）

| 路径 | 类型 | 角色 |
|---|---|---|
| `data/products/product_library.csv` | CSV | 产品主表（真源） |
| `data/products/products.normalized.json` | JSON | 标准化产物 |
| `mashes/*_merged.csv` | CSV | 10 城市运行时成本库（真源） |

#### B. 扩展数据（叙事与地图）

| 路径 | 类型 | 角色 |
|---|---|---|
| `data/citywalk/narratives.csv` | CSV | 主项目叙事数据 |
| `data/citywalk/narratives_v2.csv` | CSV | 叙事增强版 |
| `data/pois/beijing_updates.csv` | CSV | POI 辅助数据 |
| `assets/maps/shanghai_landmarks.json` | JSON | 地图数据产物 |
| `assets/maps/shanghai_landmarks_map.html` | HTML | 地图展示产物 |

### 2.4 文档目录 `docs/`

| 子目录 | 内容 |
|---|---|
| `docs/logs/` | 工作日志 |
| `docs/prompts/` | agent prompt 文档（当前保留 1~4） |
| `docs/openapi/` | openapi/coze/pretty 三份规范文件 |
| `docs/designs/` | 设计文档（citywalk） |

### 2.5 数据管道并行模块 `projects 2/`

该目录包含：
- `scripts/`：地标提取、坐标补全、坐标转换、可视化；
- `src/`：LangGraph + storage 抽象；
- 顶层数据产物：`city_narratives.csv`、`city_narratives_amap_coords.csv`、`shanghai_landmarks.*`。

定位：**能力孵化与数据加工层**，并非当前主销售交付链路的唯一运行目录。

---

## 🧠 三、核心业务链路（与 PRD 对齐）

来自 `PRD_执行路线.md` 的当前链路定义：

1. Lead Intake -> `LeadJSON`
2. Product Match -> `CandidateProductsJSON`
3. Pricing -> `PricingResultJSON`
4. Plan Structuring -> `PlanObject`
5. Delivery Composition -> `DeliveryDraftObject`

### 3.1 对应接口状态

#### v1（兼容）
- `GET /api/v1/cities`
- `GET /api/v1/survey`
- `POST /api/v1/recommend`
- `POST /api/v1/cost`
- `POST /api/v1/complete`
- `POST /api/v1/feishu/webhook`
- `POST /api/v1/feishu/card`

#### v2（结构化主链）
- `POST /api/v2/product-match`
- `POST /api/v2/pricing`
- `POST /api/v2/plan`
- `POST /api/v2/delivery`

结论：接口能力与 PRD 当前阶段描述一致。

---

## 🗄️ 四、数据库（数据资产）全量盘点

> 当前仓库没有 sqlite/db/parquet/duckdb 本地文件。  
> 主要“数据库”是 CSV/JSON 文件库；另有可连 PG 的代码骨架。

### 4.1 主链路真源（必须保留）

1. `data/products/product_library.csv`（产品真源）
2. `mashes/*_merged.csv`（成本真源）

### 4.2 标准化与校验产物

3. `data/products/products.normalized.json`（由 `scripts/normalize_product_library.py` 生成）
4. `verify_product_cost_mapping.py`（真源映射校验）

### 4.3 城市叙事相关数据

5. `data/citywalk/narratives.csv`
6. `data/citywalk/narratives_v2.csv`
7. `projects 2/city_narratives.csv`
8. `projects 2/city_narratives_amap_coords.csv`

### 4.4 地图产物

9. `assets/maps/shanghai_landmarks.json`
10. `assets/maps/shanghai_landmarks_map.html`
11. `assets/maps/shanghai_landmarks_map_v2.html`
12. `projects 2/shanghai_landmarks.json`
13. `projects 2/shanghai_landmarks_map.html`

### 4.5 代码层数据库能力（非当前主路径）

- `projects 2/src/storage/database/db.py`：支持 `PGDATABASE_URL` + SQLAlchemy；
- `projects 2/src/storage/database/shared/model.py`：DeclarativeBase。

结论：目前主流程仍以文件型数据资产为主，PG 能力尚处框架预留状态。

---

## 🔧 五、关键模块行为拆解

### 5.1 `product_engine.py`

- 从 `data/products/product_library.csv` 读取产品；
- 按“城市 + 天数”筛选；
- 返回行程、常规/可选项目、推荐可选项、以及项目编号列表；
- 当前设计偏向“单路径命中”，适合标准产品流程。

### 5.2 `cost_engine.py`

- 基于城市映射读取 `mashes/{city}_merged.csv`；
- 解析常规/可选项目编号，计算门票、酒店、交通、导游；
- 对免费项、空价、范围价有兼容；
- 返回结构化汇总与明细，契合 PricingResultJSON。

### 5.3 `city_config.py`

- 定义 10 城市成本库路径；
- 提供折扣规则（儿童/老人）；
- 提供交通车型选择规则。

### 5.4 `api_main.py`

- 同时支持 v1 和 v2；
- `API_KEY` 认证；
- 使用 `schemas.py` 做结构化响应；
- 已引入 `products.normalized.json` 路径常量。

---

## 📆 六、与工作日志（4/27 & 4/28）的一致性核对

### 6.1 4/27 关键声明对齐结果

日志声明：
- 产品真源 = `data/products/product_library.csv`
- 成本真源 = `mashes/*.csv`

核对结果：
- 与当前 PRD 和引擎代码一致；
- 该结论应继续作为删除和收口的硬约束。

### 6.2 4/28 关键声明对齐结果

日志声明：
- Delivery 层落地（`engines/delivery_engine.py` + `/api/v2/delivery`）；
- 全链路结构化对象打通。

核对结果：
- 与 `api_main.py` 及当前 PRD 描述一致；
- 当前工作重点应从“补功能”转到“治理重复资产 + 回归验证”。

---

## ⚠️ 七、问题与风险清单（按优先级）

### P0（需立刻控制）

1. **重复路径与同类文件并存**  
   易出现“工程使用 A，文档写 B”的漂移。

2. **并行模块边界模糊**  
   `projects 2/` 与主链路未形成明确输入输出契约。

3. **历史迁移痕迹仍影响认知**  
   工作日志存在多个阶段性架构叙述，容易混读。

### P1（影响迭代效率）

4. **测试资产分散**  
   有脚本但缺少统一回归入口和结果归档规范。

5. **模板渲染层未固化**  
   Delivery 对象已可用，但模板落地路径待标准化。

### P2（中长期）

6. **数据库层演进策略未定**  
   何时从 CSV/JSON 主存储转向 DB（PG）仍无正式路线。

---

## ✅ 八、已执行的文件治理动作（本轮）

根据你的确认（批次 1 + 3）已执行：

1. 删除 `docs/prompts/coze_agent.md`
2. 删除 `docs/schemas/coze_plugin.json`
3. 删除 `projects 2/scripts/rebuild_citywalk_data.py`

解释：
- 前两项用于收敛 Coze 配置真源（保留根目录新版）；
- 第三项用于收敛重复脚本（保留根目录 `scripts/rebuild_citywalk_data.py`）。

---

## 🚀 九、建议执行路线（与 PRD P0/P1 对齐）

### 阶段 A：继续路径收口（P0）

1. 明确每类资产唯一真源目录（配置、脚本、地图产物、叙事数据）；
2. 对剩余疑似重复文件逐批确认删除；
3. 同步更新 README 与工作日志“目录口径”。

### 阶段 B：回归基线建立（P1）

1. 固化 10 城市最小回归样本；
2. 统一输出测试结果格式（通过/失败/原因分类）；
3. 将失败样本沉淀进日志。

### 阶段 C：模块契约化（P1-P2）

1. 明确定义 `projects 2` 的输入输出契约；
2. 统一“数据管道产物 -> 主链路可消费数据”的发布步骤；
3. 再决定是否推进 PG 化存储。

---

## 📈 十、成熟度与里程碑判断

- 当前成熟度：**Beta+（可试运行）**
- 运行稳定性：**主链路可用**
- 主要短板：**资产治理和口径一致性**
- 下一里程碑：**进入可持续运营态（可审计、可回归、可维护）**

---

**维护建议**  
每次目录重构、接口新增、文件清理后，至少同步更新：
1. `PRD_执行路线.md`
2. `docs/logs/工作日志.md`
3. `readme.md`
4. 本文档（综合分析）
