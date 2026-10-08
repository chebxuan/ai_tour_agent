# 当前系统架构

更新：2026-10-07。代码位置已整理，业务规则与 API 契约保持。本文只描述现行实现；早期 Agent 设计保存在 [历史设计](archive/agent-designs-2026/README.md)。

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
| 旧网页 | `legacy/streamlit_app.py` |
| 运行根路径 | `backend/app/core/paths.py` |

API 的候选评分不等同于 CLI 的 CSV 精确匹配。当前 `main.py` 仍集中多项职责，拆成路由与服务属于后续工作。本轮没有为目录规范化重写这些算法。

## 数据和提示词

- 产品真源 `data/products/product_library.csv` → 标准化运行副本 `products.normalized.json`。
- 分类服务目录 `data/products/services/*.csv` → 城市运行成本库 `services/mashes/*.csv`。
- 展示增强 `data/products/attraction_highlights.json`。
- 上海路线四份输入保留在 `data/custom/`，已取消整体忽略。
- 运行提示词在 `backend/app/resources/prompts/`；默认 `lead_parse_v2`，v1 保留用于基线复现。
- 可写付款文件 `data/payments.json` 和运行日志 `logs/*.jsonl` 不随 Git 或镜像发布。

LLM 调用统计记录字符/token 数和耗时，不保存输入正文；LeadJSON 本身可以包含客户原文。工作流日志包含调用方填写的审核信息，因此不等同于完善的用户权限和审核数据库。

## 主要接口

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
