"""S10.6 测试 · GrowthConfig (growth.enabled 开关 + is_enabled())

覆盖：
- 默认 enabled=True
- env QINGQIU_GROWTH_ENABLED=false 关闭
- env QINGQIU_GROWTH_ENABLED=true 开启
- env 值空 / 奇怪值（"0"/"no"/"off"）的解析
- 显式参数 > env var
- is_enabled() 与 enabled 字段一致
- growth_config.py re-export（同一类）
- weekly_dir 可注入
- 全 growth 函数入口短路（is_enabled() 决定是否走通）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.growth.config import GrowthConfig as GrowthConfig_from_config
from qingqiu.growth.growth_config import GrowthConfig as GrowthConfig_from_growth_config


# === Re-export 一致性 ===

def test_growth_config_reexport_same_class() -> None:
    """growth_config.GrowthConfig ≡ config.GrowthConfig（同一类）"""
    assert GrowthConfig_from_growth_config is GrowthConfig_from_config


# === 基础开关 ===

def test_is_enabled_default_true() -> None:
    """不传参数 → is_enabled() = True"""
    gc = GrowthConfig_from_growth_config()
    assert gc.is_enabled() is True
    assert gc.enabled is True


def test_is_enabled_explicit_false() -> None:
    """显式传 enabled=False → is_enabled() = False"""
    gc = GrowthConfig_from_growth_config(enabled=False)
    assert gc.is_enabled() is False


def test_is_enabled_explicit_true() -> None:
    """显式传 enabled=True → is_enabled() = True"""
    gc = GrowthConfig_from_growth_config(enabled=True)
    assert gc.is_enabled() is True


# === 环境变量 ===

def test_env_var_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    """env QINGQIU_GROWTH_ENABLED=false → is_enabled() = False"""
    monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", "false")
    gc = GrowthConfig_from_growth_config()
    assert gc.is_enabled() is False


def test_env_var_disables_uppercase(monkeypatch: pytest.MonkeyPatch) -> None:
    """env FALSE / False / false 都识别为关"""
    for val in ("false", "False", "FALSE", "0", "no", "off"):
        monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", val)
        gc = GrowthConfig_from_growth_config()
        assert gc.is_enabled() is False, f"expected False for {val!r}"


def test_env_var_enables_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """env value 非 falsy → 启用"""
    for val in ("true", "1", "yes", "on", "anything-else"):
        monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", val)
        gc = GrowthConfig_from_growth_config()
        assert gc.is_enabled() is True, f"expected True for {val!r}"


def test_explicit_arg_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式参数 > env var（测试要 enabled=True 但 env 是 false）"""
    monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", "false")
    gc = GrowthConfig_from_growth_config(enabled=True)
    assert gc.is_enabled() is True


def test_explicit_false_overrides_env_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式 enabled=False > env true"""
    monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", "true")
    gc = GrowthConfig_from_growth_config(enabled=False)
    assert gc.is_enabled() is False


# === weekly_dir ===

def test_weekly_dir_default() -> None:
    """默认 weekly_dir = ~/.qingqiu/memory/weekly/"""
    gc = GrowthConfig_from_growth_config()
    assert gc.weekly_dir == Path.home() / ".qingqiu" / "memory" / "weekly"


def test_weekly_dir_override(tmp_path: Path) -> None:
    """weekly_dir 可注入"""
    custom = tmp_path / "custom"
    gc = GrowthConfig_from_growth_config(weekly_dir=custom)
    assert gc.weekly_dir == custom


# === Growth 函数入口短路集成 ===

def test_is_enabled_gates_preference_learner(tmp_path: Path) -> None:
    """is_enabled() 关闭时 PreferenceLearner.learn() 返 None"""
    from qingqiu.growth.preference import PreferenceLearner
    gc = GrowthConfig_from_growth_config(enabled=False)
    learner = PreferenceLearner(path=tmp_path / "p.yaml", growth=gc)
    assert learner.is_enabled() is False
    assert learner.learn("x") is None


def test_is_enabled_gates_vault_feeder(tmp_path: Path) -> None:
    """is_enabled() 关闭时 VaultFeeder.feed() 返 None"""
    from qingqiu.growth.vault_feed import VaultFeeder
    gc = GrowthConfig_from_growth_config(enabled=False)
    feeder = VaultFeeder(growth=gc)
    assert feeder.is_enabled() is False
    assert feeder.feed(tmp_path) is None


def test_is_enabled_gates_conflict_detector(tmp_path: Path) -> None:
    """is_enabled() 关闭时 ConflictDetector.detect() 返 []"""
    from qingqiu.growth.conflict import ConflictDetector
    from qingqiu.memory.l3 import L3FactsMemory
    gc = GrowthConfig_from_growth_config(enabled=False)
    l3 = L3FactsMemory(tmp_path / "facts.sqlite")
    detector = ConflictDetector(l3=l3, growth=gc)
    assert detector.is_enabled() is False
    assert detector.detect([("x", "1"), ("x", "2")]) == []


def test_is_enabled_gates_weekly_report(tmp_path: Path) -> None:
    """is_enabled() 关闭时 WeeklyReport.weekly() 返 None"""
    from qingqiu.growth.weekly import WeeklyReport
    from qingqiu.memory.l3 import L3FactsMemory
    gc = GrowthConfig_from_growth_config(enabled=False, weekly_dir=tmp_path / "w")
    l3 = L3FactsMemory(tmp_path / "facts.sqlite")
    report = WeeklyReport(l3=l3, growth=gc)
    assert report.weekly() is None
