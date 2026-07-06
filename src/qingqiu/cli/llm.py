"""cli.llm · LLM 子命令（拆自老 cli.py）"""

from __future__ import annotations

import asyncio

from qingqiu.cli.errors import CLIError
from qingqiu.cli.output import OutputFormatter
from qingqiu.observability import get_logger


async def run_llm_test_async(args, out: OutputFormatter) -> int:
    """`qingqiu llm test <provider>` 异步核心"""
    from qingqiu.llm import Message, get_provider
    from qingqiu.llm.exceptions import LLMError, ProviderInitError

    log = get_logger("qingqiu.cli.llm_test")
    provider_name = args.provider
    log.info(f"开始测试 provider={provider_name}")
    if not out.json_mode:
        print(f"[test] 初始化 {provider_name} provider ...")

    try:
        provider = get_provider(provider_name)
    except ProviderInitError as e:
        log.error(f"provider 初始化失败: {provider_name}, error={e}")
        raise CLIError(f"provider 初始化失败: {e}")
    except Exception as e:
        log.error(f"provider 初始化异常: {provider_name}, type={type(e).__name__}, error={e}")
        raise CLIError(f"未知错误: {e}")

    log.info(f"provider 初始化 OK: {provider_name}, default_model={provider.default_model}")
    if not out.json_mode:
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
        raise CLIError(f"LLM 调用失败: {e}")
    except Exception as e:
        log.error(f"LLM 调用异常: {provider_name}, type={type(e).__name__}, error={e}")
        raise CLIError(f"调用异常: {type(e).__name__}: {e}")

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


def run_llm_test(args, out: OutputFormatter) -> int:
    """`qingqiu llm test <provider>` 同步包装"""
    try:
        return asyncio.run(run_llm_test_async(args, out))
    except CLIError:
        raise
    except Exception as e:
        raise CLIError(f"内部错误: {type(e).__name__}: {e}")


def build_parser(subparsers):
    """`llm` 子命令 parser 装配"""
    parser = subparsers.add_parser(
        "llm",
        help="LLM provider 管理",
    )
    parser.set_defaults(_subcommand_group="llm")
    sub = parser.add_subparsers(dest="llm_subcommand", metavar="<action>")

    p_test = sub.add_parser("test", help="测试 provider")
    p_test.add_argument(
        "provider",
        choices=["openai", "anthropic", "ollama", "custom"],
    )
    p_test.add_argument("--model", default=None)
    p_test.set_defaults(_handler=run_llm_test)

    return parser