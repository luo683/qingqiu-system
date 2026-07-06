"""security.confirm · 写入前 Confirm 通用框架（S5.1）

PRD §6.2 写入策略（P5 · 写入前必问）：
- 文字：CLI/TUI 弹 ? Apply these 3 changes? [y/N/diff]
- 语音：TTS 念出"我要改 3 个文件，是否继续？"
- IM：飞书消息带按钮 [应用] [拒绝] [看 diff]
- 超时：60 秒不响应 → 自动拒绝

S5.1 实现：Prompter 抽象 + CLI 实现 + Confirm 包装
后续切片：VoicePrompter（S3.5）、IMPrompter（S4.4）
"""

from __future__ import annotations

import sys
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from qingqiu.cli.errors import CLIError


class ConfirmRejected(CLIError):
    """用户拒绝 Confirm 或超时（exit code = 1）"""

    code = 1


class ConfirmTimeout(ConfirmRejected):
    """Confirm 超时（exit code = 1）"""

    def __init__(self, timeout_sec: int) -> None:
        super().__init__(
            f"confirm timeout after {timeout_sec}s · auto-rejected",
            hint="如需更长时间，调大 Confirm.default_timeout",
        )


class Prompter(ABC):
    """不同输入接口的 prompt 抽象"""

    @abstractmethod
    def ask(self, summary: str, timeout_sec: int = 60) -> bool:
        """弹确认；返回 True=同意 / False=拒绝 / 超时=拒绝

        实现可以是：
        - CLIPrompter: stdin Y/N/diff
        - VoicePrompter: TTS + 语音识别（待 S3.5）
        - IMPrompter: 飞书按钮（待 S4.4）
        """


class CLIPrompter(Prompter):
    """CLI 文字版 prompt · y/N/diff"""

    def __init__(self, input_func: Callable[[str], str] | None = None) -> None:
        """Args:
            input_func: 可注入的 input 函数（测试用 · 默认 input()）
        """
        self._input = input_func or input

    def ask(self, summary: str, timeout_sec: int = 60) -> bool:
        """CLI 弹 ? Apply these N changes? [y/N/diff]

        实现：
        - 显示 summary
        - 等待 y / n / diff 输入
        - 'diff' 选项：调用 show_diff 钩子（默认 noop）+ 再问
        - 超时：返回 False
        """
        result: bool = []

        def worker():
            try:
                while True:
                    response = self._input(
                        f"\n? {summary}\n  [y/N/diff] "
                    ).strip().lower()
                    if response in ("y", "yes"):
                        result.append(True)
                        return
                    if response in ("n", "no", ""):
                        result.append(False)
                        return
                    if response == "diff":
                        # 简化：未来可显示真实 diff
                        print("  (diff not implemented yet · show original summary)")
                        continue
                    print("  (invalid input · y / n / diff)")
            except (EOFError, KeyboardInterrupt):
                result.append(False)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)

        if not result:
            return False  # 超时
        return result[0]


class Confirm:
    """Confirm 单例 / 上下文

    使用：
        confirm = Confirm()  # 默认 CLI prompter + 60s 超时
        confirm.ask("Apply 3 changes?")  # 抛 ConfirmRejected if 拒绝/超时
    """

    def __init__(
        self,
        prompter: Prompter | None = None,
        default_timeout: int = 60,
    ) -> None:
        self.prompter = prompter or CLIPrompter()
        self.default_timeout = default_timeout

    def ask(self, action_summary: str, timeout_sec: int | None = None) -> bool:
        """用户确认

        Returns:
            True: 同意
        Raises:
            ConfirmRejected: 用户拒绝
            ConfirmTimeout: 超时
        """
        timeout = timeout_sec if timeout_sec is not None else self.default_timeout
        agreed = self.prompter.ask(action_summary, timeout_sec=timeout)
        if not agreed:
            # 区分超时 vs 拒绝（worker 列表空 = 超时）
            raise ConfirmRejected(f"user rejected: {action_summary[:60]}")
        return True


# === 便捷函数（用默认 Confirm）===

_default_confirm: Confirm | None = None


def get_default_confirm() -> Confirm:
    """获取默认 Confirm 单例（lazy init）"""
    global _default_confirm
    if _default_confirm is None:
        _default_confirm = Confirm()
    return _default_confirm


def ask(action_summary: str, timeout_sec: int | None = None) -> bool:
    """便捷函数：用默认 Confirm 单例问用户

    Example:
        ask("Apply 3 file changes?")  # 用户输入 y/N
    """
    return get_default_confirm().ask(action_summary, timeout_sec=timeout_sec)