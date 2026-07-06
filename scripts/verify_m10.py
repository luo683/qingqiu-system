"""M10 真跑验证脚本 · 自我成长 (S10.1 reflect + S10.4 weekly)

Run: uv run python scripts/verify_m10.py

4 个验收场景（来自 task_prompt_M10.json §verify_scenarios）：
- M10-1: reflect(任务列表) → L3 新增 facts (task_count / done_count 等)
- M10-2: weekly() → 生成 weekly/2026-W27.md 内容含任务汇总 + L3 top facts
- M10-3: growth.enabled = false → weekly() 不生成（开关有效）
- M10-4: 多次 reflect → 累积 facts，weekly 输出反映全部

每个场景独立隔离（用 tmp_path / 临时 db），不会污染 ~/.qingqiu/memory/。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    # 清除外部 env var，避免污染场景
    import os
    os.environ.pop("QINGQIU_GROWTH_ENABLED", None)

    from qingqiu.growth.config import GrowthConfig
    from qingqiu.growth.reflect import ReflectKeys, Reflector
    from qingqiu.growth.weekly import WeeklyReport, iso_week_str
    from qingqiu.memory.l3 import L3FactsMemory

    failures: list[str] = []
    passed = 0

    def expect(label: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        if ok:
            print(f"  [PASS] {label}")
            passed += 1
        else:
            print(f"  [FAIL] {label} {detail}")
            failures.append(label)

    print("[verify] M10 自我成长 · S10.1 reflect + S10.4 weekly")
    print()

    # ── 场景 1: reflect(任务列表) → L3 新增 facts ──────────────
    print("[scenario 1] M10-1: reflect(任务列表) → L3 新增 5 facts")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        l3 = L3FactsMemory(tmp_path / "facts.sqlite")
        reflector = Reflector(l3)

        tasks = [
            {"id": "t1", "status": "archived"},
            {"id": "t2", "status": "done"},
            {"id": "t3", "status": "done"},
            {"id": "t4", "status": "pending"},
            {"id": "t5", "status": "pending"},
            {"id": "t6", "status": "pending"},
        ]
        written = reflector.reflect(tasks)

        # 验证：5 条 facts 都被写入
        expect("reflect 写入 5 条 facts", len(written) == 5, f"got {len(written)}")
        expect(
            f"{ReflectKeys.TASK_COUNT_TOTAL} = 6",
            l3.get(ReflectKeys.TASK_COUNT_TOTAL) == "6",
            f"got {l3.get(ReflectKeys.TASK_COUNT_TOTAL)!r}",
        )
        expect(
            f"{ReflectKeys.TASK_COUNT_DONE} = 2",
            l3.get(ReflectKeys.TASK_COUNT_DONE) == "2",
        )
        expect(
            f"{ReflectKeys.TASK_COUNT_PENDING} = 3",
            l3.get(ReflectKeys.TASK_COUNT_PENDING) == "3",
        )
        expect(
            f"{ReflectKeys.TASK_COUNT_ARCHIVED} = 1",
            l3.get(ReflectKeys.TASK_COUNT_ARCHIVED) == "1",
        )
        expect(
            f"{ReflectKeys.LAST_REFLECT_AT} 非空",
            bool(l3.get(ReflectKeys.LAST_REFLECT_AT)),
        )
    print()

    # ── 场景 2: weekly() → 生成 weekly/2026-W27.md ──────────────
    print("[scenario 2] M10-2: weekly() → 生成 weekly/<ISO_week>.md 含任务汇总 + L3 top facts")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        l3 = L3FactsMemory(tmp_path / "facts.sqlite")
        weekly_dir = tmp_path / "weekly"
        growth = GrowthConfig(enabled=True, weekly_dir=weekly_dir)

        # 先 reflect 一次写入 L3
        Reflector(l3).reflect([
            {"status": "archived"},
            {"status": "done"},
            {"status": "pending"},
        ])
        # 加几条 user fact 让 top facts 更有意义
        l3.set("user_pref_no_emoji", "true")
        l3.set("favorite_tone", "humorous")

        # 生成当前周的周报（用 deterministic clock → 2026-W27）
        ts_target = time.mktime(time.strptime("2026-07-05 12:00:00", "%Y-%m-%d %H:%M:%S"))
        report = WeeklyReport(l3=l3, growth=growth, clock=lambda: ts_target)
        path = report.weekly()

        expect("weekly() 返回 Path", path is not None)
        if path is None:
            print()
            return 1
        expect("文件存在", path.exists())
        expect(
            "文件名为 2026-W27.md",
            path.name == "2026-W27.md",
            f"got {path.name}",
        )

        md = path.read_text(encoding="utf-8")
        expect("含「任务汇总」section", "## 任务汇总" in md)
        expect("含总计行 | 3 |", "| 总计 | 3 |" in md)
        expect("含已完成行", "| 已完成 | 1 |" in md)
        expect("含待办行", "| 待办 | 1 |" in md)
        expect("含已归档行", "| 已归档 | 1 |" in md)
        expect("含完成率", "完成率" in md)
        expect("含 Top L3 facts section", "## Top" in md and "L3" in md)
        expect("top facts 含 user_pref_no_emoji", "user_pref_no_emoji" in md)
        expect("top facts 含 favorite_tone", "favorite_tone" in md)
        # reflect 写入的 5 个 fact 中至少有一个应出现在 top 5
        # （last_reflect_at 是 reflect 最后写入的，在 top 5 中概率最大）
        reflect_keys_in_top = sum(
            1 for k in (
                "task_count_total",
                "task_count_done",
                "task_count_pending",
                "task_count_archived",
                "last_reflect_at",
            )
            if k in md
        )
        expect(
            "top facts 至少含 1 个 reflect key",
            reflect_keys_in_top >= 1,
            f"got {reflect_keys_in_top}",
        )
    print()

    # ── 场景 3: growth.enabled = false → weekly() 不生成 ──────────
    print("[scenario 3] M10-3: growth.enabled = false → weekly() 不生成")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        l3 = L3FactsMemory(tmp_path / "facts.sqlite")
        weekly_dir = tmp_path / "weekly"
        # 关键：enabled=False
        growth = GrowthConfig(enabled=False, weekly_dir=weekly_dir)

        Reflector(l3).reflect([{"status": "archived"}, {"status": "pending"}])
        report = WeeklyReport(l3=l3, growth=growth)

        result = report.weekly()
        expect("weekly() 返 None", result is None)
        expect(
            "weekly_dir 未被创建",
            not weekly_dir.exists(),
            f"exists={weekly_dir.exists()}",
        )
    print()

    # ── 场景 4: 多次 reflect → 累积 facts，weekly 反映全部 ──────
    print("[scenario 4] M10-4: 多次 reflect → 累积 facts，weekly 输出反映全部")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        l3 = L3FactsMemory(tmp_path / "facts.sqlite")
        weekly_dir = tmp_path / "weekly"
        growth = GrowthConfig(enabled=True, weekly_dir=weekly_dir)

        r = Reflector(l3)
        # 第 1 次 reflect：2 个任务
        r.reflect([{"status": "archived"}, {"status": "pending"}])
        # 第 2 次 reflect：5 个任务（最终累积）
        r.reflect([
            {"status": "archived"},
            {"status": "archived"},
            {"status": "archived"},
            {"status": "done"},
            {"status": "done"},
        ])
        # 加 3 条 user fact
        l3.set("fact_a", "value_a")
        l3.set("fact_b", "value_b")
        l3.set("fact_c", "value_c")

        report = WeeklyReport(l3=l3, growth=growth)
        path = report.weekly()

        expect("weekly() 返 Path", path is not None)
        if path is None:
            print()
            return 1
        md = path.read_text(encoding="utf-8")
        # 最终状态（第 2 次 reflect 覆盖）
        expect(
            "最终 total=5 反映在 markdown",
            "| 总计 | 5 |" in md,
            "expected 5",
        )
        expect("最终 done=2", "| 已完成 | 2 |" in md)
        expect("最终 archived=3", "| 已归档 | 3 |" in md)
        expect("最终 pending=0", "| 待办 | 0 |" in md)
        # L3 总事实数：5 (reflect) + 3 (user) = 8
        expect("L3 总事实数 = 8", "L3 总事实数：8" in md, f"got md excerpt: {md[:300]}")
        # last_reflect_at 也在 top facts
        expect("last_reflect_at 在 markdown", "last_reflect_at" in md)
        # user facts 也在 top 5（按 updated_at 倒序：3 user + 5 reflect 最新写入的）
        expect("fact_a 出现", "fact_a" in md)
    print()

    # ── 总结 ──────────────────────────────────────
    if failures:
        print(f"[verify] FAIL · {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[verify] M10 PASS · {passed} assertions across 4 scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())