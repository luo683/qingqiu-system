# 清秋（QingQiu）项目

> **状态：** v0.3.0 · 立项完成 · 进入 M1
> **最后更新：** 2026-07-05

---

## 这是什么

清秋 = **一个由本地语音驱动、被动响应、权限严格、接 Obsidian 知识库的私人 AI 助理**。基于 Hermes multi-agent 思想重塑，单租户、本地优先、可热插拔 LLM、纯被动响应。

不是聊天机器人，不是 IDE 插件，不是云端 SaaS —— 是**装在你机器上、看过你所有笔记、记得你所有偏好、但要你点头才动手的私人中枢**。

---

## 文档地图（项目根目录三件套加粗）

| 文档 | 作用 | 阅读时机 |
|------|------|---------|
| **[PRD.md](./PRD.md)** | 做什么、为什么 | 想理解产品定位时 |
| **[ARCH.md](./ARCH.md)** | 怎么组织、模块怎么连 + 开发纪律 | 写代码 / 改架构时 |
| **[PROJECT.md](./PROJECT.md)** | 当前状态、下一步、已知问题、决策记录 | **开始新工作前必读** |
| [TECH-STACK.md](./TECH-STACK.md) | 用什么技术、为什么 | 选技术 / 加依赖时 |
| [DESIGN.md](./DESIGN.md) | UI 长什么样、不做什么 | 写 UI 代码时 |
| [IMPLEMENTATION-PLAN.md](./IMPLEMENTATION-PLAN.md) | 48 个切片定义 | 切片执行时 |
| [NON-FUNCTIONAL.md](./NON-FUNCTIONAL.md) | 安全/性能/可用性/成本 | 设计取舍时 |
| [AGENTS.md](./AGENTS.md) | coding agent 总规约 | 任何 AI agent 接手项目时 |
| [CHANGELOG.md](./CHANGELOG.md) | 变更历史 | 看历史 / 复盘时 |
| [references/](./references/) | **前端组件 / 样式 / 命名 / 测试标准** | 写前端代码时 |
| [src/](./src/) | 源代码（M1 开始填充） | 写代码 |
| [tests/](./tests/) | 测试代码 | 写测试 |
| [scripts/](./scripts/) | 工具脚本 | 跑工具时 |
| [tasks/](./tasks/) | Hermes task bus（HOT 数据） | 看任务状态时 |

---

## 核心约束（不可妥协）

1. **单租户、单机、本地优先**
2. **被动响应**（不在用户喊时说话）
3. **写入前必问**（每次写操作经 Confirm）
4. **私密信息零泄露**（三道防线 + 默认本地 LLM）
5. **纯被动 / 不主动**（不做定时汇报、不主动通知）
6. **密钥不进前端**（API key 全部在 daemon 后端 + keyring）

---

## 开发纪律（强约束）

- **小步迭代**：每个切片独立验收，不堆功能
- **端到端切片 MVP**：每个切片都能"今天写完明天用上"
- **主动拆分模块**：禁止写一坨代码（Python < 300 行 / 组件 < 200 行）
- **只改点名的范围**：不要重构、不要改 UI 风格、不要改无关逻辑
- **三件套同步更新**：PRD/ARCH/PROJECT 每次大改动必须同时更新
- **技术栈主流**：选主流 + 验证过的方案

详见 [ARCH.md §10](./ARCH.md) 和 [AGENTS.md](./AGENTS.md)。

---

## 仓库

- **本地：** `E:\MiniMax Code WorkSpace\qingqiu-system\`
- **远程：** `https://github.com/luo683/qingqiu-system`

---

## 许可

私人项目，未指定开源协议。