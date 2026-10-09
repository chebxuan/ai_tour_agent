# 运行数据说明

`data/` 保留现有代码需要的结构，避免目录整理改变产品匹配与计算结果。原始大文件和私人材料已移到 `references/private/`。

| 位置 | 职责 |
|---|---|
| `products/product_library.csv` | 标准产品源数据 |
| `products/products.normalized.json` | 标准化产品与 day_plans，供 API 读取 |
| `products/attraction_highlights.json` | 行程展示增强 |
| `products/cost_scope.json` | 已核实分支、计费范围、冲突拦截与销售倍率 |
| `products/services/产品服务_*.csv` | 分类服务与成本源数据 |
| `products/services/mashes/*.csv` | 当前按城市运行的成本库 |
| `products/services/Hexa_产品服务模块成本统计表(12.31)/` | 已有历史来源表，暂保留来源关系 |
| `custom/shanghai_experience_units.csv` | 35 个体验单元 |
| `custom/shanghai_transport_edges.csv` | 96 条交通边 |
| `custom/customer_profile_tags.csv` | 12 个画像 |
| `custom/shanghai_route_templates.json` | 12 个模板 |
| `payments.json` | 私有可写付款记录，Git 与 Docker 均排除 |

运行必需的 CSV/JSON 不再被整体忽略，上海半定制数据可以随明确的 Git 提交被版本管理。本轮没有执行提交或推送；可版本管理不等于已脱敏、可以公开发布。

## 当前主数据与修改方法

2026-10-09 已将标准产品、城市成本、计费范围和 Menu 文案导入 PostgreSQL，并启用数据库读取。下表中的文件保留为初始来源、文件模式基线和离线导出输入；当前标准产品网站的运行主数据在数据库。修改这些文件不会自动修改数据库，不长期双写。日常查看、改价、文案、供应商与备份使用 [数据库维护命令](../docs/database-guide.md)。供应商表当前为空，付款 JSON 和上海半定制输入本轮未迁移。

## 文件模式的数据维护

先修改源数据，再按需生成运行副本。下面的命令会写文件，不能当作只读检查：

```bash
.venv/bin/python scripts/normalize_product_library.py
.venv/bin/python scripts/merge_city_products.py --city 北京 --src-dir data/products/services --out data/products/services/mashes/北京_merged.csv
```

修改后执行不会改产品库的本地验证：

```bash
.venv/bin/python -B scripts/verify_project.py
```

`scripts/auto_verify.sh` 则先重建标准化产品再检查，适用于有意更新源数据之后。

`scripts/rebuild_citywalk_data.py` 的输入已改为 `experiments/city_narrative/city_narratives.csv`，它属于实验数据维护，不是现行 API 启动前必须执行的步骤。

数据库模式的旅客 API 使用公开字段投影，成本、供应商与保存的报价明细留在后端。网页维护与生产权限仍待后续阶段。

2026-10-09：北京产品编号已按运行成本库校正；华夏号、ATV 与长桌宴的源表和运行库记录用户确认。重庆返程不纳入当前收费范围，历史来源表不改写。销售价按所列服务成本 × 1.3，见 [接口契约](../docs/backend-api.md)。
