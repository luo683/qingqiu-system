"""tests.ui.test_graph · GraphBuilder 单元测试"""

from __future__ import annotations

from pathlib import Path

from qingqiu.ui.graph import Edge, GraphBuilder, GraphData, Node


# === S9.2 · 数据加载 ===


def test_sample_fallback_when_no_vault(builder_sample: GraphBuilder) -> None:
    """无 vault 时回落到 sample 数据，节点 ≥ 10"""
    g = builder_sample.build()
    assert isinstance(g, GraphData)
    assert g.source == "sample"
    assert len(g.nodes) >= 10
    assert len(g.edges) >= 1


def test_sample_nodes_have_required_fields(builder_sample: GraphBuilder) -> None:
    g = builder_sample.build()
    for n in g.nodes:
        assert isinstance(n, Node)
        assert n.id
        assert n.title
        assert isinstance(n.tags, list)


def test_vault_load(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    assert g.source == "vault"
    ids = {n.id for n in g.nodes}
    assert ids == {"alpha", "beta", "gamma", "delta"}


def test_vault_extracts_frontmatter_tags(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    by_id = {n.id: n for n in g.nodes}
    assert "arch" in by_id["alpha"].tags
    assert "alpha" in by_id["alpha"].tags


def test_vault_extracts_inline_tags(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    by_id = {n.id: n for n in g.nodes}
    assert "arch" in by_id["gamma"].tags


def test_vault_extracts_wikilink_edges(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    pairs = {(e.source, e.target) for e in g.edges}
    # alpha → beta, alpha → gamma, beta → alpha, beta → gamma, gamma → alpha
    assert ("alpha", "beta") in pairs
    assert ("alpha", "gamma") in pairs
    assert ("beta", "alpha") in pairs
    assert ("gamma", "alpha") in pairs
    # 所有边 kind == "wikilink"
    assert all(e.kind == "wikilink" for e in g.edges)


def test_vault_no_self_loops(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    for e in g.edges:
        assert e.source != e.target


def test_vault_no_duplicate_edges(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    pairs = [(e.source, e.target) for e in g.edges]
    assert len(pairs) == len(set(pairs))


def test_vault_preserves_extra_metadata(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    by_id = {n.id: n for n in g.nodes}
    assert by_id["delta"].metadata.get("author") == "ROG"
    assert "summary" in by_id["delta"].metadata


def test_vault_title_priority_frontmatter_then_heading(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    by_id = {n.id: n for n in g.nodes}
    # alpha: frontmatter.title = "Alpha Node"
    assert by_id["alpha"].title == "Alpha Node"
    # beta: 没有 title, 用 heading "# Beta"
    assert by_id["beta"].title == "Beta"
    # delta: frontmatter.title = "Delta"
    assert by_id["delta"].title == "Delta"


def test_empty_vault_falls_back_to_sample(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    g = GraphBuilder(vault=empty).build()
    assert g.source == "sample"


def test_nonexistent_vault_falls_back_to_sample(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nope"
    g = GraphBuilder(vault=nonexistent).build()
    assert g.source == "sample"


# === S9.4 · tag 筛选 ===


def test_filter_by_tag_keeps_only_matched_nodes(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    arch = g.filter_by_tag("arch")
    assert {n.id for n in arch.nodes} == {"alpha", "beta", "gamma"}


def test_filter_by_tag_keeps_only_inner_edges(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    arch = g.filter_by_tag("arch")
    # delta 没 tag=arch，所以 delta 相关的边都要被剔除
    for e in arch.edges:
        assert e.source in {"alpha", "beta", "gamma"}
        assert e.target in {"alpha", "beta", "gamma"}


def test_filter_empty_tag_returns_full_graph(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    assert len(g.filter_by_tag("").nodes) == len(g.nodes)


def test_filter_unknown_tag_returns_empty(builder_vault: GraphBuilder) -> None:
    g = builder_vault.build()
    out = g.filter_by_tag("nonexistent_tag")
    assert out.nodes == []
    assert out.edges == []


def test_to_json_shape(builder_sample: GraphBuilder) -> None:
    payload = builder_sample.build().to_json()
    assert "nodes" in payload
    assert "edges" in payload
    assert "source" in payload
    assert "count" in payload
    assert payload["count"]["nodes"] >= 10
    # Cytoscape 元素格式：nodes[].data.id / edges[].data.source+target
    for n in payload["nodes"]:
        assert "data" in n
        assert "id" in n["data"]
    for e in payload["edges"]:
        assert "data" in e
        assert "source" in e["data"]
        assert "target" in e["data"]


def test_node_to_cytoscape() -> None:
    n = Node(id="x", title="X", tags=["t1"], metadata={"k": "v"})
    d = n.to_cytoscape()
    assert d["data"]["id"] == "x"
    assert d["data"]["label"] == "X"
    assert d["data"]["tags"] == ["t1"]


def test_edge_to_cytoscape() -> None:
    e = Edge(source="a", target="b", kind="wikilink")
    d = e.to_cytoscape()
    assert d["data"]["id"] == "a->b"
    assert d["data"]["label"] == "wikilink"