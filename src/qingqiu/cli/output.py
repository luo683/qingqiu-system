"""cli.output · 统一输出（human / JSON）+ 错误展示

S2.1 验收：--json / --no-color 全局 flag
"""

from __future__ import annotations

import json
import sys
from typing import Any


# ANSI color codes
class C:
    """ANSI color helper（no_color=True 时全部变空）"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    @classmethod
    def wrap(cls, no_color: bool, color: str, text: str) -> str:
        if no_color:
            return text
        return f"{color}{text}{cls.RESET}"


class OutputFormatter:
    """统一输出器

    - json_mode=True: 输出 JSON（机器友好）
    - no_color=True: 禁用 ANSI（脚本 / CI）
    """

    def __init__(
        self,
        json_mode: bool = False,
        no_color: bool = False,
        stream=None,
    ) -> None:
        self.json_mode = json_mode
        self.no_color = no_color or not sys.stdout.isatty()  # TTY 检测
        self.stream = stream or sys.stdout
        self._err_stream = sys.stderr

    # --- 正常输出 ---

    def print(self, data: Any, title: str | None = None) -> None:
        """打印数据（dict / list / str）"""
        if self.json_mode:
            payload = {"ok": True}
            if title:
                payload["title"] = title
            payload["data"] = data
            self._print_json(payload)
            return

        if title:
            self._print(C.wrap(self.no_color, C.BOLD, f"▶ {title}"))
        if isinstance(data, str):
            self._print(data)
        elif isinstance(data, (dict, list)):
            self._print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            self._print(str(data))

    def table(self, rows: list[dict], columns: list[str]) -> None:
        """打印表格"""
        if not rows:
            self._print(C.wrap(self.no_color, C.DIM, "(empty)"))
            return
        if self.json_mode:
            self._print_json({"ok": True, "data": rows})
            return

        # 计算列宽
        widths = {col: len(col) for col in columns}
        for row in rows:
            for col in columns:
                widths[col] = max(widths[col], len(str(row.get(col, ""))))

        # 表头
        header = " | ".join(
            C.wrap(self.no_color, C.BOLD, col.ljust(widths[col])) for col in columns
        )
        self._print(header)
        self._print(C.wrap(self.no_color, C.DIM, "-" * len(header)))

        # 行
        for row in rows:
            line = " | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
            self._print(line)

    # --- 错误输出 ---

    def error(self, message: str, code: int = 1, hint: str | None = None) -> None:
        """打印错误（到 stderr）"""
        if self.json_mode:
            payload = {"ok": False, "error": message, "code": code}
            if hint:
                payload["hint"] = hint
            self._print_json(payload, stream=self._err_stream)
            return

        prefix = C.wrap(self.no_color, C.RED, "✗") if not self.no_color else "x"
        line = f"{prefix} {message}"
        if hint:
            line += C.wrap(self.no_color, C.DIM, f"  (hint: {hint})")
        self._print(line, stream=self._err_stream)

    def success(self, message: str) -> None:
        """打印成功提示"""
        if self.json_mode:
            self._print_json({"ok": True, "message": message})
            return
        prefix = C.wrap(self.no_color, C.GREEN, "✓") if not self.no_color else "ok"
        self._print(f"{prefix} {message}")

    def info(self, message: str) -> None:
        """打印信息"""
        if self.json_mode:
            self._print_json({"ok": True, "info": message})
            return
        prefix = C.wrap(self.no_color, C.BLUE, "ℹ") if not self.no_color else "i"
        self._print(f"{prefix} {message}")

    # --- 内部 ---

    def _print(self, text: str, stream=None) -> None:
        s = stream or self.stream
        print(text, file=s)

    def _print_json(self, payload: dict, stream=None) -> None:
        s = stream or self.stream
        print(json.dumps(payload, indent=2, ensure_ascii=False), file=s)