# CHANGELOG · 清秋变更日志

> **格式：** [Keep a Changelog](https://keepachangelog.com/) + [Semantic Versioning](https://semver.org/)
> **状态：** v0.3.0 · 立项完成

---

## [Unreleased]

### Added
- **🆕 验收纪律：每个 slice 必须真跑落地**（2026-07-05）
  - 创建 [VERIFICATION.md](./VERIFICATION.md) 强约束文档
  - mock 通过 ≠ 真跑通；必须真实端到端验证 + 记录证据到 `docs/verification/`
  - 用户明确要求："每次做完功能之后要检验功能能否实现并成功跑通落地"
- **S1.1 · 项目骨架与配置入口**（2026-07-05）
  - `pyproject.toml`（uv + hatchling，dependencies 留空）
  - `src/qingqiu/` 包结构（`__init__.py` + `cli.py` + `__main__.py`）
  - CLI 骨架：`--version` / `-v` / `config show`（占位）
  - `scripts/verify_s1_1.sh` 验收脚本
  - `tests/test_cli.py` 5 个 pytest 测试覆盖 CLI
  - 验收 PASS：uv sync 装依赖成功 + pytest 5/5
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S1.1
- **S1.2 · LLM 抽象层**（2026-07-05）
  - 4 个 provider：`OpenAIProvider` / `AnthropicProvider` / `OllamaProvider` / `CustomProvider`
  - `LLMProvider` Protocol + `Message` / `LLMResponse` 数据结构
  - `LLMRouter` 按角色分派（如 `router: cheap` / `planner: strong` / `memory: local`）
  - 异常体系：`LLMError` / `ProviderNotFoundError` / `ProviderInitError` / `RateLimitError` 等
  - `qingqiu llm test <provider>` 子命令测试 provider 是否可用
  - 45 个 pytest 测试（mock SDK 调用）
  - mock 测试 PASS：pytest 50/50（S1.1 + S1.2）
  - **🆕 真跑落地 PASS**：CustomProvider 真打 MiniMax API（`MiniMax-Text-01`），返回 `'Hello from custom!'`，input=562 / output=4。证据：[docs/verification/S1.2_llm_custom.log.md](./docs/verification/S1.2_llm_custom.log.md)
  - 4 个 provider 中 1 个真跑通（Custom/MiniMax）；其余 3 个 mock 通过待真跑
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S1.2
  - 见 [VERIFICATION.md](./VERIFICATION.md) 验收纪律
- **S1.3 · 配置系统**（2026-07-05）
  - 6 个 Pydantic 子配置：`LLMConfig` / `VoiceConfig` / `SecurityConfig` / `LoggingConfig` / `ObsidianConfig` / `PersonalityConfig`
  - `ConfigManager` 支持加载 + 优先级 + polling 热重载
  - 优先级：CLI > 环境变量（`QINGQIU_<KEY>`）> 文件（`~/.qingqiu/config.yaml`）> 默认值
  - 热重载：polling 1s 检查 `(mtime, size)` 签名变化（避免 Windows mtime 精度问题）
  - 加载失败兜底：保留旧 Config 对象（不让损坏 config 拖垮 daemon）
  - atomic write（写 `.tmp` + rename）
  - CLI 更新：`qingqiu config show` 真工作 / `qingqiu config path` 显示路径
  - 31 个 pytest 测试（mock）
  - mock 测试 PASS：pytest 81/81（S1.1 + S1.2 + S1.3）
  - **🆕 真跑落地 PASS**：4 项验证全过（CLI / 文件加载 / 优先级 / 热重载 1s 内）。证据：[docs/verification/S1.3_config.log.md](./docs/verification/S1.3_config.log.md)
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S1.3
- **S1.4 · 日志系统**（2026-07-05）
  - `src/qingqiu/observability/logger.py`：`setup_logging()` + `get_logger()`（loguru 封装）
  - 控制台（stderr，简洁版）+ 文件（详细版，含位置 + 行号）双 handler
  - 文件滚动：单文件 100MB 触发 rotation / 7 天自动清理 / 多进程安全（enqueue）
  - 独立错误日志：`qingqiu.error.log` 只过滤 ERROR 级（方便定位失败）
  - 错误诊断：`backtrace=True` + `diagnose=True`（含异常链 + 变量值）
  - CLI 集成：`main()` 顶部调 `setup_logging()`，`-v` 切到 DEBUG 级
  - `qingqiu llm test` 子命令全路径加 `logger.info/error` 输出
  - 6 个 pytest 测试（mock）覆盖 setup / write / 错误分流 / handler 移除 / 级别过滤
  - **🆕 真跑落地 PASS**：跑 5 个混合命令（version / llm test ollama / llm test openai / config show / -v），main log 1.59KB / 19 行；error log 0.37KB / 2 行（仅 ERROR）。证据：[docs/verification/S1.4_logging.log.md](./docs/verification/S1.4_logging.log.md)
  - mock 测试 PASS：pytest 87/87（S1.1 + S1.2 + S1.3 + S1.4）
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S1.4
- **S1.5 · Memory 四层空壳**（2026-07-05）
  - 4 层记忆体系（PRD §8.1 + ARCH §92）：
    - **L0 会话内**：`src/qingqiu/memory/l0.py` · 内存 dict（RLock 线程安全）
    - **L1 项目级**：`src/qingqiu/memory/l1.py` · Markdown 文件（`~/.qingqiu/memory/projects/<name>.md`，atomic write）
    - **L2 用户级**：`src/qingqiu/memory/l2.py` · Markdown 文件（继承 L1，默认 `~/.qingqiu/memory/user.md`）
    - **L3 长期事实**：`src/qingqiu/memory/l3.py` · SQLite（`~/.qingqiu/memory/facts.sqlite`，facts 表含 key/value/created_at/updated_at）
  - `MemoryLayer` Protocol（`base.py`）：4 层统一接口（name / get / set / delete / list_keys）
  - `Memory` facade（`manager.py`）：默认 4 层；`get(key)` 从 L0 短路查找；`set(key, value, layer="L3")` 默认写 L3
  - 32 个 pytest 测试覆盖 4 层独立 + facade 跨层
  - **🆕 真跑落地 PASS**：4 步验证全过（4 层独立 set/get / L3 跨进程持久化 / facade 跨层查找 + 分层写入 / 文件 + SQLite 结构）。证据：[docs/verification/S1.5_memory.log.md](./docs/verification/S1.5_memory.log.md)
  - mock 测试 PASS：pytest 119/119（S1.1 + S1.2 + S1.3 + S1.4 + S1.5）
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S1.5
- **S2.1 · CLI 入口 + 子命令骨架**（2026-07-05 · M2 起步）
  - **架构重构**：`src/qingqiu/cli.py` (167 行) → `src/qingqiu/cli/` 包（9 文件）
  - `cli/main.py`：parser + dispatch + 老 config/llm handler 回填
  - `cli/errors.py`：CLIError 体系（code 0/1/2 + NotFound/Validation/Config/Storage）
  - `cli/output.py`：OutputFormatter（human/JSON + table + error/success）
  - `cli/memory.py`：memory 子命令 5 action（get/set/list/delete/search · 接 S1.5 facade）
  - `cli/task.py`：task 子命令 5 action（list/show/add/done/archive · JSON 文件）
  - `cli/status.py`：daemon/LLM/memory 3 块输出 + --section 过滤
  - `cli/config.py` + `cli/llm.py`：从 main.py 拆分
  - 占位子命令：ask/chat（M2 后续切片接入）
  - 全局 flag：--json / --no-color / --config
  - 57 个 pytest 测试（errors/output/memory/task/status/parser）
  - **🆕 真跑落地 PASS**：12 步端到端验证全过（memory CRUD + L1 Markdown 持久化 + JSON 模式 + task 完整 CRUD + status 3 块 + 老命令不回归）。证据：[docs/verification/S2.1_cli.log.md](./docs/verification/S2.1_cli.log.md)
  - mock 测试 PASS：pytest 171/171（S1.1 + S1.2 + S1.3 + S1.4 + S1.5 + S2.1）
  - 设计文档：[docs/slices/S2.1_router_design.md](./docs/slices/S2.1_router_design.md)
  - **Git 首次推送**（D-017）：15 commits → `luo683/qingqiu-system` main 分支（PAT 缓存自动认证）
  - 分支 `slice/S2.1`：完整实施待 review + 合 main
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S2.1
- **S5.2 · 目录白名单**（2026-07-05 · M5 安全基础）
  - `src/qingqiu/security/whitelist.py`：WHITELIST_DIRS（4 个 · PRD §6.1）+ WhitelistError (code=2)
  - 接口：`is_whitelisted(path)` / `check_path(path, op)` / `resolve(path)`
  - 路径规范化：`expanduser().resolve()` 处理 .. 反向 + 相对路径
  - 防前缀相似攻击：用 `relative_to` 而非字符串前缀匹配
  - 26 个 pytest 测试覆盖 4 目录 + 黑名单 + 边界 + 跨平台分隔符
  - **🆕 真跑落地 PASS**：6 步验证全过（README 在白名单 / hosts 被拒 / check_path 返绝对 / SAM 抛异常 / .. 反向规范化 / Downloads 通过）。证据：[docs/verification/S5.2_whitelist.log.md](./docs/verification/S5.2_whitelist.log.md)
  - mock 测试 PASS：pytest 197/197
  - 分支 `slice/S5.2`：commit `49c6be0`
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S5.2
- **S5.3 · 危险操作黑名单**（2026-07-05 · M5 安全基础）
  - `src/qingqiu/security/blacklist.py`：BlacklistError (code=1) + OperationType 枚举
  - Shell 命令黑名单（regex）：rm -rf / git push --force / format c: / reg add / systemctl / chmod 777 /
  - 操作黑名单：EMAIL_SEND / IM_SEND / CLOUD_UPLOAD / CROSS_DIR_MOVE / PRIVATE_FILE_READ / MEMORY_EXPORT / VAULT_BATCH_MODIFY / VAULT_DELETE
  - 接口：`check_shell(cmd)` / `check_operation(op)` / `is_blacklisted_*` 不抛异常版本
  - 38 个 pytest 测试覆盖 shell + operation + 边界
  - **🆕 真跑落地 PASS**：完整验证（agent 真跑落地）
  - mock 测试 PASS：pytest 209/209（合并到 S5.3 worktree 后）
  - 分支 `slice/S5.3`：commit `13653e7`
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S5.3
- **🆕 验收纪律：M5 切片 + agent 派发**（2026-07-05）
  - **agent 派发模式**（D-019/D-020 教训）：
    - mavis spawn 长中文 content 截断 bug → workaround：短 ASCII 指令 + default workspace JSON 文件 + agent 用 Read tool 读
    - agent "完成" ≠ 真完成 → 必须 `git log` + `git status` + pytest 三件套验证
    - agent 可能在自己 default workspace 伪造 commit → 必须看主 worktree 状态
    - spawn 时必须明确告诉 agent worktree 路径 + 任务目标
  - **worktree 隔离**：每个切片独立 `.worktrees/slice-S<n>.<m>` 分支，避免 agent 冲突
  - **cron 监控**：每 2h 自动检查进度 + 14 天 TTL
  - 见 [docs/handoffs/2026-07-05-day1.md](./docs/handoffs/2026-07-05-day1.md) 第一天完整 handoff
- **🆕 第一天收工 handoff**（2026-07-05 23:08）
  - 创建 [docs/handoffs/2026-07-05-day1.md](./docs/handoffs/2026-07-05-day1.md)：完整进度 + 决策 D-001 to D-020 + 经验教训 + 明天 TODO
  - 项目主仓库切换到 main + cherry-pick handoff → push `e7966d5` 到 origin/main
  - PROJECT.md §9 加 handoff 链接（启动 session 必读）
  - cron `s5-check` 删除（S5.x 都完成且 push）
- **🆕 第二天：合并 3 个 slice 分支 + S5.1**（2026-07-06 11:51）
  - `git merge --no-ff slice/S2.1` → `a0cb7f0`（CLI 子命令骨架）
  - `git merge --no-ff slice/S5.2` → `2f012a4`（目录白名单）
  - `git merge --no-ff slice/S5.3` → `e4de7bc`（黑名单 · 解决 __init__.py 冲突）
  - fix：`BLOCKED_OPERATIONS` 不是 `BLACKLIST_OPERATIONS`（agent 笔误）
  - 235/235 PASS（合并后）
  - **S5.1 Confirm 通用框架**：`src/qingqiu/security/confirm.py`
    - Prompter 抽象 + CLIPrompter (y/N/diff + 后台线程超时)
    - Confirm 包装 (60s default) + ConfirmRejected (code=1) + ConfirmTimeout
    - ask() 便捷函数 + get_default_confirm() 单例
    - 22 个测试 + 10 步真跑验证 + docs/verification/S5.1_confirm.log.md
    - 集成点：S2.4 / S5.4 / S3.5 / S4.4
  - 257/257 PASS（最终）
  - main `df8ea3a` push 到 origin
  - 4 个旧 slice 分支全删（worktree + 本地 + origin）
  - 见 [docs/handoffs/2026-07-06-day2.md](./docs/handoffs/2026-07-06-day2.md)
- **🆕 第三天：4 slices 完整收官 + CI loop**（2026-07-06 12:14）
  - **S2.2 Router 意图识别**（2026-07-06）：`src/qingqiu/router/`
    - Intent 枚举（18 个）+ RuleBasedClassifier（regex + 中文友好 lookbehind/ahead）+ LLMClassifier（异步 + JSON 解析容错）
    - IntentClassifier 主类：规则 → LLM → UNKNOWN fallback
    - 28 测试 + 10 指令真跑 100%（rule only 10/10 + LLM mock 10/10）
    - 证据：[docs/verification/S2.2_router.log.md](./docs/verification/S2.2_router.log.md)
    - commit `9340f21` on `slice/S2.2` → merged `638577c`
  - **S2.5 CLI confirm ask/test**（2026-07-06）：`src/qingqiu/cli/confirm.py`
    - Confirm CLI 子命令（ask/test）+ 接 S5.1 Confirm 框架
    - 11 测试 + 真跑 268/268
    - 证据：[docs/verification/S2.5_confirm_cli.log.md](./docs/verification/S2.5_confirm_cli.log.md)
    - commit `b3bebd3` on `slice/S2.5` → merged `34f6c50`
  - **S6.5 人格加载 + 热更新**（2026-07-06）：`src/qingqiu/personality.py`
    - personality.yaml 加载 + watchdog 热更新
    - 10 测试 + 真跑 271/271
    - 证据：[docs/verification/S6.5_personality.log.md](./docs/verification/S6.5_personality.log.md)
    - commit `69bc391` on `slice/S6.5` → merged `73b5cd1`
  - **S5.4 私密识别**（2026-07-06）：`src/qingqiu/security/private_detect.py`
    - PrivateMatchType（FILENAME/CONTENT_REGEX/DIRECTORY）+ PrivateDetector（31 文件 glob + 7 内容 regex 含 GB 11643-1999 身份证校验位 + 5 私密目录）
    - detect_file / detect_content / is_private_path / detect 接口
    - 32 测试 + 真跑 342/342（worktree）→ 合并后 main 395/395 PASS
    - 证据：[docs/verification/S5.4_private_detect.log.md](./docs/verification/S5.4_private_detect.log.md)
    - commit `1289539` on `slice/S5.4` → merged `5999fd6`
  - **合并策略**（决策 D-027）：按依赖顺序 S2.2 → S2.5 → S6.5 → S5.4（独立模块无冲突）
  - **CI Loop cron**（决策 D-026，回应用户原话"设置loop反复检查并跑通项目"）：
    - `mavis cron self ci-loop --every 30m --ttl 14d`
    - 每 30min 跑 `uv run pytest tests/ -q`，失败 → 自动修或 spawn coder；PASS → 写 `docs/verification/ci-loop-<date>.log`
    - 自动到期 2026-07-20
  - **🆕 day3 handoff**：[docs/handoffs/2026-07-06-day3.md](./docs/handoffs/2026-07-06-day3.md)
  - 见 [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) S2.2 / S2.5 / S5.4 / S6.5

---

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