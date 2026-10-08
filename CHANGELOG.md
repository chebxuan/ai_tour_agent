# CHANGELOG

## 2026-10-07 — 目录与文档整理

- 后端实现迁入 `backend/app/`，保留根目录兼容入口；运行提示词迁入后端资源。
- 旧界面/CLI、测试、评测、实验与参考材料分区；修正导入、数据路径、文档链接。
- 合并两组精确重复文件，私人材料与旧付款记录保留在本地；原有用户变动未恢复或覆盖。
- 更新 Git/Docker 忽略规则、配置模板、依赖入口和容器复制范围。
- 提供 `scripts/verify_project.py`；当前说明与历史材料分开，维护统一路线图。
- 后续顺序调整为先创建 Next.js 前端，再联调并完善后端、存储和上线配置。
- 验证结果见 `docs/test_reports/organization_20261007.md`；新前端与镜像构建尚未执行。


> 变更记录按时间倒序。README 只保留"当前系统能做什么"的稳定表述，逐条更新移到这里。

## 2026-09-08

- **前端 Tab1 重构为「文本优先」**：粘贴客户原文 → AI 解析（`POST /api/lead/parse`）→ 可读「AI 已识别」摘要卡 + 「需人工确认」清单 + 表单预填 → 收敛为**单一生成路径**（`POST /api/v2/full_chain`）。内置 3 条 L2/L3 复杂度示例询单（日期弹性 / 否定偏好 / 长者节奏），移除「解析并直接生成」「一键生成」两条旁路与对应前端 wrapper。
- **运行时 Lead Parse prompt 默认切到 v2**：`llm_client.parse_lead_text(..., prompt_version="lead_parse_v2")`，live 接口未显式传版本即用 v2。
- **修复 DashScope 404**：`.env` 补齐实测可用模型 `OPENAI_MODEL=qwen3.8-27b`（此前代码默认 `gpt-4.1-mini` 打非 OpenAI 端点 → `model_not_found`）。`llm_client` 不做模型映射，模型名随 `.env` 而定。

## 2026-09-07

### Lead Parse 真实 LLM 评测跑通

- `eval_cases/lead_parse_cases.json` 扩到 **50 条**（含 over-inference 边界、units/currency/date 陷阱），真实运行 DashScope LLM（`qwen3.8-27b`），字段级准确率 **v1 75.93%（205/270）→ v2 97.78%（264/270）**：
  - [eval_v1](docs/test_reports/lead_parse_eval_v1.md) / [eval_v2](docs/test_reports/lead_parse_eval_v2.md)
  - 失败逐条分类（含 2 个 v2 真实回退）：[lead_parse_bad_cases.md](docs/test_reports/lead_parse_bad_cases.md)
  - 匿名调用证据节录：[AI_EVIDENCE_llm_log_excerpt.md](docs/AI_EVIDENCE_llm_log_excerpt.md)（原始日志 `logs/llm_calls.jsonl` 被 `.gitignore` 屏蔽）
- **Prompt 版本化 + eval 复跑**：`docs/prompts/lead_parse_v1.md` → `lead_parse_v2.md`；`scripts/eval_lead_parse.py` 支持 `--prompt-version`，同一评测集 v1/v2 可比。

### AI Workflow 基础层（新增）

- `POST /api/lead/parse`：客户自由文本 → `LeadJSON`，作为自然语言入口。
- `POST /api/v2/lead-text-full-chain`：客户自由文本 → `LeadJSON` → 产品匹配 → 报价 → 行程单 → 风险检查。
- `GET /api/llm/status`：前端显示 LLM 是否配置；未配置时规则链路仍可用。
- `POST /api/v2/human-approval`：把 `HumanApproved / HumanRejected` 人工确认节点写入 workflow trace。
- `docs/prompts/lead_parse_v1.md`：Lead Parse prompt 契约，约束模型只做结构化抽取，不推荐产品、不算价格。
- `llm_client.py`：统一 LLM 调用、JSON parse、Pydantic 校验、一次修复重试、调用日志。
- `POST /api/v2/risk-check` + `RiskCheckResultJSON`：私家车未确认、导游漏报价、avoid 约束、老人出行节奏等风险。
- `/api/v2/full_chain` 接入 `risk_check`，一键链路返回报价 + 行程 + 人工复核提示。
- `workflow_logger.py`：记录 `LeadParsed / ProductMatched / CostCalculated / ItineraryGenerated / RiskChecked` 节点。

### 评测样例与脚本（非 LLM 环节，确定性）

- Product Match：`eval_cases/product_match_cases.json` 12 条 / `scripts/eval_product_match.py` → [product_match_eval_latest.md](docs/test_reports/product_match_eval_latest.md)
- Pricing：`eval_cases/pricing_cases.json` 5 条 / `scripts/eval_pricing.py` → [pricing_eval_latest.md](docs/test_reports/pricing_eval_latest.md)
- Risk Check：`eval_cases/risk_check_cases.json` 6 条 / `scripts/eval_risk_check.py` → [risk_check_eval_latest.md](docs/test_reports/risk_check_eval_latest.md)
- Delivery Composer：`POST /api/v2/delivery-compose` + `DeliveryDraftJSON`（销售邮件草稿，不改产品和价格）/ `scripts/eval_delivery_compose.py` → [delivery_compose_eval_latest.md](docs/test_reports/delivery_compose_eval_latest.md)

### 标准产品匹配链路（已稳定）

- 仅保留 v2 API，v1 与 Coze 集成已移除。
- Streamlit Web UI（`streamlit_app.py`）：标准行程生成 / 上海半定制路线 / 付款管理三个 Tab。
- `/api/v2/full_chain` 一键链路：product-match → pricing → Markdown（day_plans + Highlights + 报价表）。
- 供应商付款管理看板：三列 Kanban（待处理/已支付/已存档），支持筛选搜索与状态流转。
- 多城市端到端回归测试通过（10/10 城市）。

### 引擎命名与代码对齐（可信度修复）

- `generated_by` 统一 `"agent_1_product_matcher"` → `"product_matcher"`。
- 早期 4 份「Agent copilot」设计稿归档至 `docs/prompts/archive_agent_designs_2026/`（未接入运行时）。
- 新建 [docs/architecture.md](docs/architecture.md) 作为现行运行时架构的唯一真相源。

### 一键链路计时（诚实化）

- `scripts/time_full_chain.py` 实测确定性全链路耗时与剩余人工复核项：确定性链 in-process **mean 1.5ms**；LLM 单次解析 median ≈ 25s / mean ≈ 30s（真实日志）；旧人工 ~30min/单明确标注**自估、非实测**，未测量的"5 分钟"口径撤销。见 [time_trial.md](docs/test_reports/time_trial.md)。

## 更早

历史变更见 git 提交记录（`git log`），本文件从 2026-09-07 起维护。
