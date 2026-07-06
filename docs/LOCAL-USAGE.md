# 清秋 qingqiu · 本地使用指南

> **目标**：不发布到 GitHub Release / PyPI，纯本地安装 + 本地使用
> **范围**：Windows 10+（其他系统需要 cross-compile · 见 v1.1 路线图）
> **状态**：v1.0 FINAL · 5 个发行包就位

---

## ⚡ 5 秒上手（最快路径）

1. 打开 `src-tauri\target\release\bundle\nsis\qingqiu_0.1.0_x64-setup.exe`
2. 双击 → 一路 Next → 桌面出现 "qingqiu" 图标
3. 双击桌面图标 → 托盘图标出现 + 主窗口弹出（webview → FastAPI 7788）

`qingqiu CLI` 也在开始菜单 / `qingqiu --help` 即可。

---

## 📦 5 种安装方式（按场景选）

### A. 普通用户（最友好）— NSIS self-extracting

```powershell
# 双击文件 / 或命令行:
.\src-tauri\target\release\bundle\nsis\qingqiu_0.1.0_x64-setup.exe
```

- 一路 Next/Install
- 装到 `C:\Program Files\qingqiu\`
- 自动创建桌面图标 + 开始菜单
- 卸载用 Windows "设置 → 应用"
- **首次运行**：系统托盘 + 主窗口

### B. Windows Installer (MSI) — 企业部署友好

```powershell
# 双击 / 或 silent install:
msiexec /i "src-tauri\target\release\bundle\msi\qingqiu_0.1.0_x64_en-US.msi" /quiet
# → 装到 C:\Program Files\qingqiu\
# 卸载: msiexec /x ...MSI...
```

### C. 开发者模式 (Symbolic link) — 推荐 for hacking

```powershell
cd "E:\MiniMax Code Work Space\qingqiu-system"
uv sync                              # 安装依赖
uv pip install -e ".[dev]"           # 装 Python package + 命令入口
qingqiu --version                     # 验证
```

**优势**：改了 `src/qingqiu/*.py` 立即生效（uvicorn/click 重新读）

### D. Wheel 安装（不可变）

```powershell
cd "E:\MiniMax Code Work Space\qingqiu-system"
uv pip install dist\qingqiu-0.3.0-py3-none-any.whl
qingqiu --version
# 想升级：重新 uv build + uv pip install --force-reinstall ...
```

### E. 免安装直接跑

```powershell
.\src-tauri\target\release\qingqiu-desktop.exe
# 或从 explorer 双击
```

无需安装，但依赖 WebView2 runtime（Win10 1803+ 自带）。

---

## 🚀 第一次跑

### 桌面应用（Tauri）

```powershell
# 启动桌面（webview 加载 FastAPI）
.\src-tauri\target\release\qingqiu-desktop.exe
# → 托盘图标出现 + 主窗口打开
```

**需要 FastAPI 在跑** — 桌面应用启动 webview → `http://127.0.0.1:7788`，所以要：

```powershell
# 另一个 terminal 启动 FastAPI daemon:
cd "E:\MiniMax Code Work Space\qingqiu-system"
uv run qingqiu web start
# → 浏览 http://127.0.0.1:7788 验证
```

托盘行为：
- 左键单击 → 显隐主窗口
- 右键 → "显示主窗口" / "退出"

### CLI 命令（直接用）

```powershell
qingqiu status                    # 健康检查
qingqiu memory list               # 列记忆
qingqiu memory get user_name      # 查 user_name
qingqiu memory set user_name "你的名字"
qingqiu task add "做某事"
qingqiu task list
qingqiu --help                    # 所有子命令

qingqiu-voice say "你好清秋"      # 系统 TTS 真发声（Win10+ / macOS / Linux）
qingqiu-voice listen              # 录音 + 识别 + 执行
```

### 飞书 IM（如需）

```powershell
$env:FEISHU_APP_ID = "cli_xxx"
$env:FEISHU_APP_SECRET = "xxx"
qingqiu im start
# → WebSocket 监听飞书消息
```

无凭据时默认走 mock transport，便于测试。

### 知识图谱（OBS vault 检索）

```powershell
qingqiu web start                 # 起 FastAPI
# 浏览器打开 http://127.0.0.1:7788
# 看到 M9 Cytoscape 图，点节点 → 用 OS default app 打开笔记
```

---

## 🔧 验证 v1.0 真跑（5 分钟）

```powershell
cd "E:\MiniMax Code Work Space\qingqiu-system"

# 1. 测试
uv run pytest tests\ -q
# 期望: 817 passed, 1 warning

# 2. TTS 真跑
uv run python scripts\verify_s3_3.py
# 期望: 5 场景 PASS · WAV 文件 150KB 输出

# 3. Planner 真跑
uv run python scripts\verify_s2_3.py
# 期望: 4 场景 PASS

# 4. 飞书 Confirm 真跑
uv run python scripts\verify_s4_4.py
# 期望: 5 场景 PASS
```

每个 verify 脚本对应 `docs\verification\S*.md`，里面是当日真跑输出。

---

## 🗑 卸载

### A. NSIS / MSI 安装的
去 Windows "设置 → 应用 → 搜索 qingqiu → 卸载"

### B. Python wheel / dev mode 装的
```powershell
uv pip uninstall qingqiu
```

### C. Tauri build artifacts
```powershell
# 物理删目录
Remove-Item -Recurse "E:\MiniMax Code Work Space\qingqiu-system\src-tauri\target\release" -ErrorAction Continue
# (会重新 build 时再生成)
```

---

## 📁 文件速查

| 需要什么 | 在哪里 |
|---------|--------|
| 安装器 (NSIS) | `src-tauri\target\release\bundle\nsis\qingqiu_0.1.0_x64-setup.exe` |
| 安装器 (MSI) | `src-tauri\target\release\bundle\msi\qingqiu_0.1.0_x64_en-US.msi` |
| 独立 exe | `src-tauri\target\release\qingqiu-desktop.exe` |
| Python wheel | `dist\qingqiu-0.3.0-py3-none-any.whl` |
| Python source | `dist\qingqiu-0.3.0.tar.gz` |
| 项目仓库 | `E:\MiniMax Code Work Space\qingqiu-system\` |
| 文档 | `docs\` 目录（ARCH / PRD / PROJECT / VERIFICATION 等） |
| 真跑证据 | `docs\verification\` 22 份 `.log.md` + 13 份 `ci-loop-*.log.md` |

---

## ⚙️ 系统要求

| 项 | 必需 / 可选 | 说明 |
|------|------|------|
| Windows 10 1803+ | 必需 | WebView2 runtime（系统自带） |
| Python 3.11+ | 必需（开发模式） | uv 装 |
| uv (Astral) | 必需（开发模式） | https://docs.astral.sh/uv/ |
| Rust toolchain | 可选（仅当从源码 build Tauri） | `rustup-init.exe` |
| tauri-cli | 可选（仅当重 build） | `cargo install tauri-cli` |
| 飞书 App | 可选（M4 飞书 IM） | 申请见飞书开放平台 |
| Ollama/OpenAI Key | 可选（LLM fallback） | env: `OPENAI_API_KEY` / `OLLAMA_HOST` |

---

## 🪞 配置

所有个性化都通过 `personality.yaml`（人格）+ memory（记忆）。

```powershell
# 项目级 / 全局 / 项目级 - 三层
~/.qingqiu/personality.yaml         # 全局
$E:\MiniMax Code Work Space\qingqiu-system\personality.yaml   # 项目级

# 热重载：watchdog 监文件改动，1s 内自动应用
```

---

## ⚠️ M2.6 + M3 + M4 没接入主 CLI (caveat)

`qingqiu` CLI 实装的子命令只有：`ask / chat / task / memory / status / confirm / config / llm`。
**没有** `web / im / voice / say` 子命令 — 是 by design（M2.6 主脑没接入 CLI 面）。

启动这些模块用独立入口：

```powershell
# M9 知识图谱 web UI
cd "E:\MiniMax Code Work Space\qingqiu-system"
uvicorn qingqiu.ui.server:app --host 0.0.0.0 --port 7788
# → 浏览器开 http://127.0.0.1:7788

# M3 语音 pipeline（录音 + STT + 执行）
uv run python -m qingqiu.voice.pipeline

# M4 飞书 IM（需 FEISHU_APP_ID/SECRET 或自动 mock）
$env:FEISHU_APP_ID = "cli_xxx"
$env:FEISHU_APP_SECRET = "xxx"
uv run python -m qingqiu.im.feishu.client

# TTS 直接发（用系统 SAPI — Windows / macOS say / Linux espeak）
uv run python -c "from qingqiu.voice.tts import speak; speak('你好清秋')"
```

Tauri 桌面启动时 webview 自动连 `127.0.0.1:7788`，所以**先用 uvicorn 起 daemon 再开桌面**。

---

## 📞 故障排查

| 问题 | 排查 |
|------|------|
| 双击 exe 闪退 | 看 Windows 事件查看器；CMD 里跑一次看 stdout |
| 托盘不出现 | Win11 可能默认折叠，看 hidden icons (^) |
| Webview 空白 | FastAPI 没启动 → 先 `qingqiu web start` |
| `qingqiu: command not found` | wheel 没装好 → `uv pip install --force-reinstall dist/qingqiu-0.3.0-py3-none-any.whl` |
| pytest 失败 | `uv sync` 重装依赖；`uv cache clean` 清缓存 |
| GitHub push 失败 | 检查 token 网络（push 不需要本地登录，提 PR 时才要） |

---

## 🎉 v1.0 已收官 · 不再发布

- 5 个发行包都在本地，**随时装**
- **817 测试稳过**，CI Loop 自动跑
- **48 切片全完**
- M7 之后想加什么 feature 随时告诉我