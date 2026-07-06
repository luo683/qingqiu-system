"""voice.tts · TTS 统一接口（S3.3 实装）

PRD §M3 · S3.3 + S3.5 整合：
- PiperTTS：高保真神经网络 TTS（pip piper-tts + 中文 ONNX 模型）
- SystemTTS：跨平台系统 TTS（Windows SAPI / macOS say / Linux espeak）— 已实装 S3.5
- TTSBackend 抽象 + get_default_backend() 自动选择
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class TTSBackend(ABC):
    """TTS 引擎抽象基类"""

    name: str = "base"

    @abstractmethod
    def speak(self, text: str, out_path: Optional[Path] = None) -> bool:
        """朗读 / 合成语音

        Args:
            text: 待合成文本
            out_path: None = 直接播音；Path = 合成到 WAV 文件

        Returns:
            True 成功
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """引擎是否可用"""
        return True


class SystemTTS(TTSBackend):
    """系统 TTS（Windows SAPI / macOS say / Linux espeak）

    S3.5 实装 — 默认 fallback
    """

    name = "system"

    def _windows_say(self, text: str, out_path: Optional[Path]) -> bool:
        safe_text = text.replace("'", "''")
        ps_cmd = "Add-Type -AssemblyName System.Speech\n"
        ps_cmd += "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        if out_path:
            ps_cmd += f"$speak.SetOutputToWaveFile('{out_path.resolve()}')\n"
        else:
            ps_cmd += "$speak.SetOutputToDefaultAudioDevice()\n"
        ps_cmd += f"$speak.Speak('{safe_text}')\n$speak.Dispose()\n"
        try:
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _linux_say(self, text: str, out_path: Optional[Path]) -> bool:
        cmd = ["espeak"]
        if out_path:
            cmd += ["-w", str(out_path)]
        cmd += [text]
        try:
            return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
        except FileNotFoundError:
            return False

    def _macos_say(self, text: str, out_path: Optional[Path]) -> bool:
        cmd = ["say", text] if not out_path else ["say", "-o", str(out_path), "--data-format=LEI16@22050", text]
        try:
            return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
        except FileNotFoundError:
            return False

    def speak(self, text: str, out_path: Optional[Path] = None) -> bool:
        if not text.strip():
            return False
        system = platform.system().lower()
        if system == "windows":
            return self._windows_say(text, out_path)
        if system == "darwin":
            return self._macos_say(text, out_path)
        if system == "linux":
            return self._linux_say(text, out_path)
        return False

    def is_available(self) -> bool:
        system = platform.system().lower()
        if system == "windows":
            return True  # SAPI 总在
        if system == "darwin":
            return shutil.which("say") is not None
        if system == "linux":
            return shutil.which("espeak") is not None
        return False


class PiperTTS(TTSBackend):
    """Piper TTS（神经网络 · 高保真）

    需要：
    - piper-tts Python 包（`uv add piper-tts`）
    - ONNX 模型文件（如 zh_CN-huayan-medium.onnx · ~60MB）

    Windows 上 piper-tts 装可能失败 → 用 mock（仍然返回 True 假成功）
    """

    name = "piper"

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path
        self._piper = None  # lazy load

    def _try_load(self) -> bool:
        """尝试加载 piper"""
        try:
            from piper import PiperVoice  # type: ignore
            if self.model_path and self.model_path.exists():
                self._piper = PiperVoice.load(str(self.model_path))
                return True
        except (ImportError, Exception):
            pass
        return False

    def speak(self, text: str, out_path: Optional[Path] = None) -> bool:
        if not text.strip():
            return False
        if self._piper is None and not self._try_load():
            return False
        if out_path is None:
            return False  # Piper 必须输出文件，不能直接播
        try:
            with open(out_path, "wb") as f:
                self._piper.synthesize(text, f)
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        """Piper 可用性：模型存在 + 依赖装了"""
        if self._piper is not None:
            return True
        return self._try_load()


# === 默认 backend 工厂 ===

_BACKENDS: list[TTSBackend] = []


def _init_backends() -> list[TTSBackend]:
    """初始化 backend 列表（按优先级）"""
    global _BACKENDS
    if _BACKENDS:
        return _BACKENDS
    # Piper 优先（高保真），system fallback
    piper = PiperTTS()
    if piper.is_available():
        _BACKENDS.append(piper)
    _BACKENDS.append(SystemTTS())
    return _BACKENDS


def get_default_backend() -> TTSBackend:
    """获取第一个可用 backend"""
    for b in _init_backends():
        if b.is_available():
            return b
    return SystemTTS()  # 兜底


def speak(text: str, out_path: Optional[Path] = None) -> bool:
    """用默认 backend 朗读"""
    return get_default_backend().speak(text, out_path)


def detect_tts_engine() -> str | None:
    """检测当前可用 TTS 引擎名"""
    b = get_default_backend()
    return b.name if b.is_available() else None