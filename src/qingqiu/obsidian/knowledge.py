"""obsidian.knowledge · M8.5 knowledge agent

PRD §M8 · S8.5 简化版：query → top 5 相关 notes
"""

from __future__ import annotations

from pathlib import Path

from qingqiu.obsidian.embed import cosine_sim, embed
from qingqiu.obsidian.parser import Note, parse_note
from qingqiu.obsidian.vault import Vault


class KnowledgeAgent:
    """knowledge agent · 复用 Vault + Parser + Embed"""

    def __init__(self, vault: Vault | None = None) -> None:
        self.vault = vault or Vault()

    def search(self, query: str, top_k: int = 5) -> list[tuple[Note, float]]:
        """query → top-k (Note, score) 列表

        跳过 private note（frontmatter private:true 或路径含 private/）
        """
        if not query.strip():
            return []
        q_vec = embed(query)
        notes = [parse_note(f) for f in self.vault.scan()]
        scored: list[tuple[Note, float]] = []
        for note in notes:
            if note.private:
                continue
            # combine title + tags + body
            text = " ".join([note.title, *note.tags, note.body[:500]])
            n_vec = embed(text)
            score = cosine_sim(q_vec, n_vec)
            scored.append((note, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get(self, note_path: Path) -> Note | None:
        """拿单条 note（None if 不存在或 private）"""
        note = parse_note(note_path)
        if note.private:
            return None
        return note