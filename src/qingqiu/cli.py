"""qingqiu CLI 入口 · S1.1 最小骨架

S1.1 范围（IMPLEMENTATION-PLAN.md）：
- pyproject.toml ✅
- 目录结构 ✅
- `qingqiu config show` 打印占位配置（实际加载在 S1.3）
- `qingqiu --version` 输出版本号
- 验收：`python -m qingqiu --version` 跑通

后续切片（不在本 slice 范围）：
- S1.3 配置系统（YAML + 优先级 + 热重载）
- S2.x 子命令填充
"""

from __future__ import annotations

import argparse
import sys

from qingqiu import __version__


def build_parser() -> argparse.ArgumentParser:
    """构建 argparse parser · 单文件保持 < 50 行"""
    parser = argparse.ArgumentParser(
        prog="qingqiu",
        description="清秋 · 本地优先的个人 AI 助理",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="输出版本号并退出",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="输出详细日志",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # config 子命令
    config_parser = subparsers.add_parser("config", help="查看和管理配置")
    config_sub = config_parser.add_subparsers(dest="subcommand")
    config_sub.add_parser("show", help="打印合并后的配置")

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


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if args.command == "config" and args.subcommand == "show":
        return cmd_config_show(args)

    if args.verbose:
        print(f"[verbose] qingqiu {__version__}")
        print(f"[verbose] Python {sys.version.split()[0]}")
        print(f"[verbose] Platform: {sys.platform}")

    # 无匹配命令时输出帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())