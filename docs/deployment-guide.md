# 当前部署与打包说明

更新：2026-10-07。当前已有 FastAPI 和旧 Streamlit Demo；新 Next.js 网站尚未创建。此处只维护本仓库现在适用的入口，不确认旧公网 Demo 的当前状态或历史平台收费。

## 后端

从项目根目录运行：

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

服务器或容器需要对外监听时，根据部署环境调整 host。`API_KEY` 必须配置；外部模型配置用于文本解析，纯规则生成不需要模型调用。

根目录兼容入口 `uvicorn api_main:app` 仍然有效。

## Docker

Dockerfile 使用 `backend/requirements.txt`，复制整个后端包（含运行提示词）以及 `data/products/`、`data/custom/`。私人材料、旧付款文件、日志、依赖目录与本地密钥不进入构建上下文。

具备 Docker 环境后，可在根目录执行：

```bash
docker build -t travel-ops-api .
docker run --env-file .env -p 8000:8000 travel-ops-api
```

本轮仅修复与迁移有关的文件覆盖，未实际构建镜像。正式使用付款功能时，必须另配置持久化存储，不能依赖容器内临时文件保存业务数据。

`render.yaml` 保留为现有后端配置；这里只引用其文件，不确认平台当前套餐或部署成功。

## 旧 Streamlit

根目录 `streamlit_app.py` 是兼容入口，适用于现有本地命令或旧平台入口配置。每次重跑会执行 `legacy/streamlit_app.py`。界面和后端从同一根目录 `.env` 读取本地配置，部署时由平台注入对应环境变量。

旧部署过程见 [历史教程](archive/streamlit-cloud-deployment.md)，其中路径、能力和收费描述仅属于历史资料。

## 新网站

按用户选择先完成前端，再完善接口、存储和权限。前端进入部署阶段后再决定具体部署方式，并补齐构建、进程托管、转发、备份与回退配置，见 [路线图](roadmap.md)。
