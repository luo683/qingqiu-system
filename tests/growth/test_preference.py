"""S10.2 测试 · PreferenceLearner (用户纠正 → personality.yaml 追加)

覆盖：
- growth.enabled 关闭 → learn() 返 None，不读不写
- 空 / 空白 preference → 返 None
- 默认文件不存在 → 自动创建默认后追加
- 平铺 YAML 格式 → 追加成功
- 嵌套 YAML 格式（PRD §8.2）→ 追加成功，结构保留
- 幂等：相同 preference 重复 learn → 不重复追加
- 多次不同 preference → 全部累积
- 中文 / emoji preference
- 文件 YAML 损坏 → 返 None，不崩
- is_enabled() 透传
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.preference import PreferenceLearner


# === Fixtures ===

@pytest.fixture
def personality_path(tmp_path: Path) -> Path:
    return tmp_path / "personality.yaml"


@pytest.fixture
def growth_enabled() -> GrowthConfig:
    return GrowthConfig(enabled=True)


@pytest.fixture
def growth_disabled() -> GrowthConfig:
    return GrowthConfig(enabled=False)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QINGQIU_GROWTH_ENABLED", raising=False)


def _write_flat(path: Path, system_prompt: str) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "name": "清秋",
                "tone": "neutral",
                "language": "zh-CN",
                "system_prompt": system_prompt,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


# === 入口短路 ===

def test_learn_disabled_returns_none(
    personality_path: Path, growth_disabled: GrowthConfig
) -> None:
    """growth.enabled=False → learn() 返 None，不创建文件"""
    learner = PreferenceLearner(path=personality_path, growth=growth_disabled)
    result = learner.learn("不写 emoji")
    assert result is None
    assert not personality_path.exists()


def test_is_enabled_proxies_growth(
    personality_path: Path, growth_disabled: GrowthConfig
) -> None:
    """is_enabled() 透传 GrowthConfig.enabled"""
    learner = PreferenceLearner(path=personality_path, growth=growth_disabled)
    assert learner.is_enabled() is False


# === 边界输入 ===

def test_learn_empty_preference_returns_none(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """空字符串 preference → 返 None"""
    _write_flat(personality_path, "你是清秋。")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    assert learner.learn("") is None
    # 文件不应被修改
    assert "你是清秋" in personality_path.read_text(encoding="utf-8")


def test_learn_whitespace_preference_returns_none(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """纯空白 preference → 返 None"""
    _write_flat(personality_path, "你是清秋。")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    assert learner.learn("   \n\t  ") is None


# === 平铺 YAML 追加 ===

def test_learn_appends_to_flat_yaml(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """平铺 YAML → system_prompt 追加 preference（bullet 风格）"""
    _write_flat(personality_path, "你是清秋。")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    new_prompt = learner.learn("不写 emoji")

    assert new_prompt is not None
    assert "不写 emoji" in new_prompt
    assert "你是清秋" in new_prompt
    # bullet 风格前缀
    assert "- 不写 emoji" in new_prompt


def test_learn_persists_to_disk(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """追加后 → 重新 PersonalityLoader 读得到新值（hot reload 友好）"""
    _write_flat(personality_path, "原 prompt")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    learner.learn("回复要简洁")

    # 重新读
    data = yaml.safe_load(personality_path.read_text(encoding="utf-8"))
    assert "回复要简洁" in data["system_prompt"]


# === 嵌套 YAML（PRD §8.2） ===

def test_learn_appends_to_nested_yaml(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """嵌套 personality: 格式 → 追加成功，结构保留"""
    personality_path.write_text(
        yaml.safe_dump(
            {"personality": {"name": "清秋", "system_prompt": "原 prompt"}},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    new_prompt = learner.learn("不写 emoji")

    assert new_prompt is not None
    assert "不写 emoji" in new_prompt
    # 嵌套结构保留
    data = yaml.safe_load(personality_path.read_text(encoding="utf-8"))
    assert "personality" in data
    assert isinstance(data["personality"], dict)
    assert "不写 emoji" in data["personality"]["system_prompt"]


# === 幂等 / 累积 ===

def test_learn_idempotent_same_preference(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """相同 preference 多次 learn → 只追加一次"""
    _write_flat(personality_path, "原 prompt")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    learner.learn("不写 emoji")
    learner.learn("不写 emoji")
    learner.learn("不写 emoji")

    content = personality_path.read_text(encoding="utf-8")
    assert content.count("- 不写 emoji") == 1


def test_learn_multiple_distinct_preferences(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """多条不同 preference → 全部累积"""
    _write_flat(personality_path, "原 prompt")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    learner.learn("不写 emoji")
    learner.learn("回复简短")
    learner.learn("用中文")

    content = personality_path.read_text(encoding="utf-8")
    assert "不写 emoji" in content
    assert "回复简短" in content
    assert "用中文" in content
    assert content.count("- ") == 3


# === 文件不存在 / 损坏 ===

def test_learn_creates_default_file_if_missing(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """文件不存在 → 自动走 schema default 创建后追加"""
    assert not personality_path.exists()
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    new_prompt = learner.learn("不写 emoji")

    assert new_prompt is not None
    assert personality_path.exists()
    data = yaml.safe_load(personality_path.read_text(encoding="utf-8"))
    assert "不写 emoji" in data["system_prompt"]
    # 默认 name 保留
    assert data.get("name") == "清秋"


def test_learn_handles_corrupted_yaml(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """YAML 损坏 → learn() 返 None，不崩"""
    personality_path.write_text(": not : valid : yaml :", encoding="utf-8")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    # 不抛异常
    result = learner.learn("不写 emoji")
    assert result is None


# === 中文 / emoji ===

def test_learn_chinese_emoji_preference(
    personality_path: Path, growth_enabled: GrowthConfig
) -> None:
    """中文 + emoji preference 正确追加（不乱码）"""
    _write_flat(personality_path, "原 prompt")
    learner = PreferenceLearner(path=personality_path, growth=growth_enabled)
    pref = "回复里不要用 emoji 🌟"
    learner.learn(pref)

    content = personality_path.read_text(encoding="utf-8")
    assert "回复里不要用 emoji 🌟" in content


# === is_enabled 默认 True ===

def test_preference_learner_default_is_enabled(personality_path: Path) -> None:
    """不传 growth → 默认 GrowthConfig(enabled=True)"""
    learner = PreferenceLearner(path=personality_path)
    assert learner.is_enabled() is True
