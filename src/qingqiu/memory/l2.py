"""L2 · 用户级记忆（Markdown · 单文件）

存储位置：~/.qingqiu/memory/user.md
格式同 L1：`key = value`（每行一对，`#` 开头是注释）
"""

from __future__ import annotations

from pathlib import Path

from qingqiu.memory.l1 import L1ProjectMemory


class L2UserMemory(L1ProjectMemory):
    """L2 · 用户级 Markdown 记忆（继承 L1 实现，仅路径固定为 user.md）"""

    DEFAULT_PATH = Path.home() / ".qingqiu" / "memory" / "user.md"

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(path or self.DEFAULT_PATH)

    @property
    def name(self) -> str:
        return "L2"