# TECH-STACK · 清秋（QingQiu）技术栈选型

> **状态：** v0.3.0 · 配套 PRD v0.2.2 / ARCH v0.3.0
> **作者：** Mavis
> **本版性质：** v0.3.0 调整：**技术栈主流化**（决策 D-003）。
> **变更点：** pywhispercpp → **faster-whisper** / aiohttp → **FastAPI** / npm → **pnpm**。

---

## 1. 一句话技术栈

**Python 3.11 核心 + Tauri/Rust 桌面壳 + React/TS 前端 + FastAPI 本地 HTTP + SQLite 数据层 + 本地 Ollama 嵌入 + faster-whisper + piper 离线语音栈 + 可热插拔 LLM provider**。

---

## 2. 选型哲学（五条原则）

| # | 原则 | 含义 |
|---|------|------|
| T1 | **本地优先** | 默认跑本地的优先 |
| T2 | **依赖最少** | 每个依赖必要且不可替代 |
| T3 | **可热插拔** | 凡是可能换的都做抽象层 |
| T4 | **单机能跑** | 不依赖 Docker / K8s / DB server |
| **T5** | **🆕 主流验证** | 选主流 + 大量生产验证的方案 |

---

## 3. 语言与运行时

| 用途 | 选型 | 理由 |
|------|------|------|
| **核心语言** | **Python 3.11+** | LLM SDK / faster-whisper / piper 都有 Python wrapper |
| **桌面壳** | **Rust（Tauri 后端）** | 体积小、启动快、安全 |
| **前端** | **TypeScript + React 18** | 生态成熟 |
| **前端构建** | **Vite 5** | 快、TS 一等公民 |
| **包管理（前端）** | **🆕 pnpm** | 节省磁盘 |

---

## 4. 核心依赖（按层）

### 4.1 LLM 抽象层

| 依赖 | 用途 |
|------|------|
| `openai` | OpenAI provider |
| `anthropic` | Anthropic provider |
| `ollama` | 本地 Ollama |
| `httpx` | 自定义 OpenAI 兼容 API |
| `tenacity` | 重试 / 降级 |
| `pydantic` | LLM response 校验 |

**不引入：** `langchain` / `llama-index` / `autogen`。

### 4.2 语音栈

| 依赖 | 用途 | **🆕 主流验证** |
|------|------|--------------|
| **🆕 faster-whisper** | STT（语音 → 文字） | 基于 CTranslate2，比 openai-whisper 快 4 倍，比 pywhispercpp 生态成熟 |
| `piper-tts` | TTS（文字 → 语音） | 离线 TTS 主流方案 |
| `sounddevice` | 麦克风录音 | 跨平台 |
| `keyboard` | 全局热键监听 | 跨平台 |

**音频模型：**
- STT：`ggml-small.bin`（~460MB）
- TTS：`zh_CN-huayan-medium.onnx`（~60MB）

### 4.3 Obsidian / 知识库

| 依赖 | 用途 |
|------|------|
| `watchdog` | vault 目录监听 |
| `python-frontmatter` | YAML frontmatter 解析 |
| `markdown-it-py` | Markdown 解析 |
| `sqlite-vec` | 嵌入向量存储 |
| `nomic-embed-text` | 嵌入模型 |

### 4.4 数据 / 存储

| 依赖 | 用途 |
|------|------|
| `sqlite3`（stdlib） | 主数据存储 |
| `PyYAML` | 配置文件 |
| `python-dateutil` | 时间处理 |

### 4.5 任务 / 通信

| 依赖 | 用途 | **🆕 主流验证** |
|------|------|--------------|
| `asyncio`（stdlib） | 异步任务调度 |
| `aiofiles` | 异步文件 I/O |
| **🆕 FastAPI** | 本地 HTTP server（127.0.0.1:7788） | 取代 aiohttp；自动 OpenAPI 文档 |
| `pydantic` | IPC 消息 schema 校验 |

**不引入：** Redis / RabbitMQ / Kafka。

### 4.6 安全 / 权限

| 依赖 | 用途 |
|------|------|
| `keyring` | 系统 keyring |
| `re`（stdlib） | 私密信息正则识别 |
| `pathlib`（stdlib） | 路径白名单校验 |

### 4.7 桌面 UI（Tauri）

