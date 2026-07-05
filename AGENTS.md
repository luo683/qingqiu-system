# AGENTS · 清秋 coding agent 总规约

> **状态：** v0.3.0
> **作者：** Mavis（自指）
> **本文件性质：** 给所有 coding agent（包括我自己、未来接手的 Claude/Cursor/Cline/Windsurf 等）的硬规则。违反的代码不许合入。

---

## 1. 适用范围

任何 AI agent 在清秋项目里写代码、改代码、提 PR 前**必读**本文件 + [README.md](./README.md) + [PROJECT.md](./PROJECT.md) + [ARCH.md](./ARCH.md)。

---

## 2. 权限限制（**核心约束**）

> 用户明确："限制你的权限，禁止你做主。"

### 2.1 禁止做的事

| 类别 | 禁止行为 |
|------|---------|
| **重构** | ❌ 未点名不重构（即使看到代码丑） |
| **改 UI** | ❌ 未点名不改 UI 风格（DESIGN.md 是宪法） |
| **改无关逻辑** | ❌ 不在本切片范围的代码不动 |
| **批量改** | ❌ 每次改动聚焦当前切片，不大刀阔斧 |
| **做主** | ❌ 不确定就问，不擅自决策 |
| **猜需求** | ❌ 不猜用户没明说的需求 |
| **跨范围** | ❌ 不跨切片、跨模块动代码 |
| **写"一坨"** | ❌ 不写大文件（Python < 300 行 / React < 200 行） |

### 2.2 必须做的事

| 类别 | 必须行为 |
|------|---------|
| **改前必读** | ✅ 先 Read 再 Edit/Write（不要猜文件内容） |
| **改后必测** | ✅ 跑测试 + 让用户验收 |
| **小步提交** | ✅ 一个切片一个 commit（不堆 commit） |
| **同步三件套** | ✅ 大改动同时更新 PRD / ARCH / PROJECT |
| **用现成模式** | ✅ 看周围代码风格 / 复用已用库 |
| **引用规范** | ✅ 引用代码用 `file:line` 格式 |
| **记录决策** | ✅ 大决策写到 PROJECT.md §6 决策记录 |
| **跑通验收** | ✅ 每个切片完成跑通验收命令再交 |

---

## 3. 工作流（每个切片）

```
1. 读 IMPLEMENTATION-PLAN.md 该 slice 定义
2. 读相关现有代码（不要猜）
3. 拉分支 slice/S<n>.<m>
4. 写测试 / 验收脚本（红）
5. 实现（绿）
6. 重构（如必要）
7. 跑 lint + type check + test
8. 跑端到端验收命令
9. 让用户验收（关键切片）
10. commit + push
11. 更新 CHANGELOG.md
```

---

## 4. 文档规则

### 4.1 三件套同步

每次大改动（新增 M / 改动 ≥ 3 个 slice / 架构调整 / 隐私策略变化 / 技术栈调整）必须**同步更新**：

- [PRD.md](./PRD.md)
- [ARCH.md](./ARCH.md)
- [PROJECT.md](./PROJECT.md)

### 4.2 文档命名

- `PRD.md` / `ARCH.md` / `PROJECT.md` / `TECH-STACK.md` / `DESIGN.md` / `IMPLEMENTATION-PLAN.md` / `NON-FUNCTIONAL.md` / `AGENTS.md` / `CHANGELOG.md` —— 项目根目录
- `references/` —— 前端标准（详见 references/README.md）
- `src/qingqiu/<module>.py` —— Python 模块（snake_case）
- `src/qingqiu-tray/src/components/<Component>.tsx` —— React 组件（PascalCase）

### 4.3 文档变更后必做

- 更新 CHANGELOG.md（一句话描述变更）
- 重大决策更新 PROJECT.md §6 决策记录

---

## 5. 代码规则

### 5.1 命名（详见 [references/naming.md](./references/naming.md)）

