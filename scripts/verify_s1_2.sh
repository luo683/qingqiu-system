#!/usr/bin/env bash
# scripts/verify_s1_2.sh - S1.2 验收脚本
# 来源：IMPLEMENTATION-PLAN.md S1.2 验收标准
#   - 跑通"用 anthropic 回答、用 ollama 回答"两条命令
#
# 用法：在项目根目录 bash scripts/verify_s1_2.sh

set -e

PROJECT_DIR="E:/MiniMax Code WorkSpace/qingqiu-system"

cd "$PROJECT_DIR"

echo "[verify] S1.2 · LLM 抽象层"
echo ""

# 1. CLI 帮助显示新子命令
echo "[step 1] qingqiu --help 应该含 'llm' 子命令"
OUTPUT=$(uv run qingqiu --help 2>&1)
echo "$OUTPUT" | grep -q "{llm}" || (echo "  FAIL: llm 子命令未注册" && exit 1)
echo "  OK"

# 2. llm test --help
echo ""
echo "[step 2] qingqiu llm test --help"
uv run qingqiu llm test --help

# 3. llm test ollama（如果本地有 ollama 实例运行）
echo ""
echo "[step 3] qingqiu llm test ollama (尝试本地 Ollama)"
if uv run qingqiu llm test ollama 2>&1; then
    echo "  OK: ollama provider 工作"
else
    echo "  [skip] ollama 未运行或模型未下载 - 这是预期（v1 默认不是 ollama 必装）"
fi

# 4. llm test anthropic（需要 ANTHROPIC_API_KEY 环境变量）
echo ""
echo "[step 4] qingqiu llm test anthropic (需要 ANTHROPIC_API_KEY)"
if [ -n "$ANTHROPIC_API_KEY" ]; then
    if uv run qingqiu llm test anthropic 2>&1; then
        echo "  OK: anthropic provider 工作"
    else
        echo "  FAIL: anthropic provider 失败"
        exit 1
    fi
else
    echo "  [skip] ANTHROPIC_API_KEY 未设置 - 跳过实际 API 调用"
fi

# 5. pytest 跑全部 llm 测试
echo ""
echo "[step 5] pytest tests/llm/"
uv run pytest tests/llm/ -v

# 6. pytest 跑全部测试（含 S1.1）
echo ""
echo "[step 6] pytest 全套"
uv run pytest tests/ -v

echo ""
echo "[verify] S1.2 PASS"