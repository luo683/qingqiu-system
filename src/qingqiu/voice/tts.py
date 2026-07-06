"""voice.tts · S3.5 文本转语音

PRD §M3 · S3.5 简化版：subprocess 调系统 TTS
- Windows: SAPI (PowerShell Add-Type)
- Linux: espeak
- macOS: say

不引入 piper（100MB 模型下载），改用系统自带。
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


def _windows_say(text: str, out_path: Path | None = None) -> bool:
    """Windows SAPI 朗读"""
    ps_cmd = f"""
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
"""
    if out_path:
        ps_cmd += f"$speak.SetOutputToWaveFile('{out_path.resolve()}')\n"
    else:
        ps_cmd += "$speak.SetOutputToDefaultAudioDevice()\n"
    ps_cmd += f"$speak.Speak('{text.replace(chr(39), chr(39)+chr(39))}')\n$speak.Dispose()\n"

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


def _linux_say(text: str, out_path: Path | None = None) -> bool:
    """Linux espeak"""
    cmd = ["espeak"]
    if out_path:
        cmd += ["-w", str(out_path)]
    cmd += [text]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def _macos_say(text: str, out_path: Path | None = None) -> bool:
    """macOS say"""
    cmd = ["say", text]
    if out_path:
        cmd = ["say", "-o", str(out_path), "--data-format=LEI16@22050", text]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def speak(text: str, out_path: Path | None = None) -> bool:
    """跨平台 TTS · 返回 True 成功"""
    if not text.strip():
        return False
    system = platform.system().lower()
    if system == "windows":
        return _windows_say(text, out_path)
    if system == "darwin":
        return _macos_say(text, out_path)
    if system == "linux":
        return _linux_say(text, out_path)
    return False


def detect_tts_engine() -> str | None:
    """返回当前系统可用的 TTS 引擎名（None = 不可用）"""
    system = platform.system().lower()
    if system == "windows":
        return "sapi"
    if system == "darwin":
        return "say"
    if system == "linux":
        if shutil.which("espeak"):
            return "espeak"
    return None