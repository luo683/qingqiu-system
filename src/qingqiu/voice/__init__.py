"""qingqiu.voice · 语音入口（M3）

S3.1 · 录音（sounddevice）
S3.2 · STT（faster-whisper，中文 small）
S3.3 · TTS（piper，预留接口；本切片可选）
S3.4 · 语音 → Executor 链路

仅复用：
- router/executor.py (Executor.execute)
- observability/logger.py
- cli/output.py (OutputFormatter)

不重新实现任何业务逻辑。
"""

from qingqiu.voice.pipeline import VoicePipeline
from qingqiu.voice.recorder import Recorder
from qingqiu.voice.stt import STT

__all__ = ["Recorder", "STT", "VoicePipeline"]