# 实验与历史原型

- `city_narrative/`：原 `projects 2/`，保留 Coze/LangGraph 工程、地标处理脚本、独立文档与地图输出；未接入现行主 API。
- `poi_planning/`：POI 数据模型与外部生成脚本；未接入现行主 API。

这些目录的依赖与运行环境不属于主后端依赖。历史文档保留原有技术背景，不代表当前网站已经实现对应能力。

POI 生成脚本可能调用外部模型；不要把它加入默认验证流程。城市叙事重建入口仍在 `scripts/rebuild_citywalk_data.py`，已同步调整源数据路径。
