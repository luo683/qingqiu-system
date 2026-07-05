"""qingqiu CLI 入口

S1.1: --version / -v / config show（占位）
S1.2: llm test <provider>
S1.3: config show（真工作）+ config path
S1.4: 集成日志系统（setup_logging + logger）

后续切片：task / chat / graph 等
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger as loguru_logger

from qingqiu import __version__
from qingqiu.observability import get_logger, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qingqiu",
        description="清秋 · 本地优先的个人 AI 助理",
    )
    parser.add_argument("--version", action="store_true", help="输出版本号并退出")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出详细日志")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # config 子命令
    config_parser = subparsers.add_parser("config", help="查看和管理配置")
    config_sub = config_parser.add_subparsers(dest="subcommand")
    config_sub.add_parser("show", help="打印合并后的配置（默认 + 文件 + 环境变量）")
    config_sub.add_parser("path", help="显示配置文件路径")

    # llm 子命令
    llm_parser = subparsers.add_parser("llm", help="LLM provider 管理")
    llm_sub = llm_parser.add_subparsers(dest="llm_subcommand")
    llm_test = llm_sub.add_parser("test", help="测试 provider 是否可用")
    llm_test.add_argument(
        "provider",
        choices=["openai", "anthropic", "ollama", "custom"],
        help="provider 名",
    )
    llm_test.add_argument(
        "--model",
        default=None,
        help="指定模型（默认用 provider 内置默认模型）",
    )

    return parser


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"qingqiu {__version__}")
    return 0


def cmd_config_show(_args: argparse.Namespace) -> int:
    """`qingqiu config show` · S1.3: 真工作（不是占位）"""
    import yaml

    from qingqiu.config import ConfigManager

    manager = ConfigManager()
    manager.load()
    data = manager.config.model_dump(mode="json", exclude_none=True)
    yaml_str = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    print(yaml_str, end="")
    print(f"# config_file: {manager.config_path}")
    print(f"# source: defaults < file < env vars")
    return 0


def cmd_config_path(_args: argparse.Namespace) -> int:
    """`qingqiu config path` · 显示配置文件位置"""
    from qingqiu.config import get_default_config_path

    path = get_default_config_path()
    print(path)
    print(f"# exists: {path.exists()}")
    return 0


async def cmd_llm_test_async(args: argparse.Namespace) -> int:
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
        print(f"[FAIL] 初始化失败：{e}", file=sys.stderr)
        return 1
    except Exception as e:
        log.error(f"provider 初始化异常: {provider_name}, type={type(e).__name__}, error={e}")
        print(f"[FAIL] 未知错误：{e}", file=sys.stderr)
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
        print(f"[FAIL] LLM 调用失败：{e}", file=sys.stderr)
        return 1
    except Exception as e:
        log.error(f"LLM 调用异常: {provider_name}, type={type(e).__name__}, error={e}")
        print(f"[FAIL] 调用异常：{type(e).__name__}: {e}", file=sys.stderr)
        return 1

    log.info(f"LLM 调用 OK: {provider_name}, model={response.model}, "
             f"input={response.usage.get('input_tokens', 0)}, "
             f"output={response.usage.get('output_tokens', 0)}")
    print(f"[OK] {provider_name} 响应：")
    print(f"  content: {response.content!r}")
    print(f"  model:   {response.model}")
    print(f"  usage:   input={response.usage.get('input_tokens', 0)}, "
          f"output={response.usage.get('output_tokens', 0)}")
    return 0


def cmd_llm_test(args: argparse.Namespace) -> int:
    return asyncio.run(cmd_llm_test_async(args))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # S1.4: 集成日志系统
    log_level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
    setup_logging(level=log_level)
    log = get_logger("qingqiu.cli")

    log.info(f"qingqiu {__version__} invoked with argv={argv or sys.argv[1:]}")

    try:
        if args.version:
            return cmd_version(args)

        if args.command == "config":
            if args.subcommand == "show":
                return cmd_config_show(args)
            if args.subcommand == "path":
                return cmd_config_path(args)
            # 无子命令输出 config 帮助
            parser.parse_args([args.command, "--help"])

        if args.command == "llm" and args.llm_subcommand == "test":
            return cmd_llm_test(args)

        if args.verbose:
            print(f"[verbose] qingqiu {__version__}")
            print(f"[verbose] Python {sys.version.split()[0]}")
            print(f"[verbose] Platform: {sys.platform}")

        parser.print_help()
        return 0
    except Exception as e:
        log.error(f"unhandled exception: {type(e).__name__}: {e}")
        log.exception("stacktrace")
        return 1


if __name__ == "__main__":
    sys.exit(main())