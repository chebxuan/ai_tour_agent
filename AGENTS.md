# AI Travel Ops Copilot 开发约定

## 当前阶段

- 已有 FastAPI 与 Streamlit 原型；新前端计划使用 Next.js App Router、JavaScript/JSX、普通 CSS 和 animejs。
- 用户选择的顺序：目录/文档整理 → 前端页面 → 接口联调与后端深化 → 上线。
- 新前端创建在 `frontend/`，不覆盖根目录，不复用个人作品集站点作为业务前端。
- 网站最终定位尚未确定，先按具体任务实现页面，不自行扩大为完整平台。
- 2026-10-09：分支与销售报价已联调；本地 PostgreSQL 已导入并启用，当前操作见 `docs/database-guide.md`。运营网页登录、维护页面与生产部署尚未完成。
- 02 联系表单与咨询存储已接入；运营暂用 `maintain_database.py enquiries/enquiry` 查看。没有自动邮件通知或 `/ops` 网页，不将咨询接收说成预订确认。

## 工程边界

- 后端实现位于 `backend/app/`，启动入口是 `backend.app.main:app`。
- 根目录 `api_main.py` 和 `streamlit_app.py` 是旧启动命令的兼容入口。
- 旧 UI/CLI 位于 `legacy/`；实验位于 `experiments/`；个人材料位于 `references/`。
- 运行提示词在 `backend/app/resources/prompts/`。历史 Agent 设计在 `docs/archive/`，不能当作已实现功能。
- 测试在 `tests/`，评测代码与样例在 `evals/`，数据维护脚本在 `scripts/`。
- 仓库根路径使用 `backend.app.core.paths.ROOT`，不要依赖启动时的工作目录。

## 业务与数据

- LLM 负责结构化询单抽取，产品匹配、成本计算与风险检查保持确定性。
- 产品源数据为 `data/products/product_library.csv`，成本运行数据为 `data/products/services/mashes/`。
- 数据库模式下，上述文件保留首次导入来源和文件模式基线；标准产品运行主数据使用 PostgreSQL，不用修改文件代替数据库维护，也不长期双写。成本改价必须新增版本并保留审计；已应用 SQL 迁移文件不改写。
- 本地数据库与备份在忽略的 `.local/database/`，凭据在 `.env.database.local`。数据库故障返回不可用，不自动退回旧文件金额；不得把配置、数据目录或备份放入前端或镜像。
- 咨询写入只用 `TRAVEL_INTAKE_DATABASE_URL` 的受限账户，不在请求中使用维护账户。预览/报价快照需核验签名，金额由服务端复核；保留旧展示金额，重复提交去重，成功回执须在事务提交之后返回。
- `data/custom/` 为上海半定制必需输入，不能被整体忽略或随意改动。
- 成本总额不等同于具有利润规则的最终销售报价；改定价必须单独说明并验证。
- `data/payments.json` 是现行可写存储，旧付款材料在 `references/private/payment-history/`；不得覆盖或自动合并。
- 不把客户、供应商私有材料和真实密钥复制到 `frontend/public/`。

## 开发与验证

- 先阅读 `readme.md`、`docs/project-structure.md` 和与任务相关的代码。
- 保留用户现有未提交变动。目录迁移同步修改导入、路径和文档链接。
- 后端路径或规则变化后运行 `.venv/bin/python -B scripts/verify_project.py`。
- 需要外部 LLM 的评测单独运行，不把付费调用混入默认本地检查。
- 默认 `verify_project.py` 显式使用文件模式；首次导入另跑 `verify_database.py` 核对。数据库测试需 `RUN_DATABASE_TESTS=1`，真实维护后改用独立基线测试库，不覆盖业务数据来通过旧金额断言。
- 前端创建后在开发服务器中检查页面，阶段完成时执行 lint 和生产构建，并报告真实结果。
- 若 Next.js 生成自己的 `frontend/AGENTS.md`，阅读其本地版本文档约定并补充项目规则。
- 不把密钥放入 `NEXT_PUBLIC_*`；新前端先使用明确标注的模拟数据，接口接入另行处理。

## 文档

- `readme.md` 是启动与导航入口，`docs/architecture.md` 是当前架构说明。
- 当前计划只维护 `docs/roadmap.md`；过时说明进入 `docs/archive/`。
- 历史证据和版本对比保留日期与样本口径，不把它们当作本次重新验证的结果。
- 启动命令从仓库根目录执行，说明改动、验证和未验证限制。
