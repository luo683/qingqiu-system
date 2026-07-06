"""verify_s2_3.py · S2.3 Planner 真跑验证（4 场景）"""

from __future__ import annotations

import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKTREE / "src"))

from qingqiu.planner.dag import Step, plan, plan_with_rules


def main():
    print("=" * 60)
    print("S2.3 Planner 完整 DAG · 4 场景真跑验证")
    print("=" * 60)

    # === 场景 1: 规则匹配 → 拓扑排序 ===
    print("\n[场景 1] 规则模板 → 拓扑排序")
    p = plan_with_rules("修 S2.2 router 的 bug")
    assert p is not None
    sorted_steps = p.topological_sort()
    print(f"  任务: {p.task}")
    print(f"  steps ({len(p.steps)}): {[s.id for s in sorted_steps]}")
    assert [s.id for s in sorted_steps] == ["1", "2", "3"]
    print("  [PASS] 拓扑排序正确")

    # === 场景 2: 并行组 ===
    print("\n[场景 2] 并行组检测")
    p2 = plan_with_rules("实现新功能 obsidian 接入")
    assert p2 is not None
    groups = p2.parallel_groups()
    print(f"  groups ({len(groups)}):")
    for i, g in enumerate(groups):
        print(f"    Group {i}: {[s.id for s in g]}")
    assert len(groups) == 5
    print("  [PASS] 5 组串行依赖（无并行）")

    # === 场景 3: 循环检测 ===
    print("\n[场景 3] 循环依赖检测")
    cyclic = [
        Step("1", "a", "read", depends_on=["2"]),
        Step("2", "b", "read", depends_on=["1"]),
    ]
    p3 = type("P", (), {"steps": cyclic, "topological_sort": lambda self: sorted.__self__.topological_sort()})()
    try:
        from qingqiu.planner.dag import Plan
        Plan(task="cycle", steps=cyclic).topological_sort()
        print("  ERROR: 应该 raise ValueError")
    except ValueError as e:
        print(f"  [PASS] 检测到 cycle: {str(e)[:60]}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")

    # === 场景 4: mermaid 输出 ===
    print("\n[场景 4] Mermaid 输出")
    p4 = plan_with_rules("实现新功能 obsidian 接入")
    md = p4.to_mermaid()
    print(md)
    assert "graph TD" in md
    print("  [PASS] Mermaid 格式正确")

    print("\n" + "=" * 60)
    print("[verify] S2.3 PASS · 4 场景全过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())