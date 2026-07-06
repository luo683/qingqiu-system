# PROJECT · 清秋项目状态

> **状态：** v0.3.0 · 立项完成 + **M1 ✅ 5/5** + **S2.1 / S5.1 / S5.2 / S5.3 / S2.2 / S2.5 / S6.5 / S5.4 真跑落地**
> **最后更新：** 2026-07-06 12:14
> **作者：** Mavis
> **本文件性质：** 项目"快照"。**状态变化、决策、下一步**都写在这里。每次 session 开始 / 结束时更新。

---

## 1. 一句话状态

**清秋 v0.3.0 + 13 切片完成（M1 + S2.1 + S2.2 + S2.5 + S5.1+S5.2+S5.3+S5.4 + S6.1 + S6.5）**。35 切片剩余 / 395/395 测试 PASS / CI Loop 每 30min 自动跑通 / 远端 main `5999fd6`。

---

## 2. 项目快照

| 维度 | 状态 |
|------|------|
| **PRD** | v0.2.2 已冻结 |
| **架构** | v0.3.0 · 五层架构 + 48 切片路径清晰 |
| **代码** | ~5500 行（src/qingqiu/ 8 模块 + router/ + personality/ + cli 9 文件 + security 4 文件） |
| **测试** | **395 个 pytest 全通过**（比 day2 +138：S2.2=28, S2.5=11, S6.5=14, S5.4=32） |
| **文档** | 11 份核心 + 5 份 references/ + **11 份真跑证据** + 3 份 handoff（day1+day2+day3） |
| **里程碑** | M0 ✅ / **M1 ✅ 5/5** / **M2 3/6**（S2.1+S2.2+S2.5）/ **M5 4/5**（S5.1+S5.2+S5.3+S5.4）/ **M6 2/3**（S6.1+S6.5）/ M3-M4-M7-M10 pending |
| **当前切片** | ✅ **Day 3 全部完成**（S2.2 + S2.5 + S6.5 + S5.4 merged to main）· CI Loop 已设 |
| **仓库** | ✅ GitHub：`https://github.com/luo683/qingqiu-system` · main `5999fd6` |
| **CI Loop** | ✅ `ci-loop` cron · 每 30min 自动 `uv run pytest tests/` · TTL 14d 到 2026-07-20 |

---

## 3. 已完成 / 进行中 / 待办

### 3.1 已完成 ✅

| 阶段 | 内容 |
|------|------|
| **立项（M0）** | 11 份核心文档 + 5 份 references/ 标准 |
| 文档体系 | README / PRD / PRD-archived / ARCH / PROJECT / TECH-STACK / DESIGN / IMPLEMENTATION-PLAN / NON-FUNCTIONAL / AGENTS / CHANGELOG |
| references/ | README / naming / components / styling / testing |
| 目录迁移 | jarvis-system/ → qingqiu-system/（旧目录已移回收站） |
| 改名 | 贾维斯 → 清秋（产品名全栈替换） |
| 接入规划 | Hermes 吸收重塑 / Obsidian 接入 / 知识图谱 / 自我成长 |
| 切片规划 | 48 个 slice 全部定义 |
| **GitHub 仓库** | URL 确认 + 多 commit 已就位待 push |
| **S1.1** | 项目骨架（pyproject + CLI + 5 测试通过） |
| **S1.2** | LLM 抽象层（4 provider + router + 45 测试通过 + CustomProvider 真打 MiniMax API PASS） |
| **S1.3** | 配置系统（YAML + env 覆盖 + 1s 热重载 + 31 测试 + 4 项真跑全 PASS） |
| **S1.4** | 日志系统（loguru + 滚动 + 错误分流 + CLI 集成 + 6 测试 + 5 命令真跑 PASS） |
| **S1.5** | Memory 四层骨架（L0 内存 / L1 项目 MD / L2 用户 MD / L3 SQLite + facade + 32 测试 + 4 步真跑 PASS） |
| **M1 收官** | 5/5 切片完成 · 119 测试通过 · 5 份真跑证据归档 |
| **S2.1** | CLI 子命令骨架（memory/task/status/config/llm + 9 文件 + 57 测试 + 12 步真跑 PASS） |
| **S5.1** | Confirm 写入前通用框架（Prompter + CLIPrompter + Confirm + ask + 22 测试 + 10 步真跑 PASS） |
| **S5.2** | 目录白名单（4 目录 + is_whitelisted/check_path/resolve + 26 测试 + 6 步真跑 PASS） |
| **S5.3** | 危险操作黑名单（SHELL_PATTERNS regex + OperationType enum + 38 测试 + 8 步真跑 PASS） |
| **S6.1** | 人格 prompt 模板（基础结构 + 加载接口） |
| **S2.2** | Router 意图识别（18 Intent + RuleBased + LLM fallback + 中文友好 + 28 测试 + 10 指令 100%） |
| **S2.5** | CLI confirm ask/test 子命令（接 S5.1 Confirm 框架 + 11 测试 + 268/268 真跑 PASS） |
| **S6.5** | 人格 personality.yaml + 热更新（watchdog + 10 测试 + 271/271 真跑 PASS） |
| **S5.4** | 私密识别 Detect（filename + content + directory + GB 11643-1999 身份证校验位 + 32 测试 + 342/342 真跑 PASS） |
| **Day 3 收官** | 4 slices merged（S2.2/S2.5/S6.5/S5.4）+ main 395/395 PASS + CI Loop cron 设置 ✅ |

