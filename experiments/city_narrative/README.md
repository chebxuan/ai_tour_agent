# 城市叙事实验

原目录名为 `projects 2/`，这里保留城市叙事、地标处理与 Coze/LangGraph 原型，尚未接入现行 FastAPI 主链路。

- `src/`：原 Coze 工程实现及存储适配。
- `scripts/`：坐标补全、地标抽取、处理和可视化工具。
- `docs/`：原工程说明，保留当时运行背景。
- `city_narratives*.csv`、`shanghai_landmarks*`：原实验输入和成果。
- `narrative_engine.py`：原独立叙事规则引擎。
- `outputs/maps/`：原主项目 `assets/maps/` 的地图输出。

本实验有独立运行前提和额外依赖，不是安装主后端依赖后即可完整运行的模块。默认项目检查不会调用这些外部服务或重建数据。

主仓库的 `scripts/rebuild_citywalk_data.py` 已将输入路径改为这里的 `city_narratives.csv`。当前网站开发请从 [根目录说明](../../readme.md) 开始。
