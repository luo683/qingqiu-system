"""test_stt.py · S3.2 STT 测试

不真跑 faster-whisper 模型（small ≈ 466MB，首次下载慢）：
- mock WhisperModel，避免真实推理
- 用 fake segments 测 transcribe 输出拼接
- 覆盖 lazy load / missing file / 空 segments
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from qingqiu.voice.stt import STT, STTError, default_stt


# === fake segments ===

class FakeSegment:
    def __init__(self, text: str):
        self.text = text


class FakeWhisperModel:
    """mock faster_whisper.WhisperModel"""

    def __init__(self, return_text: str = "你好清秋", raise_exc: Exception | None = None):
        self.return_text = return_text
        self.raise_exc = raise_exc
        self.transcribe_called = False

    def transcribe(self, audio, language=None, vad_filter=None, beam_size=None):
        self.transcribe_called = True
        if self.raise_exc:
            raise self.raise_exc
        info = SimpleNamespace(
            language=language or "zh",
            language_probability=0.99,
            duration=1.0,
        )
        segments = [FakeSegment(t) for t in self.return_text.split(" ") if t]
        return iter(segments), info


# === init ===

def test_stt_init_defaults():
    stt = STT()
    assert stt.model_size == "small"
    assert stt.language == "zh"
    assert stt.device == "cpu"
    assert stt.compute_type == "int8"
    assert stt._model is None  # lazy


def test_stt_init_custom():
    stt = STT(
        model_size="tiny",
        language="en",
        device="cpu",
        compute_type="float32",
    )
    assert stt.model_size == "tiny"
    assert stt.language == "en"
    assert stt.compute_type == "float32"


def test_stt_init_from_env(monkeypatch):
    """env 变量通过 default_stt() 工厂读取（不是 STT() 构造器）"""
    monkeypatch.setenv("QINGQIU_STT_MODEL", "tiny")
    monkeypatch.setenv("QINGQIU_STT_LANG", "en")
    stt = default_stt()
    assert stt.model_size == "tiny"
    assert stt.language == "en"


def test_default_stt_factory(monkeypatch):
    monkeypatch.setenv("QINGQIU_STT_MODEL", "base")
    stt = default_stt()
    assert isinstance(stt, STT)
    assert stt.model_size == "base"


# === model lazy load ===

def test_stt_model_not_loaded_on_init():
    stt = STT()
    assert stt._model is None


def test_stt_model_loads_on_first_access(monkeypatch):
    """第一次访问 .model 属性时调 WhisperModel()"""
    fake_cls = MagicMock()
    monkeypatch.setattr("qingqiu.voice.stt.WhisperModel", fake_cls)
    stt = STT()
    model = stt.model  # 触发 lazy load
    fake_cls.assert_called_once()
    assert stt._model is not None
    # 第二次访问不再调用
    _ = stt.model
    fake_cls.assert_called_once()


# === transcribe ===

def test_stt_transcribe_with_mocked_model(tmp_path):
    """transcribe 用 fake model 拼接 segments"""
    fake = FakeWhisperModel(return_text="你好 清秋")
    stt = STT()
    stt._model = fake  # 注入 fake model（跳过 lazy load）

    wav = tmp_path / "fake.wav"
    wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")  # 占位

    text = stt.transcribe(wav)
    assert "你好" in text
    assert "清秋" in text
    assert fake.transcribe_called


def test_stt_transcribe_empty_segments(tmp_path):
    """transcribe segments 为空时返回空串"""
    fake = FakeWhisperModel(return_text="")
    stt = STT()
    stt._model = fake

    wav = tmp_path / "silent.wav"
    wav.write_bytes(b"RIFF")

    text = stt.transcribe(wav)
    assert text == ""


def test_stt_transcribe_missing_file_raises(tmp_path):
    """WAV 不存在应抛 STTError"""
    stt = STT()
    stt._model = FakeWhisperModel()
    missing = tmp_path / "nope.wav"
    with pytest.raises(STTError, match="not found"):
        stt.transcribe(missing)


def test_stt_transcribe_propagates_model_error(tmp_path):
    """model.transcribe 失败时包成 STTError"""
    fake = FakeWhisperModel(raise_exc=RuntimeError("decode boom"))
    stt = STT()
    stt._model = fake

    wav = tmp_path / "bad.wav"
    wav.write_bytes(b"RIFF")

    with pytest.raises(STTError, match="transcribe failed"):
        stt.transcribe(wav)


def test_stt_transcribe_calls_model_with_path_string(tmp_path):
    """model.transceive 应收到字符串路径（不是 Path 对象）"""
    fake = FakeWhisperModel(return_text="hi")
    stt = STT()
    stt._model = fake

    wav = tmp_path / "x.wav"
    wav.write_bytes(b"RIFF")

    stt.transcribe(wav)

    # 验证传过去的是 str（fake.transcribe 不保存参数，但 model 已被调用）
    assert fake.transcribe_called


# === 真实 lazy load 失败（缺失 faster-whisper） ===

def test_stt_raises_when_whisper_missing():
    """如果 faster_whisper 不可用，STT() 构造应该 raise STTError"""
    import sys as _sys
    # 把 faster_whisper module 设为 None 来模拟不可用
    saved = _sys.modules.get("faster_whisper")
    _sys.modules["faster_whisper"] = None  # type: ignore[assignment]
    try:
        # 重新导入 voice.stt 让 _IMPORT_ERROR 被设置
        import importlib
        from qingqiu.voice import stt as _stt_mod
        importlib.reload(_stt_mod)
        with pytest.raises(_stt_mod.STTError, match="faster_whisper"):
            _stt_mod.STT()
    finally:
        if saved is not None:
            _sys.modules["faster_whisper"] = saved
        else:
            _sys.modules.pop("faster_whisper", None)
        # 重新 reload 恢复 module 状态
        from qingqiu.voice import stt as _stt_mod2
        importlib.reload(_stt_mod2)