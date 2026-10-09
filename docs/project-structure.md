# 目录说明与整理记录

更新：2026-10-09。下方迁移记录保留 2026-10-07 整理口径；当前已接入旅行 v3 接口与本地 PostgreSQL，数据库维护方法见 [数据库使用说明](database-guide.md)。

```text
项目根目录/
├── readme.md                     # 启动和文档入口，沿用 Git 已跟踪的文件名
├── AGENTS.md                     # 后续开发长期规则
├── .env.example                  # 配置模板，不含真实密钥
├── backend/
│   ├── app/
│   │   ├── main.py               # 现有 FastAPI 实现
│   │   ├── schemas.py
│   │   ├── llm_client.py
│   │   ├── workflow_logger.py
│   │   ├── core/paths.py         # 稳定的仓库根路径
│   │   ├── engines/              # 活跃业务规则
│   │   ├── routers/              # 旅行网站 v3 接口
│   │   ├── services/             # 产品、Menu、计费范围与销售报价
│   │   ├── storage/              # PostgreSQL 连接、读取、导入、维护与 migrations/
│   │   └── resources/prompts/    # Lead Parse v1/v2
│   ├── requirements.txt
│   └── requirements-dev.txt
├── data/                         # 运行数据与产品源数据
├── tests/                        # 原有回归/场景脚本
├── evals/                        # 评测脚本与 cases/
├── scripts/                      # 数据维护和本地检查
├── legacy/                       # 原 Streamlit、CLI、历史工具
├── frontend/                     # Next.js 两页旅客 UI；真实预览和销售报价接口
├── deploy/                       # 全站 Compose、运行入口、配置、发布包及备份
├── .local/database/              # 忽略的本地数据库、备份、核对报告
├── experiments/                  # 城市叙事、POI 实验
├── references/                   # 业务参考、个人作品集、私人材料
├── docs/                         # 当前说明、历史和评测
├── api_main.py                   # 旧后端启动入口的兼容文件
├── streamlit_app.py              # 旧 Streamlit 启动入口的兼容文件
├── Dockerfile / render.yaml      # 现有后端打包配置
└── requirements.txt              # 后端与旧界面的兼容安装入口
```

新前端已创建于 `frontend/`，已联调预览和报价。`.venv/`、`logs/`、`.local/`、`.local-backups/` 是本地环境或运行产物，不进入 Git；数据库连接配置 `.env.database.local` 同样忽略。

## 主要位置对照

| 原位置 | 现在的位置 |
|---|---|
| `api_main.py` 的实现 | `backend/app/main.py`；原文件变为兼容入口 |
| `schemas.py`、`llm_client.py`、`workflow_logger.py` | `backend/app/` |
| `engines/` 活跃规则 | `backend/app/engines/` |
| `streamlit_app.py` 的实现 | `legacy/streamlit_app.py`；原文件按每次页面重跑执行此实现 |
| `cli_app.py`、`survey_architect.py` | `legacy/` |
| `test_*.py` | `tests/` |
| `scripts/eval_*.py`、`time_full_chain.py` | `evals/` |
| `eval_cases/` | `evals/cases/` |
| `engines/merge_city_products.py` | `scripts/merge_city_products.py` |
| `docs/prompts/lead_parse_v1/v2.md` | `backend/app/resources/prompts/` |
| `projects 2/` | `experiments/city_narrative/` |
| `engines/narrative_engine.py` | `experiments/city_narrative/narrative_engine.py` |
| `engines/poi_registry.py`、`scripts/generate_city_pois.py` | `experiments/poi_planning/` |
| `assets/maps/` | `experiments/city_narrative/outputs/maps/` |
| `portfolio-site/` | `references/portfolio/site/` |
| `作品集/` | `references/portfolio/case-study/` |
| `资料/` | `references/private/` |
| `kanban/` | `references/private/payment-history/` |
| `hexa/` 工作指引 | `references/business/operations-guide.md` |
| `项目路径.md` | `docs/history/project-evolution.md` |
| `上海之行.md` | `references/business/shanghai-itinerary.md` |
| 旧操作手册、部署教程与 AI 待办 | `docs/archive/` |
| 带日期的旧规则评测报告 | `docs/test_reports/archive/` |
| 原始 PDF、Numbers、未使用的大交通源表 | `references/private/product-source-documents/` |
| 一次性修价脚本 | `legacy/tools/fix_price_issues.py`，不自动执行 |

目录迁移同步修正了导入、提示词读取、成本库路径、评测样例路径与数据重建输入。旧启动命令仍可使用；新文档推荐直接使用明确的包入口。

## 重复与历史材料

两组文件在字节内容完全相同的前提下合并：

- 客户信息表 PDF：保留于 `references/private/business/client-information-form.pdf`。
- 路书模板：保留于 `references/private/business/itinerary-template.md`。

原 `kanban/payments.json` 与当前 `data/payments.json` 内容不同，前者保存为旧资料，后者仍是运行存储，没有合并或覆盖。

保留有意义的 v1/v2 评测与时间基线。历史文档只调整链接和增加状态说明，不将历史描述改写成新版本事实。四份规则 `*_eval_latest.md` 在本轮验证后更新为本次运行结果。

## 本地备份与后续管理

整理前的文本和较小文件备份、原始哈希与逐文件迁移表保存在 `.local-backups/before-organization-2026-10-07/`，Git 已忽略该目录。原始大文件通过移动保留。备用 `venv/` 与根目录缓存也移到本地备份，当前 `.venv/` 保持原位。

用户在本次开始前已有的删除记录没有恢复，未提交代码与资料按当前文件内容迁移。本轮没有执行 Git 暂存、提交或推送。

后续开发先阅读 [前端流程](frontend-guide.md)；当前计划统一维护在 [路线图](roadmap.md)。
