"""obsidian.vault · S8.1 vault 扫描 (复制自 M8 worktree)"""

from __future__ import annotations

from pathlib import Path


class Vault:
    """Obsidian vault 扫描器"""

    DEFAULT_IGNORE = (".trash/", ".obsidian/cache/", ".trash", ".obsidian/cache")

    def __init__(self, root: Path | None = None, ignore_patterns: tuple[str, ...] = DEFAULT_IGNORE) -> None:
        self.root = root
        self.ignore_patterns = ignore_patterns

    def set_root(self, path: Path) -> None:
        self.root = path

    def scan(self) -> list[Path]:
        if self.root is None or not self.root.exists():
            return []
        files: list[Path] = []
        for md in self.root.rglob("*.md"):
            if any(part in self.ignore_patterns for part in md.parts):
                continue
            files.append(md)
        return sorted(files)

    def stats(self) -> dict:
        files = self.scan()
        return {
            "root": str(self.root) if self.root else None,
            "total_md": len(files),
            "exists": self.root.exists() if self.root else False,
        }