| 依赖 | 用途 |
|------|------|
| `tauri` | 桌面壳 |
| `cytoscape.js` | 知识图谱渲染 |
| `tailwindcss` | 样式 |
| `zustand` | 状态管理 |

### 4.8 工具链

| 依赖 | 用途 |
|------|------|
| `uv` | 依赖管理 |
| `ruff` | Linter + Formatter |
| `mypy` | 类型检查 |
| `pytest` | 测试 |

---

## 5. 进程架构

```
qingqiu/
├── qingqiu-watchdog.exe   # 监控进程
├── qingqiud.exe            # Python daemon（FastAPI + Core）
├── voice-worker.exe        # Python + faster-whisper + piper
├── feishu-bot.exe          # Python + lark WebSocket
├── qingqiu.exe             # Python CLI
├── qingqiu-tray.exe        # Tauri 桌面
└── 127.0.0.1:7788          # FastAPI（daemon 内）
```

---

## 6. 数据存储

| 数据 | 存储 |
|------|------|
| 任务 JSON | 文件 + lock |
| 长期事实 | SQLite |
| 嵌入向量 | SQLite + vec |
| 项目/用户/周报记忆 | Markdown |
| 配置 | YAML |
| 私密 patterns | YAML（不入仓） |
| 录音 | WAV（24h 清除） |
| 日志 | loguru（7 天滚动） |

---

## 7. IPC / 通信

| 场景 | 机制 |
|------|------|
| daemon 内部 | `asyncio.Queue` + `pydantic` |
| daemon ↔ voice-worker | stdio pipe |
| daemon ↔ feishu-bot | `127.0.0.1` HTTP |
| daemon ↔ Tauri UI | **`127.0.0.1:7788` HTTP/JSON（FastAPI）** |
| Hermes task bus | 文件系统 + `.lock` |

---

## 8. 桌面 UI

**选 Tauri**（默认）；Electron 作为备选。详见 [DESIGN.md](./DESIGN.md)。

---

## 9. 测试

- `pytest` + `pytest-asyncio`
- `pytest-benchmark` 性能 baseline
- 不上自动化 e2e

---

## 10. 打包

- Python daemon：`pyinstaller --onefile`
- Tauri UI：`tauri build`

---

## 11. v0.3.0 主要变更（vs v0.2.2）

| 维度 | v0.2.2 | v0.3.0 | 理由 |
|------|--------|--------|------|
| STT | pywhispercpp | **faster-whisper** | 主流验证（T5）；生态成熟 |
| HTTP server | aiohttp | **FastAPI** | 主流验证（T5）；自动 OpenAPI |
| 包管理（前端） | npm | **pnpm** | 主流验证（T5） |
| **不变** | Python 3.11 / Tauri / React / SQLite / sqlite-vec / Ollama / piper / uv / ruff | | 已主流 |

---

## 12. 关键判断的反对意见（已预演）

| 决策 | 选 | 不选 | 没选的理由 |
|------|----|----|----------|
| STT | faster-whisper | pywhispercpp / openai-whisper | faster-whisper 是当前 Python 主流推荐 |
| HTTP server | FastAPI | aiohttp / Starlette | FastAPI 70k+ stars |
| 包管理 | pnpm | npm / yarn | 节省磁盘 |
| 核心语言 | Python | Go / Rust | LLM 生态 Python 优先 |
| UI 框架 | Tauri | Electron | 体积 10MB vs 150MB |
| 向量库 | sqlite-vec | chroma / faiss | 单文件、零运维 |
| LLM 框架 | 自写 Planner | LangChain | 违反 P6 可解释 |
| 状态管理 | Zustand | Redux | 单人项目 Redux 太重 |
| 依赖管理 | uv | Poetry | 快 10-100x |

---

## 13. 风险与回退方案

| 风险 | 回退方案 |
|------|---------|
| faster-whisper 准确率不够 | 切 `large-v3` |
| FastAPI 启动慢 | `uvicorn --workers 1 --loop uvloop` |
| pnpm 学习曲线 | 退回 npm |
| sqlite-vec 不够成熟 | 切 faiss-cpu |
| Ollama 嵌入慢 | 切云端嵌入（走 LLM 抽象层） |
| Python 性能瓶颈 | 关键路径 PyO3 切 Rust |

---

**技术栈调整必须更新本文件 + [ARCH.md §11](./ARCH.md) + [PROJECT.md §6](./PROJECT.md)。**