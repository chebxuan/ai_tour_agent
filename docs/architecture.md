# 当前系统架构

更新：2026-10-09。代码位置已整理，新前端已接入产品公开内容；新增独立旅行网站 v3 接口，旧 v2 契约与算法保持。本文只描述现行实现；早期 Agent 设计保存在 [历史设计](archive/agent-designs-2026/README.md)。

## 业务链路

```text
客户原文
  └─ llm_client.parse_lead_text → LeadJSON（JSON/Pydantic 校验，允许一次修复重试）
       └─ 匹配产品 → 成本计算 → 行程渲染 → 风险检查 → 邮件草稿

Streamlit 旧界面 → HTTP + 服务端 API Key → FastAPI
上海半定制 → 静态体验单元/模板/交通边 → 路线与部分成本
付款管理 → data/payments.json
```

LLM 用于自然语言结构化抽取，其余主链路使用确定性规则。项目中存在历史 Coze/LangGraph 实验，但未接入现行主 API。

## 实现位置

| 环节 | 当前实现 |
|---|---|
| FastAPI、匹配评分、完整工作流、Markdown 渲染 | `backend/app/main.py` |
| LLM 请求、解析、校验、重试和调用统计 | `backend/app/llm_client.py` |
| Pydantic 业务结构 | `backend/app/schemas.py` |
| 成本计算 | `backend/app/engines/cost_engine.py` |
| 风险检查 | `backend/app/engines/risk_check_engine.py` |
| 邮件草稿 | `backend/app/engines/delivery_composer.py` |
| 上海路线 | `backend/app/engines/custom_route_engine.py` |
| 付款文件与状态管理 | `backend/app/engines/payment_tracker.py` |
| CLI 使用的 CSV 产品匹配 | `backend/app/engines/product_engine.py` |
| 独立旅行网站 API | `backend/app/routers/travel.py`、`travel_schemas.py`、`services/travel_catalog.py` |
| 旧网页 | `legacy/streamlit_app.py` |
| 运行根路径 | `backend/app/core/paths.py` |

API 的候选评分不等同于 CLI 的 CSV 精确匹配。当前 `main.py` 仍集中多项职责，拆成路由与服务属于后续工作。本轮没有为目录规范化重写这些算法。

## 新前端内容链路

`product_library.csv` 与 `products.normalized.json` → `scripts/export_frontend_products.py` 校验与公开字段导出 → `frontend/data/products.json` → 规划页按城市与天数查看真实路线。前端预览通过 Next.js 服务端接口调用 FastAPI `/api/v3/trips/preview`，提交人数、所选体验与服务意愿；后端进行精确产品匹配及体验校验，不调用内部成本接口。20 个产品有逐日路线，重庆 5 日产品展示概览与待确认说明。

首页继续使用 10 个目的地叙事卡片；使用开放授权实景照片，产品内容投影不包含成本、供应商与付款信息。

## 数据和提示词

- 产品真源 `data/products/product_library.csv` → 标准化运行副本 `products.normalized.json`。
- 分类服务目录 `data/products/services/*.csv` → 城市运行成本库 `services/mashes/*.csv`。
- 展示增强 `data/products/attraction_highlights.json`。
- 上海路线四份输入保留在 `data/custom/`，已取消整体忽略。
- 运行提示词在 `backend/app/resources/prompts/`；默认 `lead_parse_v2`，v1 保留用于基线复现。
- 可写付款文件 `data/payments.json` 和运行日志 `logs/*.jsonl` 不随 Git 或镜像发布。

LLM 调用统计记录字符/token 数和耗时，不保存输入正文；LeadJSON 本身可以包含客户原文。工作流日志包含调用方填写的审核信息，因此不等同于完善的用户权限和审核数据库。

新 v3 内容服务直接读取后端规范化产品库，提供受现有服务端密钥保护的目录、行程预览与独立内部成本估算。旅客预览不包含成本或供应商信息；费用计算的冲突/分支范围需复核时返回 409，销售报价保持待确认。前端已调用 v3 预览，旧 v2 行为不变。详见 [后端接口契约](backend-api.md)。

## 主要接口

- `GET /api/v3/products`：公开产品内容与真实天数范围。
- `POST /api/v3/trips/preview`：精确产品查找、日程与可选体验预览，不调用 LLM。
- `POST /api/v3/internal/cost-estimate`：受保护的内部成本估算，非销售报价。
- `POST /api/lead/parse`：客户文本结构化。
- `POST /api/v2/product-match`、`/pricing`：分步产品与成本计算。
- `POST /api/v2/full_chain`：简化表单生成。
- `POST /api/v2/lead-full-chain`：结构化需求生成。
- `POST /api/v2/lead-text-full-chain`：文本解析后生成。
- `POST /api/v2/risk-check`、`/delivery-compose`：风险与草稿。
- `POST /api/v2/custom-route`：上海半定制。
- `POST /api/v2/human-approval`：追加人工审核事件。
- `/api/v2/payments` 及关联路径：付款记录管理。
- `/health`：健康检查。完整契约由运行中的 `/docs`、`/openapi.json` 提供。

## 验证证据与限制

- [本次整理验证](test_reports/organization_20261007.md)：目录迁移与现有接口/业务基线对比。
- 规则评测：[`product_match`](test_reports/product_match_eval_latest.md)、[`pricing`](test_reports/pricing_eval_latest.md)、[`risk_check`](test_reports/risk_check_eval_latest.md)、[`delivery_compose`](test_reports/delivery_compose_eval_latest.md)。
- 历史文本抽取评测：v1 [75.93%](test_reports/lead_parse_eval_v1.md) → v2 [97.78%](test_reports/lead_parse_eval_v2.md)，50 条样例、270 个字段断言；本次未重跑外部模型。
- 耗时口径见 [历史计时报告](test_reports/time_trial.md)，不能把旧人工自估与程序执行时间混成实测节省效果。

