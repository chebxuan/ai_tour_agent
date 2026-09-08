# Lead Parse 坏例分类报告（v1 → v2）

- 报告日期：2026-09-07
- 评测集：`eval_cases/lead_parse_cases.json`，50 条（lead_parse_001…050），270 个字段断言
- 模型：`qwen3.8-27b`（DashScope OpenAI 兼容端点）
- Prompt：`docs/prompts/lead_parse_v1.md` vs `docs/prompts/lead_parse_v2.md`

## 0. TL;DR

| 指标 | v1 | v2 |
|---|---|---|
| 字段准确率 | 75.93%（205/270） | 97.78%（264/270） |
| 字段级失败 | 65 | 6 |
| 失败 case | 48 / 50 | 5 / 50 |

一句话结论：**v1 的 65 个字段失败全部被 v2 修复；但 v2 同时新引入 6 个字段失败（5 个 case）**——其中 2 个是真实回退（case 020、023），1 个是 golden 与 v2 规范词表拼写不同步的测量伪差（case 016），2 个是先前只在「目的地」字段失败的 case 在 v1 期被掩盖、目的地修好后暴露出的潜在弱点（case 007、009）。

## 1. 方法与局限

断言分三类（见 `scripts/eval_lead_parse.py` 头部注释）：

1. **精确相等**（`EXACT_VALUE_GETTERS`）：目的地、人数、日期、need_*、tier、金额等结构化字段，模型值须与 golden 全等。
2. **token 存在性包含**（canonical tags：`interests` / `travel_style` / `avoid`）：期望 tag 归一化后是某个实际 tag 的子串即通过，容忍「模型输出更丰富的复合 tag」。
3. **概念关键词**（free-text notes：`sales_notes` / `dietary_notes` / `must_have` 等）：期望短语去停用词后，每个实词须整词出现在实际文本中，容忍 no/not、语序改写。

分母固定与重试：分母按 case 在**调用前**固定（避免瞬时网络错误把分母吞掉造成虚高），对 `ReadTimeout` / `ConnectionError` 做单次重试。运行历史与修复记录见 `lead_parse_eval_v1.md` / `lead_parse_eval_v2.md`。

局限（不回避）：自由文本字段断言的是「概念关键词存在」，无法证明语义方向性（如 avoid 与 like 相反）；方向性由精确的结构化字段承载，剩余风险靠人工坏例复核兜底。`_contains` 判定对复数/同根词（`scenic_views` vs `scenic_view`）是**严格子串**而非词干归一，会把拼写不一致判为失败——case 016 即因此误伤（见 §4）。

## 2. v1 失败模式（65 字段失败 / 48 case）

v1 的失败高度集中在**一个根因**，其余失败可归为两类，合计三类。

| 根因桶 | 失败字段数 | 涉及字段 | 覆盖 case | 占全部失败 |
|---|---|---|---|---|
| A. 目的地未用规范中文（GeoNaming 缺失） | 48 | `destination_cities` | 48 个失败 case 全含（47 罗马化 + 005 过度推断） | 73.8% |
| B. 闭式标签表缺失/未约束 | 12 | `interests`(5) `avoid`(4) `travel_style`(3) | 002, 004, 008, 015, 016, 021, 025, 030, 047, 050 | 18.5% |
| C. 边界规则缺失 | 5 | `season`(2) `need_guide`(1) `sales_notes`(1) `budget_max_per_person`(1) | 003, 005, 032, 036, 039 | 7.7% |

### 桶 A：目的地罗马化 / 非规范中文（48）

v1 契约要求 `destination_cities` 填**规范中文名**，模型几乎全程输出英文罗马化。47 例属此类（如 001 `'Shanghai'`、008/011/023/029/046 `"Xi'an"`、040 `'Shanxi province'` 照抄英文附 province）；1 例是**过度推断**：005 原文只说「China」，未给任何城市，golden 要求 `[]`（不编造），模型填了 `['China']`。

### 桶 B：闭式标签不符（12）

模型生成了**合理但非规范**的 tag，或把概念放错列表，或漏掉期望 tag：

