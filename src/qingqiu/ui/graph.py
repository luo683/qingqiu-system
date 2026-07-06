"""qingqiu.ui.graph · 知识图谱数据加载器

数据来源（按优先级）：
1. 显式传入的 vault 目录（递归扫描 .md）
2. 项目内置 docs/ 目录（默认）
3. 内置 sample data（MVP 兜底，确保节点 ≥ 10）

节点提取规则（vault .md 文件）：
- id = 文件名（去 .md）
- title = 第一行 # heading（缺省用 id）
- tags = frontmatter `tags: [...]` 或正文 `#tag` 内联
- edges = 正文中 `[[其他节点id]]` 双向边（去重）
- metadata = frontmatter 全部 key=value（除 tags）+ 第一段正文摘要
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# === 兜底 sample 数据（MVP：确保 ≥ 10 节点 + 边 + tag 筛选可用）===

_SAMPLE_NODES: list[dict[str, Any]] = [
    {
        "id": "qingqiu",
        "title": "清秋系统",
        "tags": ["project", "core", "arch"],
        "metadata": {"type": "system", "status": "active", "version": "0.3.0"},
    },
    {
        "id": "memory",
        "title": "记忆层",
        "tags": ["arch", "core"],
        "metadata": {"type": "module", "layers": 4},
    },
    {
        "id": "L0",
        "title": "L0 · 会话内记忆",
        "tags": ["memory", "arch"],
        "metadata": {"type": "memory-layer", "persistence": "none"},
    },
    {
        "id": "L1",
        "title": "L1 · 项目级记忆",
        "tags": ["memory", "arch"],
        "metadata": {"type": "memory-layer", "persistence": "markdown"},
    },
    {
        "id": "L2",
        "title": "L2 · 用户级记忆",
        "tags": ["memory", "arch"],
        "metadata": {"type": "memory-layer", "persistence": "markdown"},
    },
    {
        "id": "L3",
        "title": "L3 · 长期事实",
        "tags": ["memory", "arch"],
        "metadata": {"type": "memory-layer", "persistence": "sqlite"},
    },
    {
        "id": "cli",
        "title": "CLI 入口",
        "tags": ["arch", "core"],
        "metadata": {"type": "module", "commands": 9},
    },
    {
        "id": "router",
        "title": "意图路由器",
        "tags": ["arch", "router"],
        "metadata": {"type": "module", "backends": ["rule", "llm"]},
    },
    {
        "id": "llm",
        "title": "LLM Provider",
        "tags": ["arch", "llm"],
        "metadata": {"type": "module", "providers": ["openai", "anthropic", "ollama"]},
    },
    {
        "id": "security",
        "title": "安全层",
        "tags": ["arch", "security", "core"],
        "metadata": {"type": "module", "components": 5},
    },
    {
        "id": "ui",
        "title": "知识图谱 UI",
        "tags": ["ui", "mvp", "feature"],
        "metadata": {"type": "module", "port": 7789, "version": "M9"},
    },
    {
        "id": "personality",
        "title": "人格配置",
        "tags": ["arch", "personality"],
        "metadata": {"type": "module", "scope": "system"},
    },
]

_SAMPLE_EDGES: list[dict[str, str]] = [
    {"source": "qingqiu", "target": "memory", "kind": "contains"},
    {"source": "qingqiu", "target": "cli", "kind": "contains"},
    {"source": "qingqiu", "target": "router", "kind": "contains"},
    {"source": "qingqiu", "target": "llm", "kind": "contains"},
    {"source": "qingqiu", "target": "security", "kind": "contains"},
    {"source": "qingqiu", "target": "ui", "kind": "contains"},
    {"source": "qingqiu", "target": "personality", "kind": "contains"},
    {"source": "memory", "target": "L0", "kind": "has"},
    {"source": "memory", "target": "L1", "kind": "has"},
    {"source": "memory", "target": "L2", "kind": "has"},
    {"source": "memory", "target": "L3", "kind": "has"},
    {"source": "cli", "target": "router", "kind": "uses"},
    {"source": "router", "target": "llm", "kind": "uses"},
    {"source": "ui", "target": "memory", "kind": "reads"},
    {"source": "personality", "target": "llm", "kind": "configures"},
    {"source": "security", "target": "cli", "kind": "guards"},
]


@dataclass
class Node:
    """图节点"""

    id: str
    title: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    path: str | None = None  # S9.5 · vault 文件绝对路径（用于点节点打开 Obsidian）

    def to_cytoscape(self) -> dict[str, Any]:
        return {
            "data": {
                "id": self.id,
                "label": self.title,
                "tags": list(self.tags),
                "metadata": dict(self.metadata),
                "path": self.path,
            }
        }


@dataclass
class Edge:
    """图边（有向，可选 kind 标签）"""

    source: str
    target: str
    kind: str = "related"

    def to_cytoscape(self) -> dict[str, Any]:
        return {
            "data": {
                "id": f"{self.source}->{self.target}",
                "source": self.source,
                "target": self.target,
                "label": self.kind,
            }
        }


@dataclass
class GraphData:
    """完整图"""

    nodes: list[Node]
    edges: list[Edge]
    source: str = "sample"  # "vault" / "docs" / "sample"

    def to_json(self) -> dict[str, Any]:
        """序列化为 API JSON（含 Cytoscape 兼容 nodes/edges）"""
        return {
            "source": self.source,
            "count": {"nodes": len(self.nodes), "edges": len(self.edges)},
            "nodes": [n.to_cytoscape() for n in self.nodes],
            "edges": [e.to_cytoscape() for e in self.edges],
            # 便于调试的扁平视图
            "flat_nodes": [asdict(n) for n in self.nodes],
        }

    def filter_by_tag(self, tag: str) -> GraphData:
        """按 tag 筛选：保留命中节点 + 它们之间的边"""
        if not tag:
            return self
        matched = {n.id for n in self.nodes if tag in n.tags}
        kept_edges = [e for e in self.edges if e.source in matched and e.target in matched]
        return GraphData(
            nodes=[n for n in self.nodes if n.id in matched],
            edges=kept_edges,
            source=self.source,
        )


# === 解析 helper ===

_FRONTMATTER_RE = re.compile(r"\A\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_INLINE_TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z][A-Za-z0-9_\-]+)")
_WIKILINK_RE = re.compile(r"\[\[([A-Za-z0-9_\-./]+)\]\]")


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """极简 frontmatter 解析：只识别 `key: value` / `tags: [a, b]`，其余视为 body"""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    meta: dict[str, Any] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            # YAML 风格 list
            inner = value[1:-1]
            meta[key] = [v.strip() for v in inner.split(",") if v.strip()]
        else:
            meta[key] = value.strip('"').strip("'")
    return meta, body


def _summary(body: str, max_len: int = 120) -> str:
    """取第一段非空文本作为摘要"""
    for para in body.split("\n\n"):
        text = " ".join(para.split()).strip()
        if text and not _HEADING_RE.match(text):
            return text[:max_len]
    return ""


def _parse_md_file(path: Path) -> Node | None:
    """解析单个 .md 文件为 Node。失败或非 .md 返回 None。"""
    if path.suffix.lower() != ".md":
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    front, body = _parse_frontmatter(text)

    node_id = path.stem

    # title 优先级：frontmatter.title > 第一行 heading > node_id
    title = front.get("title") if isinstance(front.get("title"), str) else None
    if not title:
        m = _HEADING_RE.search(body)
        title = m.group(1) if m else node_id

    # tags：frontmatter.tags list > 正文内联 #tag > 空
    tags: list[str] = []
    fm_tags = front.get("tags")
    if isinstance(fm_tags, list):
        tags = [str(t) for t in fm_tags]
    else:
        tags = list(dict.fromkeys(_INLINE_TAG_RE.findall(body)))

    metadata: dict[str, Any] = {
        k: v
        for k, v in front.items()
        if k not in ("title", "tags")
    }
    summary = _summary(body)
    if summary:
        metadata["summary"] = summary
    return Node(id=node_id, title=title, tags=tags, metadata=metadata, path=str(path))


def _scan_vault(vault: Path) -> tuple[list[Node], list[Edge]]:
    """递归扫描 vault，返回 (nodes, edges)"""
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_ids: set[str] = set()
    edge_set: set[tuple[str, str]] = set()

    if not vault.exists() or not vault.is_dir():
        return nodes, edges

    for md_path in sorted(vault.rglob("*.md")):
        # 跳过隐藏目录 / 节点模板目录
        parts = set(md_path.parts)
        if any(p.startswith(".") for p in parts):
            continue
        node = _parse_md_file(md_path)
        if node is None:
            continue
        if node.id in seen_ids:
            # 同名文件：保留第一个；MVP 不处理冲突
            continue
        seen_ids.add(node.id)
        nodes.append(node)

    # 边：根据 wikilink + 同目录相邻
    id_to_node = {n.id: n for n in nodes}
    for md_path in sorted(vault.rglob("*.md")):
        if any(p.startswith(".") for p in md_path.parts):
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        src_id = md_path.stem
        if src_id not in id_to_node:
            continue
        for link in _WIKILINK_RE.findall(text):
            # wikilink 可能含路径，取 basename
            target_id = link.split("/")[-1]
            if target_id not in id_to_node or target_id == src_id:
                continue
            key = (src_id, target_id)
            if key in edge_set:
                continue
            edge_set.add(key)
            edges.append(Edge(source=src_id, target=target_id, kind="wikilink"))

    return nodes, edges


class GraphBuilder:
    """知识图谱构建器：vault → GraphData（兜底 sample）

    用法：
        builder = GraphBuilder(vault=Path("./docs"))  # 或 None
        graph = builder.build()
        graph = builder.build_filtered("arch")  # tag 筛选
    """

    def __init__(self, vault: Path | None = None) -> None:
        self._vault = vault

    @property
    def vault(self) -> Path | None:
        return self._vault

    def build(self) -> GraphData:
        """构建图：vault 优先；vault 不存在或为空 → sample 兜底"""
        nodes: list[Node] = []
        edges: list[Edge] = []
        source = "sample"

        if self._vault is not None:
            vault_nodes, vault_edges = _scan_vault(self._vault)
            if vault_nodes:
                nodes, edges = vault_nodes, vault_edges
                source = "vault"

        if not nodes:
            # sample 兜底
            nodes = [Node(**n) for n in _SAMPLE_NODES]
            edges = [Edge(**e) for e in _SAMPLE_EDGES]

        return GraphData(nodes=nodes, edges=edges, source=source)

    def build_filtered(self, tag: str) -> GraphData:
        """tag 筛选便捷方法"""
        return self.build().filter_by_tag(tag)