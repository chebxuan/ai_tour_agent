# Hexa Blueprint 执行 PRD（v1.1.0）

## 1. 文档目的

本 PRD 用于统一产品、工程、运营三方对当前系统状态与下一步执行路径的理解。  
定位为”可执行文档”，重点回答三件事：

1. 当前到底做到哪一步；
2. 接下来按什么优先级推进；
3. 每一步如何验收。

## 2. 系统定义

### 2.1 系统定位

- 不是旅游问答机器人；
- 是从 Lead 到 Delivery 的结构化运营辅助系统；
- 面向运营人员：**输入需求 → 1分钟生成 → 可直接发送客户的行程草稿**。

### 2.2 当前版本结论

- 当前版本：`v1.1.0`（产品化版本）
- 实现状态：主链路可运行，v2 五接口可独立调用（含 full_chain）
- 前端状态：Streamlit Web UI 可交互，支持 10 城市
- 业务状态：**具备产品级 Demo 演示能力**，可稳定展示从输入到输出的完整闭环

## 3. 核心业务链路

`LeadJSON -> CandidateProductsJSON -> PricingResultJSON -> PlanObject -> DeliveryDraftObject`

### 阶段 1：Lead Intake
- 输入：客户初始咨询信息
- 输出：`LeadJSON`
- 状态：已实现

### 阶段 2：Product Match
- 输入：`LeadJSON`
- 输出：`CandidateProductsJSON`
- 接口：`POST /api/v2/product-match`
- 状态：已实现

### 阶段 3：Pricing
- 输入：`LeadJSON + selected_product_id`
- 输出：`PricingResultJSON`
- 接口：`POST /api/v2/pricing`
- 状态：已实现

### 阶段 4：Plan Structuring
- 输入：`LeadJSON + selected_product_ids`
- 输出：`PlanObject`
- 接口：`POST /api/v2/plan`
- 状态：已实现

### 阶段 5：Delivery Composition
- 输入：`LeadJSON + selected_product_ids`（当前接口）
- 输出：`DeliveryDraftObject`
- 接口：`POST /api/v2/delivery`
- 状态：已实现

## 4. 数据与真源策略

### 4.1 真源定义

- 产品真源：`data/products/product_library.csv`
- 成本真源：`data/products/services/mashes/*.csv`

### 4.2 治理原则

1. 优先修产品库与成本库源数据；
2. 不用 runtime alias 掩盖硬错配；
3. 每次数据变更后至少执行一次 verify；
4. 文档、接口、脚本路径要同步更新。

### 4.3 当前治理结论

- 映射类主问题已从阻塞项降为可控项；
- 当前主要风险转向“重复文件、重复路径、重复文档口径”。

## 5. 角色分工（Agent）

- Agent 1：产品匹配（`agent_1_product_matcher`）
- Agent 2：报价解释（`agent_2_pricing_copilot`）
- Agent 3：行程编排（`agent_3_plan_structurer`）
- Agent 4：交付生成（`agent_4_delivery_composer`）

统一约束：

- 输出 JSON 优先；
- 不虚构价格与资源；
- 不跳过风险字段（如 validation issues、planning notes）。

## 6. 执行路线（2026-04-29 起）

### P0：产品化体验层（已完成 ✅）

目标：让运营人员可直接通过界面生成行程，而非调用 API。

完成项：
- [x] `/api/v2/full_chain` 一键全链路接口
- [x] Markdown 行程输出（可直接复制发送客户）
- [x] Streamlit Web UI（`streamlit_app.py`）
- [x] 单城市（北京）完整闭环验证

### P1：多城市覆盖与输出增强（当前）

目标：全 10 城市可稳定输出，行程内容更丰富。

执行项：

1. ~~全城市回归测试~~ ✅ 已完成（10 城市 full_chain + pricing/plan/delivery 全部通过）
2. ~~非北京场景报价与交付抽样验证~~ ✅ 已完成（上海/广州/西安/重庆/阳朔/张家界/贵州/云南/成都均正常）
3. ~~`need_private_car=false` 生效~~ ✅ 已完成（cost_engine 尊重该标志位）
4. ~~行程描述丰富化（景点简介、时间建议、注意事项、联系人）~~ ✅ 已完成（7 章节结构化路书）
5. ~~对齐 `05-模版路书.md` 格式（联系人表格、交通衔接、应急提醒）~~ ✅ 已完成（行程表/酒店/交通/联系人/提醒齐全）
6. 多语言输出（中英文双语）。
7. 明确交付模板渲染层（Canva/Word/PDF）映射协议。

验收：

- 10 城市均可生成完整行程+报价；
- 失败样本有明确分类（数据/逻辑/外部依赖）；
- 输出内容可直接复制发送客户，无需手动编辑。

### P2：数据治理与自动化（并行）

目标：减少人工维护成本，防止回归。

执行项：

1. 固化数据更新流程：变更产品库后自动 normalize + verify；
2. 治理免费项 / 空价 / 估算价的展示策略；
3. 收敛重复资产（根目录、`data/`、`docs/`、`projects 2/` 同类文件）；
4. 清理已废弃路径与历史迁移遗留。

验收：

- 数据变更后单脚本即可完成全量验证；
- 文档、接口、脚本路径保持一致。不出现已废弃路径作为”当前路径”。

## 7. 风险与约束

### 7.1 当前主要风险

1. 重复文件与历史路径并存，造成误用；
2. 文档版本漂移快于代码更新；
3. `projects 2/` 与主链路边界未完全收口。

### 7.2 约束

1. 不破坏 v1 兼容接口；
2. 不破坏 v2 核心对象语义；
3. 不在未确认前批量删除文件。

## 8. 成功标准

满足以下条件可视为阶段成功：

1. v2 四接口可稳定串联；
2. 核心对象结构稳定、可复用；
3. 关键数据映射问题不再成为主阻塞；
4. 文档与代码路径一致；
5. 文件清理动作可审计、可回滚（通过 git）。

---

更新时间：2026-04-29  
维护说明：本文件与 `docs/logs/工作日志.md` 必须同步演进。
