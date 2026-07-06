"""S10.1 测试 · Reflector (任务归档 → L3 facts)

覆盖：
- 5 个 key 都写入 L3（total / done / pending / archived / last_reflect_at）
- summarize() 纯统计不写 L3
- 重复调用覆盖（不新增 key）
- now 参数可注入（测试用）
- 空列表 / None 合法
- ReflectKeys 常量稳定
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.growth.reflect import ReflectKeys, Reflector, _iso_utc
from qingqiu.memory.l3 import L3FactsMemory


# === Fixtures ===

@pytest.fixture
def l3(tmp_path: Path) -> L3FactsMemory:
    return L3FactsMemory(tmp_path / "facts.sqlite")


@pytest.fixture
def reflector(l3: L3FactsMemory) -> Reflector:
    return Reflector(l3)


def _sample_tasks() -> list[dict]:
    return [
        {"id": "t1", "status": "archived"},
        {"id": "t2", "status": "done"},
        {"id": "t3", "status": "done"},
        {"id": "t4", "status": "pending"},
        {"id": "t5", "status": "pending"},
    ]


# === 写入 5 条 facts ===

def test_reflector_writes_total_count(reflector: Reflector) -> None:
    written = reflector.reflect(_sample_tasks())
    assert written[ReflectKeys.TASK_COUNT_TOTAL] == "5"


def test_reflector_writes_done_count(reflector: Reflector) -> None:
    written = reflector.reflect(_sample_tasks())
    assert written[ReflectKeys.TASK_COUNT_DONE] == "2"


def test_reflector_writes_pending_count(reflector: Reflector) -> None:
    written = reflector.reflect(_sample_tasks())
    assert written[ReflectKeys.TASK_COUNT_PENDING] == "2"


def test_reflector_writes_archived_count(reflector: Reflector) -> None:
    written = reflector.reflect(_sample_tasks())
    assert written[ReflectKeys.TASK_COUNT_ARCHIVED] == "1"


def test_reflector_writes_last_reflect_at(reflector: Reflector) -> None:
    written = reflector.reflect(_sample_tasks())
    ts = written[ReflectKeys.LAST_REFLECT_AT]
    # ISO 8601 UTC with Z suffix
    from datetime import datetime
    parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    assert parsed.year >= 2026


# === summarize（纯统计 / 不写） ===

def test_reflector_summarize_does_not_write(reflector: Reflector, l3: L3FactsMemory) -> None:
    """summarize() 不应触发任何 L3.set"""
    keys_before = set(l3.list_keys())
    stats = Reflector.summarize(_sample_tasks())
    assert stats == {"total": 5, "done": 2, "pending": 2, "archived": 1}
    assert set(l3.list_keys()) == keys_before


def test_reflector_summarize_empty() -> None:
    stats = Reflector.summarize([])
    assert stats == {"total": 0, "done": 0, "pending": 0, "archived": 0}


# === 幂等 / 边界 ===

def test_reflector_idempotent_overwrites(reflector: Reflector, l3: L3FactsMemory) -> None:
    """重复 reflect 覆盖同 key（不新增）"""
    reflector.reflect([{"status": "pending"}])
    assert l3.get(ReflectKeys.TASK_COUNT_TOTAL) == "1"
    reflector.reflect([{"status": "done"}, {"status": "pending"}])
    assert l3.get(ReflectKeys.TASK_COUNT_TOTAL) == "2"
    assert l3.get(ReflectKeys.TASK_COUNT_DONE) == "1"
    # key 数量仍为 5（不变）
    assert len(l3.list_keys()) == 5


def test_reflector_empty_tasks(reflector: Reflector) -> None:
    """空列表合法"""
    written = reflector.reflect([])
    assert written[ReflectKeys.TASK_COUNT_TOTAL] == "0"
    assert written[ReflectKeys.TASK_COUNT_DONE] == "0"


def test_reflector_none_tasks(reflector: Reflector) -> None:
    """None 也合法（视为空列表）"""
    written = reflector.reflect(None)  # type: ignore[arg-type]
    assert written[ReflectKeys.TASK_COUNT_TOTAL] == "0"


def test_reflector_now_override(reflector: Reflector) -> None:
    """now 参数可注入（确定性测试）"""
    written = reflector.reflect([{"status": "pending"}], now=1700000000.0)
    # _iso_utc(1700000000.0) = "2023-11-14T22:13:20Z"
    assert written[ReflectKeys.LAST_REFLECT_AT] == "2023-11-14T22:13:20Z"


# === 常量 / 工具 ===

def test_reflect_keys_constant() -> None:
    """ReflectKeys 5 项 + 顺序稳定"""
    assert ReflectKeys.TASK_COUNT_TOTAL == "task_count_total"
    assert ReflectKeys.TASK_COUNT_DONE == "task_count_done"
    assert ReflectKeys.TASK_COUNT_PENDING == "task_count_pending"
    assert ReflectKeys.TASK_COUNT_ARCHIVED == "task_count_archived"
    assert ReflectKeys.LAST_REFLECT_AT == "last_reflect_at"


def test_iso_utc_format() -> None:
    """_iso_utc 输出 %Y-%m-%dT%H:%M:%SZ 格式"""
    assert _iso_utc(0.0) == "1970-01-01T00:00:00Z"
    assert _iso_utc(1700000000.0) == "2023-11-14T22:13:20Z"