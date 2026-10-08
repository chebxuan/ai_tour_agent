# Archive: Agent Design Docs (2026)

这 4 份文档是早期按「Agent copilot」构思的**设计稿**，标注运行时应由各自引擎产出。
它们**不是当前运行时实现**，也与现行的确定性引擎架构不一致：

| 归档文件 | 曾经声称 | 现行运行时 |
|----------|----------|-----------|
| `agent_1_product_matcher.md` | 由 `agent_1_product_matcher` 生成候选产品 | `backend/app/main.py` / `build_candidates_from_lead`（确定性规则，`generated_by="product_matcher"`） |
| `agent_2_pricing_copilot.md` | 由 `agent_2_pricing_copilot` 计算价格 | `backend/app/engines/cost_engine.py`（确定性成本库报价） |
| `agent_3_plan_structurer.md` | 由 `agent_3_plan_structurer` 生成行程骨架 | 对应模块已删除（行程骨架由产品库 `day_plans` 数据 + `format_itinerary_markdown()` 确定性渲染） |
| `agent_4_delivery_composer.md` | 由 `agent_4_delivery_composer` 生成交付草稿 | `backend/app/engines/delivery_composer.py`（确定性邮件草稿模板，不改价格/产品） |

**现行架构的唯一真相源**见 [`docs/architecture.md`](../../architecture.md)。

这些文档保留为历史设计稿，只用于追溯思路，不参与运行时，也不应被当作当前能力声明。
