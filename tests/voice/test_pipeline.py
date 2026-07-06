"""test_pipeline.py · S3.4 VoicePipeline 测试

真实链路（不 mock Executor）+ mock STT：
- 验证 wav → STT → Executor.execute 的完整流程
- 验证空 STT 结果 → note="stt_empty", exit_code=1
- 验证 STT 异常 → propagate
- 验证 PipelineResult 属性（ok, exit_code, text, wav_path）
"""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from qingqiu.cli.output import OutputFormatter
from qingqiu.cli.task import TaskStore
from qingqiu.router.executor import Executor
from qingqiu.voice.pipeline import PipelineResult, VoicePipeline
from qingqiu.voice.stt import STTError


# === fake STT ===

class FakeSTT:
    """mock STT：返回固定文本"""

    def __init__(self, text: str = "memory get user_name", raise_exc: Exception | None = None):
        self.text = text
        self.raise_exc = raise_exc
        self.called = []

    def transcribe(self, wav_path):
        self.called.append(str(wav_path))
        if self.raise_exc:
            raise self.raise_exc
        return self.text


def _make_wav(path: Path, duration: float = 1.0, sr: int = 16000) -> Path:
    """生成一段测试 WAV（静音）"""
    samples = np.zeros(int(sr * duration), dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return path


@pytest.fixture
def tmp_task_store(monkeypatch):
    """monkeypatch TaskStore 用临时路径"""
    tmp = Path(tempfile.mkdtemp(prefix="qingqiu_voice_test_"))
    orig = TaskStore.__init__

    def patched(self, path=None):
        orig(self, path=path or (tmp / "tasks.json"))

    monkeypatch.setattr(TaskStore, "__init__", patched)
    return tmp


@pytest.fixture
def out() -> OutputFormatter:
    return OutputFormatter(json_mode=True, no_color=True)


# === init ===

def test_pipeline_init_defaults():
    p = VoicePipeline()
    # 默认 stt / executor 应该是真实例（lazy）
    assert p._stt is None
    assert p._executor is None


def test_pipeline_init_with_stt_and_executor():
    stt = FakeSTT()
    ex = Executor(llm_provider=None, use_llm=False)
    p = VoicePipeline(stt=stt, executor=ex)
    assert p._stt is stt
    assert p._executor is ex


def test_pipeline_lazy_properties():
    """stt / executor / recorder 属性应 lazy 加载"""
    p = VoicePipeline()
    # 触发 lazy
    stt = p.stt
    assert stt is not None
    ex = p.executor
    assert isinstance(ex, Executor)


# === run ===

def test_pipeline_run_happy_path(tmp_path, out, tmp_task_store):
    """wav → STT("memory get user_name") → Executor.execute → 0"""
    wav = _make_wav(tmp_path / "test.wav")
    stt = FakeSTT(text="memory get user_name")
    p = VoicePipeline(stt=stt)

    result = p.run(wav, out=out)

    assert isinstance(result, PipelineResult)
    assert result.text == "memory get user_name"
    assert result.exit_code == 0
    assert result.ok is True
    assert result.note == ""
    assert stt.called == [str(wav)]


def test_pipeline_run_empty_text_returns_one(tmp_path, out):
    """STT 返回空字符串时 exit_code=1 + note='stt_empty'"""
    wav = _make_wav(tmp_path / "silent.wav")
    stt = FakeSTT(text="")
    p = VoicePipeline(stt=stt)

    result = p.run(wav, out=out)

    assert result.exit_code == 1
    assert result.ok is False
    assert result.note == "stt_empty"
    assert result.text == ""


def test_pipeline_run_whitespace_only_returns_one(tmp_path, out):
    """STT 返回纯空白字符串也按空处理"""
    wav = _make_wav(tmp_path / "ws.wav")
    stt = FakeSTT(text="   \n  ")
    p = VoicePipeline(stt=stt)

    result = p.run(wav, out=out)

    assert result.exit_code == 1
    assert result.note == "stt_empty"


def test_pipeline_run_propagates_stt_error(tmp_path, out):
    """STT 抛异常 → PipelineResult(not_empty path) or propagate?

    当前实现：propagate FileNotFoundError；其他异常 try/except 包成 STTError"""
    wav = _make_wav(tmp_path / "x.wav")
    stt = FakeSTT(raise_exc=STTError("decode boom"))
    p = VoicePipeline(stt=stt)

    with pytest.raises(STTError, match="decode boom"):
        p.run(wav, out=out)


def test_pipeline_run_propagates_file_not_found(tmp_path, out):
    """WAV 不存在时应该 propagate FileNotFoundError"""
    p = VoicePipeline(stt=FakeSTT())
    missing = tmp_path / "nope.wav"
    with pytest.raises(FileNotFoundError):
        p.run(missing, out=out)


def test_pipeline_run_calls_executor_with_stt_text(tmp_path, out, tmp_task_store):
    """验证 Executor.execute 收到的 text 是 STT 的输出"""
    wav = _make_wav(tmp_path / "x.wav")
    stt = FakeSTT(text="新建任务 测试")
    captured = []

    # 注入 executor，捕获 execute 的 text 参数
    class CapturingExecutor:
        def execute(self, text, out):
            captured.append(text)
            return 0

    p = VoicePipeline(stt=stt, executor=CapturingExecutor())
    p.run(wav, out=out)
    assert captured == ["新建任务 测试"]


def test_pipeline_run_with_real_executor_e2e(tmp_path, out, tmp_task_store):
    """端到端：STT("memory set k v") → 真实 Executor.execute → 0"""
    wav = _make_wav(tmp_path / "real.wav")
    stt = FakeSTT(text="memory set k v")
    p = VoicePipeline(stt=stt)

    result = p.run(wav, out=out)

    assert result.exit_code == 0
    assert result.ok is True


# === PipelineResult ===

def test_pipeline_result_ok_property():
    pr = PipelineResult(wav_path=Path("x.wav"), text="hi", exit_code=0)
    assert pr.ok is True


def test_pipeline_result_not_ok():
    pr = PipelineResult(wav_path=Path("x.wav"), text="hi", exit_code=2)
    assert pr.ok is False


# === run_recorded ===

def test_pipeline_run_recorded_with_mock_recorder(out, tmp_task_store, monkeypatch):
    """run_recorded 用 mock recorder 验证 record → save → run 流程"""
    from qingqiu.voice.recorder import Recorder

    class FakeRecorder:
        def __init__(self):
            self.started = False
            self.stopped = False
            self.saved_to = None
            self.is_recording = False

        def start(self):
            self.started = True
            self.is_recording = True

        def stop(self):
            self.stopped = True
            self.is_recording = False

        def save(self, path):
            self.saved_to = Path(path)
            # 写真 WAV 才能让 stt.transcribe 跑
            _make_wav(self.saved_to, duration=0.5)
            return self.saved_to

    fake_rec = FakeRecorder()
    stt = FakeSTT(text="memory get user_name")
    p = VoicePipeline(stt=stt, recorder=fake_rec)

    # run_recorded 阻塞 0.1s
    result = p.run_recorded(duration_sec=0.1, out=out, save_path=tmp_task_store / "x.wav")

    assert fake_rec.started is True
    assert fake_rec.stopped is True
    assert fake_rec.saved_to is not None
    assert result.exit_code == 0
    assert result.text == "memory get user_name"