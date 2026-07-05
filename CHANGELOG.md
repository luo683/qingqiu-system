# CHANGELOG · 清秋变更日志

> **格式：** [Keep a Changelog](https://keepachangelog.com/) + [Semantic Versioning](https://semver.org/)
> **状态：** v0.3.0 · 立项完成

---

## [Unreleased]

### Added
- **S1.1 · 项目骨架与配置入口**（2026-07-05）
  - `pyproject.toml`（uv + hatchling，dependencies 留空）
  - `src/qingqiu/` 包结构（`__init__.py` + `cli.py` + `__main__.py`）
  - CLI 骨架：`--version` / `-v` / `config show`（占位）
  - `scripts/verify_s1_1.sh` 验收脚本
  - `tests/test_cli.py` 5 个 pytest 测试覆盖 CLI
  - 验收 PASS：uv sync 装依赖成功 + pytest 5/5
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S1.1

---

## [0.3.0] - 2026-07-05

### Changed（重大变更）

- **技术栈主流化**（决策 D-003）
  - `pywhispercpp` → **`faster-whisper`**（CTranslate2 推理，更主流，性能更好）
  - `aiohttp` → **`FastAPI`**（Python HTTP server 主流，自动 OpenAPI）
  - `npm` → **`pnpm`**（节省磁盘，单仓多包友好）
- **目录迁移**：`jarvis-system/` → **`qingqiu-system/`**（决策 D-002，与产品名一致）
- **文档重组**：
  - 所有核心文档移到项目根目录：`README.md` / `PRD.md` / `ARCH.md` / `PROJECT.md` / `TECH-STACK.md` / `DESIGN.md` / `IMPLEMENTATION-PLAN.md` / `NON-FUNCTIONAL.md` / `AGENTS.md` / `CHANGELOG.md`
  - 新建 `references/` 前端标准目录
- **三件套同步更新规则**（决策 D-004）：PRD / ARCH / PROJECT 每次大改动必须同时更新
- **AI Agent 权限收紧**（决策 D-006）：禁止重构 / 禁止改 UI / 禁止改无关逻辑 / 禁止做主

### Added

- **ARCH.md**：架构总览 + 五层架构图 + 数据流 + 接口边界 + 进程模型 + **开发纪律（§10）**
- **PROJECT.md**：项目快照 + 决策记录 + 下一步
- **AGENTS.md**：coding agent 总规约
- **references/** 目录：
  - `README.md` — 前端标准索引
  - `naming.md` — 命名规则 + 文件大小上限
  - `components.md` — 组件规范（待补）
  - `styling.md` — 样式规范（待补）
  - `testing.md` — 测试规范（待补）
- **强约束**：密钥不进前端（决策 D-007）

---

## [0.2.2] - 2026-07-05 18:19

### Changed

- **改名**：贾维斯 / Jarvis → **清秋 / QingQiu**（决策 D-001，CLI / 进程 / 路径 / 热键 / 唤醒词 / prompt 全栈替换）

### Added

- **Obsidian 知识库接入**：vault 索引 / wikilink 解析 / 嵌入向量化 / 私密笔记跳过
- **知识图谱可视化**：Cytoscape.js 渲染 / 节点 / 边 / 聚类 / 筛选器
- **自我成长机制**：5 条学习路径（任务归档 / 用户纠正 / vault 反哺 / 每周复盘 / 偏好冲突检测）
- 新增 `knowledge` agent + 内部 `reflect` / `indexer` agent
- 新增里程碑 M8（Obsidian 接入）/ M9（知识图谱 UI）/ M10（自我成长）
- 切片总数：38 → **48**

---

## [0.2.1] - 2026-07-05 18:14

### Added

- **P8 私密信息零泄露原则**：身份、财务、健康、凭证、私密文件、通讯记录默认拒绝处理
- **§10.4 私密信息处理专节**：
  - 三道防线（Detect 识别 → Block 阻断 → Redact 脱敏）
  - 三种例外通道（`include_private` / `redact_only` / `private_send`，全部限时 + 逐条）
  - 记忆策略（私密默认不入 L2/L3）
  - LLM 路由策略（命中私密强制本地优先）
- §10.3 危险操作黑名单扩充（上传云端 / 跨白名单移动 / 读私密文件 / 导出记忆库）
- §14 安全新增"私密信息泄露"防护一行

---

## [0.2.0] - 2026-07-05 18:07

### Changed（**完全重写**）

- **"Hermes 叠加层"思路** → **"吃掉 Hermes 做升级替代"**
- **保留 Codex / OpenCode / ZCode** → **重设 coder / reviewer / info / life 四类 agent**
- **CLI 优先** → **语音优先**
- **主动通知** → **纯被动**（与传统 JARVIS 反差巨大的有意设计）
- **LLM 走云端路由** → **抽象层 + 可热插拔 provider**
- **单目录白名单** → **4 目录标准白名单**
- **固定中性人格** → **prompt 自定义**
- **危险操作确认** → **每次写入前确认**
- **分阶段 MVP** → **全栈第一版**
- **2 周跑通** → **不急打磨**

### Added

- PRD 五个章节大幅扩展：技术架构 / 角色体系 / 关键模块 / 数据权限 / 主动性与会话 / 记忆与人格 / 接入多模态 / 安全 / 迁移 / 里程碑

---

## [0.1.0] - 2026-07-05 17:54

### Added

- PRD 初稿：基于 Hermes 多 agent 框架做贾维斯系统（HOT 思路）

> 已归档为 [PRD-v0.1-archived.md](./PRD-v0.1-archived.md)（如需要可从 jarvis-system/docs/ 迁移）

---

## 历史对话快照（2026-07-05 一天完成）

| 时间 | 关键事件 |
|------|---------|
| 17:45 | 用户确立工作空间 `E:\MiniMax Code WorkSpace` |
| 17:54 | 第一份 PRD v0.1（Hermes 叠加） |
| 18:07 | PRD v0.2 完全重写 |
| 18:14 | PRD v0.2.1 强化私密信息保护 |
| 18:19 | PRD v0.2.2 改名清秋 + Obsidian + 知识图谱 + 自我成长 |
| 18:25 | TECH-STACK.md v0.2.2 |
| 18:27 | DESIGN.md + IMPLEMENTATION-PLAN.md（48 切片） |
| 18:37 | NON-FUNCTIONAL.md（四维量化） |
| 19:17 | **工程纪律全面收紧**：主流化 + 三件套 + references/ + Git + 模块拆分 |
| 19:19 | 用户决策：GitHub 仓库 + 迁 qingqiu-system |
| 19:25 | v0.3.0 文档重组 + references/ 标准 |

---

**变更日志必更新。** 每次大改动一行；细节看 commit。