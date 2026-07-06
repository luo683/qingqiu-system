# M9 · 知识图谱 UI 验证日志

**Slice**: slice/M9
**日期**: 2026-07-06
**范围**: M9 知识图谱 UI（3 个 MVP 切片 · S9.2 / S9.3 / S9.4）

---

## 一、切片摘要

| 切片 | 内容 | 文件 |
| --- | --- | --- |
| S9.2 | FastAPI HTTP server（127.0.0.1:7789） | `src/qingqiu/ui/server.py` |
| S9.2 | 知识图谱数据加载器（vault + sample 兜底） | `src/qingqiu/ui/graph.py` |
| S9.2 | 模块启动入口 | `src/qingqiu/ui/__main__.py` |
| S9.3 | 单 HTML 图谱窗口（Cytoscape.js CDN） | `web/index.html` |
| S9.4 | tag 筛选 + 节点 hover/click 详情 | `src/qingqiu/ui/server.py` + `web/index.html` |
| Verify | 4 场景端到端真跑 | `scripts/verify_m9.py` |

---

## 二、依赖变更

`pyproject.toml` 新增：
- `fastapi>=0.110`
- `uvicorn[standard]>=0.27`

约束遵守：未触碰 llm/ memory/ cli/ security/ personality/ chat/ planner/ daemon/ router/ voice/ im/ obsidian/。

---

## 三、单元 + 集成测试

`uv run pytest tests/ui/ -v` → **40 passed**

- `tests/ui/test_graph.py` · 19 个（GraphBuilder + GraphData 单元）
- `tests/ui/test_server.py` · 21 个（FastAPI TestClient 端到端）

**全量回归**：`uv run pytest` → **516 passed**（476 baseline + 40 新增 · 0 回归）

---

## 四、4 场景真跑验证（verify_m9.py）

```
$ uv run python scripts/verify_m9.py

[verify] M9 知识图谱 UI 真跑验证
[verify] project: E:\MiniMax Code WorkSpace\qingqiu-system
[verify] endpoint: http://127.0.0.1:7789

[step 0] cleanup port 7789
[step 1] start uvicorn server (subprocess)
[step 2] wait for /health (timeout 15.0s)
  server ready

[M9-1] GET /health
  status=200
  body={"ok":true,"service":"qingqiu-ui","version":"M9","source":"sample","nodes":12,"edges":16}

[M9-2] GET /api/graph.json
  status=200
  nodes=12 edges=16

[M9-3] GET /  (web/index.html)
  status=200 content-type=text/html; charset=utf-8
  body_len=11961

[M9-4] GET /api/filter?tag=arch
  status=200
  filtered_nodes=11/12 edges=14

[step 99] terminate server

============================================================
[verify] M9 PASS · 4/4 验证全过
```

| 场景 | 端点 | 验证点 | 结果 |
| --- | --- | --- | --- |
| M9-1 | GET /health | ok=true / service=qingqiu-ui / version=M9 / nodes ≥ 10 | PASS |
| M9-2 | GET /api/graph.json | nodes + edges + Cytoscape 格式 + count ≥ 10 | PASS |
| M9-3 | GET / | HTML + 包含 cytoscape + /api/graph.json fetch + 清秋 标题 | PASS |
| M9-4 | GET /api/filter?tag=arch | filter_tag=arch + 节点全含 arch + 边在子图内 | PASS |

---

## 五、API 端点清单

| 端点 | 方法 | 用途 |
| --- | --- | --- |
| `/health` | GET | 健康检查（顺带报告节点数 + 数据源） |
| `/api/graph.json` | GET | 全图 nodes + edges（Cytoscape 兼容格式） |
| `/api/nodes/{id}` | GET | 单节点详情（404 on miss） |
| `/api/filter?tag=X` | GET | 按 tag 筛选（空 tag = 全图） |
| `/` | GET | web/index.html |
| `/static/{name}` | GET | web/ 下的任意静态文件 |

---

## 六、数据加载策略

GraphBuilder 按优先级加载：
1. 显式 `--vault <dir>` 指定的目录（递归扫 `.md`）
2. vault 目录存在但为空 → 回落 sample
3. vault 不存在 → 直接 sample

**Markdown 解析规则**：
- `id` = 文件名（去 `.md`）
- `title` = frontmatter.title > `# heading` > id
- `tags` = frontmatter.tags list > 正文内联 `#tag`
- `edges` = `[[wikilink]]` 双向边（去重 + 无自环）
- `metadata` = frontmatter 其余字段 + 第一段摘要

**Sample 数据**（MVP 兜底）：12 节点 / 16 边，覆盖 core / arch / memory / ui / personality 等 tag。

---

## 七、web/ 单 HTML

- 纯 HTML + JS + CSS，**无构建步骤**
- Cytoscape.js 通过 unpkg CDN 加载
- 节点 click → 右侧面板显示 id / title / tags / metadata
- 节点 hover → 高亮 + tooltip 显示 tag 列表
- 顶部 search box → 回车触发 `/api/filter?tag=X`
- 左侧 tag chip → 点击直接筛选

---

## 八、启动方式

```bash
# 默认（端口 7789，sample 数据）
uv run python -m qingqiu.ui

# 指定 vault
uv run python -m qingqiu.ui --vault ./docs

# uvicorn 直启（生产风格）
uv run uvicorn qingqiu.ui.server:app --host 127.0.0.1 --port 7789
```

约束说明：任务禁止修改 `cli/`，故未把 `ui` 接入 `qingqiu` CLI 子命令；提供 `python -m qingqiu.ui` 模块入口作为替代。

---

## 九、Acceptance

- [x] pytest tests/ui/ ≥ 8 测试全过（**40 通过**）
- [x] 全量不回归 ≥ 476（**516 通过**）
- [x] verify_m9.py 4 场景全过（**4/4 PASS**）
- [x] web/index.html curl 验证 200 + 含 cytoscape
- [x] 节点 ≥ 10（**12**）
- [x] tag 筛选 work

**总评**：M9 ✅ PASS · 40/40 UI 测试 + 516/516 全量 + 4/4 端到端真跑。