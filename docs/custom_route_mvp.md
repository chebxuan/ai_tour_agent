# Custom Route MVP — 上海半定制路线生成器

> 第一阶段 MVP：以数据可计算的方式，实现从模糊客户需求到结构化半定制路线的端到端生成。

## 一句话说明

给运营人员用的上海路线半自动生成器。输入客户画像（兴趣、节奏、预算、人群），引擎从 35 个上海体验单元中推荐一条可交付、可审核、可报价的路线，输出结构化 RoutePlanJSON。

## 这个模块与 21 个标准产品库的关系

```
现有链路（标准产品匹配，不变）：
  LeadJSON → product_engine（21产品匹配）→ cost_engine → Markdown itinerary
  适合：城市和天数明确、需求标准、想快速报价的询单

新增链路（上海半定制路线，parallel module）：
  LeadProfile → custom_route_engine（POI池编排）→ RoutePlanJSON → partial cost_engine mapping → Markdown
  适合：客户喜欢小众体验、想 City Walk / 拍照 / 咖啡馆生活方式、预算敏感但要有特色
```

两条链路**不相互替代**。21 产品是"麦当劳套餐"，Custom Route 是"自选配料"。21/35 体验单元已通过 `cost_item_code` 接入 `cost_engine`（门票/活动 17 项 + 客人自理 4 项）；导游/车辆/酒店由 API 层自动补入；免费点 14 项不映射（无需成本）。

## 测试状态

| 测试 | 结果 | 说明 |
|------|------|------|
| 5 场景核心逻辑测试 | **5/5 PASS** | F1-F6 六个维度全部通过（模板合规/交通连续性/时长/成本/雨天/完整性） |
| 315 场景排列组合矩阵 | **55 unique fingerprints** | 5 interest sets × 2 durations × 3 budgets × 4 groups × 3 paces。用于发现模板覆盖和路线重复问题 |
| 模板覆盖率 | **12 templates** | Classic / Photogenic / Family / Rainy / Budget / Romantic / Creative / Water Town / Photo+Cafe / Family-half / Culture-half / Senior-slow |
| 报价映射覆盖率 | **21/35 units mapped** | 门票+活动 17 项 + 客人自理 4 项已标记编码；免费点 14 项不映射（无需成本） |

## 当前限制与已知边界

- **报价为部分接入**：21/35 体验单元已映射到 `上海_merged.csv`（38 项）。门票/活动 17 项已通过 `cost_engine` 计入团费；咖啡/骑行/新天地等 4 项已标记编码但通常客人自理；免费点 14 项无需映射。导游/车辆/酒店由 API 层自动补入。
- **仅上海一个城市**：扩展到其他城市需要补充对应的 `{city}_experience_units.csv` + `{city}_transport_edges.csv` + `{city}_route_templates.json`
- `social_heat_score` 为人工维护，无实时社媒数据
- 交通时间来自写死的 CSV 数据，不是实时地图 API
- `rainy_day` 参数需人工传入，未接入天气 API

## 它适合处理什么需求

- 客户说"我们想在上海逛一天，喜欢拍照和咖啡馆，不要太累" → 半日/一日半定制路线
- 客户说"明天上海下雨，有什么室内推荐？" → 雨天替代方案
- 客户说"带老人玩上海，慢一点，少走路" → 需要频繁休息的慢节奏路线
- 客户说"预算有限，有没有免费的好玩的地方？" → 低成本高体验路线
- 运营人员想"在上海精华2日游中把第二天的豫园换成武康路 City Walk" → 标准产品 + 替换模块

## 它不适合处理什么需求

- "帮我排一个 10 天北京+西安+上海的全中国行程" → 跨城市、多天、交通复杂，需要 itinerary_engine 而非 custom_route_engine
- "我想去这个具体的网红店，帮我查到它" → 这是地图搜索，不是路线编排
- "旅行社的所有流程帮我全自动化" → 这是完整 ERP，超出了 MVP 范围

## 为什么它是从固定产品到半定制产品的升级

| 维度 | 固定 21 产品 | 半定制路线 |
|------|-------------|-----------|
| 输入 | 城市 + 天数 | 兴趣标签 + 节奏 + 预算 + 人群 + 天气 |
| 路径 | 查表匹配 | 标签打分 + 区域聚类 + 交通检查 + 时长控制 |
| 出数 | 固定 itinerary_text | 动态组合的 unit 序列 |
| 可解释性 | "因为这个城市只有这个产品匹配" | "因为你是摄影爱好者，Wukang 的得分最高，且和 Romeo's Balcony 同区域可步行" |
| 定制空间 | 可选项目（±2个） | 任意替换/增减单元 |

