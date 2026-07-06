"""qingqiu.ui.server · FastAPI HTTP server（M9 · S9.2 + S9.5）

端点：
    GET /                → 静态 web/index.html（HTML 入口）
    GET /api/graph.json  → 全图 JSON（nodes + edges + metadata）
    GET /api/nodes/{id}  → 单节点详情（找不到 → 404）
    GET /api/filter?tag=X → 按 tag 筛选（缺省 / 空 → 全图）
    GET /api/open/{id}   → S9.5 打开 Obsidian（OS default handler）
    GET /health          → 健康检查 {ok: true, source: ...}

复用 daemon/server.py 模式（FastAPI + uvicorn + StaticFiles）。
注意：当前 slice-M9 不存在 daemon/server.py，本切片直接复用 FastAPI 标准模式。
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from qingqiu.ui.graph import GraphBuilder


def _find_web_dir() -> Path:
    """定位 web/ 目录（仓库根的 web/）"""
    # src/qingqiu/ui/server.py → 仓库根
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "web",  # .worktrees/slice-M9/web
        here.parents[2] / "web",  # src/qingqiu/../web
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # 兜底：返回期望路径（即使不存在，方便错误信息）
    return candidates[0]


def _index_path() -> Path:
    return _find_web_dir() / "index.html"


def create_ui_app(vault: Path | None = None) -> FastAPI:
    """构造 UI FastAPI app（factory pattern，方便测试用 TestClient）

    Args:
        vault: 知识库目录（None → 兜底 sample data）
    """
    app = FastAPI(
        title="清秋知识图谱 UI",
        version="M9",
        description="本地优先的知识图谱可视化（S9.2/S9.3/S9.4）",
    )
    builder = GraphBuilder(vault=vault)

    # === /health ===
    @app.get("/health")
    def health() -> dict[str, Any]:
        # 顺手统计节点数，便于验证
        graph = builder.build()
        return {
            "ok": True,
            "service": "qingqiu-ui",
            "version": "M9",
            "source": graph.source,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        }

    # === /api/graph.json ===
    @app.get("/api/graph.json")
    def graph_json() -> dict[str, Any]:
        return builder.build().to_json()

    # === /api/nodes/{id} ===
    @app.get("/api/nodes/{node_id}")
    def node_detail(node_id: str) -> dict[str, Any]:
        graph = builder.build()
        for n in graph.nodes:
            if n.id == node_id:
                return {
                    "id": n.id,
                    "title": n.title,
                    "tags": n.tags,
                    "metadata": n.metadata,
                }
        raise HTTPException(status_code=404, detail=f"node not found: {node_id!r}")

    # === /api/filter?tag=X ===
    @app.get("/api/filter")
    def filter_by_tag(tag: str = Query(default="", description="tag name; empty=all")) -> dict[str, Any]:
        full = builder.build()
        if not tag:
            return full.to_json()
        filtered = full.filter_by_tag(tag)
        payload = filtered.to_json()
        payload["filter_tag"] = tag
        payload["original_count"] = {"nodes": len(full.nodes), "edges": len(full.edges)}
        return payload

    # === S9.5 打开 Obsidian 笔记 ===
    @app.get("/api/open/{node_id}")
    def open_node(node_id: str) -> dict[str, Any]:
        """打开 vault 笔记（用 OS default handler）"""
        node = builder.get_node(node_id)
        if node is None or not node.path:
            raise HTTPException(status_code=404, detail=f"node not found or no path: {node_id}")
        path = Path(node.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"file not found: {node.path}")
        try:
            system = platform.system().lower()
            if system == "windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif system == "darwin":
                subprocess.run(["open", str(path)], check=True, timeout=5)
            else:
                subprocess.run(["xdg-open", str(path)], check=True, timeout=5)
            return {"status": "opened", "path": str(path), "node_id": node_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"open failed: {e}") from e

    # === 静态文件：根路径返回 index.html ===
    @app.get("/", include_in_schema=False, response_model=None)
    def index():
        path = _index_path()
        if not path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "index.html not found", "expected": str(path)},
            )
        return FileResponse(path, media_type="text/html")

    # === 静态目录：/static/* 任意资源 ===
    @app.get("/static/{name}", include_in_schema=False, response_model=None)
    def static_file(name: str):
        path = _find_web_dir() / name
        if not path.exists() or not path.is_file():
            return JSONResponse(status_code=404, content={"error": f"not found: {name}"})
        # 简单 mime 推断
        media = "text/plain"
        if path.suffix == ".html":
            media = "text/html"
        elif path.suffix == ".js":
            media = "application/javascript"
        elif path.suffix == ".css":
            media = "text/css"
        elif path.suffix == ".json":
            media = "application/json"
        return FileResponse(path, media_type=media)

    # === 暴露 builder / vault 给测试和调试 ===
    app._qingqiu_builder = builder  # type: ignore[attr-defined]
    app._qingqiu_vault = vault  # type: ignore[attr-defined]

    return app


# 默认 app 实例（uvicorn qingqiu.ui.server:app）
app = create_ui_app()