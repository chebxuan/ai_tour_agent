# 公网部署执行路线

## 架构

```
用户浏览器 → Streamlit Cloud（前端） → Railway（后端 API）
```

前端和后端分开部署。Streamlit 只负责 UI，API 跑在独立的 server 上。

---

## Step 1：把代码推送到 GitHub

```bash
# 在项目目录执行
git init
git add .
git commit -m "init: Hexa Blueprint project"

# 在 GitHub 建一个仓库（不要勾选 README/LICENSE/.gitignore）
# 然后把本地代码推上去
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

---

## Step 2：部署后端 API（Railway，免费额度够用）

### 2.1 创建 Railway 项目

1. 打开 [Railway](https://railway.app/)，用 GitHub 登录
2. Dashboard → **New Project** → **Deploy from GitHub repo**
3. 选刚才推送的仓库
4. 添加启动命令：
   - Settings → **Start Command** → 填 `uvicorn api_main:app --host 0.0.0.0 --port 8000`
5. 设置环境变量（Settings → Variables）：
   - `API_KEY=hexa-tour-2024`
   - `API_BASE=`（暂时留空）
6. 等待部署完成，Railway 会分配一个域名，比如 `hexa-api.up.railway.app`

> 如果 Railway 免费额度用完，备选：Render（render.com）或 Fly.io（fly.io），操作类似。

### 2.2 验证 API

```bash
# 替换成你的 Railway 域名
curl https://hexa-api.up.railway.app/api/v1/cities
# 应该返回城市列表，部署成功
```

---

## Step 3：部署前端（Streamlit Community Cloud，免费）

### 3.1 准备项目

确认 `streamlit_app.py` 在仓库根目录，并且同目录有 `requirements.txt`（内容如下）：

```text
streamlit>=1.28
requests>=2.31
pydantic>=2.0
```

### 3.2 在 Streamlit Cloud 部署

1. 打开 https://streamlit.io/cloud
2. 用 GitHub 登录
3. **New app** → 选你的仓库
4. Branch: `main`
5. Main file: `streamlit_app.py`
6. 设置环境变量（Advanced settings → Secrets）：
   - `API_BASE=https://hexa-api.up.railway.app`（你部署好的 Railway 地址）
   - `API_KEY=hexa-tour-2024`
7. **Deploy**

### 3.3 完成

Streamlit Cloud 会分配一个域名，例如 `hexa-blueprint.streamlit.app`。浏览器打开即可使用。

之后每次 push 到 GitHub main 分支，前端和后端都会自动重新部署。

---

## 环境变量总结

| 变量名 | 说明 | 设在哪 |
|--------|------|--------|
| `API_KEY` | API 认证密钥 | Railway + Streamlit Cloud |
| `API_BASE` | 后端 API 地址 | 只在 Streamlit Cloud 设置 |

---

## 开销

| 服务 | 费用 |
|------|------|
| GitHub | 免费 |
| Railway | 免费 $5/月额度，够用 |
| Streamlit Community Cloud | 免费 |

---

## 日常更新

```bash
# 改完代码后
git add .
git commit -m "what changed"
git push
```

Railway 和 Streamlit Cloud 都会自动重新部署，等 1-2 分钟生效。

---

## 如果不用 Railway（备选）

### Render（render.com）

启动命令一样 `uvicorn api_main:app --host 0.0.0.0 --port 8000`，选 **Web Service**，免费额度 750h/月。

### Fly.io（fly.io）

```bash
fly launch
fly deploy
```

需要写 `fly.toml`，稍微多几步配置。

---

## 关于数据

部署后 API 用的是代码仓库里的数据文件（`data/` 目录）。如果要改产品价格或新增产品：

1. 在本地改 CSV
2. 重新 `python scripts/normalize_product_library.py`
3. `git commit && git push`
4. 自动部署，数据更新

不需要管数据库。
