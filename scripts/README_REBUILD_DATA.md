# 数据维护脚本

所有命令从本仓库根目录执行。数据维护会写文件，先确认源数据与输出位置；只做功能检查时使用 `verify_project.py`。

## 标准产品

```bash
.venv/bin/python scripts/normalize_product_library.py
```

输入 `data/products/product_library.csv`，输出 `data/products/products.normalized.json`。

## 城市成本合并

```bash
.venv/bin/python scripts/merge_city_products.py --city 北京 --src-dir data/products/services --out data/products/services/mashes/北京_merged.csv
```

按分类服务目录重新生成指定城市成本库，不自动替其他城市改价。

## 城市叙事实验

```bash
.venv/bin/python scripts/rebuild_citywalk_data.py
```

输入 `experiments/city_narrative/city_narratives.csv`，输出 `data/citywalk/narratives_v2.csv`。它属于历史实验，当前 API 不要求运行此脚本。

## 本地业务检查

```bash
.venv/bin/python -B scripts/verify_project.py
```

不重建数据、不调用外部 LLM、不写真实付款或日志。`auto_verify.sh` 会先运行产品标准化，再执行本地检查，适用于主动维护源数据之后。

更多数据边界见 [数据说明](../data/README.md)。
