#!/usr/bin/env bash
# scripts/verify_s1_1.sh - S1.1 验收脚本
# 来源：IMPLEMENTATION-PLAN.md S1.1 验收标准
#   - uv sync 装依赖成功（或 python -m pip install -e .）
#   - CLI 命令能跑：qingqiu --version 输出版本号
#
# 用法：在项目根目录 bash scripts/verify_s1_1.sh

set -e

echo "[verify] S1.1 · 项目骨架与配置入口"
echo ""

# 1. python -m qingqiu --version
echo "[step 1] python -m qingqiu --version"
OUTPUT=$(cd "E:/MiniMax Code Work Space/qingqiu-system" && python -m qingqiu --version 2>&1)
echo "  $OUTPUT"
echo "$OUTPUT" | grep -q "qingqiu 0.3.0" || (echo "  FAIL: version 不正确" && exit 1)

# 2. python -m qingqiu --help
echo ""
echo "[step 2] python -m qingqiu --help"
cd "E:/MiniMax Code Work Space/qingqiu-system" && python -m qingqiu --help

# 3. python -m qingqiu config show
echo ""
echo "[step 3] python -m qingqiu config show"
OUTPUT=$(cd "E:/MiniMax Code Work Space/qingqiu-system" && python -m qingqiu config show 2>&1)
echo "  $OUTPUT"
echo "$OUTPUT" | grep -q "S1.1 placeholder" || (echo "  FAIL: config show 占位不正确" && exit 1)

# 4. python -m pytest
echo ""
echo "[step 4] python -m pytest tests/"
cd "E:/MiniMax Code Work Space/qingqiu-system" && python -m pytest tests/ -v

echo ""
echo "[verify] S1.1 PASS"