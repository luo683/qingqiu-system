"""ConflictDetector · 偏好冲突检测（M10 · S10.5）

检测同一 preference key 在 history 中出现多个不同值 → 写入 L3
``conflict_<key> = old→new``。

复用：
- ``qingqiu.memory.l3.L3FactsMemory``：L3 写入
- ``qingqiu.growth.config.GrowthConfig``：enabled 开关

不调 LLM：纯 dict / set 逻辑。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from qingqiu.growth.config import GrowthConfig
from qingqiu.memory.l3 import L3FactsMemory


# L3 key 前缀
CONFLICT_KEY_PREFIX = "conflict_"


# L3 默认 db 路径（与 memory/l3.py DEFAULT 一致；不依赖私有符号）
DEFAULT_L3_PATH = Path.home() / ".qingqiu" / "memory" / "facts.sqlite"


def _iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ConflictDetector:
    """偏好冲突检测器

    用法：
        detector = ConflictDetector(l3=l3)
        conflicts = detector.detect([
            ("emoji", "no"),
            ("emoji", "yes"),
        ])
        # → L3 写入 conflict_emoji = no→yes
        # → 返回 [{"key": "emoji", "old": "no", "new": "yes", "conflict_key": "conflict_emoji"}]

    MVP 行为：
    - 同一 key 在 history 中出现 ≥2 个不同值 → 判定为冲突
    - 写入 L3：``conflict_<key> = <最早值>→<最晚值>``
    - growth.enabled=False → 短路返 []（不读 history / 不写 L3）
    - 空 history / 全单值 → 返 []（不写 L3）
    - 冲突顺序：按 history 中首次出现 key 的顺序
    """

    def __init__(
        self,
        *,
        l3: L3FactsMemory | None = None,
        growth: GrowthConfig | None = None,
        db_path: Path | None = None,
        now: float | None = None,
    ) -> None:
        if l3 is not None:
            self._l3 = l3
        else:
            self._l3 = L3FactsMemory(db_path or DEFAULT_L3_PATH)
        self._growth: GrowthConfig = growth if growth is not None else GrowthConfig()
        self._now: float = now if now is not None else time.time()

    # ── 入口短路 ──────────────────────────────────────

    def is_enabled(self) -> bool:
        return self._growth.is_enabled()

    # ── 主入口 ──────────────────────────────────────

    def detect(
        self,
        preference_history: list[tuple[str, str]],
    ) -> list[dict[str, str]]:
        """检测冲突并写 L3

        Args:
            preference_history: [(key, value), ...] 按时间顺序

        Returns:
            冲突列表，每条 ``{"key", "old", "new", "conflict_key", "detected_at"}``
            disabled / 空 / 无冲突 → []
        """
        if not self.is_enabled():
            return []

        if not preference_history:
            return []

        # 收集每个 key 的所有值（保留首次出现顺序）
        values_by_key: dict[str, list[str]] = {}
        order: list[str] = []
        for k, v in preference_history:
            if k not in values_by_key:
                values_by_key[k] = []
                order.append(k)
            values_by_key[k].append(v)

        conflicts: list[dict[str, str]] = []
        detected_at = _iso_utc(self._now)

        for key in order:
            values = values_by_key[key]
            unique = set(values)
            if len(unique) <= 1:
                continue  # 无冲突

            old = values[0]
            new = values[-1]
            # 同 old/new 不算冲突（理论上 len(unique) > 1 已保证 old != new）
            if old == new:
                continue
            conflict_key = f"{CONFLICT_KEY_PREFIX}{key}"
            value = f"{old}→{new}"
            self._l3.set(conflict_key, value)
            conflicts.append({
                "key": key,
                "old": old,
                "new": new,
                "conflict_key": conflict_key,
                "detected_at": detected_at,
            })
        return conflicts
