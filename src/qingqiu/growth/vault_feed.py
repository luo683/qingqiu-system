"""VaultFeeder · vault 反哺（M10 · S10.3）

扫 vault 目录的所有 ``*.md`` → 解析 frontmatter ``tags: [a, b, ...]``
+ 正文内联 ``#tag`` → 去重 + 排序 → 写入 L2 (key=``auto_concepts``,
value=``tag1,tag2,...``)。

复用：
- ``qingqiu.memory.l2.L2UserMemory``：L2 文件写入（key = value 格式）
- ``qingqiu.growth.config.GrowthConfig``：enabled 开关

不调 LLM：纯文本 + 正则解析。

parse_note 极简实现（不依赖 obsidian 模块）：
- 识别 ``---\\n...\\n---\\n`` 之间的 frontmatter
- frontmatter 内 ``tags: [a, b, c]`` 形式
- 正文 ``#tag`` 兜底（不被 markdown 标题吞掉：要求 # 前是空白或行首）
"""

from __future__ import annotations

import re
from pathlib import Path

from qingqiu.growth.config import GrowthConfig
from qingqiu.memory.l2 import L2UserMemory


# 极简 frontmatter 解析（--- 行后面允许 EOF 或换行）
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---[ \t]*(?:\n|$)(.*)$", re.DOTALL)
# tags: [a, b, c] 形式
_LIST_TAGS_RE = re.compile(r"^tags\s*:\s*\[([^\]]*)\]\s*$", re.MULTILINE)
# 正文内联 #tag（前面是空白 / 行首；tag 字符 = 字母数字 + _ + - + /）
_INLINE_TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_\-/]+)")


def parse_note(path: Path) -> set[str]:
    """从一个 markdown 文件提取所有 tag

    解析策略（先 frontmatter.list，再 frontmatter inline list，最后正文 #tag）：
    1. frontmatter 内 ``tags: [a, b, c]`` 形式
    2. 正文 ``#tag`` 形式（前缀为空白或行首）

    Returns:
        提取出的 tag 集合（去重、空字符串过滤）
    """
    if not path.exists() or not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()

    tags: set[str] = set()

    # 1. frontmatter 优先
    m = _FRONTMATTER_RE.match(text)
    body = text
    if m:
        front_text = m.group(1)
        body = m.group(2)
        lm = _LIST_TAGS_RE.search(front_text)
        if lm:
            for raw in lm.group(1).split(","):
                t = raw.strip().strip("'\"")
                if t:
                    tags.add(t)

    # 2. 正文 #tag 兜底
    for t in _INLINE_TAG_RE.findall(body):
        tags.add(t)
    return tags


class VaultFeeder:
    """vault 反哺器

    用法：
        feeder = VaultFeeder()                  # 默认 L2 + 默认 growth
        feeder = VaultFeeder(l2=l2, growth=gc)  # 测试用
        value = feeder.feed(Path("~/notes"))    # → 写入 L2

    MVP 行为：
    - feed(vault_root) → 递归扫 *.md → 收集所有 tag → 排序后 join "," → 写 L2
    - vault 不存在 / 不是目录 → 返 None
    - growth.enabled=False → 短路返 None
    - vault 为空 → 写空字符串（覆盖前值，让用户知道扫过）
    """

    DEFAULT_KEY = "auto_concepts"

    def __init__(
        self,
        *,
        l2: L2UserMemory | None = None,
        growth: GrowthConfig | None = None,
        key: str | None = None,
    ) -> None:
        self._l2: L2UserMemory = l2 if l2 is not None else L2UserMemory()
        self._growth: GrowthConfig = growth if growth is not None else GrowthConfig()
        self._key: str = key if key is not None else self.DEFAULT_KEY

    # ── 入口短路 ──────────────────────────────────────

    def is_enabled(self) -> bool:
        return self._growth.is_enabled()

    # ── 主入口 ──────────────────────────────────────

    def feed(self, vault_root: Path | str) -> str | None:
        """扫 vault → 提取 tag → 写 L2

        Returns:
            写入 L2 的 value 字符串（tag1,tag2,...）；disabled / vault 非法 → None
        """
        if not self.is_enabled():
            return None

        root = Path(vault_root)
        if not root.exists() or not root.is_dir():
            return None

        all_tags = self.collect_tags(root)
        sorted_tags = sorted(all_tags)
        value = ",".join(sorted_tags)
        self._l2.set(self._key, value)
        return value

    # ── 工具 ──────────────────────────────────────

    def collect_tags(self, vault_root: Path | str) -> set[str]:
        """递归扫 vault 收集所有 tag（不写 L2）"""
        root = Path(vault_root)
        if not root.exists() or not root.is_dir():
            return set()

        all_tags: set[str] = set()
        for md_file in root.rglob("*.md"):
            all_tags.update(parse_note(md_file))
        return all_tags