### 3.2 进行中 🔄

| 任务 | 状态 |
|------|------|
| **CI Loop** | ✅ `ci-loop` cron 每 30min 自动 `uv run pytest tests/`，TTL 14d 到 2026-07-20 |
| **5 个旧 slice 分支清理** | ✅ 全部删除（worktree + 本地 + origin） |

### 3.3 待办 📋

| 优先级 | 切片 | 内容 | 估时 |
|--------|------|------|------|
| **P0** | **S1.1** | 项目骨架 + pyproject.toml + CLI 骨架 | 1 天 |
| P0 | S1.2 | LLM 抽象层（4 provider） | 3 天 |
| ... | ... | （共 48 个切片） | — |

---

## 4. 已知问题

### 4.1 待澄清问题（PRD §17.2 完整列表）

| # | 问题 | 默认假设 | 阻塞？ |
|---|------|---------|--------|
| 1 | Obsidian vault 路径 | `C:\Users\ROG\Documents\Obsidian Vault` | M8 之前 |
| 2 | vault 私密笔记标记方式 | frontmatter `private: true` + `private/` 目录 | M8 之前 |
| 3 | CLI 命名（qingqiu vs qq） | `qingqiu` | S1.1 之前 |
| 4 | 全局热键 `Ctrl+Shift+Q` | 接受 | S3.1 之前 |
| 5 | 默认 LLM | `anthropic` | S1.2 之前 |
| 6 | Hermes 物理仓库迁不迁 | 保留 `E:\Hermes Agent WorkSpace` | M1 之前 |
| 7 | 知识图谱 UI 形态 | 桌面端 + 网页 | M9 之前 |
| 8 | 每周复盘时间 | 周日 23:00 | M10 之前 |
| 9 | 自我成长开关 | 默认开 | M10 之前 |

### 4.2 风险与缓解

| 风险 | 严重度 | 缓解 |
|------|-------|------|
| 单人开发周期拖长 | 中 | 切片粒度细；每个 M 独立验收 |
| whisper 中文识别率 | 中 | 默认 small 模型；后期可切 large |
| Obsidian vault 解析边界 | 中 | 解析模块独立，错误隔离 |
| 自我成长误学 | 低 | 所有写入 L2/L3 前 Confirm |
| Hermes 现有任务兼容 | 中 | 协议保留；迁移前全量备份 |
| GitHub 网络不稳（git ls-remote 超时） | 低 | 推送步骤给用户自己跑 |

### 4.3 技术债

> v0.3.0 阶段无技术债（没代码）。

---

## 5. 下一步（**最重要的章节**）

### 5.1 立即（**Day 3 之后 · 下一刀**）

**Day 3 已完成**：S2.2 + S2.5 + S6.5 + S5.4 全部 merged to main（`5999fd6`）+ CI Loop 启用。

**下一步（M2 剩余 + M5 收尾）**：

- [ ] **S5.5** · 敏感字段加密（KDF + AES-GCM + 32 测试 + 真跑 PASS）· M5 最后一块
- [ ] **S2.3** · Planner 任务拆解（DAG + 依赖图 + 30 测试）· 接 S2.2 Intent
- [ ] **S2.4** · Executor 任务执行（按 Intent 路由到 coder/reviewer/info/life agent）
- [ ] **S2.6** · Long-term Scheduler（cron-like 调度器）
- [ ] CI Loop 自动跑出结果后，排查任何偶发失败
- [ ] 决定 Day 4 是否继续开切片（看 user 优先级）

### 5.2 短期（M1 范围 · 1-2 周）

完成 S1.1 - S1.5（5 个切片）。

### 5.3 中期（M2-M6 · 2-3 个月）

CLI + Router + 语音 + IM + Confirm + 白名单 + 记忆 + 人格 = **v1.0 核心可用**。

### 5.4 长期（M7-M10 · 不定）

Obsidian 接入 + 知识图谱 UI + 自我成长 + 持续打磨。

---

## 6. 决策记录（ADR 风格）

