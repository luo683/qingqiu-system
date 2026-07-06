"""Reflector · 任务归档 → L3 facts（M10 · S10.1）

复用 qingqiu.memory.l3.L3FactsMemory。
不调 LLM（纯统计方法）。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from qingqiu.memory.l3 import L3FactsMemory


class ReflectKeys:
    """Reflector 写入 L3 的 key 集合"""

    TASK_COUNT_TOTAL = "task_count_total"
    TASK_COUNT_DONE = "task_count_done"
    TASK_COUNT_PENDING = "task_count_pending"
    TASK_COUNT_ARCHIVED = "task_count_archived"
    LAST_REFLECT_AT = "last_reflect_at"


def _iso_utc(ts: float) -> str:
    """时间戳 → ISO 8601 UTC 字符串（带 Z 后缀）"""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Reflector:
    """任务归档 → L3 facts

    用法：
        l3 = L3FactsMemory(db_path)
        refl = Reflector(l3)
        facts = refl.reflect(tasks)   # tasks: list[dict]，每个 dict 含 status 字段

    MVP 写入 5 条 facts（task_count_* × 4 + last_reflect_at × 1）。
    不调 LLM，纯本地统计。
    """

    STATUS_FIELD = "status"

    def __init__(self, l3: L3FactsMemory) -> None:
        self._l3 = l3

    @staticmethod
    def summarize(tasks: list[dict[str, Any]]) -> dict[str, int]:
        """统计任务列表（不写 L3）"""
        total = len(tasks)
        done = sum(1 for t in tasks if t.get(Reflector.STATUS_FIELD) == "done")
        pending = sum(1 for t in tasks if t.get(Reflector.STATUS_FIELD) == "pending")
        archived = sum(1 for t in tasks if t.get(Reflector.STATUS_FIELD) == "archived")
        return {
            "total": total,
            "done": done,
            "pending": pending,
            "archived": archived,
        }

    def reflect(
        self,
        tasks: list[dict[str, Any]] | None = None,
        *,
        now: float | None = None,
    ) -> dict[str, str]:
        """统计 + 写入 L3

        Returns:
            dict[str, str]: 写入的 {key: value}（已落 L3）

        Side effect:
            5 条 facts 写入 L3（覆盖式 set）
        """
        task_list = list(tasks) if tasks is not None else []
        summary = self.summarize(task_list)
        ts = now if now is not None else time.time()

        facts = {
            ReflectKeys.TASK_COUNT_TOTAL: str(summary["total"]),
            ReflectKeys.TASK_COUNT_DONE: str(summary["done"]),
            ReflectKeys.TASK_COUNT_PENDING: str(summary["pending"]),
            ReflectKeys.TASK_COUNT_ARCHIVED: str(summary["archived"]),
            ReflectKeys.LAST_REFLECT_AT: _iso_utc(ts),
        }
        for k, v in facts.items():
            self._l3.set(k, v)
        return facts