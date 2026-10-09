# AI Travel Ops Copilot

面向入境游询单、产品匹配、成本核算和方案交付的运营辅助项目。旅客网站使用 Next.js，后端为 FastAPI；标准产品与成本已接入本地 PostgreSQL，旧 Streamlit 界面继续保留。

## 当前能力

- AI 将客户原文转为结构化需求，保留需要人工确认的内容。
- 标准产品匹配、成本计算、风险检查和行程生成使用确定性规则。
- 标准产品库包含 21 个产品、10 个城市；上海半定制提供独立路线流程。
- 输出 Markdown 行程和邮件草稿，供人工复核。
- 供应商付款看板目前使用本地 JSON 存储。
- 标准产品、服务成本、分支与销售规则使用 PostgreSQL；本地维护命令保留成本历史、修改记录和报价快照。
- 旅客可在行程预览中提交姓名、邮箱与留言，保存咨询及行程/报价；运营可通过本地命令查看。

## 目录入口

| 目录 | 用途 |
|---|---|
| `backend/` | 现有后端和运行提示词 |
| `data/` | 产品、成本与上海路线数据 |
| `tests/`、`evals/` | 回归脚本和评测样例 |
| `scripts/` | 数据维护与本地检查 |
| `legacy/` | 旧 Streamlit、CLI 与历史工具 |
| `experiments/` | 尚未接入主 API 的实验 |
| `references/` | 业务参考、个人作品集与私人资料 |
| `docs/` | 当前说明、历史记录与评测 |

`frontend/` 已完成旅客视角的产品首页和行程定制页组件，已接入 21 个真实产品的公开路线内容，行程预览已接入后端。根目录 `api_main.py`、`streamlit_app.py` 是原启动方式的兼容入口。

## 本地启动现有原型

以下命令在仓库根目录执行。已有 `.venv/` 可直接使用；新环境先创建并安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

尚无 `.env` 时复制模板并填写配置；已有配置不要覆盖：

```bash
cp -n .env.example .env
```

后端必须设置 `API_KEY`。外部模型密钥只用于 AI 解析，手填需求与规则生成不需要外部模型。后端与旧界面使用同一服务端密钥。

启动后端：

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

另开终端，启动旧界面：

```bash
.venv/bin/python -m streamlit run streamlit_app.py
```

旧后端入口 `uvicorn api_main:app` 仍然有效。CLI 使用 `.venv/bin/python -m legacy.cli_app`。

## 本地验证

安装本地接口检查依赖并运行：

```bash
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -B scripts/verify_project.py
```

检查不调用外部模型、不修改产品库，也不写真实付款和工作流日志。覆盖已有规则评测、10 城市标准接口、上海路线场景和兼容入口；失败会返回非零退出码。

## 当前阶段：本地数据库已接入

本机数据库已初始化并切换为主数据读取来源。启动网站前先检查数据库，未运行时执行 `start`：

```bash
.venv/bin/python -B scripts/local_database.py status
.venv/bin/python -B scripts/local_database.py start
.venv/bin/python -B scripts/database.py status
```

已经运行时不要重复启动。开发库位于 `127.0.0.1:55432/travel_copilot`；连接配置在忽略的 `.env.database.local`，不能发给前端。查看、改价、英文文案、供应商关联、报价快照及备份恢复的具体操作见 [数据库使用说明](docs/database-guide.md)。02 的联系表单已接入咨询存储；运营网页登录、邮件通知和生产数据库部署尚未完成。

启动已创建的前端，在本仓库根目录执行：

```bash
cd frontend
npm run dev
```

首次拉取后先在 `frontend/` 执行 `npm ci`。开发服务器运行后可打开产品首页 `/` 与行程定制页 `/plan`，修改代码时页面会热更新。目前对客页面为英文，预览已通过服务端调用后端，按天展示 Menu 介绍、景点亮点与所选体验；图片仍为示意插画。后端已新增独立的产品目录、行程预览与内部成本接口；本轮已接入预览，内部成本与成本 × 1.3 的旅客报价接口已独立验证，销售估算已接入前端，并可选择具体分支和包车；用户端默认标准英文导游及淡季估算，不再显示导游/季节选项。接口说明见 [后端接口契约](docs/backend-api.md)。开发约定见 [前端开发流程](docs/frontend-guide.md)，实施计划见 [路线图](docs/roadmap.md)。

## 文档

- [文档索引](docs/README.md)
- [目录与迁移对照](docs/project-structure.md)
- [当前架构](docs/architecture.md)
- [路线图](docs/roadmap.md)
- [数据说明](data/README.md)
- [数据库使用说明](docs/database-guide.md)
- [整理验证记录](docs/test_reports/organization_20261007.md)

销售估算按已明确服务成本 × 1.3，最终预订仍需确认；付款看板尚未具备多人事务存储。新网站的产品定位、账号权限与上线配置仍待后续阶段完成。
