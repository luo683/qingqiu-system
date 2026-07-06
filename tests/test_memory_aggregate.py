"""test_memory_aggregate.py · S6.2/S6.3/S6.4 L1/L2/L3 真实聚合测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.memory import Memory


@pytest.fixture
def mem(tmp_path: Path) -> Memory:
    return Memory(base_dir=tmp_path)


def test_l1_persistence_s6_2(mem, tmp_path: Path):
    """S6.2: L1 项目级记忆持久化到 MD 文件"""
    mem.set("project_lang", "python", layer="L1")
    mem.set("project_name", "qingqiu", layer="L1")

    # 文件存在
    l1_path = tmp_path / "projects" / "default.md"
    assert l1_path.exists()
    content = l1_path.read_text(encoding="utf-8")
    assert "project_lang = python" in content
    assert "project_name = qingqiu" in content

    # 新建 facade 读同一路径 → 数据持久
    mem2 = Memory(base_dir=tmp_path)
    assert mem2.get_from("L1", "project_lang") == "python"


def test_l2_user_level_s6_3(mem, tmp_path: Path):
    """S6.3: L2 用户级记忆（继承 L1，写到 user.md）"""
    mem.set("user_name", "ROG", layer="L2")

    l2_path = tmp_path / "user.md"
    assert l2_path.exists()
    content = l2_path.read_text(encoding="utf-8")
    assert "user_name = ROG" in content

    # 跨进程持久
    mem2 = Memory(base_dir=tmp_path)
    assert mem2.get_from("L2", "user_name") == "ROG"


def test_l3_sqlite_persistence_s6_4(mem, tmp_path: Path):
    """S6.4: L3 SQLite 长期事实持久化 + 跨进程"""
    mem.set("favorite_color", "blue", layer="L3")
    mem.set("timezone", "Asia/Shanghai", layer="L3")

    l3_path = tmp_path / "facts.sqlite"
    assert l3_path.exists()
    assert l3_path.stat().st_size > 0

    # 跨进程
    mem2 = Memory(base_dir=tmp_path)
    assert mem2.get_from("L3", "favorite_color") == "blue"
    assert mem2.get_from("L3", "timezone") == "Asia/Shanghai"


def test_aggregate_basic(mem):
    """Memory.aggregate() 报告每层 key 数 + 文件大小"""
    mem.set("L1_a", "x", layer="L1")
    mem.set("L1_b", "y", layer="L1")
    mem.set("L2_a", "z", layer="L2")
    mem.set("L3_a", "w", layer="L3")

    agg = mem.aggregate()
    assert agg["total_keys"] == 4
    assert agg["per_layer"]["L1"]["keys"] == 2
    assert agg["per_layer"]["L2"]["keys"] == 1
    assert agg["per_layer"]["L3"]["keys"] == 1
    assert "size_bytes" in agg["per_layer"]["L1"]
    assert "size_bytes" in agg["per_layer"]["L3"]


def test_aggregate_duplicate_keys(mem):
    """同一 key 出现在多层 → duplicate_keys 列表"""
    mem.set("shared", "from L1", layer="L1")
    mem.set("shared", "from L2", layer="L2")
    mem.set("shared", "from L3", layer="L3")

    agg = mem.aggregate()
    assert "shared" in agg["duplicate_keys"]


def test_aggregate_empty(mem):
    """空 memory aggregate"""
    agg = mem.aggregate()
    assert agg["total_keys"] == 0
    assert agg["duplicate_keys"] == []


def test_search_returns_layer_info(mem):
    """Memory.search 跨层返回 layer 信息（已实装 P0-6 验证）"""
    mem.set("k1", "python power", layer="L1")
    mem.set("k2", "rust speed", layer="L2")
    mem.set("k3", "python again", layer="L3")

    results = mem.search("python")
    layers = {r["layer"] for r in results}
    assert "L1" in layers
    assert "L3" in layers
    assert "L2" not in layers


def test_e2e_aggregate_after_10_writes(mem):
    """S6.4 验证：10 任务后聚合查询"""
    for i in range(10):
        mem.set(f"task_{i:02d}", f"task value {i}", layer="L3")

    agg = mem.aggregate()
    assert agg["per_layer"]["L3"]["keys"] == 10
    assert agg["total_keys"] == 10

    # 搜 "task" → 10 命中
    results = mem.search("task")
    assert len(results) == 10