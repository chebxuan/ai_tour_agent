# AI 证据：真实 LLM 调用日志节录（可提交版）

> **为什么有这个文件**：原始调用日志 `logs/llm_calls.jsonl` 因 `*.jsonl` 被 `.gitignore` 屏蔽，无法随仓库提交。本文件是从该日志摘出的**匿名化**证据节录，用于在代码库内自证「LLM 结构化抽取环节有真实运行记录」。

- 生成日期：2026-09-07（日志累计至 2026-09-08T04:46Z）
- 数据源：`logs/llm_calls.jsonl`（256 条，累计 = 冒烟 + 开发期 + 两轮全量 eval）
- 模型：`qwen3.8-27b`（DashScope OpenAI 兼容端点，base_url 与 key 来自 `.env`）
- 任务：全部为 `lead_parse`（客户文本 → LeadJSON 结构化抽取）

## 1. 日志记录了哪些字段（已匿名化）

每条调用记录**只存**这些键，**不存**客户原文、也不存模型输出正文——只存 token/字符计数，因此整份日志本身就是匿名的：

```
request_id, task_name, prompt_version, model_name, input_chars,
success, error_type, created_at, input_tokens, output_tokens,
output_chars, retry_used, latency_ms
```

## 2. 累计统计（256 条）

| 维度 | 值 |
|---|---|
| 总记录数 | 256 |
| prompt_version 分布 | `lead_parse_v1` = 156，`lead_parse_v2` = 100 |
| 调用成功 | 243 / 256 |
| 失败（全部为基础设施 `ReadTimeout`） | 13（均被 harness 单次重试兜住） |
| 记录为「重试后成功」 | 17 |
| 延迟 `latency_ms` | median ≈ 24.6s，mean ≈ 30.3s，min 11.9s，max 138.0s |
| input_tokens | median ≈ 1166，mean ≈ 1913 |
| output_tokens | median ≈ 1344，mean ≈ 1580 |

关键事实：**整条链路只有这一个 LLM 调用**，而它单次 median ~25s——这是「端到端耗时」的主要来源（确定性环节合计 ~ms，见 `docs/test_reports/time_trial.md`）。日志里 13 次 `ReadTimeout` 与 138s 的长尾说明真实端点有偶发慢响应，这与 eval 报告的 retry 逻辑一致。

## 3. 两轮权威全量 run（字段准确率来自这两轮）

| run | 窗口（日志 UTC） | 成功/调用 | 字段准确率 | 报告 |
|---|---|---|---|---|
| v1 全量 50 条 | `2026-09-08T04:15+` | 50 成功 + 1 次被 retry 吸收的失败 | 75.93%（205/270） | `docs/test_reports/lead_parse_eval_v1.md` |
| v2 全量 50 条 | `2026-09-08T04:15+` | 50 成功，0 未吸收失败 | 97.78%（264/270） | `docs/test_reports/lead_parse_eval_v2.md` |

注：上表「调用成功」指 LLM 成功返回并解析成 LeadJSON；v1 准确率 75.93% 表示其中 48 个 case 存在**字段级**断言失败（模型成功返回但字段不对）——两件事不矛盾。失败模式逐条见 `docs/test_reports/lead_parse_bad_cases.md`。

## 4. 摘录 10 条（v2 全量 run，匿名化字段）

| created_at | prompt_version | input_tok | output_tok | retry_used | latency_ms |
|---|---|---|---|---|---|
| 2026-09-08T04:30:49Z | lead_parse_v2 | 3122 | 1554 | – | 27916 |
| 2026-09-08T04:31:17Z | lead_parse_v2 | 3126 | 1512 | – | 26181 |
| 2026-09-08T04:31:43Z | lead_parse_v2 | 3123 | 2392 | – | 42682 |
| 2026-09-08T04:32:26Z | lead_parse_v2 | 3126 | 2517 | – | 43265 |
| 2026-09-08T04:33:09Z | lead_parse_v2 | 3125 | 1324 | – | 22716 |
| 2026-09-08T04:33:32Z | lead_parse_v2 | 3130 | 1324 | – | 21502 |
| 2026-09-08T04:33:53Z | lead_parse_v2 | 3141 | 1074 | – | 17610 |
| 2026-09-08T04:34:11Z | lead_parse_v2 | 3132 | 1400 | – | 23178 |
| 2026-09-08T04:34:34Z | lead_parse_v2 | 3132 | 1166 | – | 19727 |
| 2026-09-08T04:34:54Z | lead_parse_v2 | 3137 | 1535 | – | 28402 |

两条原始日志（真实格式，便于核对）：

```json
{"request_id":"req_878fb0d505","created_at":"2026-09-08T04:30:49Z","prompt_version":"lead_parse_v2","model_name":"qwen3.8-27b","success":true,"input_tokens":3122,"output_tokens":1554,"retry_used":null,"latency_ms":27916}
{"request_id":"req_2d92cb7713","created_at":"2026-09-08T04:31:17Z","prompt_version":"lead_parse_v2","model_name":"qwen3.8-27b","success":true,"input_tokens":3126,"output_tokens":1512,"retry_used":null,"latency_ms":26181}
```

## 5. 复现命令

```bash
set -a && . ./.env && set +a
# 全量 v1
python3 scripts/eval_lead_parse.py --prompt-version lead_parse_v1 --report docs/test_reports/lead_parse_eval_v1.md --out-json docs/test_reports/lead_parse_eval_v1_full.json
# 全量 v2
python3 scripts/eval_lead_parse.py --prompt-version lead_parse_v2 --report docs/test_reports/lead_parse_eval_v2.md --out-json docs/test_reports/lead_parse_eval_v2_full.json
```

每次运行会追加写入 `logs/llm_calls.jsonl`。校验日志是否真实：重新跑一次任意子集，`wc -l logs/llm_calls.jsonl` 应增加。
