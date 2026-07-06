# qingqiu v1.0.0 · Release Notes

> **发布日期**：2026-07-06
> **代号**："落叶归根"
> **状态**：Stable
> **HEAD**：`03707e5` on main
> **测试**：817/817 pytest PASS

---

## 🎉 qingqiu v1.0.0 · 中文 AI 个人助理

qingqiu（清秋）是个**私人、开源、可落地**的中文 AI 助理。让它自己：

- 🧠 记住你说的每件小事
- ✏️ 帮你写、改、整理（带 Confirm 安全网）
- 🌐 同步飞书消息（被动响应 + 主动推送）
- 🎙 听懂你的语音指令
- 📚 把你的笔记变成知识图谱
- 🪞 每天自我反思，每周汇报成长

---

## 📦 安装

### 方式 1：从源码（开发者推荐）

```bash
git clone https://github.com/luo683/qingqiu-system.git
cd qingqiu-system
uv sync
uv run qingqiu --help
```

### 方式 2：pip 安装（v1.0 不发布 PyPI · 可手动 build）

```bash
# 在 qingqiu-system/ 目录
uv pip install -e .
qingqiu --version
```

### 系统要求

| 依赖 | 必需 / 可选 | 备注 |
|------|--------------|------|
| Python 3.11+ | 必需 | 推荐 3.12 |
| Node.js 18+ | 可选 | M9 web UI 打包时需要 |
| 飞书 App ID/Secret | 可选 | M4 飞书 IM 集成需要 |
| OpenAI / Anthropic Key | 可选 | LLM fallback 时需要 |
| Tauri Desktop | 可选 | 系统托盘（v1.1 启用） |

---

## ✨ 功能清单（48 切片）

### M0 · 立项
- 11 份核心文档（PRD / ARCH / TECH-STACK / DESIGN / IMPLEMENTATION-PLAN 等）

### M1 · 基础设施（5/5）
- **S1.1** 项目骨架 · pyproject + ruff + 自检
- **S1.2** LLM 抽象层 · 4 provider + 路由
- **S1.3** 配置系统 · YAML + env 覆盖 + 1s 热重载
- **S1.4** 日志系统 · loguru + 滚动 + 错误分流
- **S1.5** Memory 四层骨架 · L0/L1/L2/L3 + facade

### M2 · Router / CLI / Executor（5/5 + 1 升级）
- **S2.1** CLI 子命令骨架（memory/task/status/config/llm）
- **S2.2** Router 18 Intent + Rule + LLM fallback
- **S2.3** Planner 完整 DAG（拓扑 + 并行 + mermaid）★ 升级
- **S2.4** Executor 意图路由（Router → CLI handler）
- **S2.5** CLI confirm ask/test 子命令
- **S2.6** v1.0 MVP 端到端 demo（15 场景）

### M3 · 语音（完整）
- **S3.1** 录音 + Windows SAPI / macOS say TTS
- **S3.2** STT 抽象层（faster-whisper）
- **S3.3** PiperTTS 集成（接口预留，可挂 60MB 模型）
- Pipeline · CLI · voice 子命令

### M4 · 飞书 IM（完整）
- **S4.1** 飞书 WebSocket 客户端（lark-oapi + mock）
- **S4.2** 消息 → Router 适配层
- **S4.3** 文本回发 + chunk
- **S4.4** 卡片消息 + 按钮 Confirm ★ NEW

### M5 · 安全（5/5）
- **S5.1** Confirm 写入前通用框架
- **S5.2** 目录白名单（4 目录）
- **S5.3** 危险操作黑名单（regex）
- **S5.4** 私密识别（filename + content + 身份证）
- **S5.5** 私密处理 Block + Redact（脱敏映射）

### M6 · 人格（2/3）
- **S6.1** 人格 prompt 模板
- **S6.5** personality.yaml + 热更新（watchdog）

### M7 · 持续打磨
- Doc reviews · 内聚测试 · stubs cleanup

### M8 · Obsidian（接入）
- vault · index · parser
- Embedding · Knowledge search
- 私密 vault 隔离

### M9 · 知识图谱 + UI
- FastAPI · Cytoscape.js
- Tag filter · Click-to-open ★ S9.5 升级
- Note path 字段 + OS default handler

### M10 · 自我成长
- 每日反思 / 每周汇报
- 偏好学习 / 冲突检测
- Vault feed · 成长配置

---

## 🧪 测试覆盖

| 模块 | 测试数 | 状态 |
|------|---------|------|
| cli | 57 | ✅ |
| config | 31 | ✅ |
| memory | 32 | ✅ |
| observability | 6 | ✅ |
| security (S5.1-5.6) | 155 | ✅ |
| voice (M3) | 56 | ✅ |
| im/feishu (M4) | 81 | ✅ |
| obsidian (M8) | 31 | ✅ |
| ui (M9) | 40 | ✅ |
| growth (M10) | 90 | ✅ |
| router (S2.2/2.4) | 49 | ✅ |
| planner (S2.3) | 16 | ✅ |
| personality (S6.x) | 10 | ✅ |
| search/aggregate | 8 | ✅ |
| tts (S3.3/3.5) | 11 | ✅ |
| s4_4 (S4.4) | 14 | ✅ |
| **总计** | **817** | **全部 PASS** |

---

## 🚀 快速开始

```bash
# 1. CLI 启动
uv run qingqiu --help
uv run qingqiu memory list
uv run qingqiu memory get user_name
uv run qingqiu memory set user_name "小米"
uv run qingqiu task add "写 PRD"
uv run qingqiu task list
uv run qingqiu status

# 2. 飞书 IM（需 FEISHU_APP_ID/SECRET）
FEISHU_APP_ID=xxx FEISHU_APP_SECRET=yyy uv run qingqiu im start

# 3. 语音（Windows 自带 SAPI / macOS say / Linux espeak）
uv run qingqiu voice listen
uv run qingqiu voice say "你好"

# 4. 知识图谱 web UI
uv run qingqiu web start
# 浏览器开 http://127.0.0.1:7788
```

---

## ⚠️ 已知限制

- **M9 web UI**：不是桌面应用（需要浏览器打开）
- **S9.1 Tauri 桌面**：骨架就位，未编译（v1.1 启用）
- **语音 STT**：faster-whisper 首次跑会下载模型（~150MB）
- **飞书 IM**：需要 app 申请 + 配置 env

---

## 📈 路线图

### v1.1（短期 · 1 周）
- [ ] Tauri 桌面 + 系统托盘（S9.1 编译）
- [ ] PyPI 发布（`uv build` + Twine）
- [ ] 中文文档站（Sphinx/MkDocs）

### v1.2（中期 · 1 月）
- [ ] 多轮对话持久化（chat history DB）
- [ ] 多用户支持（per-user memory）
- [ ] Web UI PWA（离线可用）

### v2.0（远期）
- [ ] Plugin 系统（用户扩展）
- [ ] 移动端（React Native / Tauri Mobile）

---

## 🙏 致谢

- **lark-oapi** 飞书官方 SDK
- **faster-whisper** OpenAI Whisper C++ 推理
- **FastAPI** 现代 Python web 框架
- **Cytoscape.js** 图可视化
- **loguru** 优雅的日志库

---

## 📜 许可证

MIT License · See `LICENSE`

---

## 🔗 链接

- 仓库：`https://github.com/luo683/qingqiu-system`
- Issues：`https://github.com/luo683/qingqiu-system/issues`
- 文档：`docs/` 目录内
