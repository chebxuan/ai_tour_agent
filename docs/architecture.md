# 系统架构（真相源 / Source of Truth）

> 本文档是**现行运行时架构**的唯一权威说明。所有"系统能做什么"的表述都应能在这份文档、
> 对应代码路径、以及 `docs/test_reports/` 下的真实评测报告里找到产物。
> 早期按「Agent」措辞撰写的设计稿已归档，见
> [`docs/prompts/archive_agent_designs_2026/README.md`](prompts/archive_agent_designs_2026/README.md)，
> 不参与运行时，也不代表当前能力。

## 一句话

把"客户自由文本 → 结构化交付物"拆成两步：**LLM 只负责自然语言结构化抽取**
（客户文本 → `LeadJSON`），**其余环节全部是确定性规则引擎**（产品匹配、报价、行程渲染、风险检查、
交付草稿）。这样报价/产品不会被模型编造，中间对象可评测、可审计、可回放。

## 端到端 Workflow

```text
                       ┌─────────────────────────────────────────────┐
  客户自由文本          │  LLM（唯一自然语言环节）                       │
  (email/whatsapp/…) ─▶│  llm_client.parse_lead_text()               │
                       │  prompt = docs/prompts/lead_parse_vX.md      │
                       │  输出经 JSON parse + Pydantic(LeadJSON) 校验   │
                       │  + 一次修复重试；调用全量落 logs/llm_calls.jsonl│
                       └──────────────────────┬──────────────────────┘
                                              ▼ LeadJSON
                       ┌─────────────────────────────────────────────┐
                       │  确定性引擎链（无 LLM）                       │
                       │  product match → pricing → risk → itinerary  │
                       │  → delivery draft                            │
                       └──────────────────────┬──────────────────────┘
                                              ▼
                        CandidateProductsJSON → PricingResultJSON
                        → RiskCheckResultJSON → Markdown 行程单 → DeliveryDraftJSON
```

## 各环节：LLM vs 规则、落地状态、评测

| 环节 | 运行时实现（文件/函数） | 类型 | 评测 |
|------|------------------------|------|------|
| 客户文本 → `LeadJSON` | `llm_client.parse_lead_text()` | **LLM（Structured Output 抽取）** | 字段级准确率 v1 **75.93%**（205/270）→ v2 **97.78%**（264/270）：[eval_v1](test_reports/lead_parse_eval_v1.md)、[eval_v2](test_reports/lead_parse_eval_v2.md)；坏例分类：[lead_parse_bad_cases.md](test_reports/lead_parse_bad_cases.md) |
| `LeadJSON` → 候选产品 | `engines/product_engine.py` / `api_main.build_candidates_from_lead()` | 确定性规则 | [product_match_eval_latest.md](test_reports/product_match_eval_latest.md) |
| 报价 | `engines/cost_engine.py` `calculate_total_cost()` | 确定性成本库 | [pricing_eval_latest.md](test_reports/pricing_eval_latest.md) |
| 风险检查 | `engines/risk_check_engine.py` `check_workflow_risks()` | 确定性规则 | [risk_check_eval_latest.md](test_reports/risk_check_eval_latest.md) |
| 行程 Markdown | `format_itinerary_markdown()`（读 day_plans + Highlights） | 确定性渲染 | 端到端：[test_multi_city.py](../test_multi_city.py)、[test_custom_route_shanghai.py](../test_custom_route_shanghai.py) |
| 销售邮件草稿 | `engines/delivery_composer.py` `compose_delivery_draft()` | 确定性模板 | [delivery_compose_eval_latest.md](test_reports/delivery_compose_eval_latest.md) |
| 半定制路线（上海 MVP） | `engines/custom_route_engine.py` | 确定性规则 | [custom_route_mvp.md](custom_route_mvp.md) + matrix 测试 |
| 一键链路（含计时） | `api_main.run_full_chain_for_lead()` | 确定性链 | [time_trial.md](test_reports/time_trial.md) |

## 唯一的 LLM 环节：Lead Parse

- 目的：把非结构化客户文本转成 `LeadJSON`；**prompt 明确禁止**该步骤推荐产品 / 算价格 / 写行程。
- 运行时：`llm_client.py`。JSON 输出 → `parse_json_output` → `LeadJSON.model_validate`；
  失败则用一次"修复重试"（`_build_fix_prompt`），仍失败即报错（不静默丢字段）。
- 每次调用写入 `logs/llm_calls.jsonl`：prompt_version / model / tokens / latency_ms / success /
  error_type / retry_used。该日志**只存 token/字符计数，不存客户原文与输出正文**（`input_chars` /
  `output_chars` 为长度而非内容，见 `llm_client.py` 的 `log_record`），本身已匿名；但因
  `*.jsonl` 被 `.gitignore` 屏蔽无法随仓库提交，可提交证据节录见
  [`docs/AI_EVIDENCE_llm_log_excerpt.md`](AI_EVIDENCE_llm_log_excerpt.md)。
- 配置：走 OpenAI 兼容端点（本仓库实测为 DashScope `OPENAI_BASE_URL`），模型名读 `OPENAI_MODEL`
  （实测可用模型见 [readme](../readme.md) `.env` 示例）。模型名随 `.env` 而定，不硬编码进代码语义。
- 迭代：prompt 版本化（`docs/prompts/lead_parse_v1.md` → `v2`），eval 脚本用 `--prompt-version` 复跑，
  坏例驱动修订，`## Changes vs vX` 记录差异。v1 与 v2 报告同源可比。
- **运行时默认 `lead_parse_v2`**（`llm_client.parse_lead_text` 签名默认值，2026-09-08 起）：live 接口
  `/api/lead/parse`、`/api/v2/lead-text-full-chain` 未显式传版本即用 v2（97.78%）。eval 脚本 CLI 默认仍为
  v1，供复现 v1 基线；两处命令都显式带 `--prompt-version` 保证可比。

## `generated_by` 命名的约定

早期把每个环节称作 `agent_N_*`，但运行时这些环节是确定性代码，`generated_by` 字符串却不一致地
写成 `agent_1_product_matcher`，造成"文档说 Agent、代码没有"的信任风险。现已统一为**引擎名**：

- `generated_by="product_matcher"`（`schemas.py` `CandidateProductsJSON`、`api_main.py`）
- `RiskCheckResultJSON.generated_by="risk_check_tool"`、`DeliveryDraftJSON.generated_by="delivery_composer"`
  （这两个本来就不含 agent 字样）

## 数据层（四层治理）

产品真源 `product_library.csv` → `products.normalized.json`（day_plans + item_codes）；
服务目录 `services/*.csv` → 按城市成本库 `mashes/*.csv`（运行时真源）。
原则：**优先修源数据，不用 runtime alias 掩盖数据问题**。

## 现状声明纪律

- 凡写"评测/准确率/耗时"都必须指向可复现产物：`docs/test_reports/` 下的报告或
  `logs/`（运行证据）。
- 未实测的叙述（如旧人工流程耗时）只在 [time_trial.md](test_reports/time_trial.md) 中**明确标注"自估、非实测"**。
