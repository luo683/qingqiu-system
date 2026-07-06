"""cli.config · 配置子命令（拆自老 cli.py）"""

from __future__ import annotations

from qingqiu.cli.output import OutputFormatter


def run_config_show(args, out: OutputFormatter) -> int:
    """`qingqiu config show` · 打印合并后的配置"""
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


def run_config_path(args, out: OutputFormatter) -> int:
    """`qingqiu config path` · 配置文件路径"""
    from qingqiu.config import get_default_config_path

    path = get_default_config_path()
    if out.json_mode:
        out.print({"path": str(path), "exists": path.exists()})
        return 0
    print(path)
    print(f"# exists: {path.exists()}")
    return 0


def build_parser(subparsers):
    """`config` 子命令 parser 装配"""
    parser = subparsers.add_parser(
        "config",
        help="查看和管理配置",
    )
    parser.set_defaults(_subcommand_group="config")
    sub = parser.add_subparsers(dest="subcommand", metavar="<action>")

    p_show = sub.add_parser("show", help="打印合并后的配置")
    p_show.set_defaults(_handler=run_config_show)

    p_path = sub.add_parser("path", help="显示配置文件路径")
    p_path.set_defaults(_handler=run_config_path)

    return parser