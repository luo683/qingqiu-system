"""voice.stt · 语音转文字（S3.2）

faster-whisper（中文 small 模型）
- 模型在首次调用时下载（约 460MB）
- 转写输出中文文本（自动语言检测）
- 支持 compute_type="int8"（CPU 友好）

公开 API：
- STT(model_size="small", language="zh", device="cpu")
- stt.transcribe(wav_path: Path) -> str
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from faster_whisper import WhisperModel
except Exception as _exc:  # pragma: no cover
    WhisperModel = None  # type: ignore[assignment,misc]
    _IMPORT_ERROR = _exc
else:
    _IMPORT_ERROR = None

from qingqiu.observability import get_logger

log = get_logger("qingqiu.voice.stt")


class STTError(RuntimeError):
    """STT 异常（依赖未装 / 模型加载失败 / 音频解码失败）"""


def _ensure_faster_whisper():
    if WhisperModel is None:
        raise STTError(
            f"faster_whisper import failed: {_IMPORT_ERROR}。"
            "请先 `uv add faster-whisper`。"
        )


class STT:
    """语音转文字（faster-whisper 封装）

    Args:
        model_size: 模型大小（tiny/base/small/medium/large-v3）
        language:   语言代码（None=自动检测；'zh' = 中文）
        device:     'cpu' / 'cuda'
        compute_type: 'int8' / 'float16' / 'float32'
    """

    DEFAULT_MODEL_SIZE = "small"
    DEFAULT_LANGUAGE = "zh"
    DEFAULT_DEVICE = "cpu"
    DEFAULT_COMPUTE_TYPE = "int8"

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL_SIZE,
        language: Optional[str] = DEFAULT_LANGUAGE,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
    ) -> None:
        _ensure_faster_whisper()
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None  # lazy load
        self._model_load_lock_count = 0

    @property
    def model(self):
        """lazy load 模型（首次调用 transcribe 时下载/加载）"""
        if self._model is None:
            log.info(
                f"loading faster-whisper model: size={self.model_size} "
                f"device={self.device} compute_type={self.compute_type}"
            )
            self._model = WhisperModel(  # type: ignore[misc]
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            log.info("faster-whisper model loaded")
        return self._model

    def transcribe(self, wav_path: Path | str) -> str:
        """转写 WAV 文件 → 拼接后的中文文本

        Returns:
            字符串（多个 segment 用空格拼接）。识别失败返回空串。
        """
        path = Path(wav_path)
        if not path.exists():
            raise STTError(f"audio file not found: {path}")

        try:
            segments, info = self.model.transcribe(  # type: ignore[union-attr]
                str(path),
                language=self.language,
                vad_filter=True,  # 静音过滤（短录音友好）
                beam_size=1,      # 最快速度（MVP）
            )
            parts: list[str] = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    parts.append(text)
            text = " ".join(parts).strip()
            log.info(
                f"stt.transcribe: file={path.name} "
                f"lang={info.language} (prob={info.language_probability:.2f}) "
                f"duration={info.duration:.2f}s → text={text!r}"
            )
            return text
        except Exception as exc:
            log.error(f"stt.transcribe failed: {type(exc).__name__}: {exc}")
            raise STTError(f"transcribe failed: {exc}") from exc


def default_stt() -> STT:
    """工厂：默认 STT 实例（small + zh + cpu）"""
    # 允许通过环境变量覆盖（CI / 低端机）
    model_size = os.environ.get("QINGQIU_STT_MODEL", STT.DEFAULT_MODEL_SIZE)
    language = os.environ.get("QINGQIU_STT_LANG", STT.DEFAULT_LANGUAGE)
    compute_type = os.environ.get("QINGQIU_STT_COMPUTE", STT.DEFAULT_COMPUTE_TYPE)
    return STT(model_size=model_size, language=language, compute_type=compute_type)