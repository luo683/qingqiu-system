"""S1.5 测试 · 4 层记忆骨架"""

import sqlite3
from pathlib import Path

import pytest

from qingqiu.memory import (
    L0SessionMemory,
    L1ProjectMemory,
    L2UserMemory,
    L3FactsMemory,
    Memory,
    MemoryLayer,
)


# === L0 · 会话内 ===

def test_l0_basic_set_get():
    mem = L0SessionMemory()
    assert mem.get("k") is None
    mem.set("k", "v")
    assert mem.get("k") == "v"


def test_l0_overwrite():
    mem = L0SessionMemory()
    mem.set("k", "v1")
    mem.set("k", "v2")
    assert mem.get("k") == "v2"


def test_l0_delete():
    mem = L0SessionMemory()
    mem.set("k", "v")
    assert mem.delete("k") is True
    assert mem.delete("k") is False  # 第二次不存在
    assert mem.get("k") is None


def test_l0_list_keys():
    mem = L0SessionMemory()
    mem.set("a", "1")
    mem.set("b", "2")
    assert set(mem.list_keys()) == {"a", "b"}


def test_l0_clear():
    mem = L0SessionMemory()
    mem.set("a", "1")
    mem.clear()
    assert mem.list_keys() == []


def test_l0_name():
    assert L0SessionMemory().name == "L0"


# === L1 · 项目 Markdown ===

def test_l1_basic_set_get(tmp_path):
    mem = L1ProjectMemory(tmp_path / "p.md")
    mem.set("lang", "python")
    assert mem.get("lang") == "python"


def test_l1_persists_to_file(tmp_path):
    """L1 写入应该真的落到磁盘"""
    p = tmp_path / "p.md"
    mem = L1ProjectMemory(p)
    mem.set("key1", "value1")
    mem.set("key2", "value2")

    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "key1 = value1" in content
    assert "key2 = value2" in content


def test_l1_reload_picks_up_disk_state(tmp_path):
    """新实例应该从文件加载"""
    p = tmp_path / "p.md"
    mem1 = L1ProjectMemory(p)
    mem1.set("persisted", "yes")
    assert p.exists()

    # 新实例（同路径）
    mem2 = L1ProjectMemory(p)
    assert mem2.get("persisted") == "yes"


def test_l1_handles_missing_file(tmp_path):
    """文件不存在应返回 None，不报错"""
    mem = L1ProjectMemory(tmp_path / "nope.md")
    assert mem.get("anything") is None


def test_l1_skips_comments_and_blanks(tmp_path):
    """# 开头是注释，空行忽略"""
    p = tmp_path / "p.md"
    p.write_text(
        "# comment\n"
        "\n"
        "real_key = real_value\n"
        "# another comment\n"
        "k2 = v2\n",
        encoding="utf-8",
    )
    mem = L1ProjectMemory(p)
    assert mem.get("real_key") == "real_value"
    assert mem.get("k2") == "v2"
    assert "comment" not in mem.list_keys()


def test_l1_delete(tmp_path):
    mem = L1ProjectMemory(tmp_path / "p.md")
    mem.set("k", "v")
    assert mem.delete("k") is True
    assert mem.get("k") is None
    # 文件也应该更新
    content = (tmp_path / "p.md").read_text(encoding="utf-8")
    assert "k = v" not in content


def test_l1_name():
    assert L1ProjectMemory(Path("/tmp/x.md")).name == "L1"


# === L2 · 用户 Markdown ===

def test_l2_uses_default_path():
    """L2 默认路径应该是 ~/.qingqiu/memory/user.md"""
    mem = L2UserMemory()
    assert mem.name == "L2"
    assert mem.path.name == "user.md"
    assert ".qingqiu" in str(mem.path)


def test_l2_custom_path(tmp_path):
    mem = L2UserMemory(tmp_path / "my_user.md")
    mem.set("pref", "dark_mode")
    assert mem.get("pref") == "dark_mode"
    assert (tmp_path / "my_user.md").exists()


# === L3 · SQLite ===

def test_l3_basic_set_get(tmp_path):
    mem = L3FactsMemory(tmp_path / "facts.sqlite")
    assert mem.get("k") is None
    mem.set("k", "v")
    assert mem.get("k") == "v"


def test_l3_persists_across_instances(tmp_path):
    """SQLite 数据应该跨进程持久化"""
    db = tmp_path / "facts.sqlite"
    mem1 = L3FactsMemory(db)
    mem1.set("user_name", "ROG")
    mem1.set("count", "42")

    # 新实例（模拟进程重启）
    mem2 = L3FactsMemory(db)
    assert mem2.get("user_name") == "ROG"
    assert mem2.get("count") == "42"


