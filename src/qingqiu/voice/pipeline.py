"""voice.pipeline · 语音 → Executor 链路（S3.4）

VoicePipeline 串接：
    wav_path → STT.transcribe → Executor.execute → 输出

公开 API：
- VoicePipeline(stt=..., executor=...)
- pipeline.run(wav_path) -> PipelineResult
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from qingqiu.cli.output import OutputFormatter
from qingqiu.observability import get_logger
from qingqiu.router.executor import Executor
from qingqiu.voice.recorder import Recorder
from qingqiu.voice.stt import STT, default_stt

log = get_logger("qingqiu.voice.pipeline")


@dataclass
class PipelineResult:
    """一次完整 run 的结果"""

    wav_path: Path
    text: str            # STT 识别出的文字
    exit_code: int       # Executor.execute 返回的 exit code
    note: str = ""       # 备注（识别空 / UNKNOWN 等）

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class VoicePipeline:
    """语音 → Executor 链路

    Args:
        stt:      STT 实例（None → default_stt() lazy）
        executor: Executor 实例（None → Executor() 默认）
        recorder: Recorder 实例（None → Recorder() 默认；run_recorded 才会用到）
    """

    def __init__(
        self,
        stt: Optional[STT] = None,
        executor: Optional[Executor] = None,
        recorder: Optional[Recorder] = None,
    ) -> None:
        self._stt = stt
        self._executor = executor
        self._recorder = recorder

    # --- 懒加载 ---

    @property
    def stt(self) -> STT:
        if self._stt is None:
            self._stt = default_stt()
        return self._stt

    @property
    def executor(self) -> Executor:
        if self._executor is None:
            self._executor = Executor(llm_provider=None, use_llm=False)
        return self._executor

    @property
    def recorder(self) -> Recorder:
        if self._recorder is None:
            self._recorder = Recorder()
        return self._recorder

    # --- 主入口 ---

    def run(self, wav_path: Path | str, out: Optional[OutputFormatter] = None) -> PipelineResult:
        """wav → stt.transcribe → executor.execute → PipelineResult"""
        wav_path = Path(wav_path)
        out = out or OutputFormatter(json_mode=False, no_color=True)

        if not wav_path.exists():
            raise FileNotFoundError(f"wav file not found: {wav_path}")

        text = self.stt.transcribe(wav_path)
        if not text or not text.strip():
            log.warning(f"stt returned empty/whitespace text for {wav_path}: {text!r}")
            return PipelineResult(wav_path=wav_path, text="", exit_code=1, note="stt_empty")

        log.info(f"pipeline: text={text!r} → executor.execute")
        exit_code = self.executor.execute(text, out)

        return PipelineResult(wav_path=wav_path, text=text, exit_code=exit_code)

    def run_recorded(
        self,
        duration_sec: float,
        out: Optional[OutputFormatter] = None,
        save_path: Optional[Path] = None,
    ) -> PipelineResult:
        """录 → 存 → 跑（阻塞；duration_sec 后自动停止）"""
        import time
        rec = self.recorder
        out = out or OutputFormatter(json_mode=False, no_color=True)
        if rec.is_recording:
            rec.stop()

        rec.start()
        out.info(f"recording for {duration_sec:.1f}s ...")
        time.sleep(duration_sec)
        rec.stop()

        save_path = save_path or (Path(tempfile.gettempdir()) / "qingqiu_voice" / "last_rec.wav")
        rec.save(save_path)
        return self.run(save_path, out)