# ARCH · 清秋架构总览

> **状态：** v0.3.0 · 配套 PRD v0.2.2
> **作者：** Mavis
> **本文件性质：** 架构的"骨架图 + 边界 + 纪律"。**架构大改动时本文件必须更新**（与 PRD / PROJECT 同步）。

---

## 1. 一句话架构

**清秋 = 五层单体应用 + 五类 Agent + 多进程本地部署 + 完全本地数据 + 可热插拔 LLM**。

---

## 2. 五层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│ L1 · Inputs（输入聚合层）                                          │
│ ├─ 🎙️ Voice（faster-whisper STT · 全局热键 Ctrl+Shift+Q）          │
│ ├─ ⌨️  CLI（qingqiu "..." 文本命令）                                │
│ ├─ 💬 Feishu Bot（飞书 WebSocket 补充入口）                         │
│ └─ 📊 Graph UI（Tauri 桌面壳 / 127.0.0.1:7788 FastAPI）            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ NormalizedInput
┌─────────────────────────▼───────────────────────────────────────┐
│ L2 · QingQiu Core（核心层 · asyncio 单进程）                       │
│                                                                   │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐ ┌────────┐│
│  │ Router  │→ │ Planner  │→ │Executor │→ │ Confirm  │→│Reflect ││
│  └─────────┘  └──────────┘  └─────────┘  └──────────┘ └────────┘│
└─────────────────────────┬───────────────────────────────────────┘
                          │ Hermes Task Protocol
┌─────────────────────────▼───────────────────────────────────────┐
│ L3 · Agents（执行层）                                              │
│ ├─ 🔨 coder       代码实现 · PR · shell · 测试                     │
│ ├─ 🔍 reviewer     PR 评审 · 代码质量                              │
│ ├─ 📚 info         PDF/网页/视频摘要 · 检索                         │
│ ├─ 🗓️ life         日程/邮件/IM/提醒                              │
│ └─ 🧠 knowledge   vault 检索 · 知识图谱构建                       │
│                                                                   │
│ 内部角色：reflect · indexer                                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│ L4 · External Tools（外部工具层 · 白名单）                         │
│ ├─ File I/O（白名单 4 目录 + vault）                                │
│ ├─ Shell（受限白名单 + 黑名单）                                     │
│ ├─ Git（gh CLI）                                                  │
│ ├─ Browser（playwright）                                          │
│ ├─ Feishu（lark-tools）                                           │
│ └─ Email / Web Search / Web Fetch                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│ L5 · Storage（存储层 · 全本地）                                    │
│ ├─ SQLite（任务 / 事实 / 嵌入 / 配置 / 审计）                       │
│ ├─ Markdown（项目记忆 / 用户记忆 / 每周复盘 / vault）              │
│ ├─ Hermes task bus（JSON 文件 + lock）                            │
│ ├─ 录音 WAV（24h 自动清除）                                       │
│ └─ 日志（loguru · 7 天滚动 · 100MB 上限）                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 模块关系（依赖图）

```
qingqiu/
├── core/             ← L2（QingQiu Core · 唯一入口）
│   ├── router.py     ← 意图识别
│   ├── planner.py    ← 任务拆解
│   ├── executor.py   ← agent 调度
│   ├── confirm.py    ← 写入确认
│   └── reflect.py    ← 复盘
├── llm/              ← LLM 抽象层
│   ├── base.py       ← LLMProvider Protocol
│   ├── openai.py
│   ├── anthropic.py
│   ├── ollama.py
│   └── custom.py
├── agents/           ← L3（5 类 agent + 2 内部）
│   ├── base.py       ← Agent Protocol
│   ├── coder.py
│   ├── reviewer.py
│   ├── info.py
│   ├── life.py
│   ├── knowledge.py
│   ├── reflect.py
│   └── indexer.py
├── memory/           ← L5 + Memory 接口
│   ├── l0.py         ← 会话上下文（内存）
│   ├── l1.py         ← 项目记忆（Markdown）
│   ├── l2.py         ← 用户记忆（Markdown）
│   └── l3.py         ← 长期事实（SQLite）
├── knowledge/        ← Obsidian 集成
│   ├── vault.py
│   ├── wikilink.py
│   ├── frontmatter.py
│   ├── embed.py
│   └── privacy.py
├── voice/            ← 语音 worker（独立进程）
│   ├── stt.py        ← faster-whisper
│   └── tts.py        ← piper
├── security/         ← L4 安全相关
│   ├── whitelist.py
│   ├── blacklist.py
│   ├── private.py    ← 三道闸
│   └── keyring.py    ← API key 存储
├── ipc/              ← 进程间通信
│   ├── http.py       ← 127.0.0.1:7788 (FastAPI)
│   ├── pipe.py
│   └── hermes.py     ← 任务总线
├── inputs/           ← L1 输入层
│   ├── cli.py
│   ├── voice.py
│   ├── feishu.py
│   └── graph.py
└── cli.py
```

