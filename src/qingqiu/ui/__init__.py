"""qingqiu.ui · 知识图谱 UI（M9 · S9.2/S9.3/S9.4）

MVP 切片：
- S9.2 FastAPI HTTP server（127.0.0.1:7789）
- S9.3 单 HTML 图谱窗口（Cytoscape.js CDN）
- S9.4 节点 / 边 / tag 筛选

启动方式：
    uv run python -m qingqiu.ui            # 默认端口 7789
    uv run python -m qingqiu.ui --port 7789
    uv run uvicorn qingqiu.ui.server:app --port 7789
"""

from __future__ import annotations

from qingqiu.ui.graph import GraphBuilder, GraphData, Node, Edge
from qingqiu.ui.server import create_ui_app

__all__ = ["create_ui_app", "GraphBuilder", "GraphData", "Node", "Edge"]