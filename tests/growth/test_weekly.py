"""S10.4 测试 · WeeklyReport (每周复盘 → memory/weekly/<ISO_week>.md)

覆盖：
- growth.enabled 关闭 → weekly() 返 None，不写文件
- 启用 → 生成 ISO 周命名 markdown
- 内容含任务汇总（4 个计数）+ 完成率
- 内容含 top 5 L3 facts
- 多次 reflect 后 weekly 反映累积值
- output_dir 自动创建
- 顶层 public API 完整
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.reflect import ReflectKeys, Reflector
from qingqiu.growth.weekly import TOP_FACTS_LIMIT, WeeklyReport, iso_week_str
from qingqiu.memory.l3 import L3FactsMemory


# === Fixtures ===

@pytest.fixture
def l3(tmp_path: Path) -> L3FactsMemory:
    return L3FactsMemory(tmp_path / "facts.sqlite")


@pytest.fixture
def weekly_dir(tmp_path: Path) -> Path:
    return tmp_path / "weekly"


@pytest.fixture
def growth(weekly_dir: Path) -> GrowthConfig:
    return GrowthConfig(enabled=True, weekly_dir=weekly_dir)


@pytest.fixture
def disabled_growth(weekly_dir: Path) -> GrowthConfig:
    return GrowthConfig(enabled=False, weekly_dir=weekly_dir)


@pytest.fixture
def report(l3: L3FactsMemory, growth: GrowthConfig) -> WeeklyReport:
    return WeeklyReport(l3=l3, growth=growth)


@pytest.fixture(autouse=True)
def _isolate_growth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """确保测试期间无外部 env var 影响"""
    monkeypatch.delenv("QINGQIU_GROWTH_ENABLED", raising=False)


# === GrowthConfig ===

def test_growth_config_default_enabled() -> None:
    """缺省 enabled=True"""
    gc = GrowthConfig()
    assert gc.enabled is True


def test_growth_config_env_var_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    """env QINGQIU_GROWTH_ENABLED=false → enabled=False"""
    monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", "false")
    gc = GrowthConfig()
    assert gc.enabled is False


def test_growth_config_env_var_overrides_true_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """显式参数 > env var"""
    monkeypatch.setenv("QINGQIU_GROWTH_ENABLED", "false")
    gc = GrowthConfig(enabled=True)
    assert gc.enabled is True


def test_growth_config_weekly_dir_override(tmp_path: Path) -> None:
    """weekly_dir 可注入（测试隔离）"""
    custom = tmp_path / "custom_weekly"
    gc = GrowthConfig(weekly_dir=custom)
    assert gc.weekly_dir == custom


# === GrowthConfig 开关生效 ===

def test_weekly_disabled_returns_none(
    l3: L3FactsMemory, disabled_growth: GrowthConfig, weekly_dir: Path
) -> None:
    """growth.enabled=False → weekly() 返 None，不写文件"""
    report = WeeklyReport(l3=l3, growth=disabled_growth)
    result = report.weekly()
    assert result is None
    assert not weekly_dir.exists() or not any(weekly_dir.iterdir())


def test_weekly_disabled_does_not_create_dir(
    l3: L3FactsMemory, tmp_path: Path
) -> None:
    """disabled 时不应创建 weekly_dir"""
    target = tmp_path / "should_not_exist"
    gc = GrowthConfig(enabled=False, weekly_dir=target)
    report = WeeklyReport(l3=l3, growth=gc)
    assert report.weekly() is None
    assert not target.exists()


# === 文件生成 ===

def test_weekly_generates_md_file(report: WeeklyReport, weekly_dir: Path) -> None:
    path = report.weekly()
    assert path is not None
    assert path.exists()
    assert path.suffix == ".md"
    assert path.parent == weekly_dir


def test_weekly_filename_uses_iso_week(report: WeeklyReport) -> None:
    """文件名 = 当前 ISO 周（YYYY-Www.md）"""
    path = report.weekly()
    assert path is not None
    expected = f"{iso_week_str()}.md"
    assert path.name == expected


def test_weekly_creates_output_dir_if_missing(
    l3: L3FactsMemory, tmp_path: Path
) -> None:
    """output_dir 不存在时自动创建"""
    target = tmp_path / "deep" / "nested" / "weekly"
    gc = GrowthConfig(enabled=True, weekly_dir=target)
    report = WeeklyReport(l3=l3, growth=gc)
    path = report.weekly()
    assert path is not None
    assert target.exists()


def test_weekly_clock_override_deterministic(
    l3: L3FactsMemory, weekly_dir: Path
) -> None:
    """clock 参数可注入（测试用，确定 ISO 周）"""
    # 2026-07-05 12:00:00 UTC 是 Sunday → ISO 2026-W27
    ts = time.mktime(time.strptime("2026-07-05 12:00:00", "%Y-%m-%d %H:%M:%S"))
    gc = GrowthConfig(enabled=True, weekly_dir=weekly_dir)
    report = WeeklyReport(l3=l3, growth=gc, clock=lambda: ts)
    path = report.weekly()
    assert path is not None
    assert path.name == "2026-W27.md"


# === 内容 ===

def test_weekly_contains_task_summary(report: WeeklyReport, l3: L3FactsMemory) -> None:
    """markdown 含「任务汇总」section + 4 个计数"""
    Reflector(l3).reflect([
        {"status": "archived"},
        {"status": "archived"},
        {"status": "done"},
        {"status": "pending"},
        {"status": "pending"},
        {"status": "pending"},
    ])
    path = report.weekly()
    assert path is not None
    md = path.read_text(encoding="utf-8")
    assert "## 任务汇总" in md
    assert "| 总计 | 6 |" in md
    assert "| 已完成 | 1 |" in md
    assert "| 待办 | 3 |" in md
    assert "| 已归档 | 2 |" in md
    assert "完成率" in md


def test_weekly_contains_top_l3_facts(report: WeeklyReport, l3: L3FactsMemory) -> None:
    """markdown 含 top N L3 facts（默认 5）"""
    for i in range(7):
        l3.set(f"custom_fact_{i}", f"value_{i}")
    path = report.weekly()
    assert path is not None
    md = path.read_text(encoding="utf-8")
    assert f"## Top {TOP_FACTS_LIMIT}" in md or "## Top" in md
    # 至少出现 1 个 custom_fact（top 5 包含前 5 个）
    assert "custom_fact_" in md


def test_weekly_no_reflect_shows_zero_counts(report: WeeklyReport) -> None:
    """没 reflect 过 → 全 0 + 0% 完成率"""
    path = report.weekly()
    assert path is not None
    md = path.read_text(encoding="utf-8")
    assert "| 总计 | 0 |" in md
    assert "0.0%" in md


def test_weekly_reflects_multiple_reflects(
    report: WeeklyReport, l3: L3FactsMemory
) -> None:
    """多次 reflect → weekly 反映累积值（最后一次的状态）"""
    r = Reflector(l3)
    r.reflect([{"status": "archived"}, {"status": "pending"}])  # total=2
    r.reflect(
        [{"status": "archived"}, {"status": "archived"}, {"status": "done"}]
    )  # total=3, archived=2, done=1
    path = report.weekly()
    assert path is not None
    md = path.read_text(encoding="utf-8")
    # 最终状态
    assert "| 总计 | 3 |" in md
    assert "| 已完成 | 1 |" in md
    assert "| 已归档 | 2 |" in md
    # last_reflect_at 在 top facts 中
    assert ReflectKeys.LAST_REFLECT_AT in md


def test_weekly_top_facts_includes_l3_extras(
    report: WeeklyReport, l3: L3FactsMemory
) -> None:
    """top facts 不只 Reflector 写入的 5 条，也包含其他 L3 facts"""
    r = Reflector(l3)
    r.reflect([{"status": "pending"}])
    l3.set("user_pref", "no_emoji")
    l3.set("favorite_lang", "zh-CN")
    path = report.weekly()
    assert path is not None
    md = path.read_text(encoding="utf-8")
    assert "user_pref" in md
    assert "favorite_lang" in md


# === 工具 / 公共符号 ===

def test_iso_week_str_format() -> None:
    """iso_week_str 输出 YYYY-Www"""
    import re
    s = iso_week_str()
    assert re.fullmatch(r"\d{4}-W\d{2}", s)


def test_iso_week_str_known_date() -> None:
    """iso_week_str 已知日期"""
    # 2026-01-01 (Thursday) → 2026-W01
    import time as _t
    ts = _t.mktime(_t.strptime("2026-01-01 12:00:00", "%Y-%m-%d %H:%M:%S"))
    assert iso_week_str(ts) == "2026-W01"


def test_top_facts_limit_constant() -> None:
    """TOP_FACTS_LIMIT = 5"""
    assert TOP_FACTS_LIMIT == 5


def test_growth_module_public_api() -> None:
    """growth/__init__.py 导出 Reflector / WeeklyReport / GrowthConfig"""
    import qingqiu.growth as g
    assert hasattr(g, "Reflector")
    assert hasattr(g, "WeeklyReport")
    assert hasattr(g, "GrowthConfig")