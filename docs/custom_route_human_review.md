# Custom Route Human Review — 上海半定制路线人工审核

## 目的

人工审核不是重复看系统能不能运行，而是判断路线是否真的适合发给客户、是否可报价、是否可交付。  
建议每轮选 6 个真实感 lead，生成路线后由运营人员按统一标准打分。

## 审核流程

1. 准备客户需求：用一句英文/中文模拟真实询单。
2. 在 Streamlit 或 `/api/v2/custom-route` 输入同样参数生成路线。
3. 记录系统输出：路线节点、总时长、交通段、估算成本、风险提示、模板合规。
4. 人工审核打分：每项 1-5 分，低于 3 分必须写修改建议。
5. 标记结论：可直接发客户 / 需小改 / 需重排 / 不适合自动生成。

## 审核评分表

| 维度 | 评分标准 |
|------|----------|
| 客户匹配度 | 是否符合兴趣、人群、预算、节奏 |
| 时间合理性 | 总时长是否合理，是否留出餐食/休息/交通余量 |
| 交通顺路性 | 点位是否同区或顺路，跨区是否有必要 |
| 体验完整度 | 是否有锚点、过渡、休息/餐饮、亮点 |
| 商业可交付 | 是否能报价，是否需要供应商/预约/导游 |
| 风险透明度 | 系统是否提示天气、拥挤、预约、体力等风险 |
| 英文可发送度 | 输出描述是否适合海外客户理解 |

建议通过线：总分 >= 28/35，且没有单项低于 3 分。

## 6 个建议审核样例

### 1. First-time Shanghai One Day

Lead: "We are a couple visiting Shanghai for the first time. We like history, skyline views and local food, but don't want the day to feel too rushed."

参数建议：
- duration_type: `one_day`
- interests: `culture, history, photography`
- pace: `moderate`
- budget_level: `medium`
- group_type: `couple`

重点看：是否覆盖经典上海，是否过度跨区，晚间外滩/陆家嘴是否合理。

### 2. Young Couple Photo & Cafe Half Day

Lead: "We only have half a day in Shanghai and want photogenic streets, architecture and a nice cafe stop."

参数建议：
- duration_type: `half_day`
- interests: `photography, architecture, cafe`
- pace: `moderate`
- budget_level: `medium`
- group_type: `couple`

重点看：是否真的像 City Walk，而不是普通景点拼接。

### 3. Family Rainy Day One Day

Lead: "We are a family with one child. It may rain tomorrow, so we prefer indoor places and easy transport."

参数建议：
- duration_type: `one_day`
- interests: `family, museum, interactive`
- pace: `relaxed`
- budget_level: `medium`
- group_type: `family`
- rainy_day: `true`
- need_private_car: `true`

重点看：户外比例、孩子是否会无聊、交通是否少折腾。

### 4. Senior Slow Culture Day

Lead: "My parents are in their 60s. They enjoy history and old Shanghai architecture, but cannot walk too much."

参数建议：
- duration_type: `one_day`
- interests: `history, literature, garden`
- pace: `relaxed`
- budget_level: `flexible`
- group_type: `senior`
- need_private_car: `true`

重点看：步行强度、休息点、是否有太多台阶/拥挤街区。

### 5. Budget Solo Half Day

Lead: "I am traveling solo on a low budget. I want free or low-cost places with good photos and local street life."

参数建议：
- duration_type: `half_day`
- interests: `street life, photography, architecture`
- pace: `moderate`
- budget_level: `low`
- group_type: `solo`

重点看：是否控制成本，是否仍有体验亮点。

### 6. Premium Romantic Evening

Lead: "We are a couple celebrating an anniversary. We want a romantic Shanghai evening with skyline views, dinner and maybe a cruise."

参数建议：
- duration_type: `half_day`
- interests: `romantic, night view, dining`
- pace: `relaxed`
- budget_level: `flexible`
- group_type: `couple`

重点看：是否有商业升单空间，晚餐/游船/酒吧顺序是否合理。

## 审核记录模板

| 字段 | 内容 |
|------|------|
| Review ID | SH-REV-001 |
| Lead | 客户原始需求 |
| Input Params | duration/interests/pace/budget/group/rain/car/guide |
| Generated Route | Unit sequence |
| Total Time | activity + transit + buffer |
| Estimated Cost | RMB |
| Main Risks | 风险提示 |
| Score | 客户匹配/时间/交通/体验/商业/风险/英文 |
| Decision | 可直接发客户 / 需小改 / 需重排 / 不适合 |
| Manual Fix | 需要替换/删除/新增的节点 |
| Data Action | 需要补充的 POI、交通边、成本编码或模板 |

## 如何把审核结果反哺系统

- 如果路线不顺路：补 `shanghai_transport_edges.csv` 或调整模板 `preferred_areas`。
- 如果兴趣不匹配：补体验单元标签，或调整 `customer_profile_tags.csv` 的 positive/negative tags。
- 如果总价不准：补 `cost_item_code`，必要时先在上海成本库新增服务项目。
- 如果同类路线重复太多：增加同区域替代 POI，或在模板里设置不同的 route_story_angle。
- 如果风险没提示：补 `operational_risk`、`booking_required`、`rainy_day_friendly`、`elderly_friendly` 字段。
