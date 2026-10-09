# 文档索引

当前入口是根目录 [readme.md](../readme.md)。按用途查阅，历史材料不作为当前操作步骤。

| 文档 | 用途 |
|---|---|
| [目录说明](project-structure.md) | 新目录职责、迁移对照与保留文件 |
| [架构说明](architecture.md) | 当前业务链路与实现边界 |
| [前端开发流程](frontend-guide.md) | 下一阶段创建 Next.js、开发页面与阶段检查 |
| [运营使用说明](operations-guide.md) | 现有 Streamlit 询单、报价与付款流程 |
| [数据说明](../data/README.md) | 数据来源、运行输入、私有存储与维护 |
| [数据库使用说明](database-guide.md) | 本地 PostgreSQL 启停、查看、改价、文案、供应商、报价快照及备份恢复 |
| [部署说明](deployment-guide.md) | 全站 Docker Compose、生产配置、域名 HTTPS、咨询查看及备份恢复 |
| [路线图](roadmap.md) | 按“先前端”的顺序维护后续计划 |
| [上海半定制 MVP](custom_route_mvp.md) | 上海路线能力、数据和限制 |
| [上海路线人工复核](custom_route_human_review.md) | 场景与复核模板 |

## 验证与历史

- [目录整理验证](test_reports/organization_20261007.md)：本次迁移与已有业务基线的对比。
- `test_reports/`：有效评测、基线对比和性能证据；有日期的旧运行报告位于 `test_reports/archive/`。
- [LLM 调用历史证据](AI_EVIDENCE_llm_log_excerpt.md)：保留原有采样口径，本次未重跑外部 LLM。
- [整理前分析](project-analysis-2026-10-07.md)：整理前快照，不作为新目录导航。
- `history/`：项目演进与工作日志。
- `archive/`：旧操作手册、旧部署教程、旧待办和设计稿，均标注历史状态。
- [参考材料](../references/README.md)：业务材料、个人作品集与本地私人资料。

运行提示词属于后端资源，位于 [`backend/app/resources/prompts/`](../backend/app/resources/prompts/)，不再混入说明文档。
