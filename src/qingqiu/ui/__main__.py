"""qingqiu.ui · 启动入口

用法：
    uv run python -m qingqiu.ui                # 默认 127.0.0.1:7789
    uv run python -m qingqiu.ui --host 0.0.0.0 --port 7789
    uv run python -m qingqiu.ui --vault ./docs

为什么需要 __main__：任务约束禁止修改 cli/，所以提供模块级启动入口。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7789


def _parse_argv(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m qingqiu.ui",
        description="清秋知识图谱 UI（M9 · S9.2）",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"bind host (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default {DEFAULT_PORT})")
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="vault 目录（None → 兜底 sample data）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开启 uvicorn 热重载（开发用）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_argv(argv)
    try:
        import uvicorn  # noqa: WPS433  (lazy import for CLI startup time)
    except ImportError as e:
        print(f"error: uvicorn not installed: {e}", file=sys.stderr)
        print("hint: uv add uvicorn[standard]", file=sys.stderr)
        return 1

    from qingqiu.ui.server import create_ui_app

    app = create_ui_app(vault=args.vault)
    vault_info = str(args.vault) if args.vault else "<sample>"
    print(f"[qingqiu.ui] starting on http://{args.host}:{args.port}  vault={vault_info}")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())