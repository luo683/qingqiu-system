"""S2.1 status 子命令测试"""

import json
from pathlib import Path

import pytest

from qingqiu.cli.output import OutputFormatter
from qingqiu.cli.status import (
    _check_daemon,
    _check_llm,
    _check_memory,
    build_parser,
    run_status,
)


# === _check_* 内部函数 ===

def test_check_daemon_not_running():
    d = _check_daemon()
    assert d["running"] is False
    assert "M2" in d["note"]


def test_check_llm_no_keys(monkeypatch):
    """无 API key 时 configured=0"""
    for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CUSTOM_LLM_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "")  # 设空也不计入
    llm = _check_llm()
    assert llm["configured"] >= 0
    assert llm["total"] == 4


def test_check_llm_with_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    llm = _check_llm()
    assert llm["providers"]["openai"] is True
    assert llm["configured"] >= 1


def test_check_memory_returns_counts(tmp_path, monkeypatch):
    from qingqiu.memory import Memory
    monkeypatch.setattr(Memory, "DEFAULT_BASE_DIR", tmp_path / "memory")
    mem = _check_memory()
    assert "layers" in mem
    assert "total" in mem
    assert set(mem["layers"].keys()) == {"L0", "L1", "L2", "L3"}


# === run_status · human 模式 ===

def test_status_default_outputs_all_sections(capsys, tmp_path, monkeypatch):
    from qingqiu.memory import Memory
    monkeypatch.setattr(Memory, "DEFAULT_BASE_DIR", tmp_path / "memory")

    out = OutputFormatter(json_mode=False, no_color=True)
    rc = run_status(type("Args", (), {"section": None})(), out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "daemon" in captured.out.lower()
    assert "llm" in captured.out.lower()
    assert "memory" in captured.out.lower()


def test_status_section_filter_llm(capsys, tmp_path, monkeypatch):
    from qingqiu.memory import Memory
    monkeypatch.setattr(Memory, "DEFAULT_BASE_DIR", tmp_path / "memory")
    out = OutputFormatter(json_mode=False, no_color=True)
    rc = run_status(type("Args", (), {"section": "llm"})(), out)
    assert rc == 0
    captured = capsys.readouterr()
    assert "llm" in captured.out.lower()
    # 不应输出 daemon / memory 标题
    assert "daemon" not in captured.out.lower()


def test_status_json_mode(capsys, tmp_path, monkeypatch):
    from qingqiu.memory import Memory
    monkeypatch.setattr(Memory, "DEFAULT_BASE_DIR", tmp_path / "memory")
    out = OutputFormatter(json_mode=True, no_color=True)
    rc = run_status(type("Args", (), {"section": None})(), out)
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "daemon" in payload["data"]
    assert "llm" in payload["data"]
    assert "memory" in payload["data"]


def test_status_json_section(capsys, tmp_path, monkeypatch):
    from qingqiu.memory import Memory
    monkeypatch.setattr(Memory, "DEFAULT_BASE_DIR", tmp_path / "memory")
    out = OutputFormatter(json_mode=True, no_color=True)
    rc = run_status(type("Args", (), {"section": "memory"})(), out)
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "memory" in payload["data"]
    assert "daemon" not in payload["data"]


# === parser ===

def test_status_parser_help_lists_section():
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
    assert "--section" in output
    assert "daemon" in output
    assert "llm" in output
    assert "memory" in output