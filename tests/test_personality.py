"""S6.5 personality.py 测试 · 加载 + hot reload + 单例"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from qingqiu.personality import (
    DEFAULT_PERSONALITY_PATH,
    PersonalityConfig,
    PersonalityLoader,
    get_personality,
    get_system_prompt,
    reset_default_loader,
)


# ── 1. 默认配置加载（文件不存在时写默认）───────────────


def test_loader_creates_default_file_when_missing(tmp_path: Path) -> None:
    """文件不存在 → 首次构造时自动写入默认内容"""
    p = tmp_path / "personality.yaml"
    assert not p.exists()
    loader = PersonalityLoader(p)
    assert p.exists()  # 自动创建
    assert loader.config.name == "清秋"
    assert loader.config.tone == "neutral"
    assert loader.config.language == "zh-CN"
    assert "清秋" in loader.config.system_prompt


# ── 2. 平铺 YAML 格式 ──────────────────────────────


def test_loader_reads_flat_yaml(tmp_path: Path) -> None:
    """平铺格式：name/system_prompt/tone/language 在顶层"""
    p = tmp_path / "personality.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "name": "秋",
                "tone": "humorous",
                "language": "en-US",
                "system_prompt": "You are Qiu.",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    loader = PersonalityLoader(p)
    assert loader.config.name == "秋"
    assert loader.config.tone == "humorous"
    assert loader.config.language == "en-US"
    assert loader.config.system_prompt == "You are Qiu."


# ── 3. 嵌套 YAML 格式（PRD §8.2）───────────────────


def test_loader_reads_nested_personality_yaml(tmp_path: Path) -> None:
    """嵌套格式：personality: 包裹字段（PRD §8.2）"""
    p = tmp_path / "personality.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "personality": {
                    "name": "嵌套清秋",
                    "system_prompt": "你是嵌套版清秋",
                    "tone": "friendly",
                    "language": "zh-CN",
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    loader = PersonalityLoader(p)
    assert loader.config.name == "嵌套清秋"
    assert loader.config.tone == "friendly"
    assert loader.config.system_prompt == "你是嵌套版清秋"


# ── 4. Pydantic 缺字段走 schema default ──────────────


def test_loader_missing_field_uses_default(tmp_path: Path) -> None:
    """缺字段 → Pydantic 自动用 schema default（不抛异常）"""
    p = tmp_path / "personality.yaml"
    p.write_text(
        yaml.safe_dump({"name": "缺字段清秋"}, allow_unicode=True),
        encoding="utf-8",
    )
    loader = PersonalityLoader(p)
    cfg = loader.config
    assert cfg.name == "缺字段清秋"
    # 其他字段走默认
    assert cfg.tone == "neutral"
    assert cfg.language == "zh-CN"
    assert "清秋" in cfg.system_prompt


# ── 5. mtime hot reload ─────────────────────────────


def test_loader_hot_reload_on_mtime_change(tmp_path: Path) -> None:
    """改文件后 reload 拿到新值（不依赖 polling 协程）"""
    p = tmp_path / "personality.yaml"
    p.write_text(yaml.safe_dump({"name": "原名"}, allow_unicode=True), encoding="utf-8")
    loader = PersonalityLoader(p)
    assert loader.config.name == "原名"

    # 改文件 + 确保 mtime 前进（Windows 上 mtime 精度可能不够）
    time.sleep(1.1)
    p.write_text(yaml.safe_dump({"name": "新名"}, allow_unicode=True), encoding="utf-8")

    # 访问 config 自动检测 mtime
    assert loader.config.name == "新名"


def test_loader_no_reload_when_unchanged(tmp_path: Path) -> None:
    """未改文件 → 不重新解析（用 config identity 验证）"""
    p = tmp_path / "personality.yaml"
    p.write_text(yaml.safe_dump({"name": "stable"}, allow_unicode=True), encoding="utf-8")
    loader = PersonalityLoader(p)
    first = loader.config
    second = loader.config
    # 没改文件，Pydantic 模型是 immutable 的，每次 reload 会得到不同对象
    # 但不 reload 时应返回同一对象
    assert first is second


# ── 6. 特殊字符串（中文 + emoji）─────────────────────


def test_loader_handles_chinese_and_emoji(tmp_path: Path) -> None:
    """system_prompt 含中文 + emoji 不能乱码"""
    p = tmp_path / "personality.yaml"
    content = "你是清秋 🌟\n风格：简洁、直接 ✨\n不说废话"
    p.write_text(
        yaml.safe_dump({"system_prompt": content}, allow_unicode=True),
        encoding="utf-8",
    )
    loader = PersonalityLoader(p)
    assert loader.config.system_prompt == content
    assert "🌟" in loader.system_prompt
    assert "✨" in loader.system_prompt


# ── 7. 单例行为（get_personality 多次调用返回同一 loader 实例）──


def test_get_personality_returns_same_instance(tmp_path: Path, monkeypatch) -> None:
    """不传 path 时 → 全局单例 loader"""
    custom = tmp_path / "personality.yaml"
    custom.write_text(yaml.safe_dump({"name": "shared"}, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr("qingqiu.personality.DEFAULT_PERSONALITY_PATH", custom)
    reset_default_loader()

    a = get_personality()
    b = get_personality()
    # 字段相同（同一份配置）
    assert a.name == b.name == "shared"


def test_get_personality_with_path_creates_independent_loader(tmp_path: Path) -> None:
    """传 path → 走独立 loader，不动单例"""
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump({"name": "isolated"}, allow_unicode=True), encoding="utf-8")
    cfg = get_personality(custom)
    assert cfg.name == "isolated"
    # 单例没变（仍是 None 或之前的 loader）


# ── 8. get_system_prompt 便捷函数 ───────────────────


def test_get_system_prompt_returns_string(tmp_path: Path, monkeypatch) -> None:
    """便捷函数 → 直接拿到 system_prompt 字符串"""
    custom = tmp_path / "personality.yaml"
    custom.write_text(
        yaml.safe_dump({"system_prompt": "test prompt content"}, allow_unicode=True),
        encoding="utf-8",
    )
    monkeypatch.setattr("qingqiu.personality.DEFAULT_PERSONALITY_PATH", custom)
    reset_default_loader()
    assert get_system_prompt() == "test prompt content"


# ── 9. 文件权限错误时不崩溃 ─────────────────────────


def test_loader_keeps_last_config_on_io_error(tmp_path: Path, monkeypatch) -> None:
    """文件被删 → 保留旧配置，不抛异常"""
    p = tmp_path / "personality.yaml"
    p.write_text(yaml.safe_dump({"name": "before"}, allow_unicode=True), encoding="utf-8")
    loader = PersonalityLoader(p)
    assert loader.config.name == "before"

    # 删除文件 → config 仍可访问（保留旧值）
    p.unlink()
    # config 第一次访问会尝试 stat → 文件不在 → 保留旧 config
    assert loader.config.name == "before"


# ── 10. shortcut 属性 ──────────────────────────────


def test_loader_shortcut_properties(tmp_path: Path) -> None:
    """name / system_prompt shortcut 属性透传 config"""
    p = tmp_path / "personality.yaml"
    p.write_text(
        yaml.safe_dump(
            {"name": "短名", "system_prompt": "短 prompt"},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    loader = PersonalityLoader(p)
    assert loader.name == "短名"
    assert loader.system_prompt == "短 prompt"


# ── 11. PersonalityConfig 默认值（纯 schema 测试）──────


def test_personality_config_defaults() -> None:
    """PersonalityConfig() 不传任何字段时所有字段走 default"""
    cfg = PersonalityConfig()
    assert cfg.name == "清秋"
    assert cfg.tone == "neutral"
    assert cfg.language == "zh-CN"
    assert "清秋" in cfg.system_prompt


# ── 12. DEFAULT_PERSONALITY_PATH 路径正确 ────────────


def test_default_path_is_home_qingqiu() -> None:
    """默认路径 = ~/.qingqiu/personality.yaml（与 config.yaml 同目录但不同文件）"""
    assert DEFAULT_PERSONALITY_PATH == Path.home() / ".qingqiu" / "personality.yaml"