| 类型 | 风格 | 示例 |
|------|------|------|
| Python 模块 | snake_case | `task_scheduler.py` |
| Python 类 | PascalCase | `TaskScheduler` |
| Python 函数 | snake_case | `schedule_task()` |
| Python 常量 | UPPER_SNAKE | `MAX_RETRIES = 3` |
| Python 私有 | _leading | `_internal_helper()` |
| React 组件 | PascalCase.tsx | `TaskCard.tsx` |
| React Hook | useXxx.ts | `useTaskList.ts` |
| React 类型 | PascalCase | `TaskCardProps` |
| CSS class | kebab-case | `.task-card` |
| 文件名 | snake_case (Python) / PascalCase (React) | — |

### 5.2 文件大小上限（详见 [references/naming.md §2](./references/naming.md)）

| 类型 | 上限 | 超出处理 |
|------|------|---------|
| Python 模块 | 300 行 | 拆模块 |
| React 组件 | 200 行 | 拆组件或 hooks |
| 单个 Markdown 文档 | 1500 行 | 拆文档 |
| 单个测试文件 | 400 行 | 拆测试 |

### 5.3 依赖规则

- ❌ 不引非主流库（除非 T5 主流验证通过）
- ❌ 不引"看起来更好但冷门"的库
- ✅ 优先用 Python 标准库
- ✅ 优先用主流 React 生态库
- ✅ 加新依赖必须更新 TECH-STACK.md

### 5.4 测试规则

- 每个切片必须有验收脚本
- 关键路径必须有单元测试
- 性能 baseline 用 pytest-benchmark
- 测试覆盖率不强制（单人项目，性价比低）

---

## 6. 安全规则（**不可妥协**）

### 6.1 密钥

- ❌ **任何 API key 不进前端代码 / bundle / 配置文件**
- ✅ 所有 API key 走 daemon 后端 + Windows Credential Manager（keyring）
- ✅ UI 只通过 `127.0.0.1:7788/api/*` 调 daemon（HTTP 不带 key）
- ❌ 不写 `.env` 文件（v1.0 阶段）
- ❌ 不提交任何含 token / key / 凭证的文件

### 6.2 Confirm

- 任何写操作必须经 `core.confirm.ask_write()`
- 不绕过 Confirm（P5）
- 不写"自动跳过 Confirm" 的逻辑

### 6.3 私密信息

- 三道闸（Detect / Block / Redact）必须都实现
- 不写"批量跳过私密识别"的逻辑
- 不在日志里打印私密信息

### 6.4 网络

- HTTP server 只能绑定 `127.0.0.1`，不暴露 `0.0.0.0`
- daemon 不跑 system 权限
- vault 路径不在 Git 跟踪

---

## 7. 与用户的沟通

### 7.1 何时问

| 触发 | 动作 |
|------|------|
| 不确定的需求 | 立刻问 |
| 多个合理方案 | 列出来 + 推荐 + 等用户选 |
| 切片完成 | 让用户试用 + 等反馈 |
| 发现潜在 bug / 风险 | 立刻告诉用户 |

### 7.2 何时不问

- 切片定义明确（IMPLEMENTATION-PLAN.md 写了的）
- 命名 / 格式等有明确规范
- 默认值明确（如 `qingqiu` CLI 名）

### 7.3 沟通风格

- 中文为主，技术名词保留英文
- 简洁、直接、不啰嗦
- 不卖萌、不"我帮您"、不"希望这有帮助"
- 给判断不给选项 —— "我推荐 X，理由 Y"

---

## 8. 自我反思（agent 必做）

每个 session 结束前自问：

- [ ] 我有没有改未点名的范围？
- [ ] 我有没有重构用户没要求的？
- [ ] 我有没有动 UI 风格？
- [ ] 我有没有猜需求？
- [ ] 我有没有写大文件？
- [ ] 我有没有密钥进前端？
- [ ] 我有没有绕过 Confirm？
- [ ] 我有没有同步三件套？

如有任一项"是" → 立刻 revert + 重新做。

---

## 9. 紧急情况

| 场景 | 动作 |
|------|------|
| 发现自己写了未点名的代码 | 立刻告诉用户 + 提议 revert |
| 发现 P5 / P8 违规 | 立刻修复 + 报告 |
| 不确定改不改 | **问，不擅自** |
| 用户说"不要 X" | 立刻停止 X 相关所有改动 |

---

**这份规约不妥协。** 违反 = 不合入 = 回滚。