> 历史归档：保留原有内容与当时口径。当前开发与使用方式见 [文档索引](../README.md)。

# Next AI Workflow Upgrades

This document tracks the next practical upgrades for Hexa Blueprint as an AI workflow project.

## P0 — Demo Reliability

Completed:

- Lead Parse eval set expanded to 25 seed cases.
- Product Match eval added with 12 seed cases and a latest sample report.
- Pricing eval added with 5 seed cases and a latest sample report.
- Risk Check eval added with 6 seed cases and a latest sample report.
- Delivery Composer added with 1 seed eval case and a latest sample report.

1. Expand Lead Parse eval cases from 25 to 50.
   - Current coverage includes family, senior, optional car, missing city, budget, hotel preference, airport transfer, dietary notes, and multi-city requests.
   - Next coverage should add visa, payment constraints, supplier constraints, Chinese/English mixed input, unclear dates, and refusal/handoff cases.
   - Add bad case tags: `missing_field`, `wrong_type`, `over_inference`, `tag_normalization`, `optional_misread`.

2. Add a generated sample eval report.
   - Run `python3 scripts/eval_lead_parse.py` after configuring `OPENAI_API_KEY`.
   - Keep one representative report under `docs/test_reports/`.

3. Add Streamlit error states for LLM configuration.
   - If `OPENAI_API_KEY` is missing, show a friendly message explaining that form-based workflow still works.

## P1 — Workflow Quality

4. Expand product-match evaluation.
   - Current seed cases cover 10 cities, exact duration, near duration, missing city, and family travel.
   - Add more cases for avoid constraints, weak interest fit, multi-city requests, and optional item warnings.
   - Metrics: top-1 accuracy, top-3 accuracy, warning coverage.

5. Expand risk-check evaluation.
   - Current seed cases cover optional car, pricing gaps, avoid constraints, senior pace risk, and a clean case.
   - Add route-specific cases after custom route output is normalized.
   - Metrics: issue recall, false positive count.

6. Improve tag normalization.
   - Map customer phrases like `quiet neighborhoods`, `not rushed`, `local food` to stable tags such as `local_life`, `slow_pace`, `local_food`.
   - Keep raw customer wording in `source.raw_text`.

## P2 — Product Experience

7. Add human approval state.
   - Add an explicit `HumanApproved` node after risk check.
   - Store approval status in workflow trace.

8. Expand customer-facing delivery composer.
   - Current version generates a deterministic editable English email from structured workflow results.
   - Add more eval cases for missing pricing, blocking risk issues, family travel, and multi-city trips.
   - Rule: never change product IDs or prices.

9. Export itinerary to PDF or DOCX.
   - Keep Markdown as the source.
   - Add rendering only after the workflow output is stable.

## Interview Talking Points

- This project uses a workflow-style agent rather than a fully autonomous agent.
- LLM is used for natural language parsing; pricing and product matching remain deterministic.
- Every major step has structured input/output and can be logged, tested, and reviewed.
- Risk check and human review are first-class workflow nodes, not afterthoughts.
