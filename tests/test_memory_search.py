"""test_memory_search.py · P0-6 跨层 query 测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.memory import Memory


@pytest.fixture
def mem(tmp_path: Path) -> Memory:
    return Memory(base_dir=tmp_path)


def test_search_by_key(mem):
    mem.set("user_name", "ROG", layer="L3")
    mem.set("project_name", "qingqiu", layer="L1")
    results = mem.search("user")
    assert any(r["key"] == "user_name" for r in results)


def test_search_by_value(mem):
    mem.set("k1", "我喜欢 python", layer="L3")
    mem.set("k2", "我喜欢 rust", layer="L3")
    results = mem.search("python")
    assert any(r["value"] == "我喜欢 python" for r in results)
    assert not any(r["value"] == "我喜欢 rust" for r in results)


def test_search_cross_layer(mem):
    mem.set("L3_key", "在 L3", layer="L3")
    mem.set("L1_key", "在 L1", layer="L1")
    mem.set("L2_key", "在 L2", layer="L2")
    results = mem.search("在")
    assert len(results) >= 3
    layers = {r["layer"] for r in results}
    assert "L1" in layers
    assert "L2" in layers
    assert "L3" in layers


def test_search_specific_layer(mem):
    mem.set("k1", "L3 only", layer="L3")
    mem.set("k2", "L1 only", layer="L1")
    results = mem.search("only", layer="L3")
    assert all(r["layer"] == "L3" for r in results)
    assert len(results) == 1


def test_search_no_match(mem):
    mem.set("k1", "value 1", layer="L3")
    results = mem.search("不存在")
    assert results == []


def test_stats(mem):
    mem.set("a", "1", layer="L1")
    mem.set("b", "2", layer="L1")
    mem.set("c", "3", layer="L3")
    stats = mem.stats()
    assert stats["L1"]["keys"] == 2
    assert stats["L3"]["keys"] == 1
    assert "L0" in stats
    assert "L2" in stats