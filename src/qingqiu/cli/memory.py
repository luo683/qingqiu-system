"""cli.memory · 记忆管理子命令（接 S1.5 facade）

S2.1 阶段：5 个子命令
- get <key>          读取
- set <key> <value>  写入（默认 L3，可 --layer 指定）
- list               列出全部 key
- delete <key>       删除
- search <query>     搜索（占位：精确匹配 key 名）
"""

from __future__ import annotations

from pathlib import Path

from qingqiu.cli.errors import NotFoundError, ValidationError
from qingqiu.cli.output import OutputFormatter
from qingqiu.memory import Memory


def _make_memory(base_dir: Path | None) -> Memory:
    """构造 Memory facade（base_dir 优先于默认）"""
    if base_dir is not None:
        return Memory(base_dir=base_dir)
    return Memory()


def run_memory_get(args, out: OutputFormatter) -> int:
    """`qingqiu memory get <key>`"""
    mem = _make_memory(getattr(args, "config_dir", None))
    value, layer = mem.get(args.key)
    if value is None:
        out.error(f"key not found: {args.key!r}", code=1, hint="用 `memory list` 看全部 key")
        return 1
    out.print({"key": args.key, "value": value, "layer": layer}, title=f"memory get")
    return 0


def run_memory_set(args, out: OutputFormatter) -> int:
    """`qingqiu memory set <key> <value> [--layer L0|L1|L2|L3]`"""
    layer = getattr(args, "layer", "L3")
    if layer not in ("L0", "L1", "L2", "L3"):
        raise ValidationError(
            f"invalid layer: {layer!r}",
            hint="layer 必须是 L0 / L1 / L2 / L3 之一",
        )
    mem = _make_memory(getattr(args, "config_dir", None))
    mem.set(args.key, args.value, layer=layer)
    out.success(f"set {args.key!r} in {layer} (length={len(args.value)})")
    return 0


def run_memory_list(args, out: OutputFormatter) -> int:
    """`qingqiu memory list`"""
    mem = _make_memory(getattr(args, "config_dir", None))
    layer_filter = getattr(args, "layer", None)
    keys = mem.list_keys(layer=layer_filter)

    if layer_filter:
        rows = [{"key": k, "layer": layer_filter} for k in keys]
    else:
        # 全层合并：标出每个 key 在哪层
        rows = []
        for k in keys:
            value, lyr = mem.get(k)
            rows.append({"key": k, "layer": lyr or "-", "value": value or ""})
    out.table(rows, columns=["key", "layer", "value"] if not layer_filter else ["key"])
    return 0


def run_memory_delete(args, out: OutputFormatter) -> int:
    """`qingqiu memory delete <key>`"""
    layer = getattr(args, "layer", "L3")
    if layer not in ("L0", "L1", "L2", "L3"):
        raise ValidationError(
            f"invalid layer: {layer!r}",
            hint="layer 必须是 L0 / L1 / L2 / L3 之一",
        )
    mem = _make_memory(getattr(args, "config_dir", None))
    deleted = mem.delete(args.key, layer=layer)
    if not deleted:
        raise NotFoundError(f"key not found in {layer}: {args.key!r}")
    out.success(f"deleted {args.key!r} from {layer}")
    return 0


def run_memory_search(args, out: OutputFormatter) -> int:
    """`qingqiu memory search <query>`（占位：精确匹配 key 名或 substring 匹配 value）"""
    mem = _make_memory(getattr(args, "config_dir", None))
    query = args.query
    all_keys = mem.list_keys()
    matches = []
    for k in all_keys:
        value, layer = mem.get(k)
        if query in k or (value and query in value):
            matches.append({"key": k, "layer": layer or "-", "preview": (value or "")[:60]})
    out.table(matches, columns=["key", "layer", "preview"])
    if not matches:
        out.info(f"no matches for {query!r}")
        return 1
    return 0


# === 子命令注册 ===

SUBCOMMANDS = {
    "get": run_memory_get,
    "set": run_memory_set,
    "list": run_memory_list,
    "delete": run_memory_delete,
    "search": run_memory_search,
}


def build_parser(subparsers):
    """`memory` 子命令 parser 装配"""
    parser = subparsers.add_parser(
        "memory",
        help="记忆管理（4 层：L0 内存 / L1 项目 MD / L2 用户 MD / L3 SQLite）",
        description=(
            "记忆管理：默认读写 L3（长期事实）。可用 --layer 指定层。\n"
            "例：\n"
            "  qingqiu memory set user_name ROG\n"
            "  qingqiu memory set --layer L1 project_lang python\n"
            "  qingqiu memory get user_name\n"
            "  qingqiu memory list\n"
            "  qingqiu memory search 'python'"
        ),
        formatter_class=__import__("argparse").RawDescriptionHelpFormatter,
    )
    parser.set_defaults(_subcommand_group="memory")
    memory_sub = parser.add_subparsers(dest="memory_subcommand", metavar="<action>")

    # get
    p_get = memory_sub.add_parser("get", help="按 key 读")
    p_get.add_argument("key", help="记忆 key")
    p_get.set_defaults(_handler=run_memory_get)

    # set
    p_set = memory_sub.add_parser("set", help="按 key 写")
    p_set.add_argument("key", help="记忆 key")
    p_set.add_argument("value", help="记忆 value")
    p_set.add_argument(
        "--layer",
        choices=["L0", "L1", "L2", "L3"],
        default="L3",
        help="目标层（默认 L3）",
    )
    p_set.set_defaults(_handler=run_memory_set)

    # list
    p_list = memory_sub.add_parser("list", help="列出全部 key")
    p_list.add_argument(
        "--layer",
        choices=["L0", "L1", "L2", "L3"],
        default=None,
        help="仅列指定层（默认合并 4 层）",
    )
    p_list.set_defaults(_handler=run_memory_list)

    # delete
    p_del = memory_sub.add_parser("delete", help="按 key 删")
    p_del.add_argument("key", help="记忆 key")
    p_del.add_argument(
        "--layer",
        choices=["L0", "L1", "L2", "L3"],
        default="L3",
        help="从哪层删（默认 L3）",
    )
    p_del.set_defaults(_handler=run_memory_delete)

    # search
    p_search = memory_sub.add_parser("search", help="搜 key/value（占位）")
    p_search.add_argument("query", help="搜索关键词")
    p_search.set_defaults(_handler=run_memory_search)

    return parser