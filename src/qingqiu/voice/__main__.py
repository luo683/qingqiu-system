"""voice.__main__ · `python -m qingqiu.voice --file <wav>` 入口

支持：
    python -m qingqiu.voice --file recording.wav
    python -m qingqiu.voice --text "memory get user_name"   # 仅跑 Executor（跳过 STT）

NOTE: 不动 cli/ 子包；这是 voice 模块的独立 entrypoint，
    由 `scripts/verify_m3.py` 调用做端到端验证。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qingqiu.cli.output import OutputFormatter
from qingqiu.router.executor import Executor
from qingqiu.voice.pipeline import VoicePipeline
from qingqiu.voice.stt import default_stt


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m qingqiu.voice",
        description="清秋 · 语音入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "例：\n"
            "  python -m qingqiu.voice --file rec.wav          # STT → Executor\n"
            "  python -m qingqiu.voice --text '看任务'          # 跳过 STT，直接 Executor\n"
        ),
    )
    p.add_argument("--file", type=Path, default=None, help="WAV 音频路径（与 --text 互斥）")
    p.add_argument("--text", type=str, default=None, help="直接给文本（跳过 STT）")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = OutputFormatter(json_mode=args.json, no_color=True)

    if not args.file and not args.text:
        out.error("必须提供 --file <wav> 或 --text <句子>", code=2)
        return 2

    if args.file and args.text:
        out.error("--file 和 --text 互斥，只能二选一", code=2)
        return 2

    if args.text:
        # 跳过 STT，直接走 Executor
        executor = Executor(llm_provider=None, use_llm=False)
        return executor.execute(args.text, out)

    if not args.file.exists():
        out.error(f"WAV 文件不存在: {args.file}", code=2, hint="检查 --file 路径")
        return 2

    pipeline = VoicePipeline(stt=default_stt())
    result = pipeline.run(args.file, out)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())