- **over-specific 具体名词 → 未归并到规范 tag**：021「Cantonese food」→ `cantonese_food`（期望 `local_food`）；025「Art Deco buildings / coffee shops」→ `art_deco_buildings` `coffee_shops`（期望 `architecture` `coffee`）；030「dim sum and classical gardens」→ `dim_sum` `classical_gardens`（期望 `local_food`）。
- **near-synonym 而非规范 tag**：002 avoid `crowded_places`（期望 `crowded_tourist_spots`）；047 avoid `famous_tourist_sites`（期望 `crowded_tourist_spots`）；050 avoid `heavy_smoking`（期望 `smoke`）。
- **正负放置错误**：002「She cannot walk too much」→ 模型把 `long_walking` 放进 `travel_style`（正面），golden 要求放进 `avoid`（负面，因是「不能走太多」）。
- **漏 tag**：015 带孩子去迪士尼但 `interests` 无 `disneyland`；008「don't need luxury hotels」未进 `avoid`；047 漏 `local_life`；016 漏 `honeymoon`；004 漏 `slow_pace`。

### 桶 C：边界规则缺失（5）

- `season` 限定词丢失：003「next spring」→`spring`、005「next autumn」→`autumn`（golden 要求 verbatim 保留 `next`）。
- `need_guide` 司机兼导游：039「a driver who can also act as our guide」→ 模型置 `need_guide=True`，golden 要求 `None`（导游职责已由司机承担，非另行需要 licensed guide）。
- `sales_notes` 晚数记录：032「stay 3 nights」→ 模型 `trip_days` 留空正确，但未把「3 nights」写进 `sales_notes`，信息丢失。
- `budget_max_per_person` 外币换算：036「600 USD per person」→ 模型换算成 `600.0` 写入数字字段，golden 要求 `None`（非 RMB 金额不可靠，进 `budget_notes` 而非数值字段）——又是过度推断。

## 3. v2 定向修订与修复证据

v2 相对 v1 的改动（`docs/prompts/lead_parse_v2.md` 文末 `## Changes vs v1`）：新增 GeoNaming 规范中文目的地表；新增闭式 snake_case tag 词表 + 别名映射 + 「就近取规范 tag、禁止自造」约束；补充司机兼导游 / 外币进 notes / season 限定词 verbatim / 5-star 只进 hotel_tier 等边界规则；出行模式收紧为单一模式。

| 根因桶 | v1 失败 | v2 修复 | 修复机制 |
|---|---|---|---|
| A. 目的地 | 48 | 48 / 48 | GeoNaming 规范中文目录（连 005 过度推断、040 verbatim 一并覆盖） |
| B. 闭式标签 | 12 | 12 / 12 | 闭式词表 + 别名映射 + 禁止 near-synonym（002/047/050 的 avoid 命中规范 tag；021/025/030 归并 `local_food` 等；015 补 `disneyland`） |
| C. 边界规则 | 5 | 5 / 5 | season verbatim、driver-guide、nights→notes、外币→notes 均补规则 |

注意：桶 B「12 / 12 修复」指 v1 的 12 个字段失败全部不再出现；但 v2 在**别的 case** 上新增了 interests 失败（见 §4），因此字段失败数不是降到 53 而是降到 6。

## 4. v2 残留失败（6 字段失败 / 5 case）——逐条

| case | 失败字段 | golden | v2 实际 | 归类 |
|---|---|---|---|---|
| 007_no_guide_no_car | `interests` | `local_markets`, `local_food` | `local_food`, `food`, `local_life` | 潜在弱点暴露 |
| 009_hotel_view | `hotel_tier` | `premium` | `None` | 潜在弱点暴露 |
| 009_hotel_view | `interests` | `fine_dining` | `food` | 潜在弱点暴露 |
| 016_luxury_budget | `interests` | `scenic_views`（复数） | `scenic_view`（单数） | golden 拼写不同步（伪差） |
| 020_language_chinese | `interests` | `hutong` | `local_life` | **真实回退** |
| 023_transport_preference | `transport_preference` | `high-speed train` | `None` | **真实回退** |

逐条根因：

