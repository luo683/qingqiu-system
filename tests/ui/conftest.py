"""tests.ui.conftest · M9 测试 fixtures"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qingqiu.ui.graph import GraphBuilder
from qingqiu.ui.server import create_ui_app


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """临时 vault：4 个 .md 节点 + 2 个 wikilink 边"""
    docs = tmp_path / "vault"
    docs.mkdir()
    (docs / "alpha.md").write_text(
        "---\n"
        "title: Alpha Node\n"
        "tags: [arch, alpha]\n"
        "---\n"
        "# Alpha\n\n"
        "links to [[beta]] and [[gamma]].\n",
        encoding="utf-8",
    )
    (docs / "beta.md").write_text(
        "---\n"
        "tags: [arch, beta]\n"
        "---\n"
        "# Beta\n\n"
        "see also [[alpha]] and [[gamma]].\n",
        encoding="utf-8",
    )
    (docs / "gamma.md").write_text(
        "# Gamma\n\n"
        "Inline #arch tag. points to [[alpha]].\n",
        encoding="utf-8",
    )
    (docs / "delta.md").write_text(
        "---\n"
        "title: Delta\n"
        "tags: [misc]\n"
        "author: ROG\n"
        "---\n"
        "# Delta\n\n"
        "This is a delta node with no wikilinks but custom metadata.\n\n"
        "Second paragraph for summary test.\n",
        encoding="utf-8",
    )
    return docs


@pytest.fixture
def client():
    """默认 client（无 vault → sample data）"""
    app = create_ui_app()
    return TestClient(app)


@pytest.fixture
def client_vault(vault_dir: Path):
    """vault 模式 client"""
    app = create_ui_app(vault=vault_dir)
    return TestClient(app)


@pytest.fixture
def empty_vault(tmp_path: Path) -> Path:
    return tmp_path / "empty_vault"  # not created on purpose


@pytest.fixture
def builder_sample() -> GraphBuilder:
    return GraphBuilder(vault=None)


@pytest.fixture
def builder_vault(vault_dir: Path) -> GraphBuilder:
    return GraphBuilder(vault=vault_dir)


@pytest.fixture
def web_dir() -> Path:
    """仓库根的 web/ 目录"""
    here = Path(__file__).resolve()
    # tests/ui/conftest.py → 仓库根 → web
    return here.parents[2] / "web"