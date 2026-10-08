#!/usr/bin/env bash
# ============================================================
# auto_verify.sh — 数据治理自动化脚本
# 一键执行：normalize → 本地规则评测与接口检查
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
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
echo "▶ Step 1/2: 标准化产品库..."
cd "$ROOT/scripts"
"$PYTHON_BIN" normalize_product_library.py
echo "  ✅ products.normalized.json 已更新"
echo ""

# Step 2: Deterministic evaluation and local API checks
echo "▶ Step 2/2: 本地业务检查..."
cd "$ROOT"
"$PYTHON_BIN" -B scripts/verify_project.py
echo ""

echo "========================================"
echo "  ✅ Auto Verify 完成"
echo "========================================"
