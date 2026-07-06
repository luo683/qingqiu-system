"""test_obsidian.py · M8 完整测试 (vault/index/parser + embed/knowledge/private)"""

from __future__ import annotations

from pathlib import Path


# === S8.1 vault ===

def test_vault_scan(tmp_path: Path):
    from qingqiu.obsidian.vault import Vault

    (tmp_path / "note1.md").write_text("# Note 1", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "note2.md").write_text("# Note 2", encoding="utf-8")

    v = Vault(root=tmp_path)
    files = v.scan()
    assert len(files) == 2


def test_vault_scan_with_ignore(tmp_path: Path):
    from qingqiu.obsidian.vault import Vault

    (tmp_path / "keep.md").write_text("x", encoding="utf-8")
    (tmp_path / "trash.md").write_text("x", encoding="utf-8")
    v = Vault(root=tmp_path, ignore_patterns=("trash.md",))
    files = v.scan()
    assert len(files) == 1


def test_vault_scan_nonexistent(tmp_path: Path):
    from qingqiu.obsidian.vault import Vault
    v = Vault(root=tmp_path / "nope")
    assert v.scan() == []


def test_vault_stats(tmp_path: Path):
    from qingqiu.obsidian.vault import Vault
    (tmp_path / "n1.md").write_text("x", encoding="utf-8")
    v = Vault(root=tmp_path)
    stats = v.stats()
    assert stats["total_md"] == 1
    assert stats["exists"] is True


# === S8.2 index ===

def test_index_record():
    from qingqiu.obsidian.index import Index
    idx = Index()
    p = Path("/tmp/x.md")
    idx._record(p, "created")
    idx._record(p, "modified")
    events = idx.get_changed()
    assert len(events) == 2


# === S8.3 parser ===

def test_parser_frontmatter(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    md = tmp_path / "n.md"
    md.write_text(
        "---\n"
        "title: My Note\n"
        "tags: [python, fastapi]\n"
        "private: false\n"
        "---\n\n"
        "Body with #extra tag and [[link]] here.",
        encoding="utf-8",
    )
    note = parse_note(md)
    assert note.title == "My Note"
    assert note.private is False
    assert "link" in note.wikilinks


def test_parser_no_frontmatter(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    md = tmp_path / "n.md"
    md.write_text("Plain text with [[X]] and #y tag.", encoding="utf-8")
    note = parse_note(md)
    assert note.title == "n"
    assert note.frontmatter == {}


def test_parser_multiple_wikilinks(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    md = tmp_path / "n.md"
    md.write_text("Link [[A]] and [[B|C]] here.", encoding="utf-8")
    note = parse_note(md)
    assert "A" in note.wikilinks


def test_parser_file_not_found(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_note(tmp_path / "nope.md")


# === S8.4 embed ===

def test_embed_deterministic():
    from qingqiu.obsidian.embed import embed
    v1 = embed("python programming")
    v2 = embed("python programming")
    assert v1 == v2


def test_embed_different_text():
    from qingqiu.obsidian.embed import embed
    v1 = embed("python")
    v2 = embed("rust")
    assert v1 != v2


def test_embed_empty():
    from qingqiu.obsidian.embed import embed
    v = embed("")
    assert len(v) == 32
    assert all(x == 0.0 for x in v)


def test_embed_dim():
    from qingqiu.obsidian.embed import embed
    v = embed("hello world", dim=64)
    assert len(v) == 64


def test_cosine_sim_identical():
    from qingqiu.obsidian.embed import embed, cosine_sim
    v = embed("python")
    assert cosine_sim(v, v) > 0.99


def test_cosine_sim_zero():
    from qingqiu.obsidian.embed import cosine_sim
    assert cosine_sim([0] * 32, [0] * 32) == 0.0


# === S8.5 knowledge agent ===

def test_knowledge_search_top_k(tmp_path: Path):
    from qingqiu.obsidian.knowledge import KnowledgeAgent
    from qingqiu.obsidian.vault import Vault

    (tmp_path / "a.md").write_text(
        "---\ntags: [python]\n---\n# Python #python", encoding="utf-8"
    )
    (tmp_path / "b.md").write_text("Just #rust content", encoding="utf-8")

    v = Vault(root=tmp_path)
    agent = KnowledgeAgent(vault=v)
    results = agent.search("python", top_k=2)
    assert len(results) == 2
    paths = [str(n.path) for n, _ in results]
    assert any("a.md" in p for p in paths)


def test_knowledge_search_empty_query(tmp_path: Path):
    from qingqiu.obsidian.knowledge import KnowledgeAgent
    from qingqiu.obsidian.vault import Vault

    (tmp_path / "n.md").write_text("x", encoding="utf-8")
    v = Vault(root=tmp_path)
    agent = KnowledgeAgent(vault=v)
    assert agent.search("") == []


# === S8.6 private 跳过 ===

def test_private_via_frontmatter(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    md = tmp_path / "n.md"
    md.write_text("---\ntitle: Secret\nprivate: true\n---\nSecret body", encoding="utf-8")
    note = parse_note(md)
    assert note.private is True


def test_private_via_path(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    (tmp_path / "private").mkdir()
    md = tmp_path / "private" / "n.md"
    md.write_text("# Secret", encoding="utf-8")
    note = parse_note(md)
    assert note.private is True


def test_knowledge_skips_private(tmp_path: Path):
    from qingqiu.obsidian.knowledge import KnowledgeAgent
    from qingqiu.obsidian.vault import Vault

    (tmp_path / "public.md").write_text("# Python #python", encoding="utf-8")
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "secret.md").write_text(
        "---\nprivate: true\n---\n# Python #python secret", encoding="utf-8"
    )

    v = Vault(root=tmp_path)
    agent = KnowledgeAgent(vault=v)
    results = agent.search("python", top_k=5)
    paths = [str(n.path) for n, _ in results]
    assert not any("secret.md" in p for p in paths)


# === 端到端 ===

def test_e2e_vault_to_notes(tmp_path: Path):
    from qingqiu.obsidian.parser import parse_note
    from qingqiu.obsidian.vault import Vault

    (tmp_path / "a.md").write_text(
        "---\ntags: [python]\n---\n# Heading #python", encoding="utf-8"
    )
    (tmp_path / "b.md").write_text("Just [[link]] #rust", encoding="utf-8")

    v = Vault(root=tmp_path)
    notes = [parse_note(f) for f in v.scan()]
    assert any("python" in n.frontmatter.get("tags", []) or "python" in n.tags for n in notes)