"""S10.3 测试 · VaultFeeder (vault tag 统计 → L2 写入)

覆盖：
- growth.enabled 关闭 → feed() 返 None
- vault 不存在 / 不是目录 → 返 None
- vault 为空 → 写空字符串
- frontmatter `tags: [a, b]` 解析
- 正文内联 `#tag` 解析
- frontmatter + 正文混合（去重）
- 嵌套目录递归扫描
- 写入 L2 key=auto_concepts, value=tag1,tag2,...（按字母序）
- parse_note 单元测试（frontmatter / inline / 空文件 / 损坏 / 不存在）
- collect_tags 不写 L2
- is_enabled 透传
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.vault_feed import VaultFeeder, parse_note
from qingqiu.memory.l2 import L2UserMemory


# === Fixtures ===

@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    return tmp_path / "vault"


@pytest.fixture
def l2_path(tmp_path: Path) -> Path:
    return tmp_path / "user.md"


@pytest.fixture
def l2(l2_path: Path) -> L2UserMemory:
    return L2UserMemory(l2_path)


@pytest.fixture
def growth_enabled() -> GrowthConfig:
    return GrowthConfig(enabled=True)


@pytest.fixture
def growth_disabled() -> GrowthConfig:
    return GrowthConfig(enabled=False)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QINGQIU_GROWTH_ENABLED", raising=False)


def _write_note(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# === 入口短路 ===

def test_feed_disabled_returns_none(
    vault_root: Path, l2: L2UserMemory, growth_disabled: GrowthConfig
) -> None:
    """growth.enabled=False → feed() 返 None，不写 L2"""
    _write_note(vault_root / "a.md", "---\ntags: [python]\n---\nbody")
    feeder = VaultFeeder(l2=l2, growth=growth_disabled)
    assert feeder.feed(vault_root) is None
    assert l2.get("auto_concepts") is None


def test_feed_nonexistent_vault_returns_none(
    l2: L2UserMemory, growth_enabled: GrowthConfig, tmp_path: Path
) -> None:
    """vault 不存在 → 返 None"""
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    assert feeder.feed(tmp_path / "no_such_dir") is None


def test_feed_file_instead_of_dir_returns_none(
    l2: L2UserMemory, growth_enabled: GrowthConfig, tmp_path: Path
) -> None:
    """vault 是文件而不是目录 → 返 None"""
    f = tmp_path / "not_a_dir.md"
    f.write_text("---\ntags: [x]\n---", encoding="utf-8")
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    assert feeder.feed(f) is None


def test_is_enabled_proxies_growth(
    l2: L2UserMemory, growth_disabled: GrowthConfig
) -> None:
    """is_enabled() 透传"""
    feeder = VaultFeeder(l2=l2, growth=growth_disabled)
    assert feeder.is_enabled() is False


# === Vault 扫描 ===

def test_feed_writes_tags_to_l2(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """扫到 tag → 写 L2 (key=auto_concepts)"""
    _write_note(
        vault_root / "a.md",
        "---\ntags: [python, fastapi]\n---\n这是笔记 #python",
    )
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    result = feeder.feed(vault_root)
    assert result is not None
    assert l2.get("auto_concepts") == result
    # 排序后写入（去重 + 字母序）
    assert "python" in result
    assert "fastapi" in result


def test_feed_writes_sorted_alphabetically(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """写入顺序 = 字母升序（确定性）"""
    _write_note(
        vault_root / "a.md",
        "---\ntags: [zebra, apple, mango]\n---\nbody",
    )
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    result = feeder.feed(vault_root)
    assert result == "apple,mango,zebra"


def test_feed_deduplicates_tags(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """frontmatter 和正文都出现同一 tag → 去重"""
    _write_note(
        vault_root / "a.md",
        "---\ntags: [python]\n---\n正文提到 #python 多次 #python",
    )
    _write_note(
        vault_root / "b.md",
        "---\ntags: [python, fastapi]\n---\nbody",
    )
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    result = feeder.feed(vault_root)
    assert result is not None
    assert result.count("python") == 1
    assert "fastapi" in result


def test_feed_recursive_scan(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """递归扫所有子目录 *.md"""
    _write_note(
        vault_root / "projects" / "p1" / "note.md",
        "---\ntags: [project1]\n---",
    )
    _write_note(
        vault_root / "projects" / "p2" / "deep" / "note.md",
        "---\ntags: [project2]\n---",
    )
    _write_note(
        vault_root / "inbox" / "scratch.md",
        "#inbox-tag 随手记",
    )
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    result = feeder.feed(vault_root)
    assert result is not None
    assert "project1" in result
    assert "project2" in result
    assert "inbox-tag" in result


def test_feed_empty_vault_writes_empty(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """vault 为空 → 写空字符串"""
    vault_root.mkdir()
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    result = feeder.feed(vault_root)
    assert result == ""
    assert l2.get("auto_concepts") == ""


def test_feed_overrides_previous_value(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """多次 feed → 后值覆盖前值（不累积 history）"""
    _write_note(vault_root / "a.md", "---\ntags: [old]\n---")
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    feeder.feed(vault_root)
    assert l2.get("auto_concepts") == "old"

    # 改 vault 内容
    (vault_root / "a.md").write_text("---\ntags: [new]\n---", encoding="utf-8")
    feeder.feed(vault_root)
    assert l2.get("auto_concepts") == "new"


# === Custom key ===

def test_feed_uses_custom_key(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """可注入 key（避免和别的写入者冲突）"""
    _write_note(vault_root / "a.md", "---\ntags: [x]\n---")
    feeder = VaultFeeder(l2=l2, growth=growth_enabled, key="my_vault_tags")
    feeder.feed(vault_root)
    assert l2.get("my_vault_tags") == "x"
    assert l2.get("auto_concepts") is None


# === parse_note 单元测试 ===

def test_parse_note_frontmatter_tags(vault_root: Path) -> None:
    """frontmatter `tags: [a, b, c]` 解析"""
    _write_note(
        vault_root / "x.md",
        "---\ntags: [alpha, beta, gamma]\n---\nbody",
    )
    tags = parse_note(vault_root / "x.md")
    assert tags == {"alpha", "beta", "gamma"}


def test_parse_note_inline_tags(vault_root: Path) -> None:
    """正文内联 #tag 解析"""
    _write_note(
        vault_root / "x.md",
        "今天聊 #python 和 #fastapi 的设计。\n另一个 #arch 决策。",
    )
    tags = parse_note(vault_root / "x.md")
    assert tags == {"python", "fastapi", "arch"}


