"""voice.recorder · 录音器（S3.1）

sounddevice 录 16kHz mono PCM → numpy.ndarray
保存为标准 WAV（16-bit PCM, mono, 16kHz — faster-whisper 期望格式）。

公开 API：
- Recorder(samplerate=16000, channels=1)         构造
- recorder.start()                                开始录音（异步）
- recorder.stop()                                 停止录音（同步）
- recorder.save(path)                             保存为 WAV（int16 PCM）
- recorder.frames                                 录音数据（np.ndarray, float32 in [-1, 1]）
- recorder.is_recording                           bool
- recorder.duration_sec                           float（已录时长）

集成热键：`Ctrl+Shift+Q`（在 Windows 上可能冲突；fallback `Ctrl+Alt+Q`）。
    hotkey = RecorderHotkey(recorder, primary="ctrl+shift+q", fallback="ctrl+alt+q")
    hotkey.start()  # blocking until KeyboardInterrupt
"""

from __future__ import annotations

import tempfile
import threading
import wave
from pathlib import Path
from typing import Callable, Optional

import numpy as np

try:
    import sounddevice as sd
except Exception as _exc:  # pragma: no cover - 测试环境可能未装 PortAudio
    sd = None  # type: ignore[assignment]
    _IMPORT_ERROR = _exc
else:
    _IMPORT_ERROR = None

from qingqiu.observability import get_logger

log = get_logger("qingqiu.voice.recorder")


class RecorderError(RuntimeError):
    """录音器异常（依赖未装 / 设备无 / 采样率不支持）"""


def _ensure_sounddevice():
    if sd is None:
        raise RecorderError(
            f"sounddevice import failed: {_IMPORT_ERROR}。"
            "请在 Windows 上安装 PortAudio 或检查 sounddevice 安装。"
        )


