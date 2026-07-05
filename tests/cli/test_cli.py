"""S2.1 测试 · CLI 子命令"""

import json
from pathlib import Path

import pytest

from qingqiu.cli.errors import (
    AlreadyExistsError,
    CLIError,
    ConfigError,
    NotFoundError,
    StorageError,
    SystemError_,
    UserError,
    ValidationError,
)
from qingqiu.cli.memory import (
    build_parser as build_memory_parser,
)
from qingqiu.cli.output import OutputFormatter


# === errors ===

def test_clierror_default_code():
    e = CLIError("boom")
    assert e.code == 1
    assert "boom" in str(e)


def test_clierror_with_hint():
    e = CLIError("boom", hint="try X")
    assert "hint: try X" in str(e)


def test_user_error_code():
    assert UserError("x").code == 1
    assert ValidationError("x").code == 1
    assert NotFoundError("x").code == 1
    assert AlreadyExistsError("x").code == 1


def test_system_error_code():
    assert SystemError_("x").code == 2
    assert ConfigError("x").code == 2
    assert StorageError("x").code == 2


def test_clierror_subclass_relationship():
    assert issubclass(UserError, CLIError)
    assert issubclass(SystemError_, CLIError)
    assert issubclass(NotFoundError, UserError)


# === output · human 模式 ===

def test_output_print_string(capsys):
    out = OutputFormatter(json_mode=False, no_color=True)
    out.print("hello world")
    captured = capsys.readouterr()
    assert "hello world" in captured.out


def test_output_print_dict(capsys):
    out = OutputFormatter(json_mode=False, no_color=True)
    out.print({"a": 1, "b": "x"})
    captured = capsys.readouterr()
    assert '"a": 1' in captured.out
    assert '"b": "x"' in captured.out


def test_output_table(capsys):
    out = OutputFormatter(json_mode=False, no_color=True)
    out.table([{"name": "alice", "age": "30"}, {"name": "bob", "age": "25"}],
              columns=["name", "age"])
    captured = capsys.readouterr()
    assert "name" in captured.out
    assert "alice" in captured.out
    assert "bob" in captured.out


def test_output_empty_table(capsys):
    out = OutputFormatter(json_mode=False, no_color=True)
    out.table([], columns=["k", "v"])
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower()


# === output · JSON 模式 ===

def test_output_json_mode(capsys):
    out = OutputFormatter(json_mode=True, no_color=True)
    out.print({"key": "value"}, title="test")
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["title"] == "test"
    assert payload["data"] == {"key": "value"}