def test_parse_note_mixed_frontmatter_and_inline(vault_root: Path) -> None:
    """frontmatter + 正文混合 → 去重"""
    _write_note(
        vault_root / "x.md",
        "---\ntags: [python, fastapi]\n---\n正文提到 #arch 和 #python",
    )
    tags = parse_note(vault_root / "x.md")
    assert tags == {"python", "fastapi", "arch"}


def test_parse_note_empty_file(vault_root: Path) -> None:
    """空文件 → 空 set"""
    _write_note(vault_root / "x.md", "")
    assert parse_note(vault_root / "x.md") == set()


def test_parse_note_nonexistent(tmp_path: Path) -> None:
    """文件不存在 → 空 set，不抛"""
    assert parse_note(tmp_path / "nope.md") == set()


def test_parse_note_ignores_markdown_headings(vault_root: Path) -> None:
    """``# 标题`` 不应被当作 tag（前缀是空 + 标题里通常含空格）"""
    # "# 标题" 前缀是行首 #，但后面是空格 + 中文 → 不匹配 [A-Za-z0-9_\-/]+
    _write_note(
        vault_root / "x.md",
        "# 这是标题\n## 副标题\n#tag-ok",
    )
    tags = parse_note(vault_root / "x.md")
    # 只有 #tag-ok 被识别（标题含空格 / 中文，匹配失败）
    assert "tag-ok" in tags
    # 标题内容不会成为 tag
    assert "这是标题" not in tags
    assert "副标题" not in tags


# === collect_tags ===

def test_collect_tags_does_not_write(
    vault_root: Path, l2: L2UserMemory, growth_enabled: GrowthConfig
) -> None:
    """collect_tags() 不写 L2"""
    _write_note(vault_root / "a.md", "---\ntags: [python]\n---")
    feeder = VaultFeeder(l2=l2, growth=growth_enabled)
    tags = feeder.collect_tags(vault_root)
    assert "python" in tags
    assert l2.get("auto_concepts") is None
