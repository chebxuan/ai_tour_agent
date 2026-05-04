#!/usr/bin/env bash
# ============================================================
# auto_verify.sh — 数据治理自动化脚本
# 一键执行：normalize → verify mapping → test
# 用法: bash scripts/auto_verify.sh
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "========================================"
echo "  Hexa Blueprint — Auto Verify"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "========================================"
echo ""

# Step 1: Normalize product library
echo "▶ Step 1/3: 标准化产品库..."
cd "$ROOT/scripts"
python3 normalize_product_library.py
echo "  ✅ products.normalized.json 已更新"
echo ""

# Step 2: Verify product-cost mapping
echo "▶ Step 2/3: 验证产品-成本映射..."
cd "$ROOT"
python3 test_multi_city.py 2>&1 | tail -20
echo ""

# Step 3: Optional items check
echo "▶ Step 3/3: 验证 Optional 项目..."
cd "$ROOT"
python3 test_optional_items.py 2>&1 | tail -10
echo ""

echo "========================================"
echo "  ✅ Auto Verify 完成"
echo "========================================"
