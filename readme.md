# AI Travel Ops Copilot

面向入境游询单、产品匹配、成本核算和方案交付的运营辅助原型。现有界面为 Streamlit，后端为 FastAPI；新网站计划先建设 Next.js 前端，再接入接口、完善存储与权限。

## 当前能力

- AI 将客户原文转为结构化需求，保留需要人工确认的内容。
- 标准产品匹配、成本计算、风险检查和行程生成使用确定性规则。
- 标准产品库包含 21 个产品、10 个城市；上海半定制提供独立路线流程。
- 输出 Markdown 行程和邮件草稿，供人工复核。
- 供应商付款看板目前使用本地 JSON 存储。

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

`frontend/` 已完成旅客视角的产品首页和行程定制页组件，目前使用示意数据，产品内容与接口接入仍待后续完成。根目录 `api_main.py`、`streamlit_app.py` 是原启动方式的兼容入口。

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

## 当前阶段：前端

启动已创建的前端，在本仓库根目录执行：

```bash
cd frontend
npm run dev
```

首次拉取后先在 `frontend/` 执行 `npm ci`。开发服务器运行后可打开产品首页 `/` 与行程定制页 `/plan`，修改代码时页面会热更新。当前使用示意数据，尚未连接业务接口。下一轮整理正式产品内容，再进行后端联调。开发约定见 [前端开发流程](docs/frontend-guide.md)，实施计划见 [路线图](docs/roadmap.md)。

## 文档

- [文档索引](docs/README.md)
- [目录与迁移对照](docs/project-structure.md)
- [当前架构](docs/architecture.md)
- [路线图](docs/roadmap.md)
- [数据说明](data/README.md)
- [整理验证记录](docs/test_reports/organization_20261007.md)

成本计算不等于统一销售定价；付款看板尚未具备多人事务存储。新网站的产品定位、账号权限与上线配置仍待后续阶段完成。