def test_output_json_table(capsys):
    out = OutputFormatter(json_mode=True, no_color=True)
    out.table([{"a": "1"}, {"a": "2"}], columns=["a"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["data"] == [{"a": "1"}, {"a": "2"}]


def test_output_json_error_to_stderr(capsys):
    out = OutputFormatter(json_mode=True, no_color=True)
    out.error("failed", code=2, hint="try X")
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["ok"] is False
    assert payload["error"] == "failed"
    assert payload["code"] == 2
    assert payload["hint"] == "try X"


def test_output_no_color_strips_ansi(capsys):
    out = OutputFormatter(json_mode=False, no_color=True)
    out.success("done")
    captured = capsys.readouterr()
    # 不应有 ANSI 转义码
    assert "\033[" not in captured.out


# === memory 子命令 · 接 Memory facade ===

@pytest.fixture
def clean_memory_dir(tmp_path, monkeypatch):
    """隔离 memory 目录：monkeypatch Memory.DEFAULT_BASE_DIR"""
    from qingqiu.memory import Memory
    new_base = tmp_path / ".qingqiu" / "memory"
    monkeypatch.setattr(Memory, "DEFAULT_BASE_DIR", new_base)
    return new_base


def test_memory_set_default_writes_l3(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_set, run_memory_get
    out = OutputFormatter(json_mode=False, no_color=True)

    args_set = type("Args", (), {"key": "test_k", "value": "test_v", "layer": "L3"})()
    rc = run_memory_set(args_set, out)
    assert rc == 0

    args_get = type("Args", (), {"key": "test_k"})()
    rc = run_memory_get(args_get, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "test_v" in captured.out


def test_memory_set_explicit_layer_l1(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_set, run_memory_get
    out = OutputFormatter(json_mode=False, no_color=True)

    args_set = type("Args", (), {"key": "lang", "value": "python", "layer": "L1"})()
    rc = run_memory_set(args_set, out)
    assert rc == 0

    # 应该写到 L1 文件
    l1_file = clean_memory_dir / "projects" / "default.md"
    assert l1_file.exists()
    content = l1_file.read_text(encoding="utf-8")
    assert "lang = python" in content


def test_memory_get_not_found(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_get
    out = OutputFormatter(json_mode=False, no_color=True)

    args = type("Args", (), {"key": "nonexistent"})()
    rc = run_memory_get(args, out)
    assert rc == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err


def test_memory_get_json_mode(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_set, run_memory_get

    # set 用 human 输出
    out_h = OutputFormatter(json_mode=False, no_color=True)
    args_set = type("Args", (), {"key": "k", "value": "v", "layer": "L3"})()
    run_memory_set(args_set, out_h)
    capsys.readouterr()  # 清空

    # get 用 json 输出
    out_json = OutputFormatter(json_mode=True, no_color=True)
    args_get = type("Args", (), {"key": "k"})()
    rc = run_memory_get(args_get, out_json)
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["data"]["value"] == "v"
    assert payload["data"]["layer"] == "L3"


def test_memory_list_table(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_list, run_memory_set
    out = OutputFormatter(json_mode=False, no_color=True)

    for k, v in [("alpha", "1"), ("beta", "2")]:
        args = type("Args", (), {"key": k, "value": v, "layer": "L3"})()
        run_memory_set(args, out)

    args = type("Args", (), {"layer": None})()
    rc = run_memory_list(args, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "alpha" in captured.out
    assert "beta" in captured.out


def test_memory_delete_success(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_delete, run_memory_set
    out = OutputFormatter(json_mode=False, no_color=True)

    args = type("Args", (), {"key": "k", "value": "v", "layer": "L3"})()
    run_memory_set(args, out)

    args_del = type("Args", (), {"key": "k", "layer": "L3"})()
    rc = run_memory_delete(args_del, out)
    assert rc == 0


def test_memory_delete_not_found_raises(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_delete
    out = OutputFormatter(json_mode=False, no_color=True)

    args = type("Args", (), {"key": "nope", "layer": "L3"})()
    with pytest.raises(NotFoundError):
        run_memory_delete(args, out)


def test_memory_search_finds_match(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_search, run_memory_set
    out = OutputFormatter(json_mode=False, no_color=True)

    args = type("Args", (), {"key": "lang", "value": "python is great", "layer": "L3"})()
    run_memory_set(args, out)

    args_search = type("Args", (), {"query": "python"})()
    rc = run_memory_search(args_search, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "lang" in captured.out


def test_memory_search_no_match_returns_1(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_search
    out = OutputFormatter(json_mode=False, no_color=True)

    args = type("Args", (), {"query": "nonexistent_xyz"})()
    rc = run_memory_search(args_search if False else args, out)
    assert rc == 1


def test_memory_set_invalid_layer_raises(capsys, clean_memory_dir):
    from qingqiu.cli.memory import run_memory_set
    out = OutputFormatter(json_mode=False, no_color=True)

    args = type("Args", (), {"key": "k", "value": "v", "layer": "L99"})()
    with pytest.raises(ValidationError):
        run_memory_set(args, out)


# === parser 装配 ===

def test_memory_parser_builds():
    """build_memory_parser 应该能装配 parser"""
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    p = build_memory_parser(subparsers)
    assert p is not None


def test_main_parser_top_level_help():
    """顶层 --help 应包含所有子命令"""
    from qingqiu.cli.main import build_parser
    import io
    import contextlib

    parser = build_parser()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            parser.parse_args(["--help"])
        except SystemExit:
            pass
    output = out.getvalue()
    for cmd in ["ask", "chat", "task", "memory", "status", "config", "llm"]:
        assert cmd in output, f"--help should list {cmd}"