## 数据文件

| 文件 | 内容 | 行数 |
|------|------|------|
| `data/custom/shanghai_experience_units.csv` | 上海体验最小单元库 | 35 条 |
| `data/custom/shanghai_transport_edges.csv` | POI 间点对点交通关系 | 99 条 |
| `data/custom/customer_profile_tags.csv` | 客户画像标签 | 12 个画像 |
| `data/custom/shanghai_route_templates.json` | 路线模板 | 12 个模板 |

## 引擎逻辑（custom_route_engine.py）

```
输入：interests, pace, budget, group_type, rainy_day, need_private_car
  │
  ├─ Step 1: match_profile_to_tag() → 匹配最近画像（12选1，classic→TAG-01，budget=low→TAG-08）
  │
  ├─ Step 2: score_unit() × 35 → 打分（兴趣直击 0.45/hit + 画像标签 0.30/hit + 人群 ±0.35 + 预算 ±0.45）
  │
  ├─ Step 3: filter_and_rank() → 硬过滤+排序
  │
  ├─ Step 4: select_route_units() → 按 9 条规则选点：
  │   规则1: 模板 preferred_areas + required_unit_types 驱动锚点
  │   规则2: group-aware fill（couple→photo, family→activity, solo/senior→freebie）
  │   规则3: 全天加 dining + activity（全对交通检查，未知边 25min）
  │   规则4: 雨天过滤 + 单元底线 + 辅助点规则 + 首次客经典锚点
  │
  └─ Step 5: assess_risks() + 模板合规报告 → 风险+定制+Markdown
```

## 5 个测试场景结果

| # | 场景 | 匹配画像 | 推荐路线 | 时长 | 成本 |
|---|------|---------|---------|------|------|
| 1 | First-timer, classic, one day | First-time Visitor | Yu Garden → Romeo's Balcony → One Step Garden Cafe → Peace Hotel | 337min | ¥120 |
| 2 | Young couple, photogenic, half day | Budget-conscious / Backpacker | Bund Viewing Platform → Xujiahui Cathedral | 163min | ¥0 |
| 3 | Family + child, rainy, one day | Family with Children | Shanghai Museum → Huangpu River Cruise → Peace Hotel → Xiaolongbao | 430min | ¥336 |
| 4 | Culture slow pace, senior, one day | Culture & History Deep-dive | First CPC Site → Peace Hotel → Xintiandi → Ba Jin Former Residence | 346min | ¥200 |
| 5 | Budget solo, free/low-cost, half day | Budget-conscious / Backpacker | Bund Viewing Platform → Old Street → Xujiahui Cathedral | 215min | ¥0 |

## Streamlit UI（已完成）

Streamlit 新增 "🏙️ 上海半定制" Tab（三个 Tab 中的第二个）。运营人员在浏览器中：
1. 选择兴趣标签、节奏、预算、人群 → 设置人数/雨天/包车/导游
2. 点击"生成半定制路线" → 调用 `/api/v2/custom-route`
3. 展示路线卡片（unit 序列 + 交通 + 报价明细 + 编排逻辑 + 风险提示 + 模板合规 + Markdown 预览）

## 报价映射（已完成）

- 上海成本库从 28 项扩展为 38 项（新增 SH-TICKET-09~12、SH-ACTIVITY-09~14）
- **21/35 体验单元已通过 `cost_item_code` 语义接入 `cost_engine`**：门票/活动类 17 项 + 餐饮/咖啡/骑行（客人自理）4 项已标记编码
- 14 个免费拍照/漫步点不映射（无需成本，正确的设计选择）
- 导游/车辆/酒店由 `/api/v2/custom-route` 根据 `need_guide`、`need_private_car`、`duration_type` 从上海成本库自动补入
- 未映射项仍保留 `estimated_cost_rmb` 作为业务参考

## 已知边界

- 仅上海一个城市。扩展到其他城市需要：{city}_experience_units.csv + {city}_transport_edges.csv + {city}_route_templates.json
- `social_heat_score` 为人工维护，无实时社媒数据
- 交通时间为写死的 CSV 数据，不是实时地图 API
- 没有实时天气 API，rainy_day 需要人工传入
- 不接入供应商自动匹配（以后做）
