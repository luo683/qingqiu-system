"""test_cli.py · qingqiu-voice CLI 测试

不调真实麦克风 / WhisperModel：
- CLI parser 测试
- mock STT / Recorder 测端到端 dispatch
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from qingqiu.voice import cli as voice_cli


# === parser ===

def test_cli_help():
    """`qingqiu-voice --help` 应该不抛异常"""
    with pytest.raises(SystemExit) as exc:
        voice_cli.main(["--help"])
    assert exc.value.code == 0


def test_cli_default_no_file_returns_one(capsys):
    """`qingqiu-voice` (没 --file) → exit 1"""
    rc = voice_cli.main([])
    assert rc == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "缺少" in combined or "file" in combined.lower()


def test_cli_run_text_executes_directly():
    """`qingqiu-voice run-text '<text>'` 跳过 STT 直接 Executor"""
    # 用 status 命令（不依赖任何 state）确认链路通
    rc = voice_cli.main(["run-text", "status"])
    assert rc == 0


def test_cli_transcribe_with_missing_file(capsys):
    """`qingqiu-voice transcribe --file <missing>` → exit 2 + 错误信息"""
    # 缺文件时 STTError 走到通用 except 分支 → exit 2
    rc = voice_cli.main(["transcribe", "--file", "/tmp/nonexistent_voice_xyz.wav"])
    assert rc in (1, 2)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "不存在" in combined or "not found" in combined.lower() or "失败" in combined


def test_cli_transcribe_with_mocked_stt(tmp_path, monkeypatch):
    """`qingqiu-voice transcribe --file <wav>` 用 fake STT 返回文字"""
    wav = tmp_path / "fake.wav"
    wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")

    class FakeSTT:
        def transcribe(self, path):
            return "你好清秋"

    # cli.py 里 `from ... import default_stt`，需要 monkeypatch 它的本地引用
    monkeypatch.setattr(voice_cli, "default_stt", lambda: FakeSTT())

    rc = voice_cli.main(["transcribe", "--file", str(wav)])
    assert rc == 0


def test_cli_run_text_with_status():
    """`qingqiu-voice run-text 'status'` → exit 0"""
    rc = voice_cli.main(["run-text", "status"])
    assert rc == 0


def test_cli_run_text_empty_returns_one():
    """`qingqiu-voice run-text ''` → exit 1"""
    rc = voice_cli.main(["run-text", ""])
    # 空字符串会被 strip 成空 → exit 1
    assert rc == 1


# === build_parser ===

def test_build_parser_returns_argparse():
    p = voice_cli.build_parser()
    assert p is not None
    # 验证有 --file 和 subcommands
    args = p.parse_args(["--file", "x.wav"])
    assert args.file == Path("x.wav")
    assert args.voice_command is None


def test_build_parser_subcommand_transcribe():
    p = voice_cli.build_parser()
    args = p.parse_args(["transcribe", "--file", "x.wav"])
    assert args.voice_command == "transcribe"
    assert args.file == Path("x.wav")