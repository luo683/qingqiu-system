"""WeeklyReport · 每周复盘生成（M10 · S10.4）

复用：
- qingqiu.memory.l3.L3FactsMemory · 长期事实读取
- qingqiu.growth.config.GrowthConfig · enabled 开关
- qingqiu.growth.reflect.ReflectKeys · L3 key 集合

特性：
- weekly() → 生成 weekly/<ISO_week>.md（如 2026-W27.md）
- growth.enabled=False 时 weekly() 返回 None，不生成
- 不调 LLM（数据汇总 + Markdown 模板）
- 任务数从 L3 读（Reflector 累积值），保证"多次 reflect → weekly 反映全部"
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.reflect import ReflectKeys
from qingqiu.memory.l3 import L3FactsMemory


def iso_week_str(ts: float | None = None) -> str:
    """时间戳 → ISO 周字符串（YYYY-Www，如 2026-W27）

    用 datetime.isocalendar() 拿 (year, week)；周一为一周第一天。
    """
    dt = datetime.fromtimestamp(ts if ts is not None else time.time(), tz=timezone.utc)
    year, week, _ = dt.isocalendar()
    return f"{year:04d}-W{week:02d}"


# 默认 top-N 数量
TOP_FACTS_LIMIT = 5


class WeeklyReport:
    """每周复盘生成器

    用法：
        l3 = L3FactsMemory(db_path)
        growth = GrowthConfig()  # 默认 enabled=True
        tasks = TaskStore()  # 任何带 .list() 的对象（仅用于活动上下文，可选）
        report = WeeklyReport(l3=l3, growth=growth, task_source=tasks)
        path = report.weekly()    # → Path 或 None（disabled 时）
    """

    def __init__(
        self,
        *,
        l3: L3FactsMemory,
        growth: GrowthConfig,
        task_source: Any = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._l3 = l3
        self._growth = growth
        self._tasks = task_source  # optional, 保留接口但不强制依赖
        self._clock = clock

    # ── 主入口 ──────────────────────────────────────────

    def weekly(self, top_limit: int = TOP_FACTS_LIMIT) -> Path | None:
        """生成当前 ISO 周的周报

        Returns:
            写入文件路径（Path）；growth.enabled=False 时返回 None。
        """
        if not self._growth.enabled:
            return None

        ts = self._clock()
        week = iso_week_str(ts)
        out_path = self._growth.weekly_dir / f"{week}.md"

        # 1. 任务汇总：从 L3 读（Reflector 累积的 values）
        task_stats = self._task_stats_from_l3()

        # 2. Top L3 facts（按 updated_at 倒序）
        top_facts = self._top_facts(limit=top_limit)
        all_fact_count = len(self._l3.list_keys())

        # 3. 渲染 markdown
        content = self._render_markdown(
            week=week,
            ts=ts,
            task_stats=task_stats,
            top_facts=top_facts,
            all_fact_count=all_fact_count,
        )

        # 4. 写入
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        return out_path

    # ── 数据收集 ──────────────────────────────────────────

    def _task_stats_from_l3(self) -> dict[str, int]:
        """从 L3 读 Reflector 写入的 4 个计数（缺则 0）"""
        def _read_int(key: str) -> int:
            val = self._l3.get(key)
            try:
                return int(val) if val is not None else 0
            except (TypeError, ValueError):
                return 0

        return {
            "total": _read_int(ReflectKeys.TASK_COUNT_TOTAL),
            "done": _read_int(ReflectKeys.TASK_COUNT_DONE),
            "pending": _read_int(ReflectKeys.TASK_COUNT_PENDING),
            "archived": _read_int(ReflectKeys.TASK_COUNT_ARCHIVED),
        }

    def _top_facts(self, limit: int) -> list[tuple[str, str, float]]:
        """取最新 limit 条 facts（按 updated_at 倒序）"""
        items: list[tuple[str, str, float]] = []
        for key in self._l3.list_keys():
            meta = self._l3.get_with_metadata(key)
            if meta is None:
                continue
            items.append((key, str(meta["value"]), float(meta["updated_at"])))
        items.sort(key=lambda x: x[2], reverse=True)
        return items[:limit]

    # ── Markdown 渲染 ──────────────────────────────────────────

    @staticmethod
    def _render_markdown(
        *,
        week: str,
        ts: float,
        task_stats: dict[str, int],
        top_facts: list[tuple[str, str, float]],
        all_fact_count: int,
    ) -> str:
        iso_ts = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        completion_rate = (
            (task_stats["done"] / task_stats["total"] * 100) if task_stats["total"] > 0 else 0.0
        )

        lines: list[str] = []
        lines.append(f"# 周报 · {week}")
        lines.append("")
        lines.append(f"- 生成时间：{iso_ts}")
        lines.append(f"- L3 总事实数：{all_fact_count}")
        lines.append("")

        # 任务汇总
        lines.append("## 任务汇总")
        lines.append("")
        lines.append("| 状态 | 数量 |")
        lines.append("|------|------|")
        lines.append(f"| 总计 | {task_stats['total']} |")
        lines.append(f"| 已完成 | {task_stats['done']} |")
        lines.append(f"| 待办 | {task_stats['pending']} |")
        lines.append(f"| 已归档 | {task_stats['archived']} |")
        lines.append(f"| 完成率 | {completion_rate:.1f}% |")
        lines.append("")

        # Top L3 facts
        lines.append(f"## Top {len(top_facts)} L3 事实（按更新时间倒序）")
        lines.append("")
        if top_facts:
            for key, value, _ in top_facts:
                # 截断过长的 value（>80 字符）
                v_disp = value if len(value) <= 80 else value[:77] + "..."
                lines.append(f"- `{key}` = {v_disp}")
        else:
            lines.append("- (empty)")
        lines.append("")

        return "\n".join(lines) + "\n"