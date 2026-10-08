# 旧界面与工具

这里保存仍可使用的 Streamlit 界面、CLI 问卷，以及历史维护工具。新前端单独创建在 `frontend/`，不会通过改个人作品集来代替业务网站。

从仓库根目录启动旧界面：

```bash
.venv/bin/python -m streamlit run streamlit_app.py
```

启动 CLI：

```bash
.venv/bin/python -m legacy.cli_app
```

根目录 Streamlit 兼容入口在每次页面重跑时执行此目录的实现，保留原有用户改动。本地读取根目录 `.env`，部署环境变量仍优先。

`tools/fix_price_issues.py` 是历史修价工具，可能写入价格表，且额外依赖 pandas。本次只归档并更新路径，没有执行；不把它作为正常启动或验证步骤。
