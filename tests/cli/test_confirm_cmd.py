"""S2.5 Confirm CLI 测试 · 子命令 + handler + 集成"""

from __future__ import annotations

import argparse
import contextlib
import io

import pytest

from qingqiu.cli.confirm import (
    build_parser,
    run_confirm_ask,
    run_confirm_test,
)
from qingqiu.cli.output import OutputFormatter
from qingqiu.security.confirm import (
    CLIPrompter,
    Confirm,
    ConfirmRejected,
    Prompter,
)


# === parser ===

def test_confirm_parser_builds():
    """build_parser 应该能装配 confirm 子命令"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    p = build_parser(subparsers)
    assert p is not None


def test_confirm_parser_help_lists_actions():
    """confirm --help 应包含 ask + test"""
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
    for action in ["ask", "test"]:
        assert action in output, f"confirm --help should list {action}"


def test_confirm_parser_ask_parses_summary_and_timeout():
    """qingqiu confirm ask "..." --timeout 30 解析正确"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    p = build_parser(subparsers)
    args = p.parse_args(["ask", "Apply 3 changes?", "--timeout", "30"])
    assert args.summary == "Apply 3 changes?"
    assert args.timeout == 30
    assert args.confirm_subcommand == "ask"


def test_confirm_parser_test_parses_flags():
    """qingqiu confirm test --always-no 解析正确"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    p = build_parser(subparsers)
    args = p.parse_args(["test", "--always-no", "--timeout", "1"])
    assert args.always_no is True
    assert args.always_yes is False
    assert args.timeout == 1


# === handlers · run_confirm_ask · 注入 prompter ===

class _ScriptedPrompter(Prompter):
    """测试用 prompter：按 responses 顺序返回 True/False"""

    def __init__(self, responses: list[bool]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def ask(self, summary: str, timeout_sec: int = 60) -> bool:
        self.calls.append(summary)
        if not self._responses:
            return False  # 兜底：超时/拒绝
        return self._responses.pop(0)


def test_confirm_ask_approved_returns_zero(capsys, monkeypatch):
    """ask 同意 → exit 0 + 输出 approved"""
    scripted = _ScriptedPrompter([True])
    monkeypatch.setattr(
        "qingqiu.cli.confirm.Confirm",
        lambda default_timeout=60: Confirm(prompter=scripted, default_timeout=default_timeout),
    )
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"summary": "Apply changes?", "timeout": 2})()
    rc = run_confirm_ask(args, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "approved" in captured.out
    assert "Apply changes?" in captured.out
    assert scripted.calls == ["Apply changes?"]


def test_confirm_ask_rejected_returns_one(capsys, monkeypatch):
    """ask 拒绝 → exit 1 + 输出错误"""
    scripted = _ScriptedPrompter([False])
    monkeypatch.setattr(
        "qingqiu.cli.confirm.Confirm",
        lambda default_timeout=60: Confirm(prompter=scripted, default_timeout=default_timeout),
    )
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"summary": "Delete?", "timeout": 2})()
    rc = run_confirm_ask(args, out)
    assert rc == 1
    captured = capsys.readouterr()
    assert "rejected" in captured.err.lower() or "rejected" in captured.out.lower()


def test_confirm_ask_json_mode(capsys, monkeypatch):
    """--json 模式下错误应为 JSON 格式"""
    import json
    scripted = _ScriptedPrompter([False])
    monkeypatch.setattr(
        "qingqiu.cli.confirm.Confirm",
        lambda default_timeout=60: Confirm(prompter=scripted, default_timeout=default_timeout),
    )
    out = OutputFormatter(json_mode=True, no_color=True)
    args = type("Args", (), {"summary": "x?", "timeout": 2})()
    rc = run_confirm_ask(args, out)
    assert rc == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["ok"] is False
    assert payload["code"] == 1


# === handlers · run_confirm_test ===

def test_confirm_test_always_yes_returns_zero(capsys):
    """test --always-yes → exit 0"""
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"always_yes": True, "always_no": False, "timeout": 2})()
    rc = run_confirm_test(args, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "passed" in captured.out.lower() or "approved" in captured.out.lower()


def test_confirm_test_always_no_returns_zero(capsys):
    """test --always-no → exit 0（prompter 返回 False，handler 期望 reject）"""
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"always_yes": False, "always_no": True, "timeout": 2})()
    rc = run_confirm_test(args, out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "passed" in captured.out.lower() or "rejected" in captured.out.lower()


def test_confirm_test_default_yes_returns_zero(capsys):
    """test 默认（无 flag） → exit 0（默认行为是 yes）"""
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("Args", (), {"always_yes": False, "always_no": False, "timeout": 2})()
    rc = run_confirm_test(args, out)
    assert rc == 0


# === 集成 · main 顶层 --help 包含 confirm ===

def test_main_top_level_help_includes_confirm():
    """qingqiu --help 应包含 confirm 子命令"""
    from qingqiu.cli.main import build_parser as build_main_parser

    parser = build_main_parser()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            parser.parse_args(["--help"])
        except SystemExit:
            pass
    output = out.getvalue()
    assert "confirm" in output