"""test_main_module.py · `python -m qingqiu.voice` 测试"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from qingqiu.voice import __main__ as voice_main


def test_main_module_help():
    with pytest.raises(SystemExit):
        voice_main.main(["--help"])


def test_main_module_no_args_returns_two():
    """`python -m qingqiu.voice` (没参数) → exit 2"""
    rc = voice_main.main([])
    assert rc == 2


def test_main_module_text_mode():
    """`python -m qingqiu.voice --text 'status'` → 走 Executor"""
    rc = voice_main.main(["--text", "status"])
    assert rc == 0


def test_main_module_file_and_text_conflict(tmp_path):
    """`--file` 和 `--text` 互斥"""
    rc = voice_main.main(["--file", "x.wav", "--text", "hello"])
    assert rc == 2


def test_main_module_file_missing(tmp_path):
    """`--file <missing>` → exit 2 + 错误信息"""
    rc = voice_main.main(["--file", str(tmp_path / "missing.wav")])
    assert rc == 2


def test_main_module_file_with_mocked_stt(tmp_path, monkeypatch):
    """`--file <wav>` 用 fake STT 跑完整 pipeline"""
    wav = tmp_path / "fake.wav"
    wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")

    class FakeSTT:
        def transcribe(self, path):
            return "memory set k v"

    # __main__.py 里 `from ... import default_stt`，monkeypatch 本地引用
    monkeypatch.setattr(voice_main, "default_stt", lambda: FakeSTT())

    rc = voice_main.main(["--file", str(wav)])
    assert rc == 0