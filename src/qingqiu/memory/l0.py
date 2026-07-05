"""L0 · 会话内记忆（in-process dict）

进程退出即消失。临时变量 / 当前会话状态用这层。
不持久化。
"""

from __future__ import annotations

from threading import RLock


class L0SessionMemory:
    """L0 · 内存层（线程安全）"""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._lock = RLock()  # 线程安全（虽然单进程但防御）

    @property
    def name(self) -> str:
        return "L0"

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    def list_keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def clear(self) -> None:
        """清空（会话结束或重启）"""
        with self._lock:
            self._data.clear()