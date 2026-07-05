"""Memory manager · 4 层统一 facade

get(key) 从 L0 → L1 → L2 → L3 顺序查找（短路）
set(key, value, layer="L3") 默认写到 L3；可指定层
"""

from __future__ import annotations

from pathlib import Path

from qingqiu.memory.base import MemoryLayer
from qingqiu.memory.l0 import L0SessionMemory
from qingqiu.memory.l1 import L1ProjectMemory
from qingqiu.memory.l2 import L2UserMemory
from qingqiu.memory.l3 import L3FactsMemory


class Memory:
    """4 层记忆统一接口（façade）

    默认初始化（base_dir 缺省 = ~/.qingqiu/memory/）：
      - L0: 会话内（内存）
      - L1: projects/default.md（项目级）
      - L2: user.md（用户级）
      - L3: facts.sqlite（长期事实）

    get(key) → (value, layer_name) | (None, "")
    set(key, value, layer="L3") → 写到指定层（默认 L3）
    delete(key, layer="L3") → 从指定层删除（默认 L3）
    """

    DEFAULT_BASE_DIR = Path.home() / ".qingqiu" / "memory"

    def __init__(
        self,
        layers: list[MemoryLayer] | None = None,
        base_dir: Path | None = None,
    ) -> None:
        if layers is not None:
            self._layers = list(layers)
            return
        bd = base_dir or self.DEFAULT_BASE_DIR
        self._layers = [
            L0SessionMemory(),
            L1ProjectMemory(bd / "projects" / "default.md"),
            L2UserMemory(bd / "user.md"),
            L3FactsMemory(bd / "facts.sqlite"),
        ]

    @property
    def layers(self) -> list[MemoryLayer]:
        """所有层（只读）"""
        return list(self._layers)

    def get(self, key: str) -> tuple[str | None, str]:
        """从 L0 开始找第一个存在的 value"""
        for layer in self._layers:
            value = layer.get(key)
            if value is not None:
                return value, layer.name
        return None, ""

    def get_from(self, layer_name: str, key: str) -> str | None:
        """从指定层读"""
        return self._find_layer(layer_name).get(key)

    def set(self, key: str, value: str, layer: str = "L3") -> None:
        """写到指定层（默认 L3）"""
        self._find_layer(layer).set(key, value)

    def delete(self, key: str, layer: str = "L3") -> bool:
        """从指定层删除"""
        return self._find_layer(layer).delete(key)

    def list_keys(self, layer: str | None = None) -> list[str]:
        """列出 key；不指定层时合并所有层"""
        if layer is not None:
            return self._find_layer(layer).list_keys()
        all_keys: set[str] = set()
        for lyr in self._layers:
            all_keys.update(lyr.list_keys())
        return sorted(all_keys)

    def _find_layer(self, name: str) -> MemoryLayer:
        for layer in self._layers:
            if layer.name == name:
                return layer
        available = [layer.name for layer in self._layers]
        raise ValueError(f"layer not found: {name!r}, available: {available}")