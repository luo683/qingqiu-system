"""cli.main · CLI 入口 + parser 装配 + dispatch

S2.1 范围：
- 全局 flag: -V / -v / --json / --no-color / --config
- 子命令树: memory / config / llm (老的) + ask / chat / task / status (M2 占位)
- 统一输出: OutputFormatter (human / JSON)
- 错误处理: CLIError → exit code 0/1/2/130
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger as loguru_logger

from qingqiu import __version__
from qingqiu.cli.config import build_parser as build_config_parser
from qingqiu.cli.confirm import build_parser as build_confirm_parser
from qingqiu.cli.errors import CLIError
from qingqiu.cli.llm import build_parser as build_llm_parser
from qingqiu.cli.memory import build_parser as build_memory_parser
from qingqiu.cli.output import OutputFormatter
from qingqiu.cli.status import build_parser as build_status_parser
from qingqiu.cli.task import build_parser as build_task_parser
from qingqiu.observability import get_logger, setup_logging
from qingqiu.router.executor import run_ask


def build_parser() -> argparse.ArgumentParser:
    """构造顶层 parser"""
    parser = argparse.ArgumentParser(
        prog="qingqiu",
        description="清秋 · 本地优先的个人 AI 助理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "子命令：\n"
            "  ask <prompt>          单次提问（占位）\n"
            "  chat                  交互模式（占位）\n"
            "  task <action>         任务管理（M2.6）\n"
            "  memory <action>       记忆管理（L0/L1/L2/L3）\n"
            "  status                健康状态\n"
            "  confirm <action>      Confirm 询问（CLI/TUI 适配 S5.1）\n"
            "  config <action>       配置\n"
            "  llm <action>          LLM provider\n"
            "\n"
            "全局 flag：\n"
            "  -v / --verbose        DEBUG 日志\n"
            "  -V / --version        版本\n"
            "  --json                JSON 输出\n"
            "  --no-color            禁用 ANSI\n"
            "  --config <path>       临时配置文件\n"
            "\n"
            "详细每个子命令：`qingqiu <subcmd> --help`"
        ),
    )
    # 全局 flag
    parser.add_argument("-V", "--version", action="store_true", help="输出版本号")
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")
    parser.add_argument("--json", action="store_true", help="JSON 输出模式")
    parser.add_argument("--no-color", action="store_true", help="禁用 ANSI 颜色")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="临时配置文件（覆盖 ~/.qingqiu/config.yaml）",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<subcommand>")

    # === M2 占位子命令（仅 help 完整 + 友好错误） ===
    p_ask = subparsers.add_parser(
        "ask",
        help="自然语言入口：识别意图并执行（S2.4 router 接入）",
        description=(
            "自然语言入口。例：\n"
            "  qingqiu ask 'memory get user_name'\n"
            "  qingqiu ask 'memory set user_name ROG'\n"
            "  qingqiu ask 'task add 写文档'\n"
            "  qingqiu ask '看任务'\n"
            "  qingqiu ask 'status'"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_ask.add_argument("prompt", nargs="+", help="自然语言指令")
    p_ask.set_defaults(_handler=_handle_ask)

    p_chat = subparsers.add_parser("chat", help="交互模式（占位：M2.6 端到端）")
    p_chat.set_defaults(_handler=lambda args, out: _placeholder_chat(args, out))

    # task（接 S2.1 task.py · 5 action）
    build_task_parser(subparsers)

    # status（接 S2.1 status.py · 3 块输出）
    build_status_parser(subparsers)

    # memory（接 S1.5 facade）
    build_memory_parser(subparsers)

    # confirm（接 S5.1 Confirm 框架 · S2.5）
    build_confirm_parser(subparsers)

    # config
    build_config_parser(subparsers)

    # llm
    build_llm_parser(subparsers)

    return parser


# === ask handler（S2.4 router 接入） ===

def _handle_ask(args, out: OutputFormatter) -> int:
    """`qingqiu ask "<natural language>"` — 路由到 Executor"""
    return run_ask(args, out, llm_provider=None)


def _placeholder_chat(args, out: OutputFormatter) -> int:
    out.info("chat 子命令尚未实现（S2.6 端到端后启用）")
    return 0


# === main ===

def main(argv: list[str] | None = None) -> int:
    """CLI 主入口"""
    parser = build_parser()
    args = parser.parse_args(argv)

    # 全局 flag 解析
    log_level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
    setup_logging(level=log_level)
    log = get_logger("qingqiu.cli")
    out = OutputFormatter(
        json_mode=getattr(args, "json", False),
        no_color=getattr(args, "no_color", False) or not sys.stdout.isatty(),
    )

    log.info(f"qingqiu {__version__} invoked argv={argv or sys.argv[1:]}")

    # --version 单独处理
    if getattr(args, "version", False):
        if out.json_mode:
            out.print({"version": __version__})
        else:
            print(f"qingqiu {__version__}")
        return 0

    try:
        # 无子命令：友好 help
        if not getattr(args, "command", None):
            parser.print_help()
            return 0

        # 子命令有 _handler（由 set_defaults 设置）
        handler = getattr(args, "_handler", None)
        if handler is None:
            # 子命令存在但没具体 action（如 `qingqiu config` 不带 sub）
            parser.parse_args([args.command, "--help"])

        return handler(args, out)

    except CLIError as e:
        log.error(f"CLI error: {e.message}, code={e.code}")
        out.error(e.message, code=e.code, hint=e.hint)
        return e.code
    except KeyboardInterrupt:
        log.warning("interrupted by user")
        out.error("interrupted", code=130)
        return 130
    except Exception as e:
        log.exception(f"unhandled exception: {type(e).__name__}: {e}")
        out.error(f"内部错误: {type(e).__name__}: {e}", code=2)
        return 2


if __name__ == "__main__":
    sys.exit(main())