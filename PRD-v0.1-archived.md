# PRD · 清秋 v0.1（已归档 · 被 v0.2 / v0.2.1 / v0.2.2 取代）

> **状态：** ⚠️ Archived · 不再演进
> **取代版本：** [PRD.md](./PRD.md)
> **作废原因：** 用户基于澄清需求决定「吃掉 Hermes / 语音优先 / 纯被动 / LLM 抽象层 / 全栈第一版」 —— 与 v0.1 的"Hermes 叠加层"思路根本性冲突，作废重写。

---

## 历史正文（仅供追溯）

<details>
<summary>点击展开 v0.1 全文</summary>

### v0.1 关键决策（已被 v0.2 全部推翻）

| 维度 | v0.1（旧） | v0.2（新） |
|------|-----------|-----------|
| Hermes 关系 | 叠加层 | 吃掉升级 |
| Agent 体系 | 保留 Codex/OpenCode/ZCode | 按新需求重设计 |
| 主入口 | CLI → 托盘 → IM → 语音 | 语音优先（本地离线） |
| 主动性 | 定时汇报 + 异常触发 | 纯被动 |
| LLM 后端 | 走 mavis 云端路由 | 抽象层 + 可换脑 |
| 数据范围 | 只 Code WorkSpace | 标准白名单（4 个目录） |
| 人格 | 固定中性 | prompt 自定义 |
| 写权限 | 危险操作确认 + 其余自动 | 每次写入前确认 |
| 范围策略 | 分阶段 MVP | 第一版全栈 |
| 时间态度 | 2 周跑通 MVP | 不急，做好做扎实 |

### v0.1 一句话定位（历史）

贾维斯 = **一个始终在线、听得懂人话、能动手执行的个人 AI 助理**。底层跑的是 Hermes 多 agent 协作体系，对外只露一个名字「Jarvis」，对内由多个专精 agent 协同完成任务。

### v0.1 系统架构（历史）

三层架构：L1 Interface Layer（CLI / Voice / IM Bot / Tray）/ L2 Jarvis Core（Router / Planner / Memory / Executor / Reflector）/ L3 Hermes Agents（Hermes / Codex / OpenCode / ZCode）。

### v0.1 角色（历史）

Hermes 协调 / Codex 实现 / OpenCode 评审 / ZCode 移动端+文档+GLM。

### v0.1 里程碑（历史）

| 阶段 | 周期 | 交付 |
|------|------|------|
| M0 · 立项 | 本周 | PRD + 骨架 |
| M1 · CLI MVP | 2 周 | `jarvis "..."` 跑通 Hermes 链路 |
| M2 · Tray 常驻 | 2 周 | 托盘 + 全局快捷键 |
| M3 · IM 接入 | 1 周 | 飞书 Bot |
| M4 · 记忆/复盘 | 2 周 | Memory + 周报 |
| M5 · 语音 | 待定 | 本地 STT/TTS |
| M6 · 主动助理 | 待定 | 定时/事件/异常通知 |

</details>

---

**完整 v0.1 正文见历史备份：** 如需查阅，从 `jarvis-system/docs/PRD-v0.1-archived.md` 取（迁移时可一并搬过来）。