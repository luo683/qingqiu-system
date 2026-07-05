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
from qingqiu.cli.errors import CLIError
from qingqiu.cli.memory import build_parser as build_memory_parser
from qingqiu.cli.output import OutputFormatter
from qingqiu.observability import get_logger, setup_logging


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
    p_ask = subparsers.add_parser("ask", help="单次提问（占位：M2.2 router 接入）")
    p_ask.add_argument("prompt", nargs="+", help="提问内容")
    p_ask.set_defaults(_handler=lambda args, out: _placeholder_ask(args, out))

    p_chat = subparsers.add_parser("chat", help="交互模式（占位：M2.6 端到端）")
    p_chat.set_defaults(_handler=lambda args, out: _placeholder_chat(args, out))

    # task 占位
    p_task = subparsers.add_parser("task", help="任务管理（M2.6 实现）")
    task_sub = p_task.add_subparsers(dest="task_subcommand")
    p_task_list = task_sub.add_parser("list", help="列任务")
    p_task_list.set_defaults(_handler=lambda args, out: _placeholder_task(args, out))
    p_task_show = task_sub.add_parser("show", help="看任务")
    p_task_show.add_argument("id")
    p_task_show.set_defaults(_handler=lambda args, out: _placeholder_task(args, out))
    p_task_add = task_sub.add_parser("add", help="加任务")
    p_task_add.add_argument("description", nargs="+")
    p_task_add.set_defaults(_handler=lambda args, out: _placeholder_task(args, out))

    # status 占位
    p_status = subparsers.add_parser("status", help="健康状态（占位）")
    p_status.set_defaults(_handler=lambda args, out: _placeholder_status(args, out))

    # memory（接 S1.5）
    build_memory_parser(subparsers)

    # config（老的，回填）
    p_config = subparsers.add_parser("config", help="查看和管理配置")
    config_sub = p_config.add_subparsers(dest="subcommand")
    p_config_show = config_sub.add_parser("show", help="打印合并后的配置")
    p_config_show.set_defaults(_handler=_config_show)
    p_config_path = config_sub.add_parser("path", help="显示配置文件路径")
    p_config_path.set_defaults(_handler=_config_path)

    # llm（老的，回填）
    p_llm = subparsers.add_parser("llm", help="LLM provider 管理")
    llm_sub = p_llm.add_subparsers(dest="llm_subcommand")
    p_llm_test = llm_sub.add_parser("test", help="测试 provider")
    p_llm_test.add_argument(
        "provider", choices=["openai", "anthropic", "ollama", "custom"]
    )
    p_llm_test.add_argument("--model", default=None)
    p_llm_test.set_defaults(_handler=_llm_test)

    return parser


# === 占位 handlers（M2 后续切片实现） ===

def _placeholder_ask(args, out: OutputFormatter) -> int:
    out.info("ask 子命令尚未实现（S2.2 router 接入后启用）")
    out.print({"prompt": " ".join(args.prompt), "status": "placeholder"})
    return 0


def _placeholder_chat(args, out: OutputFormatter) -> int:
    out.info("chat 子命令尚未实现（S2.6 端到端后启用）")
    return 0


def _placeholder_task(args, out: OutputFormatter) -> int:
    out.info("task 子命令尚未实现（S2.6 端到端后启用）")
    return 0


def _placeholder_status(args, out: OutputFormatter) -> int:
    out.info("status 子命令尚未实现（M3+ 启用）")
    return 0


# === 老 config / llm handlers（从老 cli.py 搬过来） ===

def _config_show(args, out: OutputFormatter) -> int:
    import yaml

    from qingqiu.config import ConfigManager

    manager = ConfigManager()
    manager.load()
    data = manager.config.model_dump(mode="json", exclude_none=True)
    if out.json_mode:
        out.print({"config": data, "source": "defaults < file < env vars"})
        return 0
    yaml_str = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    print(yaml_str, end="")
    print(f"# config_file: {manager.config_path}")
    print(f"# source: defaults < file < env vars")
    return 0


def _config_path(args, out: OutputFormatter) -> int:
    from qingqiu.config import get_default_config_path

    path = get_default_config_path()
    if out.json_mode:
        out.print({"path": str(path), "exists": path.exists()})
        return 0
    print(path)
    print(f"# exists: {path.exists()}")
    return 0


async def _llm_test_async(args, out: OutputFormatter) -> int:
    from qingqiu.llm import Message, get_provider
    from qingqiu.llm.exceptions import LLMError, ProviderInitError

    log = get_logger("qingqiu.cli.llm_test")
    provider_name = args.provider
    log.info(f"开始测试 provider={provider_name}")
    print(f"[test] 初始化 {provider_name} provider ...")

    try:
        provider = get_provider(provider_name)
    except ProviderInitError as e:
        log.error(f"provider 初始化失败: {provider_name}, error={e}")
        out.error(f"provider 初始化失败: {e}", code=1)
        return 1
    except Exception as e:
        log.error(f"provider 初始化异常: {provider_name}, type={type(e).__name__}, error={e}")
        out.error(f"未知错误: {e}", code=1)
        return 1

    log.info(f"provider 初始化 OK: {provider_name}, default_model={provider.default_model}")
    print(f"[test] 初始化 OK (default_model={provider.default_model})")
    print(f"[test] 发送测试 prompt ...")

    try:
        response = await provider.complete(
            [Message(role="user", content=f"Say hello from {provider_name} and nothing else.")],
            model=args.model,
            max_tokens=50,
        )
    except LLMError as e:
        log.error(f"LLM 调用失败: {provider_name}, error={e}")
        out.error(f"LLM 调用失败: {e}", code=1)
        return 1
    except Exception as e:
        log.error(f"LLM 调用异常: {provider_name}, type={type(e).__name__}, error={e}")
        out.error(f"调用异常: {type(e).__name__}: {e}", code=1)
        return 1

    log.info(f"LLM 调用 OK: {provider_name}, model={response.model}")
    if out.json_mode:
        out.print({
            "provider": provider_name,
            "model": response.model,
            "content": response.content,
            "usage": response.usage,
        })
    else:
        print(f"[OK] {provider_name} 响应：")
        print(f"  content: {response.content!r}")
        print(f"  model:   {response.model}")
        print(f"  usage:   input={response.usage.get('input_tokens', 0)}, "
              f"output={response.usage.get('output_tokens', 0)}")
    return 0


def _llm_test(args, out: OutputFormatter) -> int:
    import asyncio
    return asyncio.run(_llm_test_async(args, out))


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