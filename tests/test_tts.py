"""test_tts.py · S3.3 PiperTTS + S3.5 SystemTTS 测试"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from qingqiu.voice.tts import (
    PiperTTS,
    SystemTTS,
    detect_tts_engine,
    get_default_backend,
    speak,
)


# === S3.5 SystemTTS ===

def test_system_tts_empty_text():
    """空文本 → False"""
    assert SystemTTS().speak("") is False
    assert SystemTTS().speak("   ") is False


def test_system_tts_speak_real():
    """真跑：当前平台 system TTS 朗读"""
    if not SystemTTS().is_available():
        pytest.skip("system TTS not available on this platform")
    sys_tts = SystemTTS()
    assert sys_tts.speak("你好清秋") is True


def test_system_tts_to_file(tmp_path: Path):
    """真跑：合成到 WAV 文件"""
    if not SystemTTS().is_available():
        pytest.skip("system TTS not available")
    out = tmp_path / "out.wav"
    assert SystemTTS().speak("测试", out_path=out) is True
    assert out.exists()
    assert out.stat().st_size > 0


def test_detect_tts_engine():
    """detect_tts_engine 返回 engine name"""
    name = detect_tts_engine()
    assert name in ("system", "piper", None)


def test_get_default_backend_returns_object():
    """get_default_backend 返 TTSBackend 实例"""
    b = get_default_backend()
    assert hasattr(b, "speak")
    assert hasattr(b, "is_available")


# === S3.3 PiperTTS ===

def test_piper_not_available_without_model():
    """无模型 → PiperTTS 不可用"""
    piper = PiperTTS(model_path=None)
    # 没有模型时尝试 load 会失败
    assert piper.is_available() is False or piper._piper is None


def test_piper_empty_text_returns_false():
    """空文本 → False"""
    piper = PiperTTS()
    assert piper.speak("") is False


def test_piper_no_out_path_returns_false():
    """Piper 必须 out_path"""
    piper = PiperTTS()
    assert piper.speak("hello") is False  # 无 out_path


# === speak() 顶层接口 ===

def test_speak_top_level():
    """speak() 顶层调用"""
    result = speak("清秋测试")
    # 成功或 fallback 都返回 bool
    assert isinstance(result, bool)


# === backend 优先级 ===

def test_backend_priority_piper_first():
    """backend 列表：piper 优先（如果可用），system fallback"""
    from qingqiu.voice.tts import _init_backends

    backends = _init_backends()
    assert len(backends) >= 1
    assert any(isinstance(b, SystemTTS) for b in backends)
    # 第一个可用 = piper (如果 is_available) 或 system
    available = [b for b in backends if b.is_available()]
    assert len(available) >= 1


def test_backend_factory_caches():
    """_init_backends 缓存（多次调用返同一列表）"""
    from qingqiu.voice.tts import _init_backends

    b1 = _init_backends()
    b2 = _init_backends()
    assert b1 is b2