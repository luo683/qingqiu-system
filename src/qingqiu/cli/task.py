"""cli.task · 任务管理子命令

S2.1 阶段：JSON 文件存储（轻量、可见、易测试）
S2.6 / M2.6 真实现：换 SQLite

子命令：
- list              列任务（pending / done / archived）
- show <id>         看详情
- add "<desc>"      加任务（自动生成 ID）
- done <id>         标完成
- archive <id>      归档
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from qingqiu.cli.errors import NotFoundError, ValidationError
from qingqiu.cli.output import OutputFormatter


# === 存储层 ===

class TaskStore:
    """任务 JSON 文件存储

    路径：~/.qingqiu/tasks.json
    格式：[{"id": "t-...", "desc": "...", "status": "pending|done|archived",
           "created_at": ts, "done_at": ts|null}, ...]
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".qingqiu" / "tasks.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self._tasks = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._tasks = []  # 损坏兜底

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._tasks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def list(self, status: str | None = None) -> list[dict]:
        if status is None:
            return list(self._tasks)
        return [t for t in self._tasks if t["status"] == status]

    def get(self, task_id: str) -> dict | None:
        for t in self._tasks:
            if t["id"] == task_id:
                return t
        return None

    def add(self, desc: str) -> str:
        if not desc or not desc.strip():
            raise ValidationError("task description 不能为空")
        task_id = f"t-{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "desc": desc.strip(),
            "status": "pending",
            "created_at": time.time(),
            "done_at": None,
        }
        self._tasks.append(task)
        self._save()
        return task_id

    def mark_done(self, task_id: str) -> bool:
        task = self.get(task_id)
        if task is None or task["status"] == "archived":
            return False
        if task["status"] == "done":
            return True  # 幂等
        task["status"] = "done"
        task["done_at"] = time.time()
        self._save()
        return True

    def archive(self, task_id: str) -> bool:
        task = self.get(task_id)
        if task is None:
            return False
        task["status"] = "archived"
        self._save()
        return True


# === handlers ===

def _store(getattr_args=None) -> TaskStore:
    """构造 TaskStore（支持测试隔离：args._task_path）"""
    # 默认从 ~/.qingqiu/tasks.json 读
    # 测试可通过 monkeypatch TaskStore 默认路径
    return TaskStore()


def run_task_list(args, out: OutputFormatter) -> int:
    """`qingqiu task list`"""
    store = TaskStore()
    status_filter = getattr(args, "status", None)
    if status_filter and status_filter not in ("pending", "done", "archived"):
        raise ValidationError(
            f"invalid status: {status_filter!r}",
            hint="status 必须是 pending / done / archived",
        )
    tasks = store.list(status=status_filter)
    if not tasks:
        out.info(f"no tasks (filter={status_filter or 'all'})")
        return 0
    rows = [
        {
            "id": t["id"],
            "status": t["status"],
            "desc": t["desc"][:60],
            "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(t["created_at"])),
        }
        for t in tasks
    ]
    out.table(rows, columns=["id", "status", "desc", "created"])
    return 0


def run_task_show(args, out: OutputFormatter) -> int:
    """`qingqiu task show <id>`"""
    store = TaskStore()
    task = store.get(args.id)
    if task is None:
        raise NotFoundError(f"task not found: {args.id!r}")
    out.print(task, title=f"task {args.id}")
    return 0


def run_task_add(args, out: OutputFormatter) -> int:
    """`qingqiu task add "<desc>"`"""
    desc = " ".join(args.description)
    store = TaskStore()
    task_id = store.add(desc)
    out.success(f"task added: {task_id} — {desc}")
    return 0


def run_task_done(args, out: OutputFormatter) -> int:
    """`qingqiu task done <id>`"""
    store = TaskStore()
    if not store.mark_done(args.id):
        raise NotFoundError(f"task not found or already archived: {args.id!r}")
    out.success(f"task done: {args.id}")
    return 0


def run_task_archive(args, out: OutputFormatter) -> int:
    """`qingqiu task archive <id>`"""
    store = TaskStore()
    if not store.archive(args.id):
        raise NotFoundError(f"task not found: {args.id!r}")
    out.success(f"task archived: {args.id}")
    return 0


# === parser 装配 ===

def build_parser(subparsers):
    """`task` 子命令 parser 装配"""
    parser = subparsers.add_parser(
        "task",
        help="任务管理（S2.1 JSON 存储 · S2.6 换 SQLite）",
        description=(
            "任务管理：增删改查 + 状态流转。\n"
            "例：\n"
            "  qingqiu task add '修 S2.2 router 接入'\n"
            "  qingqiu task list\n"
            "  qingqiu task list --status pending\n"
            "  qingqiu task show t-abc12345\n"
            "  qingqiu task done t-abc12345\n"
            "  qingqiu task archive t-abc12345"
        ),
        formatter_class=__import__("argparse").RawDescriptionHelpFormatter,
    )
    parser.set_defaults(_subcommand_group="task")
    sub = parser.add_subparsers(dest="task_subcommand", metavar="<action>")

    # list
    p_list = sub.add_parser("list", help="列任务")
    p_list.add_argument(
        "--status",
        choices=["pending", "done", "archived"],
        default=None,
        help="按状态过滤",
    )
    p_list.set_defaults(_handler=run_task_list)

    # show
    p_show = sub.add_parser("show", help="看任务详情")
    p_show.add_argument("id", help="task ID (如 t-abc12345)")
    p_show.set_defaults(_handler=run_task_show)

    # add
    p_add = sub.add_parser("add", help="加任务")
    p_add.add_argument("description", nargs="+", help="任务描述")
    p_add.set_defaults(_handler=run_task_add)

    # done
    p_done = sub.add_parser("done", help="标记完成")
    p_done.add_argument("id", help="task ID")
    p_done.set_defaults(_handler=run_task_done)

    # archive
    p_archive = sub.add_parser("archive", help="归档")
    p_archive.add_argument("id", help="task ID")
    p_archive.set_defaults(_handler=run_task_archive)

    return parser