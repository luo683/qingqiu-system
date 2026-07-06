"""cli.confirm · Confirm 询问 CLI 入口（S2.5）

S2.5 范围：
- `qingqiu confirm ask "<summary>" [--timeout 60]`    弹 Confirm 问用户
- `qingqiu confirm test [--always-yes|--always-no]`    烟雾测试 Confirm 框架

复用了 S5.1 的 Prompter / Confirm / ConfirmRejected（不修改 security/）。
TUI 适配（Voice / IM）后续切片再做。
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from qingqiu.cli.output import OutputFormatter
from qingqiu.security.confirm import (
    Confirm,
    ConfirmRejected,
    Prompter,
)


# === handlers ===

def _build_test_prompter(args) -> Prompter:
    """根据 args 构造 test 子命令用的 Prompter（始终是非交互的）"""

    class _FixedPrompter(Prompter):
        def __init__(self, agreed: bool) -> None:
            self._agreed = agreed

        def ask(self, summary: str, timeout_sec: int = 60) -> bool:
            return self._agreed

    if getattr(args, "always_yes", False) and getattr(args, "always_no", False):
        # 两个都给 → 优先 yes（更安全）
        return _FixedPrompter(agreed=True)
    if getattr(args, "always_yes", False):
        return _FixedPrompter(agreed=True)
    if getattr(args, "always_no", False):
        return _FixedPrompter(agreed=False)

    # 默认：固定 yes（让 test 烟雾通过）
    return _FixedPrompter(agreed=True)


def run_confirm_ask(args, out: OutputFormatter) -> int:
    """`qingqiu confirm ask <summary> [--timeout 60]`

    用默认 Confirm 框架问用户。同意 → exit 0，拒绝/超时 → exit 1。
    """
    timeout = getattr(args, "timeout", 60)
    confirm = Confirm(default_timeout=timeout)
    try:
        confirm.ask(args.summary, timeout_sec=timeout)
    except ConfirmRejected as e:
        out.error(str(e), code=e.code, hint=e.hint)
        return e.code
    out.success(f"approved: {args.summary}")
    return 0


def run_confirm_test(args, out: OutputFormatter) -> int:
    """`qingqiu confirm test [--always-yes|--always-no|--timeout 2]`

    用固定 Prompter 跑一次 Confirm.ask()，用于验证 Confirm 框架集成。
    默认 always-yes（exit 0）；--always-no 则 exit 1。
    """
    timeout = getattr(args, "timeout", 2)
    prompter = _build_test_prompter(args)
    confirm = Confirm(prompter=prompter, default_timeout=timeout)
    expected_yes = not getattr(args, "always_no", False)
    summary = "qingqiu confirm test"
    try:
        agreed = confirm.ask(summary, timeout_sec=timeout)
    except ConfirmRejected as e:
        if expected_yes:
            out.error(f"test failed (expected approve): {e}", code=e.code)
            return e.code
        out.success(f"test passed (rejected as expected): {e.message}")
        return 0

    if not expected_yes and agreed:
        out.error("test failed (expected reject, got approve)", code=1)
        return 1
    out.success("test passed: Confirm framework wired correctly")
    return 0


# === parser 装配 ===

def build_parser(subparsers):
    """`confirm` 子命令 parser 装配"""
    parser = subparsers.add_parser(
        "confirm",
        help="Confirm 询问（CLI/TUI 适配 S5.1 Confirm 框架）",
        description=(
            "Confirm 询问 CLI 入口。\n"
            "例：\n"
            "  qingqiu confirm ask 'Apply 3 file changes?'\n"
            "  qingqiu confirm ask --timeout 30 'Delete /tmp/test?'\n"
            "  qingqiu confirm test --always-yes\n"
            "  qingqiu confirm test --always-no\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(_subcommand_group="confirm")
    sub = parser.add_subparsers(dest="confirm_subcommand", metavar="<action>")

    # ask
    p_ask = sub.add_parser("ask", help="询问用户")
    p_ask.add_argument("summary", help="询问摘要")
    p_ask.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="超时秒数（默认 60）",
    )
    p_ask.set_defaults(_handler=run_confirm_ask)

    # test
    p_test = sub.add_parser("test", help="测试 Confirm 框架（烟雾）")
    p_test.add_argument("--always-yes", action="store_true", help="强制 yes")
    p_test.add_argument("--always-no", action="store_true", help="强制 no")
    p_test.add_argument(
        "--timeout",
        type=int,
        default=2,
        help="超时秒数（默认 2）",
    )
    p_test.set_defaults(_handler=run_confirm_test)

    return parser