共享 API Key、同步 LLM 调用、JSON 存储、工作流标识与审核关联等限制仍存在。新浏览器前端不能直接复用服务端共享密钥。完善身份、业务记录和调用策略见 [路线图](roadmap.md)。

## 英文 Menu 内容

PDF 全量文字存档在忽略的私人参考目录；24 条编号 Route、贵州/云南整线介绍和 19 项体验提取到 `attraction_highlights.json`。`menu_presentation.json` 单独维护真实产品按天映射、英文名称及必要的编辑说明。旧 `product_days` 保留兼容，新预览不依赖其重复映射。公开响应不含 PDF 原价，未选体验不进入已选体验卡片。

2026-10-09 计费更新：共享产品源已校正北京编号与重庆游轮范围；`cost_scope.py` 校验已核实映射并选择互斥分支，游轮陆地服务只计 2 日。`sales_pricing.py` 按服务端规则成本 × 1.3 生成白名单旅客报价，`/api/v3/trips/quote` 与运营 `/internal/cost-estimate` 分离。前端目前只调用预览，报价接入待下一阶段。

2026-10-09 报价联调：Next.js `/api/products` 读取公开分支/导游选项，`/api/trips/quote` 固定转发旅客报价接口。前端选择季节与具体路线，展示估算价和范围；成本与供应商数据留在后端。

## PostgreSQL 主数据（2026-10-09 已接入）

本地 PostgreSQL 位于 `127.0.0.1:55432/travel_copilot`。`storage/repository.py` 将关系表还原为既有领域对象，保留成本算法和旅客响应契约。v3 请求使用只读、可重复读事务快照，产品、价格和销售规则不会在同一次报价中混用不同版本。数据库故障返回 503，不自动回退文件金额。

产品、每天路线、项目引用、分支、服务、历史成本、供应商及关联均有关系表；复杂 Menu 文案和部分范围规则保留 JSONB。金额使用 NUMERIC，服务引用由外键约束。首次导入包含 21 个产品、261 个服务和 6 个分支，保存文件哈希与批次；重复导入同批次不创建重复数据，维护后的数据库不接受新源文件强制覆盖。

FastAPI 使用只读 `travel_app`，本地维护工具使用 `travel_owner`。改价新增版本并记录修改人，使用预期版本限制过期覆盖；产品英文标题/介绍、供应商录入与关联均有维护命令。运营显式保存报价时保留需求、内部成本、旅客金额与价格/销售规则版本；普通预览不自动落库，提交询单时保存快照。供应商当前为空，没有迁移不明身份资料。

CSV/JSON 继续作为初始来源和文件基线，`data/custom/`、付款 JSON 与旧日志保留现状。网页运营登录、维护表单、询单提交和生产数据库尚未实现；详细操作、备份恢复及验证边界见 [数据库使用说明](database-guide.md)。

## 咨询留资链路（2026-10-09 已接入）

02 的 `JourneyEnquiry.jsx` 展开 Name/Email/Message 表单，复用当前预览，不重新填写行程。浏览器 → Next.js `/api/trips/enquiries` → FastAPI `/api/v3/trips/enquiries` → PostgreSQL `journey_enquiries`。

预览/报价接口签发有效 2 小时的公开快照签名，后端核对签名及需求一致性，保留展示时的产品文案与估算。提交时在可重复读事务中重新计算当前成本/销售报价；若成功，关联独立报价快照及当时的价格/政策版本。显示估算和当前复核结果分别保存，避免改价覆盖客户曾看到的金额。

写入使用单独的 `travel_intake` 权限，原目录账户不能读取客户咨询；维护命令以本地 owner 权限查看。唯一请求编号与内容哈希保护重复请求，事务提交成功后才返回咨询编号。报价待确认不阻断咨询，快照过期要求更新预览。没有邮件发送、客户账号、订单或运营网页。本地运营入口与接口限制见数据库使用说明及接口契约。


## 目的地预览与独立联系页（2026-10-09）

`/plan` 直接访问显示联系表单；`/plan?destination=…` 和已有 `?journey=…` 显示产品选择及 Menu 预览。目的地卡片不再与直接联系页重复。

产品询单继续使用签名预览／报价，新增住宿偏好单独进入 `journey_enquiries.preferences`，不进入成本计算，也不改变既有费用 × 1.3 规则。酒店仍需另行报价。

独立联系页通过同源 Next.js `/api/trips/custom-enquiries` 转发受 API Key 保护的 FastAPI 同名 v3 接口。新增 `003_custom_enquiries.sql` 允许产品编号为空，通过 `enquiry_kind` 与约束区分产品／自定义询单；自定义询单只保存偏好和待人工确认状态，不插入报价快照。沿用受限 intake 账户、事务、UUID 去重与公开收据白名单，读取账户仍不能查询客户信息。

照片与文化叙事只引用公开内容。实景资源来源与授权集中记录，图片署名在组件和页脚可查；本地 Next Image 提供适配屏幕的图片，不依赖运行时第三方图片请求。


2026-10-09 图片更新：当前页面改用用户提供的城市／首页素材，由 `frontend/data/sitePhotography.js` 管理。首页固定石桥照片，以本地 CSS 持续缩放／平移覆盖全屏首屏，不访问后端；先前 Wikimedia 来源记录保留，但已不显示在新图片的署名中。
