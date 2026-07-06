"""test_planner_dag.py · S2.3 Planner 完整 DAG 测试（拓扑 + 并行组 + cycle + mermaid）"""

from __future__ import annotations

import pytest

from qingqiu.planner.dag import Plan, Step, plan, plan_with_rules


def test_topological_sort_basic():
    """基本依赖链：1 → 2 → 3"""
    p = Plan(
        task="test",
        steps=[
            Step("3", "third", "shell", depends_on=["2"]),
            Step("1", "first", "read"),
            Step("2", "second", "edit", depends_on=["1"]),
        ],
    )
    sorted_steps = p.topological_sort()
    assert [s.id for s in sorted_steps] == ["1", "2", "3"]


def test_topological_sort_parallel():
    """并行分支：1, 2 都无依赖 → 3 依赖两者"""
    p = Plan(
        task="parallel",
        steps=[
            Step("3", "join", "edit", depends_on=["1", "2"]),
            Step("1", "branch_a", "read"),
            Step("2", "branch_b", "read"),
        ],
    )
    sorted_steps = p.topological_sort()
    assert sorted_steps[2].id == "3"
    # 1 和 2 顺序由 sort 稳定保证（数字顺序）
    assert sorted_steps[0].id in ["1", "2"]
    assert sorted_steps[1].id in ["1", "2"]


def test_topological_sort_cycle_detection():
    """循环依赖：1 → 2 → 1"""
    p = Plan(
        task="cycle",
        steps=[
            Step("1", "a", "read", depends_on=["2"]),
            Step("2", "b", "read", depends_on=["1"]),
        ],
    )
    with pytest.raises(ValueError, match="cycle"):
        p.topological_sort()


def test_parallel_groups():
    """分组：Group 0 = 无依赖，Group 1 = 依赖 Group 0"""
    p = Plan(
        task="groups",
        steps=[
            Step("1", "a", "read"),
            Step("2", "b", "read"),
            Step("3", "c", "edit", depends_on=["1"]),
            Step("4", "d", "edit", depends_on=["2"]),
            Step("5", "e", "shell", depends_on=["3", "4"]),
        ],
    )
    groups = p.parallel_groups()
    assert len(groups) == 3
    assert {s.id for s in groups[0]} == {"1", "2"}
    assert {s.id for s in groups[1]} == {"3", "4"}
    assert {s.id for s in groups[2]} == {"5"}


def test_mermaid_output():
    """Mermaid 输出格式正确"""
    p = Plan(
        task="md",
        steps=[
            Step("1", "first", "read"),
            Step("2", "second", "edit", depends_on=["1"]),
        ],
    )
    md = p.to_mermaid()
    assert "graph TD" in md
    assert "1_node" in md
    assert "2_node" in md
    assert "1_node --> 2_node" in md
    assert md.startswith("```mermaid")
    assert md.endswith("```")


def test_plan_with_rules_bug_fix():
    """规则模板：修 bug → 3 步"""
    p = plan_with_rules("修 router 的 bug")
    assert p is not None
    assert len(p.steps) == 3
    assert p.steps[0].title == "定位 bug 范围"


def test_plan_with_rules_feature():
    """规则模板：实现功能 → 5 步"""
    p = plan_with_rules("实现新功能 obsidian 接入")
    assert p is not None
    assert len(p.steps) == 5


def test_plan_with_rules_no_match():
    """无匹配 → None"""
    p = plan_with_rules("hello world")
    assert p is None


def test_plan_main_entry_rule_match():
    """plan() 主入口：规则匹配时直接返"""
    p = plan("优化 performance")
    assert p is not None


def test_plan_main_entry_llm_fallback():
    """plan() 无规则匹配 + LLM → 调 LLM"""
    from unittest.mock import MagicMock

    from qingqiu.llm import LLMResponse

    mock_provider = MagicMock()

    async def mock_complete(messages, **kw):
        return LLMResponse(
            content='{"steps": [{"id": "1", "title": "investigate", "action": "read"}, {"id": "2", "title": "execute", "action": "shell", "depends_on": ["1"]}]}',
            model="mock",
            provider="mock",
        )

    mock_provider.complete = mock_complete

    p = plan("这是一个复杂任务但没有规则匹配", provider=mock_provider)
    assert p is not None
    assert len(p.steps) == 2
    assert p.steps[0].title == "investigate"


def test_plan_main_entry_no_provider_no_rule():
    """plan() 无规则 + 无 provider → None"""
    p = plan("complex unmatched task", provider=None)
    assert p is None


def test_topological_sort_empty_plan():
    """空 plan 拓扑排序"""
    p = Plan(task="empty", steps=[])
    assert p.topological_sort() == []


def test_topological_sort_single_step():
    """单 step"""
    p = Plan(task="single", steps=[Step("1", "only", "read")])
    assert [s.id for s in p.topological_sort()] == ["1"]


def test_parallel_groups_empty():
    """空 plan 分组"""
    p = Plan(task="empty", steps=[])
    assert p.parallel_groups() == []


def test_to_dict_round_trip():
    """Plan → dict → 完整字段保留"""
    p = Plan(
        task="dict test",
        steps=[
            Step("1", "first", "read", detail="init step"),
            Step("2", "second", "edit", depends_on=["1"], detail="apply patch"),
        ],
    )
    d = p.to_dict()
    assert d["task"] == "dict test"
    assert len(d["steps"]) == 2
    assert d["steps"][0]["detail"] == "init step"
    assert d["steps"][1]["depends_on"] == ["1"]


def test_e2e_rule_to_topological_to_mermaid():
    """端到端：规则 → 拓扑 → mermaid"""
    p = plan_with_rules("修 S2.2 router 的 bug")
    assert p is not None
    sorted_steps = p.topological_sort()
    assert [s.id for s in sorted_steps] == ["1", "2", "3"]
    md = p.to_mermaid()
    assert "graph TD" in md
    assert all(f"{i}_node" in md for i in ["1", "2", "3"])