| ID | 日期 | 决策 | 影响 |
|----|------|------|------|
| D-001 | 2026-07-05 | 改名：贾维斯 → 清秋 | CLI / 进程 / 路径 / 热键 / 唤醒词 / prompt 全栈替换 |
| D-002 | 2026-07-05 | 目录迁移：jarvis-system → qingqiu-system | 与产品名一致；旧目录待删 |
| D-003 | 2026-07-05 | 技术栈主流化：faster-whisper / FastAPI / pnpm | TECH-STACK.md v0.3.0 |
| D-004 | 2026-07-05 | 三件套同步更新规则 | PRD / ARCH / PROJECT 每次大改动必须同步 |
| D-005 | 2026-07-05 | references/ 前端标准 | 所有前端代码必须符合 |
| D-006 | 2026-07-05 | AI Agent 严格遵守权限限制 | 禁止重构 / 改 UI / 改无关逻辑 / 做主 |
| D-007 | 2026-07-05 | 密钥不进前端 | API key 全在 daemon + keyring |
| D-008 | 2026-07-05 | **Git 仓库对接**：luo683/qingqiu-system | 已确认 URL；待首次 push |
| D-009 | 2026-07-05 | **S1.1 完成**：项目骨架就位 | pyproject.toml + src/ + CLI + 5 测试通过；分支 master → main |
| D-010 | 2026-07-05 | **S1.2 真跑落地完成**：LLM 抽象层就位 | 4 provider + router + 工厂；50/50 mock 测试通过 + **CustomProvider 真打 MiniMax API PASS** |
| D-011 | 2026-07-05 | **验收纪律立规则**：每个 slice 必须真实端到端跑通，不只 mock | 创建 VERIFICATION.md 文档；S1.2 是首个未满足此规则的切片（待补真跑） |
| D-012 | 2026-07-05 | **S1.3 真跑落地完成**：配置系统就位 | YAML 加载 + env 覆盖 + 1s 热重载 + 损坏兜底；81/81 mock 测试 + 4 项真跑全 PASS |
| D-013 | 2026-07-05 | **S1.4 真跑落地完成**：日志系统就位 | loguru 双 handler（控制台 + 文件）+ 100MB 滚动 + 7 天保留 + 错误日志独立分流；87/87 mock 测试 + 5 命令真跑全 PASS |
| D-014 | 2026-07-05 | **S1.5 真跑落地完成**：Memory 四层骨架就位 | L0 内存（RLock）/ L1 项目 MD（atomic write）/ L2 用户 MD（继承 L1）/ L3 SQLite facts 表 + Memory facade 跨层；119/119 mock 测试 + 4 步真跑全 PASS · **M1 收官** |
| D-015 | 2026-07-05 | **S2.1 设计 review 通过**：5 review 点全 OK | 子命令树范围 OK / `--json` 一刀切 OK / 退出码 0/1/2 OK / 不加 tui OK / status 3 块输出 OK |
| D-016 | 2026-07-05 | **S2.1 核心实施 40%**：CLI 子命令骨架 | cli/ 包拆分（4 个新文件）+ errors 体系 + output human/json + memory 子命令接 S1.5 + 25 测试 + 10 步真跑 PASS · 139/139 全量不回归 · 分支 `slice/S2.1` 待 push |
| D-017 | 2026-07-05 | **Git 首次推送成功**（PAT 缓存自动认证） | `git remote add` + `git push -u` 一次性完成 · 16 commits 到 `luo683/qingqiu-system` main |
| D-018 | 2026-07-05 | **S2.1 完整实施 100%**：CLI 子命令骨架全部就位 | cli/ 包 8 文件 + memory/task/status 三个完整子命令 + config/llm 拆分 + 57 测试 + 12 步真跑 PASS · 171/171 全量不回归 · 分支 `slice/S2.1` |
| D-019 | 2026-07-06 | **agent 假报告教训**：agent "完成" ≠ 真完成 | 必须 `git log` + `git status` + pytest 三件套验证；S5.2 agent 曾在 default workspace 伪造 commit，被发现后纠正 |
| D-020 | 2026-07-06 | **mavis spawn 长中文截断 workaround** | spawn content 截断 >1KB 中文 → 短 ASCII 指令 + workspace JSON 文件 + agent 自己 Read |
| D-021 | 2026-07-06 | **Day 2 合并 3 slices + S5.1 框架** | S2.1/S5.2/S5.3 → main；fix `BLOCKED_OPERATIONS` import 名（不是 `BLACKLIST_`）；S5.1 Confirm 22 测试 + 10 步真跑；257/257 PASS；main `df8ea3a` |
| D-022 | 2026-07-06 | **S5.1 Confirm 通用框架合并到 main** | Prompter/CLIPrompter/Confirm 集成点：S2.4/S5.4/S3.5/S4.4 |
| D-023 | 2026-07-06 | **S5.1 实施完成 + 真跑验证** | 22 测试 + 10 步真跑（CLI ask/test 端到端） |
| D-024 | 2026-07-06 | **Day 2 收尾** + day2 handoff 写完 | docs/handoffs/2026-07-06-day2.md |
| D-025 | 2026-07-06 | **S2.2 Router 实施完成**：18 Intent + Rule + LLM fallback | 28 测试 + 10 指令真跑 100%；中文友好用 `(?<![a-zA-Z0-9_])` lookbehind/ahead（不是 `\b`） |
| D-026 | 2026-07-06 | **CI Loop cron 设置**：用户原话"设置loop反复检查并跑通项目" | `mavis cron self ci-loop --every 30m --ttl 14d`；自动到期 2026-07-20；失败时自动修或 spawn coder |
| D-027 | 2026-07-06 | **Day 3 合并策略**：S2.2 → S2.5 → S6.5 → S5.4 顺序 | 独立模块无冲突；最终 main `5999fd6`；395/395 PASS |