class Recorder:
    """同步录音器（push-to-talk 风格：start/stop 配对）

    Usage:
        rec = Recorder()
        rec.start()
        # ... user speaks ...
        rec.stop()
        rec.save(Path("output.wav"))
    """

    DEFAULT_SAMPLERATE = 16000
    DEFAULT_CHANNELS = 1

    def __init__(
        self,
        samplerate: int = DEFAULT_SAMPLERATE,
        channels: int = DEFAULT_CHANNELS,
        dtype: str = "float32",
    ) -> None:
        # 不在 __init__ 调用 _ensure_sounddevice()，让构造始终能成功
        # （sounddevice 不可用时，仅在 start/save 时报错）
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self._frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None  # type: ignore[name-defined]
        self._lock = threading.Lock()
        self._recording = False
        self._start_time: Optional[float] = None

    # --- 状态属性 ---

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def frames(self) -> np.ndarray:
        """合并后的完整录音（float32 in [-1, 1]）；若未录返回空数组"""
        if not self._frames:
            return np.zeros((0,), dtype=np.float32)
        return np.concatenate(self._frames, axis=0).flatten()

    @property
    def duration_sec(self) -> float:
        if self._frames:
            return len(self.frames) / self.samplerate
        return 0.0

    # --- 录音控制 ---

    def start(self) -> None:
        """开始录音（异步流式采集）；重复 start 会忽略"""
        _ensure_sounddevice()
        with self._lock:
            if self._recording:
                log.warning("recorder already started, ignoring duplicate start")
                return
            self._frames = []
            self._stream = sd.InputStream(  # type: ignore[name-defined]
                samplerate=self.samplerate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._on_audio,
            )
            self._stream.start()
            self._recording = True
            import time
            self._start_time = time.monotonic()
            log.info(
                f"recorder started: samplerate={self.samplerate} channels={self.channels}"
            )

    def stop(self) -> np.ndarray:
        """停止录音；返回完整音频（float32）"""
        with self._lock:
            if not self._recording:
                log.warning("recorder not running, stop is no-op")
                return self.frames
            try:
                if self._stream is not None:
                    self._stream.stop()
                    self._stream.close()
            finally:
                self._stream = None
                self._recording = False
            duration = self.duration_sec
            log.info(f"recorder stopped: duration={duration:.2f}s samples={len(self.frames)}")
            return self.frames

    # --- 持久化 ---

    def save(self, path: Path | str) -> Path:
        """保存录音为 WAV（16-bit PCM mono @ samplerate）"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        frames = self.frames
        if frames.size == 0:
            raise RecorderError("no audio frames to save (did you start/stop?)")

        # float32 [-1, 1] → int16 PCM
        pcm = np.clip(frames, -1.0, 1.0)
        pcm_int16 = (pcm * 32767.0).astype(np.int16)

        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.samplerate)
            wf.writeframes(pcm_int16.tobytes())

        log.info(f"recorder saved: path={path} duration={self.duration_sec:.2f}s")
        return path

    # --- 内部 ---

    def _on_audio(self, indata, frames_count, time_info, status) -> None:
        if status:
            log.warning(f"sounddevice status: {status}")
        # indata shape: (frames, channels) · 复制避免底层 buffer 复用
        self._frames.append(indata.copy().astype(np.float32, copy=False))


class RecorderHotkey:
    """全局热键绑定（Ctrl+Shift+Q → fallback Ctrl+Alt+Q）

    按下 → start()，再次按下 → stop() 并触发 on_stopped(path) 回调。
    阻塞主线程直到 KeyboardInterrupt。
    """

    PRIMARY = "ctrl+shift+q"
    FALLBACK = "ctrl+alt+q"

    def __init__(
        self,
        recorder: Recorder,
        on_stopped: Optional[Callable[[Path], None]] = None,
        primary: str = PRIMARY,
        fallback: str = FALLBACK,
        output_dir: Path | str | None = None,
    ) -> None:
        self.recorder = recorder
        self.on_stopped = on_stopped
        self.primary = primary
        self.fallback = fallback
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "qingqiu_voice"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._hotkey_handle = None

    def _on_press(self) -> None:
        if not self.recorder.is_recording:
            self.recorder.start()
        else:
            self.recorder.stop()
            import time
            path = self.output_dir / f"rec_{int(time.time() * 1000)}.wav"
            self.recorder.save(path)
            if self.on_stopped:
                try:
                    self.on_stopped(path)
                except Exception as exc:
                    log.error(f"on_stopped callback failed: {exc}")

    def start(self, blocking: bool = True) -> None:
        """注册热键；blocking=True 时阻塞当前线程"""
        try:
            import keyboard  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover - keyboard 在某些环境失败
            raise RecorderError(
                f"keyboard import failed: {exc}。在 Windows 上请用管理员权限运行。"
            )

        # 优先 primary；注册失败则降级 fallback
        try:
            self._hotkey_handle = keyboard.add_hotkey(self.primary, self._on_press)
            log.info(f"hotkey bound: {self.primary}")
        except Exception as exc:
            log.warning(f"primary hotkey {self.primary!r} failed: {exc}; using fallback {self.fallback!r}")
            try:
                self._hotkey_handle = keyboard.add_hotkey(self.fallback, self._on_press)
                log.info(f"hotkey bound: {self.fallback}")
            except Exception as exc2:  # pragma: no cover
                raise RecorderError(
                    f"hotkey bind failed (primary={self.primary}, fallback={self.fallback}): {exc2}"
                )

        if blocking:
            log.info("recorder hotkey listening (Ctrl+C to exit)")
            try:
                keyboard.wait()  # type: ignore[attr-defined]
            except KeyboardInterrupt:
                log.info("hotkey interrupted by user")
                self.stop()

    def stop(self) -> None:
        """注销热键；停止正在进行的录音"""
        try:
            import keyboard  # type: ignore[import-untyped]
            keyboard.remove_hotkey(self._hotkey_handle)  # type: ignore[arg-type]
        except Exception:
            pass
        if self.recorder.is_recording:
            self.recorder.stop()