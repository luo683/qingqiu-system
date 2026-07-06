"""S10.5 测试 · ConflictDetector (偏好冲突 → L3 写入)

覆盖：
- growth.enabled 关闭 → detect() 返 []，不写 L3
- 空 history → 返 []，不写 L3
- 同一 key 多次相同值 → 不算冲突
- 同一 key 多次不同值 → 触发冲突，写 L3
- 多 key 各自独立处理
- L3 写入格式：``conflict_<key> = old→new``
- 多次 detect 累积写入 L3
- detected_at 字段 ISO 8601 UTC
- is_enabled 透传
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.conflict import ConflictDetector
from qingqiu.memory.l3 import L3FactsMemory


# === Fixtures ===

@pytest.fixture
def l3(tmp_path: Path) -> L3FactsMemory:
    return L3FactsMemory(tmp_path / "facts.sqlite")


@pytest.fixture
def growth_enabled() -> GrowthConfig:
    return GrowthConfig(enabled=True)


@pytest.fixture
def growth_disabled() -> GrowthConfig:
    return GrowthConfig(enabled=False)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QINGQIU_GROWTH_ENABLED", raising=False)


# === 入口短路 ===

def test_detect_disabled_returns_empty(
    l3: L3FactsMemory, growth_disabled: GrowthConfig
) -> None:
    """growth.enabled=False → detect() 返 []，不写 L3"""
    detector = ConflictDetector(l3=l3, growth=growth_disabled)
    result = detector.detect([("emoji", "no"), ("emoji", "yes")])
    assert result == []
    assert l3.get("conflict_emoji") is None


def test_detect_empty_history_returns_empty(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """空 history → 返 []"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    assert detector.detect([]) == []


def test_is_enabled_proxies_growth(
    l3: L3FactsMemory, growth_disabled: GrowthConfig
) -> None:
    """is_enabled() 透传"""
    detector = ConflictDetector(l3=l3, growth=growth_disabled)
    assert detector.is_enabled() is False


# === 冲突检测 ===

def test_detect_single_conflict(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """同一 key 不同值 → 1 个冲突"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    result = detector.detect([("emoji", "no"), ("emoji", "yes")])
    assert len(result) == 1
    c = result[0]
    assert c["key"] == "emoji"
    assert c["old"] == "no"
    assert c["new"] == "yes"
    assert c["conflict_key"] == "conflict_emoji"


def test_detect_writes_to_l3(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """冲突写 L3：conflict_<key> = old→new"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    detector.detect([("emoji", "no"), ("emoji", "yes")])
    assert l3.get("conflict_emoji") == "no→yes"


def test_detect_no_conflict_when_same_value(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """同一 key 多次相同值 → 不算冲突"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    result = detector.detect([("emoji", "no"), ("emoji", "no"), ("emoji", "no")])
    assert result == []
    assert l3.get("conflict_emoji") is None


def test_detect_multiple_keys_independent(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """多 key 各自独立：有的冲突有的不冲突"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    history = [
        ("emoji", "no"),       # 1 次单值 → 无冲突
        ("emoji", "no"),
        ("tone", "formal"),    # 多次不同值 → 冲突
        ("tone", "casual"),
        ("lang", "zh"),        # 单次 → 无冲突
    ]
    result = detector.detect(history)
    assert len(result) == 1
    assert result[0]["key"] == "tone"
    assert result[0]["old"] == "formal"
    assert result[0]["new"] == "casual"
    assert l3.get("conflict_tone") == "formal→casual"
    assert l3.get("conflict_emoji") is None


def test_detect_three_way_conflict(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """3 个不同值 → 仍算 1 个冲突（old = 第一次, new = 最后一次）"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    result = detector.detect([
        ("tone", "formal"),
        ("tone", "casual"),
        ("tone", "humorous"),
    ])
    assert len(result) == 1
    c = result[0]
    assert c["old"] == "formal"
    assert c["new"] == "humorous"
    assert l3.get("conflict_tone") == "formal→humorous"


def test_detect_multiple_conflicts(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """多个 key 都冲突 → 多个 conflict_key"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    history = [
        ("emoji", "no"),
        ("emoji", "yes"),
        ("tone", "formal"),
        ("tone", "casual"),
    ]
    result = detector.detect(history)
    assert len(result) == 2
    keys = {c["key"] for c in result}
    assert keys == {"emoji", "tone"}
    assert l3.get("conflict_emoji") == "no→yes"
    assert l3.get("conflict_tone") == "formal→casual"


def test_detect_preserves_first_seen_order(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """冲突列表顺序 = history 中 key 首次出现的顺序"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    result = detector.detect([
        ("b", "x"),
        ("b", "y"),
        ("a", "1"),
        ("a", "2"),
        ("c", "p"),
        ("c", "q"),
    ])
    keys = [c["key"] for c in result]
    assert keys == ["b", "a", "c"]


# === 累计调用 ===

def test_detect_multiple_calls_accumulate(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """多次 detect → L3 累积（INSERT ON CONFLICT DO UPDATE 语义）"""
    detector = ConflictDetector(l3=l3, growth=growth_enabled)
    detector.detect([("emoji", "no"), ("emoji", "yes")])
    assert l3.get("conflict_emoji") == "no→yes"

    # 第二次 detect 同 key 再次冲突 → 覆盖为新冲突
    detector.detect([("emoji", "yes"), ("emoji", "maybe")])
    # 最后一次 set 覆盖
    assert l3.get("conflict_emoji") == "yes→maybe"


# === detected_at 时间戳 ===

def test_detect_includes_detected_at_iso(
    l3: L3FactsMemory, growth_enabled: GrowthConfig
) -> None:
    """返回值含 detected_at = ISO 8601 UTC 字符串"""
    from datetime import datetime
    detector = ConflictDetector(l3=l3, growth=growth_enabled, now=1700000000.0)
    result = detector.detect([("emoji", "no"), ("emoji", "yes")])
    assert len(result) == 1
    ts = result[0]["detected_at"]
    parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    assert parsed.year == 2023