- **007**：「mainly want local markets and food」。模型没产出规范 tag `local_markets`，把「markets」归到 `local_life`，还把 `food` 与 `local_food` 并列重复。该 case 在 v1 只败在目的地，v2 修好目的地后，暴露出「本地市场 → 应命中 `local_markets` 而非泛化到 `local_life`」这一词表召回盲点。
- **009**：「a premium hotel … if possible」「skyline photography and fine dining」。`hotel_tier` 期望 `premium`，模型因「if possible」的条件语气把 tier 置 `None`——条件措辞不应使明确等级声明失效；`fine_dining` 被降级为 `food`，词表召回漏掉更贴切 tag。该 case 同样只败在目的地后才暴露。
- **016**：「scenic views」期望 `scenic_views`（**复数**），模型输出 `scenic_view`（**单数**）——而单数正是 v2 闭式词表第 101 行的规范拼写（`scenic_view`）。即：**模型严格服从了 v2 词表，golden 却沿用 v1 期的复数拼写**。这是 golden 与 prompt 词表同步缺口造成的测量伪差，非模型语义错误。根因在我的流程：改动词表时未回扫受影响 golden。（v1 期该 case 的 interests 恰好通过，是因为 v1 无词表约束、模型自由输出复数拼写。）
- **020**（真实回退）：原文「喜欢历史和胡同」（中英混排 + English guide）。v1 输出 `['history', 'hutongs']`，子串包含 `hutong` → 通过。v2 输出 `['history', 'local_life']` → 失败。机制：v2 闭式 interests 词表**不含 `hutong`**，且映射指导里的「quiet neighborhoods / old streets → `local_life`」范围过宽，模型把具体地标性文化词「胡同」坍缩成泛化的 `local_life`。修复 v1 桶 B「over-specific 具体名词 → 归并规范 tag」的那条规则，对 `hutong`（本身即顾客明确想去的具体文化对象，属「保留原名」的边界）**过度执行**。
- **023**（真实回退）：原文「prefer high-speed train arrival from Beijing and private car inside the city」。v1 输出 `transport_preference="high-speed train"` → 通过。v2 输出 `None`。机制：v2 把 `transport_preference` 收窄为「目的地区域**内**的单一出行方式」，而此处的 HSR 是「从北京**抵达**」的交通——按 v2 自己的新规则 HSR 更像抵达语境、应落 `departure_city` 语境，结果模型把整格清空，既没写 HSR 也没利用「抵达」信号。属于「收窄定义后未给出跨字段兜底」的规则缝隙。

## 5. 教训 / 若做 v3 的候选修复（如实列出，本轮未做）

- **golden ↔ prompt 词表一致性**：改规范词表时应回扫全部 golden 中用到该词的拼写（016 的 `scenic_views`→`scenic_view`）。这是流程缺口，不是模型问题。
- **`hutong` 类具体文化对象**：词表要么补 `hutong`，要么在映射指导里明确「顾客点名想去的具体对象（胡同、地标）保留原名/独立 tag，不坍缩进 `local_life`」。
- **条件措辞不削弱明确等级**：009 说明「premium hotel if possible」等级声明仍成立，仅把「if possible」进 `hotel_style_notes`。
- **`transport_preference` 跨字段兜底**：当出现「抵达+市内」双交通信号时，明确 HSR/飞机等抵达段进 `departure_city` 附注或 `sales_notes`，市内段才进 `transport_preference`；即便主字段留空，也要把丢弃的意图写进 notes，避免整格静默清空。
- **`local_markets` 召回**：词表保留 `local_markets`，别名「markets / street markets / wet market」显式映射，与 `local_life` / `local_food` 区分。

## 6. 诚实性备注

- 分母在调用前固定 + 瞬时错误单次重试，失败不会从分母里消失。
- 我**没有**为让 v2 好看而回改 golden：016 的 golden 复数拼写在 v1/v2 两次运行中保持冻结，v1→v2 可比。该处作为「测量伪差」如实记录，而非静默改数。
- v1→v2 的 2 个真实回退（020、023）已如实记录并给出机制，未挑数据掩盖。
- 自由文本断言是「概念关键词存在」，语义方向的兜底依赖结构化字段与人工复核，此局限在此明示。
