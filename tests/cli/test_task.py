"""S2.1 task 子命令 + TaskStore 测试"""

import json
import time
from pathlib import Path

import pytest

from qingqiu.cli.errors import NotFoundError, ValidationError
from qingqiu.cli.output import OutputFormatter
from qingqiu.cli.task import TaskStore, build_parser


# === TaskStore · 存储层 ===

def test_taskstore_init_creates_file(tmp_path):
    """初始化应该建空文件（如不存在）"""
    store = TaskStore(tmp_path / "tasks.json")
    # 不应该立即建文件（lazy load），除非 add
    assert not (tmp_path / "tasks.json").exists()


def test_taskstore_add_returns_id(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task_id = store.add("修 S2.2 router 接入")
    assert task_id.startswith("t-")
    assert len(task_id) > 5


def test_taskstore_add_persists(tmp_path):
    p = tmp_path / "tasks.json"
    store = TaskStore(p)
    task_id = store.add("test task")
    assert p.exists()
    # 新实例应能读到
    store2 = TaskStore(p)
    task = store2.get(task_id)
    assert task is not None
    assert task["desc"] == "test task"
    assert task["status"] == "pending"


def test_taskstore_get_not_found(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    assert store.get("t-nonexistent") is None


def test_taskstore_list_all(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    store.add("a")
    store.add("b")
    store.add("c")
    tasks = store.list()
    assert len(tasks) == 3


def test_taskstore_list_filter_status(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    a = store.add("a")
    b = store.add("b")
    store.mark_done(a)
    pending = store.list(status="pending")
    done = store.list(status="done")
    assert len(pending) == 1 and pending[0]["id"] == b
    assert len(done) == 1 and done[0]["id"] == a


def test_taskstore_mark_done(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task_id = store.add("x")
    assert store.mark_done(task_id) is True
    task = store.get(task_id)
    assert task["status"] == "done"
    assert task["done_at"] is not None
    assert task["done_at"] >= task["created_at"]


def test_taskstore_mark_done_idempotent(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task_id = store.add("x")
    assert store.mark_done(task_id) is True
    assert store.mark_done(task_id) is True  # 第二次也 True


def test_taskstore_mark_done_not_found(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    assert store.mark_done("t-nope") is False


def test_taskstore_archive(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task_id = store.add("x")
    assert store.archive(task_id) is True
    assert store.get(task_id)["status"] == "archived"


def test_taskstore_archive_not_found(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    assert store.archive("t-nope") is False


def test_taskstore_handles_corrupted_file(tmp_path):
    """损坏 JSON 应该兜底为空（不抛）"""
    p = tmp_path / "tasks.json"
    p.write_text("{not valid json", encoding="utf-8")
    store = TaskStore(p)
    assert store.list() == []
    # 加新 task 应该能覆盖
    store.add("new")
    assert len(store.list()) == 1


def test_taskstore_add_empty_desc_raises(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    with pytest.raises(ValidationError):
        store.add("")
    with pytest.raises(ValidationError):
        store.add("   ")


# === CLI handler ===

@pytest.fixture
def task_store_path(tmp_path, monkeypatch):
    """隔离 tasks.json 路径"""
    # monkeypatch TaskStore 默认路径
    new_path = tmp_path / "tasks.json"
    # 直接修改 TaskStore.__init__ 的 default path 不优雅，改用 monkeypatch home
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return new_path


def test_task_add_outputs_id(capsys, task_store_path):
    from qingqiu.cli.task import run_task_add
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"description": ["fix", "bug"]})()
    rc = run_task_add(args, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "task added" in captured.out
    assert "fix bug" in captured.out


def test_task_list_empty(capsys, task_store_path):
    from qingqiu.cli.task import run_task_list
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"status": None})()
    rc = run_task_list(args, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "no tasks" in captured.out


def test_task_list_table(capsys, task_store_path):
    from qingqiu.cli.task import run_task_add, run_task_list
    out = OutputFormatter(json_mode=False, no_color=True)
    for desc in ["alpha", "beta"]:
        run_task_add(type("Args", (), {"description": [desc]})(), out)
    capsys.readouterr()  # 清空

    rc = run_task_list(type("Args", (), {"status": None})(), out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "alpha" in captured.out
    assert "beta" in captured.out


def test_task_show_not_found_raises(capsys, task_store_path):
    from qingqiu.cli.task import run_task_show
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"id": "t-nope"})()
    with pytest.raises(NotFoundError):
        run_task_show(args, out)


def test_task_show_success(capsys, task_store_path):
    from qingqiu.cli.task import run_task_add, run_task_show
    out = OutputFormatter(json_mode=False, no_color=True)
    args_add = type("Args", (), {"description": ["check"]})()
    run_task_add(args_add, out)

    # 找到 task_id
    from qingqiu.cli.task import TaskStore
    store = TaskStore()
    tasks = store.list()
    task_id = tasks[0]["id"]

    rc = run_task_show(type("Args", (), {"id": task_id})(), out)
    assert rc == 0


def test_task_done_success(capsys, task_store_path):
    from qingqiu.cli.task import run_task_add, run_task_done
    out = OutputFormatter(json_mode=False, no_color=True)
    run_task_add(type("Args", (), {"description": ["x"]})(), out)

    from qingqiu.cli.task import TaskStore
    store = TaskStore()
    task_id = store.list()[0]["id"]

    rc = run_task_done(type("Args", (), {"id": task_id})(), out)
    assert rc == 0


def test_task_done_not_found_raises(capsys, task_store_path):
    from qingqiu.cli.task import run_task_done
    out = OutputFormatter(json_mode=False, no_color=True)
    with pytest.raises(NotFoundError):
        run_task_done(type("Args", (), {"id": "t-nope"})(), out)


def test_task_list_invalid_status_raises(capsys, task_store_path):
    from qingqiu.cli.task import run_task_list
    out = OutputFormatter(json_mode=False, no_color=True)
    with pytest.raises(ValidationError):
        run_task_list(type("Args", (), {"status": "bogus"})(), out)


# === parser ===

def test_task_parser_builds():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    p = build_parser(subparsers)
    assert p is not None


def test_task_parser_list_help_lists_actions():
    import argparse
    import io
    import contextlib
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    p = build_parser(subparsers)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            p.parse_args(["--help"])
        except SystemExit:
            pass
    output = out.getvalue()
    for action in ["list", "show", "add", "done", "archive"]:
        assert action in output