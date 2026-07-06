"""voice.cli · `qingqiu-voice` CLI 入口

S3.4 范围：
- `qingqiu-voice --file <wav>`        识别 WAV → 路由 Executor
- `qingqiu-voice transcribe --file <wav>`  只转写（不执行）
- `qingqiu-voice record --duration N --out FILE`  录音 → 保存 WAV

设计要点：
- 复用 OutputFormatter / Executor.execute（不重新实现）
- 独立 entry point（在 pyproject.toml 注册 `qingqiu-voice`）
- 不修改 `cli/main.py`（约束范围之外）
- 真实端到端：不 mock Recorder / STT；只用 monkeypatch 隔离 sounddevice/WhisperModel
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qingqiu.cli.output import OutputFormatter
from qingqiu.router.executor import Executor
from qingqiu.voice.pipeline import VoicePipeline
from qingqiu.voice.recorder import Recorder
from qingqiu.voice.stt import STT, default_stt


# === parser ===

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qingqiu-voice",
        description="清秋语音入口（M3 切片）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "例：\n"
            "  qingqiu-voice --file recording.wav\n"
            "  qingqiu-voice transcribe --file recording.wav\n"
            "  qingqiu-voice record --duration 3 --out test.wav"
        ),
    )
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--no-color", action="store_true", help="禁用 ANSI 颜色")
    parser.add_argument(
        "--model-size",
        default=None,
        help="whisper 模型尺寸（tiny/base/small/medium/large-v3）",
    )

    subparsers = parser.add_subparsers(dest="voice_command", metavar="<action>")

    # 默认（顶层 --file）：直接转写 + 执行
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="WAV 文件路径（与 --file 同级时不需子命令，直接转写+执行）",
    )

    # === transcribe ===
    p_tr = subparsers.add_parser("transcribe", help="只转写 WAV → 输出文字")
    p_tr.add_argument("--file", type=Path, required=True, help="WAV 文件")
    p_tr.set_defaults(_handler=_handle_transcribe)

    # === record ===
    p_rec = subparsers.add_parser(
        "record",
        help="录制音频到 WAV",
        description=(
            "录制麦克风音频到 WAV 文件。例：\n"
            "  qingqiu-voice record --duration 3 --out test.wav"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_rec.add_argument(
        "--duration", type=float, required=True, help="录制时长（秒）"
    )
    p_rec.add_argument("--out", type=Path, required=True, help="输出 WAV 路径")
    p_rec.add_argument(
        "--sample-rate", type=int, default=16000, help="采样率（默认 16000）"
    )
    p_rec.set_defaults(_handler=_handle_record)

    # === run-text (debug / 跳过 STT) ===
    p_text = subparsers.add_parser(
        "run-text",
        help="跳过 STT，直接调 Executor（debug 用）",
        description="直接执行文本（不经过 STT），等同于 qingqiu ask",
    )
    p_text.add_argument("text", nargs="+", help="自然语言指令")
    p_text.set_defaults(_handler=_handle_run_text)

    return parser


# === handlers ===

def _make_out(args) -> OutputFormatter:
    return OutputFormatter(
        json_mode=getattr(args, "json", False),
        no_color=getattr(args, "no_color", False) or not sys.stdout.isatty(),
    )


def _handle_transcribe(args, out: OutputFormatter) -> int:
    """`qingqiu-voice transcribe --file <wav>`"""
    try:
        stt = (
            STT(model_size=args.model_size)
            if args.model_size
            else default_stt()
        )
        text = stt.transcribe(args.file)
    except FileNotFoundError:
        out.error(f"WAV 文件不存在: {args.file}", code=1)
        return 1
    except Exception as e:
        out.error(f"STT 失败: {type(e).__name__}: {e}", code=2)
        return 2

    if out.json_mode:
        out.print({"file": str(args.file), "text": text})
    else:
        out.info(f"识别结果: {text!r}")
    return 0 if text else 1


def _handle_record(args, out: OutputFormatter) -> int:
    """`qingqiu-voice record --duration N --out FILE`"""
    rec = Recorder(samplerate=args.sample_rate)
    try:
        import time as _t

        rec.start()
        _t.sleep(args.duration)
        rec.stop()
        path = rec.save(args.out)
    except Exception as e:
        out.error(f"录音失败: {type(e).__name__}: {e}", code=2)
        return 2

    if out.json_mode:
        out.print({"path": str(path), "duration": args.duration})
    else:
        out.success(f"已录制 {args.duration}s → {path}")
    return 0


def _handle_run_text(args, out: OutputFormatter) -> int:
    """`qingqiu-voice run-text "<text>"` — 跳过 STT 直接 Executor"""
    text = " ".join(args.text).strip()
    if not text:
        out.error("空文本", code=1)
        return 1
    executor = Executor(llm_provider=None, use_llm=False)
    return executor.execute(text, out)


def _handle_default(args, out: OutputFormatter) -> int:
    """`qingqiu-voice --file <wav>` — 转写 + 执行"""
    if args.file is None:
        out.error(
            "缺少 --file 参数",
            code=1,
            hint="qingqiu-voice --file <wav>  或  qingqiu-voice --help",
        )
        return 1

    try:
        stt = (
            STT(model_size=args.model_size)
            if args.model_size
            else default_stt()
        )
        pipeline = VoicePipeline(stt=stt, executor=Executor(llm_provider=None, use_llm=False))
        result = pipeline.run(args.file, out=out)
    except FileNotFoundError:
        out.error(f"WAV 文件不存在: {args.file}", code=1)
        return 1
    except Exception as e:
        out.error(f"pipeline 失败: {type(e).__name__}: {e}", code=2)
        return 2

    if out.json_mode:
        out.print(
            {
                "file": str(args.file),
                "text": result.text,
                "exit_code": result.exit_code,
                "ok": result.ok,
                "note": result.note,
            }
        )
    return result.exit_code


# === main ===

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = _make_out(args)

    sub = getattr(args, "voice_command", None)
    if sub == "transcribe":
        return _handle_transcribe(args, out)
    if sub == "record":
        return _handle_record(args, out)
    if sub == "run-text":
        return _handle_run_text(args, out)
    return _handle_default(args, out)


if __name__ == "__main__":
    sys.exit(main())