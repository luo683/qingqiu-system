"""qingqiu CLI 测试 · S1.1

覆盖范围（IMPLEMENTATION-PLAN.md S1.1 验收）：
- `qingqiu --version` 输出版本号
- `qingqiu config show` 输出占位配置
- `qingqiu --help` 输出帮助
- exit code 0
"""

from __future__ import annotations

import subprocess
import sys


def run_qingqiu(*args: str) -> subprocess.CompletedProcess[str]:
    """通过 `python -m qingqiu` 调用，确保走的是当前代码（不是已安装版本）"""
    return subprocess.run(
        [sys.executable, "-m", "qingqiu", *args],
        capture_output=True,
        text=True,
        cwd="E:/MiniMax Code WorkSpace/qingqiu-system",
    )


def test_version_flag_outputs_version() -> None:
    """`qingqiu --version` 输出当前版本号"""
    result = run_qingqiu("--version")
    assert result.returncode == 0, f"expected 0, got {result.returncode}"
    assert "qingqiu 0.3.0" in result.stdout


def test_help_flag_outputs_usage() -> None:
    """`qingqiu --help` 输出使用说明"""
    result = run_qingqiu("--help")
    assert result.returncode == 0
    assert "清秋" in result.stdout or "qingqiu" in result.stdout


def test_config_show_outputs_real_config() -> None:
    """S1.3: `qingqiu config show` 真显示配置（不再是占位）"""
    result = run_qingqiu("config", "show")
    assert result.returncode == 0
    # S1.1 的占位文本已废弃
    assert "S1.1 placeholder" not in result.stdout
    # 应该含真实配置字段
    assert "0.3.0" in result.stdout  # 版本号
    assert "personality:" in result.stdout  # 配置段
    assert "清秋" in result.stdout  # 默认人格名


def test_verbose_flag_outputs_extra_info() -> None:
    """`qingqiu -v` 输出 verbose 标记"""
    result = run_qingqiu("-v")
    assert result.returncode == 0
    assert "[verbose]" in result.stdout


def test_no_args_prints_help() -> None:
    """无参数时输出帮助（exit 0）"""
    result = run_qingqiu()
    assert result.returncode == 0
    assert "qingqiu" in result.stdout