---

## 7. 仓库

- **本地路径：** `E:\MiniMax Code WorkSpace\qingqiu-system\`
- **远程：** **`https://github.com/luo683/qingqiu-system`** ✅ 已确认
- **Git 用户：** `luo683`
- **分支策略：** `main`（稳定）+ `slice/S<n>.<m>`（每个切片一个分支）
- **Commit 风格：** Conventional Commits（`feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`）
- **.gitignore：** 见 `.gitignore`（不提交 `~/.qingqiu/`、API key、vault 内容、venv、build）
- **真跑证据：** `docs/verification/S<n>.<m>.log`（详见 [VERIFICATION.md](./VERIFICATION.md)）

### 7.1 Git 推送步骤（**你跑**）

**第 1 步：在 PowerShell 里执行：**

```powershell
cd E:\MiniMax Code WorkSpace\qingqiu-system
git init
git add .
git commit -m "docs: init project documentation v0.3.0

- 11 份核心文档（PRD/ARCH/PROJECT/TECH-STACK/DESIGN 等）
- 5 份 references/ 前端标准
- 三件套同步更新规则就位
- 命名规则 + 文件大小上限就位

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
git branch -M main
git remote add origin https://github.com/luo683/qingqiu-system.git
git push -u origin main
```

**第 2 步：push 时会弹认证窗口**

- 用户名：`luo683`
- 密码：**Personal Access Token（PAT）**，不是 GitHub 登录密码

**生成 PAT（如果你还没）：**

1. 打开 https://github.com/settings/tokens
2. **Generate new token** → **Fine-grained tokens**（推荐）或 **Classic**
3. 权限勾选 `repo`（完整仓库访问）
4. 过期选 90 天
5. 生成 → **复制 token**（只显示一次！）
6. push 时把 token 当密码粘进去

**PAT 会被 Windows Credential Manager 记住**，以后 push 不用再输。

---

## 8. 沟通记录（与用户的对话历史快照）

| 日期 | 关键决策 |
|------|---------|
| 2026-07-05 17:45 | 确立工作空间 `E:\MiniMax Code WorkSpace` |
| 2026-07-05 17:54 | 第一份 PRD v0.1 |
| 2026-07-05 18:07 | PRD v0.2 完全重写 |
| 2026-07-05 18:14 | PRD v0.2.1 强化私密信息保护 |
| 2026-07-05 18:19 | PRD v0.2.2 改名清秋 + Obsidian + 知识图谱 + 自我成长 |
| 2026-07-05 18:25 | TECH-STACK.md 定稿 |
| 2026-07-05 18:27 | DESIGN.md + IMPLEMENTATION-PLAN.md |
| 2026-07-05 18:37 | NON-FUNCTIONAL.md |
| 2026-07-05 19:17 | 工程纪律全面收紧 |
| 2026-07-05 19:19 | GitHub 已有仓库 + 迁 qingqiu-system |
| 2026-07-05 19:21-19:46 | 文档重组 + references/ 标准 |
| 2026-07-05 19:46-19:52 | GitHub URL 确认 + rename 为 qingqiu-system |

---

## 9. 下次 session 必读

1. **🔥 [docs/handoffs/2026-07-06-day2.md](./docs/handoffs/2026-07-06-day2.md)** — 第二天完整 handoff（合 main + S5.1 + 经验）
2. [docs/handoffs/2026-07-05-day1.md](./docs/handoffs/2026-07-05-day1.md) — 第一天
3. [README.md](./README.md) — 文档地图
4. [PROJECT.md](./PROJECT.md)（本文）— 当前状态
5. [ARCH.md](./ARCH.md) §10 — 开发纪律

---

**PROJECT.md 是项目快照。** 状态变了、决策变了、下一步变了，都来更新这里。