"""verify_m8_remaining.py · M8 剩余切片真跑验证（S8.4/5/6）

3 场景：
1. embed: 相同 text → 相同 vector
2. knowledge search: query → top 5 notes
3. private 跳过：frontmatter private:true → search 不返回
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKTREE / "src"))

from qingqiu.obsidian.embed import embed, cosine_sim
from qingqiu.obsidian.knowledge import KnowledgeAgent
from qingqiu.obsidian.vault import Vault


def main():
    print("=" * 60)
    print("M8 剩余切片 · 3 场景真跑验证")
    print("=" * 60)

    # === 场景 1: embed deterministic ===
    print("\n[场景 1] embed deterministic")
    v1 = embed("python programming")
    v2 = embed("python programming")
    assert v1 == v2, "embed 应该 deterministic"
    print(f"  embed('python programming') dim={len(v1)}")
    assert len(v1) == 32, "默认 32-dim"
    print("  [PASS] embed 一致 + 32-dim")

    # === 场景 2: knowledge search ===
    print("\n[场景 2] knowledge agent search")
    tmp = Path(tempfile.mkdtemp(prefix="qingqiu_m8r_"))
    (tmp / "a.md").write_text(
        "---\ntitle: Python\ntags: [python]\n---\n# Python #python is great", encoding="utf-8"
    )
    (tmp / "b.md").write_text("Rust #rust is fast", encoding="utf-8")
    (tmp / "c.md").write_text("More python #python content", encoding="utf-8")

    vault = Vault(root=tmp)
    agent = KnowledgeAgent(vault=vault)
    results = agent.search("python", top_k=3)
    assert len(results) == 3, f"应该返 3 结果，实际 {len(results)}"
    print(f"  search 'python' → {len(results)} notes")
    for note, score in results:
        print(f"    [{score:.3f}] {note.path.name}")
    print("  [PASS] knowledge 返 top-3")

    # === 场景 3: private 跳过 ===
    print("\n[场景 3] private 跳过")
    (tmp / "private").mkdir()
    (tmp / "private" / "secret.md").write_text(
        "---\nprivate: true\n---\n# Python #python secret", encoding="utf-8"
    )

    results2 = agent.search("python", top_k=10)
    paths = [str(n.path) for n, _ in results2]
    assert not any("secret.md" in p for p in paths), "private note 应被跳过"
    print(f"  search 'python' after private → {len(results2)} notes (no secret)")
    print("  [PASS] private 跳过")

    print("\n" + "=" * 60)
    print("[verify] M8 remaining PASS · 3 场景全过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())