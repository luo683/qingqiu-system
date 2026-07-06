"""obsidian.parser · S8.3 解析 + S8.6 private (重写含 private 字段)"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_TAG_RE = re.compile(r"#[\w\-/\.]+")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class Note:
    """解析后的 note"""

    path: Path
    title: str
    frontmatter: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    body: str = ""
    private: bool = False  # S8.6


def parse_note(path: Path) -> Note:
    if not path.exists():
        raise FileNotFoundError(f"note not found: {path}")

    text = path.read_text(encoding="utf-8")
    frontmatter: dict = {}
    body = text

    m = _FRONTMATTER_RE.match(text)
    if m:
        try:
            frontmatter = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        body = text[m.end() :]

    wikilinks = _WIKILINK_RE.findall(body)
    tags = [t.lstrip("#") for t in _TAG_RE.findall(body)]

    title = str(frontmatter.get("title", path.stem))

    # S8.6: private 检测
    private = bool(frontmatter.get("private", False)) or any(
        "private" in part.lower() for part in path.parts
    )

    return Note(
        path=path,
        title=title,
        frontmatter=frontmatter,
        tags=tags,
        wikilinks=wikilinks,
        body=body,
        private=private,
    )