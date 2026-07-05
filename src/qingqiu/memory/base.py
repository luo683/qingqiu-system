"""Memory base - 4 层记忆统一接口"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryLayer(Protocol):
    """Memory layer 统一接口

    所有 4 层（L0 会话内 / L1 项目级 / L2 用户级 / L3 长期事实）必须实现这 4 个方法。
    sync 接口为主（简化实现 + 测试）；需要异步的层可在内部用 asyncio.run。
    """

    @property
    def name(self) -> str:
        """层名（L0 / L1 / L2 / L3）"""
        ...

    def get(self, key: str) -> str | None:
        """按 key 读取值；不存在返回 None"""
        ...

    def set(self, key: str, value: str) -> None:
        """按 key 写入值；存在则覆盖"""
        ...

    def delete(self, key: str) -> bool:
        """按 key 删除；返回是否实际删除（True=删了 / False=不存在）"""
        ...

    def list_keys(self) -> list[str]:
        """列出所有 key"""
        ...