"""qingqiu CLI 入口 · S1.2 含 LLM 子命令

S1.1 范围（已完成）：
- qingqiu --version
- qingqiu config show（占位）

S1.2 范围（新增）：
- qingqiu llm test <provider> 测试 provider 是否可用

后续切片（不在本 slice 范围）：
- S1.3 配置系统（YAML + 优先级 + 热重载）
- S2.x 子命令填充（task / chat / graph 等）
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from qingqiu import __version__


def build_parser() -> argparse.ArgumentParser:
    """构建 argparse parser"""
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
    config_sub.add_parser("show", help="打印合并后的配置")

    # llm 子命令（S1.2 新增）
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
    """`qingqiu --version`"""
    print(f"qingqiu {__version__}")
    return 0


def cmd_config_show(_args: argparse.Namespace) -> int:
    """`qingqiu config show` · S1.1 占位（实现在 S1.3）"""
    print("# qingqiu config (S1.1 placeholder)")
    print(f"# version: {__version__}")
    print("# config_file: ~/.qingqiu/config.yaml (创建于 S1.3)")
    print("# 实际配置加载将在 S1.3 实现")
    return 0


async def cmd_llm_test_async(args: argparse.Namespace) -> int:
    """`qingqiu llm test <provider>` · S1.2 异步入口"""
    from qingqiu.llm import Message, get_provider
    from qingqiu.llm.exceptions import LLMError, ProviderInitError

    provider_name = args.provider
    print(f"[test] 初始化 {provider_name} provider ...")

    try:
        provider = get_provider(provider_name)
    except ProviderInitError as e:
        print(f"[FAIL] 初始化失败：{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[FAIL] 未知错误：{e}", file=sys.stderr)
        return 1

    print(f"[test] 初始化 OK (default_model={provider.default_model})")
    print(f"[test] 发送测试 prompt ...")

    try:
        response = await provider.complete(
            [Message(role="user", content=f"Say hello from {provider_name} and nothing else.")],
            model=args.model,
            max_tokens=50,
        )
    except LLMError as e:
        print(f"[FAIL] LLM 调用失败：{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[FAIL] 调用异常：{type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(f"[OK] {provider_name} 响应：")
    print(f"  content: {response.content!r}")
    print(f"  model:   {response.model}")
    print(f"  usage:   input={response.usage.get('input_tokens', 0)}, "
          f"output={response.usage.get('output_tokens', 0)}")
    return 0


def cmd_llm_test(args: argparse.Namespace) -> int:
    """`qingqiu llm test <provider>` · 同步包装"""
    return asyncio.run(cmd_llm_test_async(args))


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if args.command == "config" and args.subcommand == "show":
        return cmd_config_show(args)

    if args.command == "llm" and args.llm_subcommand == "test":
        return cmd_llm_test(args)

    if args.verbose:
        print(f"[verbose] qingqiu {__version__}")
        print(f"[verbose] Python {sys.version.split()[0]}")
        print(f"[verbose] Platform: {sys.platform}")

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())