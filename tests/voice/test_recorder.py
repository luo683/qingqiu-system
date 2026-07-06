"""test_recorder.py · S3.1 Recorder 测试

不依赖真实麦克风 / PortAudio：
- 直接 monkeypatch `sounddevice.InputStream` 为 fake stream
- 用 fake audio 数据手动填充 `recorder._frames` 测 save()
- 验证 WAV 输出格式正确（16-bit PCM mono @ samplerate）
"""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from qingqiu.voice.recorder import Recorder, RecorderError, RecorderHotkey


# === fake sounddevice stream ===

class FakeInputStream:
    """模拟 sd.InputStream"""

    def __init__(self, *args, **kwargs):
        self.callback = kwargs.get("callback")
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def close(self):
        pass


@pytest.fixture
def fake_sd(monkeypatch):
    """monkeypatch qingqiu.voice.recorder.sd 为 fake"""
    fake = MagicMock()
    fake.InputStream = FakeInputStream
    monkeypatch.setattr("qingqiu.voice.recorder.sd", fake)
    return fake


def _make_audio(duration_sec: float, samplerate: int = 16000, freq: float = 440.0) -> np.ndarray:
    """生成一段正弦波 float32 音频"""
    t = np.linspace(0, duration_sec, int(samplerate * duration_sec), dtype=np.float32)
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# === init ===

def test_recorder_init_defaults():
    rec = Recorder()
    assert rec.samplerate == 16000
    assert rec.channels == 1
    assert rec.dtype == "float32"
    assert rec.is_recording is False
    assert rec.duration_sec == 0.0


def test_recorder_init_custom():
    rec = Recorder(samplerate=22050, channels=1, dtype="float32")
    assert rec.samplerate == 22050
    assert rec.channels == 1


def test_recorder_frames_initially_empty():
    rec = Recorder()
    assert rec.frames.size == 0


# === start / stop（mocked sd）===

def test_recorder_start_creates_stream(fake_sd):
    rec = Recorder()
    rec.start()
    assert rec.is_recording is True
    rec.stop()
    assert rec.is_recording is False


def test_recorder_start_twice_noop(fake_sd):
    """重复 start() 应该被忽略（不是 raise）"""
    rec = Recorder()
    rec.start()
    rec.start()  # noop
    assert rec.is_recording is True
    rec.stop()


def test_recorder_stop_without_start_noop(fake_sd):
    """未 start 就 stop 不抛异常"""
    rec = Recorder()
    audio = rec.stop()
    assert audio.size == 0
    assert rec.is_recording is False


def test_recorder_stop_returns_frames(fake_sd):
    """stop() 后 frames 包含 buffer 内容"""
    rec = Recorder()
    rec.start()
    # 手动 push 一帧数据
    rec._frames.append(_make_audio(0.5))
    audio = rec.stop()
    assert audio.size > 0
    assert rec.is_recording is False


# === save / WAV ===

def test_recorder_save_empty_frames_raises(fake_sd, tmp_path):
    rec = Recorder()
    out = tmp_path / "out.wav"
    with pytest.raises(RecorderError, match="no audio frames"):
        rec.save(out)


def test_recorder_save_writes_valid_wav(fake_sd, tmp_path):
    """save() 应该写出 16-bit PCM mono WAV"""
    rec = Recorder(samplerate=16000)
    rec._frames.append(_make_audio(0.5, samplerate=16000))

    out = tmp_path / "test.wav"
    rec.save(out)

    assert out.exists()
    # 验证 WAV header
    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2  # 16-bit
        nframes = wf.getnframes()
    # 0.5s @ 16kHz ≈ 8000 frames
    assert 7000 <= nframes <= 9000


def test_recorder_save_creates_parent_dir(fake_sd, tmp_path):
    """save() 应该自动建父目录"""
    rec = Recorder()
    rec._frames.append(_make_audio(0.1))

    out = tmp_path / "deep" / "nested" / "test.wav"
    rec.save(out)
    assert out.exists()


def test_recorder_save_returns_path(fake_sd, tmp_path):
    rec = Recorder()
    rec._frames.append(_make_audio(0.1))
    out = tmp_path / "x.wav"
    result = rec.save(out)
    assert isinstance(result, Path)
    assert result == out


# === duration_sec ===

def test_recorder_duration_with_frames(fake_sd):
    rec = Recorder(samplerate=16000)
    rec._frames.append(_make_audio(1.0, samplerate=16000))
    duration = rec.duration_sec
    assert 0.95 <= duration <= 1.05


def test_recorder_duration_no_frames(fake_sd):
    rec = Recorder()
    assert rec.duration_sec == 0.0


# === RecorderHotkey ===

def test_recorder_hotkey_init_defaults():
    rec = Recorder()
    hk = RecorderHotkey(recorder=rec)
    assert hk.primary == "ctrl+shift+q"
    assert hk.fallback == "ctrl+alt+q"
    assert hk.output_dir.exists()


def test_recorder_hotkey_init_custom_bindings(tmp_path):
    rec = Recorder()
    hk = RecorderHotkey(
        recorder=rec,
        primary="ctrl+x",
        fallback="ctrl+y",
        output_dir=tmp_path / "test_hotkey",
    )
    assert hk.primary == "ctrl+x"
    assert hk.fallback == "ctrl+y"
    assert hk.output_dir == tmp_path / "test_hotkey"


def test_recorder_hotkey_start_fails_without_keyboard(monkeypatch):
    """keyboard 不可用时应该 raise RecorderError"""
    import sys as _sys

    # 模拟 keyboard 不存在
    monkeypatch.setitem(_sys.modules, "keyboard", None)
    # 重新触发 import
    rec = Recorder()
    hk = RecorderHotkey(recorder=rec)
    with pytest.raises(RecorderError, match="keyboard"):
        hk.start(blocking=False)