def test_l3_overwrite_keeps_history(tmp_path):
    """覆盖应该更新 updated_at；created_at 不变"""
    db = tmp_path / "facts.sqlite"
    mem = L3FactsMemory(db)
    mem.set("k", "v1")
    meta1 = mem.get_with_metadata("k")
    assert meta1 is not None
    assert meta1["value"] == "v1"

    import time
    time.sleep(0.01)  # 确保时间戳差异

    mem.set("k", "v2")
    meta2 = mem.get_with_metadata("k")
    assert meta2["value"] == "v2"
    assert meta2["created_at"] == meta1["created_at"]  # 不变
    assert meta2["updated_at"] > meta1["updated_at"]  # 更新


def test_l3_delete(tmp_path):
    db = tmp_path / "facts.sqlite"
    mem = L3FactsMemory(db)
    mem.set("k", "v")
    assert mem.delete("k") is True
    assert mem.delete("k") is False  # 不存在
    assert mem.count() == 0


def test_l3_list_keys_sorted(tmp_path):
    mem = L3FactsMemory(tmp_path / "facts.sqlite")
    mem.set("z", "1")
    mem.set("a", "2")
    mem.set("m", "3")
    assert mem.list_keys() == ["a", "m", "z"]


def test_l3_table_schema(tmp_path):
    """验证 facts 表结构"""
    db = tmp_path / "facts.sqlite"
    L3FactsMemory(db)
    with sqlite3.connect(db) as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()]
    assert "key" in cols
    assert "value" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_l3_name():
    assert L3FactsMemory(Path("/tmp/facts.sqlite")).name == "L3"


# === Memory · 4 层统一 facade ===

def test_memory_default_layers():
    """默认应该初始化 4 层"""
    mem = Memory(base_dir=Path("/tmp/qq_test_mem"))
    names = [layer.name for layer in mem.layers]
    assert names == ["L0", "L1", "L2", "L3"]


def test_memory_get_finds_first_layer():
    """get 应该从 L0 开始找（短路）"""
    l0 = L0SessionMemory()
    l0.set("k", "from_L0")
    l3 = L3FactsMemory(Path("/tmp/test_mem_get.sqlite"))
    l3.set("k", "from_L3")

    mem = Memory(layers=[l0, l3])
    value, layer = mem.get("k")
    assert value == "from_L0"
    assert layer == "L0"


def test_memory_get_falls_through_layers():
    """L0 没有应该 fall through 到下一层"""
    l0 = L0SessionMemory()
    l3 = L3FactsMemory(Path("/tmp/test_mem_fallthrough.sqlite"))
    l3.set("k", "from_L3")

    mem = Memory(layers=[l0, l3])
    value, layer = mem.get("k")
    assert value == "from_L3"
    assert layer == "L3"


def test_memory_get_not_found_returns_empty_tuple():
    """所有层都没有应该返回 (None, '')"""
    mem = Memory(layers=[L0SessionMemory(), L3FactsMemory(Path("/tmp/test_mem_nf.sqlite"))])
    value, layer = mem.get("nonexistent")
    assert value is None
    assert layer == ""


def test_memory_set_default_writes_to_l3(tmp_path):
    """set 不指定 layer 默认写 L3"""
    mem = Memory(base_dir=tmp_path / "mem")
    mem.set("k", "v")
    # 应该能从 L3 读到
    assert mem.get_from("L3", "k") == "v"


def test_memory_set_explicit_layer(tmp_path):
    mem = Memory(base_dir=tmp_path / "mem")
    mem.set("lang", "python", layer="L1")
    assert mem.get_from("L1", "lang") == "python"
    # L3 不应该有
    assert mem.get_from("L3", "lang") is None


def test_memory_delete(tmp_path):
    mem = Memory(base_dir=tmp_path / "mem")
    mem.set("k", "v", layer="L3")
    assert mem.delete("k", layer="L3") is True
    assert mem.get("k")[0] is None


def test_memory_list_keys_merges_all_layers(tmp_path):
    mem = Memory(base_dir=tmp_path / "mem")
    mem.set("a", "1", layer="L0")  # L0 set 暂时只能通过 set("L0") 但 default L3
    # 改用直接 layer.set
    mem.layers[0].set("a", "1")  # L0
    mem.set("b", "2", layer="L1")
    mem.set("c", "3", layer="L3")
    assert set(mem.list_keys()) >= {"a", "b", "c"}


def test_memory_find_layer_raises_for_unknown():
    mem = Memory(base_dir=Path("/tmp/test_unknown_layer"))
    with pytest.raises(ValueError, match="layer not found"):
        mem.set("k", "v", layer="L99")
    with pytest.raises(ValueError, match="layer not found"):
        mem.get_from("L99", "k")


# === MemoryLayer Protocol ===

def test_all_layers_implement_protocol():
    """所有 4 层必须实现 MemoryLayer protocol"""
    l0 = L0SessionMemory()
    l1 = L1ProjectMemory(Path("/tmp/p.md"))
    l2 = L2UserMemory(Path("/tmp/u.md"))
    l3 = L3FactsMemory(Path("/tmp/f.sqlite"))
    for layer in [l0, l1, l2, l3]:
        assert isinstance(layer, MemoryLayer), f"{layer.name} should implement MemoryLayer"