**依赖方向（严格单向，禁止反向）：**

```
inputs → core → {agents, llm, memory, knowledge}
                  ↓
                tools → storage
```

---

## 4. 数据流（典型场景）

### 4.1 语音 → 任务 → 写入

```
用户按 Ctrl+Shift+Q
   ↓
voice-worker 录音
   ↓
WAV 文件
   ↓
faster-whisper STT → text
   ↓
core.router.intent(text)
   ↓
core.planner.plan(intent) → [Task]
   ↓
core.executor.dispatch(task) → Agent
   ↓
Agent 调用 tool（受白名单限制）
   ↓
core.confirm.ask_write(changes)  ← 写入必问
   ↓
用户确认 → 真正执行
   ↓
output TTS
```

### 4.2 vault 检索 → 知识图谱

```
watchdog 监听 vault
   ↓
knowledge.indexer 增量索引
   ↓
wikilink / frontmatter / 标签 解析
   ↓
嵌入向量化（Ollama → sqlite-vec）
   ↓
Tauri UI 拉取 /api/graph.json
   ↓
Cytoscape.js 渲染
```

---

## 5. 接口边界（严格）

| 接口 | 谁调谁 | 形态 | 备注 |
|------|--------|------|------|
| `LLMProvider.complete()` | core → llm | async function | 所有 LLM 调用必经 |
| `Agent.run(task)` | core → agents | async function | 所有 agent 任务必经 |
| `Tool.execute(params)` | agent → tools | async function | **不允许 agent 直接调 shell** |
| `Confirm.ask(question, options)` | core → confirm | sync function | 所有写入必经 |
| `Memory.get/set(key)` | core → memory | sync function | 四层统一接口 |
| `/api/*` (FastAPI) | UI → daemon | HTTP/JSON | 127.0.0.1 only |

**强约束：**

- ❌ core 不直接调 LLM SDK，必须经 `LLMProvider`
- ❌ agent 不直接调 shell，必须经 `Tool.execute()`
- ❌ UI 不持有任何 API key（密钥全在 daemon）

---

## 6. 进程模型

| 进程 | 角色 | 启动方式 | 监控 |
|------|------|---------|------|
| `qingqiu-watchdog.exe` | 最小监控进程 | OS 启动 | 自监控 |
| `qingqiud.exe` | Python daemon（核心） | watchdog 启动 | watchdog |
| `voice-worker.exe` | 语音推理 | daemon 启动 | daemon |
| `feishu-bot.exe` | 飞书 WebSocket | daemon 启动 | daemon |
| `qingqiu.exe` | CLI 一次性进程 | 用户调 | — |
| `qingqiu-tray.exe` | Tauri 桌面 UI | 用户登录后 | 用户手动 |

---

## 7. 数据存储

| 数据 | 存储 | 路径 | 备份 |
|------|------|------|------|
| 任务 JSON | 文件 | `~/.qingqiu/tasks/<agent>/<state>/*.json` | atomic write |
| 长期事实 | SQLite | `~/.qingqiu/memory/facts.sqlite` | 每周 |
| 嵌入向量 | SQLite + vec | `~/.qingqiu/memory/embeddings.sqlite` | 每周 |
| 项目记忆 | Markdown | `~/.qingqiu/memory/projects/*.md` | git |
| 用户记忆 | Markdown | `~/.qingqiu/memory/user.md` | git |
| 每周复盘 | Markdown | `~/.qingqiu/memory/weekly/*.md` | git |
| 配置 | YAML | `~/.qingqiu/config.yaml` | git |
| 私密 patterns | YAML | `~/.qingqiu/private-patterns.yaml` | 不入仓 |
| 录音 | WAV | `~/.qingqiu/voice/recordings/*.wav` | 24h 清除 |
| 日志 | loguru | `~/.qingqiu/logs/*.log` | 7 天滚动 |

