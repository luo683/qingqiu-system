"""cli.status · 健康状态子命令

S2.1 阶段：daemon / LLM / memory 三块概况
- daemon: M2 还未实现，固定显示 "not running"
- LLM: 各 provider 配置状态（key 是否设置）
- memory: 各层 key 数

后续切片：
- M2 接入 daemon 后：探活 + 状态码
- M3 接入 web 端口：端口监听状态
"""

from __future__ import annotations

from qingqiu.cli.output import OutputFormatter


def _check_daemon() -> dict:
    """daemon 状态（M2 阶段：未实现）"""
    return {
        "running": False,
        "note": "M2 daemon 尚未实现（M2.6 接入）",
    }


def _check_llm() -> dict:
    """LLM provider 配置状态"""
    import os

    providers = {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "ollama": bool(os.environ.get("OLLAMA_HOST", "http://localhost:11434")),
        "custom": bool(os.environ.get("CUSTOM_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")),
    }
    configured = sum(1 for v in providers.values() if v)
    return {
        "providers": providers,
        "configured": configured,
        "total": len(providers),
    }


def _check_memory() -> dict:
    """memory 各层 key 数"""
    from pathlib import Path

    from qingqiu.memory import Memory

    try:
        mem = Memory()
        counts = {}
        for layer in mem.layers:
            counts[layer.name] = len(layer.list_keys())
        return {
            "layers": counts,
            "total": sum(counts.values()),
            "base_dir": str(Memory.DEFAULT_BASE_DIR),
        }
    except Exception as e:
        return {
            "error": f"{type(e).__name__}: {e}",
        }


def run_status(args, out: OutputFormatter) -> int:
    """`qingqiu status`"""
    section = getattr(args, "section", None)

    if out.json_mode:
        # JSON 模式：全输出
        payload = {}
        if section is None or section == "daemon":
            payload["daemon"] = _check_daemon()
        if section is None or section == "llm":
            payload["llm"] = _check_llm()
        if section is None or section == "memory":
            payload["memory"] = _check_memory()
        out.print(payload, title="qingqiu status")
        return 0

    # human 模式：分块彩色输出
    if section is None or section == "daemon":
        out.print(_check_daemon(), title="daemon")
    if section is None or section == "llm":
        llm = _check_llm()
        out.print({
            "configured": f"{llm['configured']}/{llm['total']} providers",
            "details": llm["providers"],
        }, title="llm")
    if section is None or section == "memory":
        mem = _check_memory()
        if "error" in mem:
            out.error(mem["error"], code=2)
        else:
            out.print(mem, title="memory")
    return 0


# === parser 装配 ===

def build_parser(subparsers):
    """`status` 子命令 parser 装配"""
    parser = subparsers.add_parser(
        "status",
        help="健康状态（daemon / LLM / memory）",
        description=(
            "健康状态：默认输出三块（daemon / LLM / memory）。\n"
            "可用 --section 只看一块。\n"
            "例：\n"
            "  qingqiu status\n"
            "  qingqiu status --section llm\n"
            "  qingqiu --json status"
        ),
        formatter_class=__import__("argparse").RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--section",
        choices=["daemon", "llm", "memory"],
        default=None,
        help="只看一块（默认三块都看）",
    )
    parser.set_defaults(_handler=run_status)
    return parser