---

## 8. 安全边界

| 边界 | 实现 |
|------|------|
| **API key 不进前端** | 全在 daemon；UI 只调 `/api/*` 不带 key |
| **私密信息三层防护** | Detect 识别 → Block 阻断 → Redact 脱敏 |
| **写入必问** | Confirm 模块强制 |
| **白名单目录** | 路径校验 |
| **命令黑名单** | shell 拦截 |
| **daemon user 权限** | 不跑 system 权限 |
| **127.0.0.1 only** | HTTP server 绑定 loopback |
| **原子写** | write tmp + rename |
| **WAL** | SQLite WAL 模式 |

**密钥存放：** Windows Credential Manager（`keyring` Python 包）。

---

## 9. 性能热点

详见 [NON-FUNCTIONAL.md §3](./NON-FUNCTIONAL.md)。

| 瓶颈 | 优化 |
|------|------|
| LLM 调用时延 | 流式响应 + 5min 缓存 + smart routing |
| whisper 转写 | `small` 模型 + CPU 推理 |
| 嵌入向量化 | 本地 Ollama + 后台异步 |
| 知识图谱渲染 | > 1k 节点自动聚类折叠 |
| SQLite 写并发 | WAL + 批量 flush |

---

## 10. 开发纪律（**最重要的一节**）

### 10.1 全局上下文三件套

每次大改动（新增 M / 改动 ≥ 3 个 slice / 架构调整 / 隐私策略变化 / 技术栈调整），必须**同步更新**：

1. **[PRD.md](./PRD.md)**
2. **[ARCH.md](./ARCH.md)**
3. **[PROJECT.md](./PROJECT.md)**

### 10.2 小步迭代 + 端到端切片 MVP

每个切片独立验收、可独立交付、可独立回滚。估时 < 5 天。

### 10.3 主动拆分模块

- ❌ 禁止写一坨（Python < 300 行 / React < 200 行）
- ✅ 单一职责：一个文件只做一件事
- ✅ 强边界：通过接口调用

### 10.4 只改点名的范围

- ❌ 不要顺手重构
- ❌ 不要改 UI 风格（DESIGN.md 是宪法）
- ❌ 不要改无关逻辑
- ✅ 增量提交：一个切片一个 commit
- ✅ 测试通过 + 用户验收才能合入

### 10.5 命名规则 + 文件大小

详见 [references/naming.md](./references/naming.md)。

### 10.6 前端标准

所有前端代码必须符合 [references/](./references/) 下的标准。

### 10.7 安全底线

- ❌ **密钥不进前端**
- ✅ 所有 API key 走 daemon 后端 + keyring
- ✅ Confirm 不可绕过（P5）
- ✅ 私密信息三道闸（P8）

### 10.8 AI Agent 权限限制

- ❌ 禁止做主
- ❌ 禁止重构
- ❌ 禁止改 UI
- ❌ 禁止改无关逻辑
- ❌ 禁止批量改
- ✅ 改前必读
- ✅ 改后必测
- ✅ 大改动必更新三件套

详见 [AGENTS.md](./AGENTS.md)。

---

## 11. 架构演进历史

| 版本 | 主要变更 |
|------|---------|
| v0.1 | Hermes 叠加层思路 |
| v0.2 | 完全重写 |
| v0.2.1 | 强化私密信息保护 |
| v0.2.2 | 改名清秋 + Obsidian + 知识图谱 + 自我成长 |
| v0.3.0 | **当前**：技术栈主流化 + 文档重组 + 目录迁移 |

---

**架构改动必须更新本文件。** 改完顺手去 [PROJECT.md](./PROJECT.md) 标 done + 写决策记录。