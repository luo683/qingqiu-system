# NON-FUNCTIONAL · 清秋非功能性需求（安全 / 性能 / 可用性 / 成本）

> **状态：** v0.3.0 · 配套 PRD v0.2.2 / TECH-STACK v0.3.0
> **本文件性质：** 安全、性能、可用性、成本四个维度的**量化承诺 + 关键判断**。

---

## 1. 一句话总结

**安全零妥协 / 性能以"流畅"为底线（端到端 < 3s）/ 可用性以"挂掉能自愈"为目标（watchdog 重启 < 5s）/ 成本以"本地为主、云端按需"为策略（默认月成本 < $5）**。

---

## 2. 安全

### 2.1 威胁模型

| 威胁源 | 攻击向量 | 优先级 |
|--------|---------|--------|
| **恶意 Prompt 注入** | 外部内容（网页 / PDF / IM）含恶意指令 | **P0** |
| **用户不清醒误操作** | 误触 / 误喊 | **P0** |
| **第三方 API 妥协** | 飞书 / GitHub token 泄露 | **P1** |
| **物理访问** | 别人坐到电脑前 | **P1** |
| **网络窃听** | 127.0.0.1:7788 被同机器进程读 | **P1** |
| **磁盘失窃** | 笔记本被偷 | **P2** |
| **LLM provider 日志** | 云端记录 query | **P2** |
| **代码供应链** | pip 依赖投毒 | **P2** |

### 2.2 关键决策

| # | 决策 | 理由 |
|---|------|------|
| **D-S1** | daemon 跑 user 权限（不 system） | 最小权限原则 |
| **D-S2** | 127.0.0.1 only（不暴露 0.0.0.0） | 单机不需要 LAN |
| **D-S3** | API key 走 Windows Credential Manager | OS 级隔离 |
| **D-S4** | LLM 输出经白名单工具调用（不让 LLM 直接调 shell） | LLM 是想执行，工具是真执行，必须分离 |
| **D-S5** | 所有写操作经 Confirm（包括自动任务） | 安全优先于便利 |
| **D-S6** | Hermes 任务 JSON 用 atomic write（write tmp + rename） | 任务历史是审计依据 |
| **D-S7** | 私密信息默认走本地 LLM | P8 强制兑现 |
| **D-S8** | 密码 / token 模式默认过滤入 prompt | 即使本地 LLM 也不该看 token 明文 |
| **D-S9** | **密钥不进前端**（用户明确要求） | UI 只调 /api/* 不带 key |

### 2.3 风险与缓解

| 风险 | 缓解 |
|------|------|
| Prompt 注入 | 工具白名单 + LLM 输出经 Tool.execute() |
| 用户误操作 | Confirm 严格 + 长任务分阶段点头 |
| 飞书 token 泄露 | WebSocket 双向心跳 + 异常重连告警 |
| 物理访问 | daemon 需 OS 用户登录后才启动 |
| 127.0.0.1:7788 被读 | 进程白名单（只 qingqiud / qingqiu-tray） |
| 笔记本被偷 | 假设 BitLocker 已开 |
| 依赖投毒 | `uv.lock` 锁定 + `pip-audit` 定期扫 |

### 2.4 不在 v1.0 范围

❌ 代码签名 / ❌ SOC2 合规 / ❌ 远程擦除 / ❌ 硬件密钥 / ❌ MFA / ❌ 反逆向

---

## 3. 性能

### 3.1 性能预算（v1.0 目标）

| 指标 | 目标 | 切片 |
|------|------|------|
| daemon 启动 | < 2s | S1.1 |
| UI 启动（Tauri） | < 1s | S9.1 |
| **语音端到端** | **< 3s** | S3.4 |
| LLM 首 token | < 500ms | S1.2 |
| whisper 转写（10s 中文） | < 2s | S3.2 |
| piper TTS（100 字） | < 1s | S3.3 |
| 嵌入向量化（1000 笔记） | < 1h | S8.4 |
| 嵌入检索（top 5） | < 100ms | S8.5 |
| SQLite 查询 | < 50ms | S6.4 |
| vault 增量索引 | < 1s | S8.2 |
| 图谱渲染（1000 节点） | 60fps | S9.3 |
| 图谱渲染（10000 节点） | 30fps + 折叠 | S9.4 |
| Hermes 任务调度 | < 100ms | S2.3 |

### 3.2 内存预算

| 组件 | 内存 |
|------|------|
| qingqiud.exe | < 200MB |
| voice-worker.exe | < 500MB（运行） / < 50MB（待机） |
| feishu-bot.exe | < 80MB |
| qingqiu.exe（CLI） | < 50MB |
| qingqiu-tray.exe（Tauri） | < 300MB |
| **总计峰值** | **< 1.2GB** |

### 3.3 磁盘预算

| 内容 | 大小 |
|------|------|
| Python daemon + 依赖 | ~80MB |
| Tauri UI | ~30MB |
| faster-whisper small 模型 | ~460MB |
| piper TTS 模型 | ~60MB |
| Ollama + nomic-embed-text | ~270MB（可选） |
| SQLite 数据库 | ~50MB-200MB |
| 日志（7 天滚动） | < 100MB |
| **总计** | **~1.3GB（纯本地）/ ~800MB（云端 LLM）** |

### 3.4 性能瓶颈 + 优化策略

| 瓶颈 | 优化 |
|------|------|
| LLM 调用时延（最大） | 流式响应 + 5min 缓存 + smart routing |
| faster-whisper 慢 | 默认 small 模型 |
| 嵌入向量化慢 | 后台异步 |
| vault 索引慢 | watchdog 增量 |
| 图谱渲染卡 | > 1k 自动聚类折叠 |
| SQLite 写并发 | WAL + 批量 flush |

### 3.5 性能监控

- 每个任务耗时自动写入 L3 facts
- CLI `qingqiu stats`：启动时间 / 平均任务时延 / LLM 调用次数 / 缓存命中率
- `pytest-benchmark` baseline + 回归检测

---

## 4. 可用性

### 4.1 可靠性目标

| 指标 | 目标 |
|------|------|
| 启动成功率 | > 99%（一周内） |
| 平均无故障运行时间（MTBF） | > 7 天 |
| 崩溃恢复时间 | < 5s |
| 数据丢失率（任务历史） | 0（atomic write） |
| 离线运行能力 | LLM 走本地时不依赖网络 |
| API 错误可读性 | 100% 错误都有"什么错 + 怎么修" |

### 4.2 降级策略

| 故障 | 降级路径 |
|------|---------|
| whisper 失败 | 提示用文字输入 |
| LLM cloud 失败 | 重试 3 次 → 切下一个 → 切本地 → 报错 |
| LLM 本地失败 | 报错"清秋大脑暂时不可用" |
| vault watcher 失败 | 启动时全量重建 |
| 飞书断线 | 自动重连（指数退避）+ 本地缓冲 |
| daemon 崩溃 | watchdog 重启（< 5s） + 通知 |
| voice-worker 崩溃 | 重启进程 + 清语音队列 |
| UI 崩溃 | 不影响 daemon；重启 UI |
| SQLite 损坏 | 自动备份恢复 + 全量重建 |
| config.yaml 损坏 | 用 defaults + 报警 |

### 4.3 崩溃恢复

```
qingqiud.exe ← qingqiu-watchdog.exe 监控，5s 内重启
voice-worker.exe ← qingqiud 监控
feishu-bot.exe ← qingqiud 监控
qingqiu-tray.exe ← 用户手动重启

5 分钟内崩溃 3 次 → 不再重启 + 通知用户
```

### 4.4 数据完整性

| 数据 | 保证 |
|------|------|
| Hermes 任务 JSON | atomic write + lock 文件 |
| SQLite | WAL + foreign key + 事务 |
| 嵌入向量 | 与笔记 ID 强关联 |
| vault 索引 | watchdog 增量同步 |
| 配置文件 | YAML schema 校验 |

### 4.5 错误处理原则

- ✅ 错误可读：`qingqiu: 任务失败：测试未通过 (3 failed)。查看详情：[路径]`
- ✅ 错误可操作：告诉用户下一步做什么
- ✅ 错误可上报：可选 `qingqiu report-bug`
- ❌ 不抛未处理异常
- ❌ 不抛 stack trace 给用户

---

## 5. 成本

### 5.1 一次性成本

| 项目 | 费用 |
|------|------|
| faster-whisper small | 0 |
| piper TTS | 0 |
| Ollama + nomic-embed-text | 0 |
| Anthropic / OpenAI 注册 | 0（按用量） |
| **总计** | **$0** |

### 5.2 持续成本（按月）

#### 场景 A：纯本地（默认 · v1.0 推荐）

| 项目 | 月成本 |
|------|--------|
| Ollama 本地 LLM | $0 |
| Ollama 本地嵌入 | $0 |
| faster-whisper 本地 STT | $0 |
| piper 本地 TTS | $0 |
| **月总计** | **$0** |

#### 场景 B：本地 LLM + 云端辅助（推荐）

| 项目 | 月成本 |
|------|--------|
| Anthropic Claude Sonnet 4 | ~$8 |
| OpenAI GPT-4o-mini | ~$1 |
| Ollama 本地嵌入 | $0 |
| **月总计** | **~$9** |

#### 场景 C：重度全云端

| 项目 | 月成本 |
|------|--------|
| Anthropic Claude Sonnet 4 | ~$80 |
| OpenAI text-embedding-3-small | ~$1 |
| **月总计** | **~$81** |

### 5.3 第三方 API 成本

| API | 月成本 |
|-----|--------|
| 飞书（lark-tools） | $0（免费配额） |
| GitHub（gh CLI） | $0（公开仓库免费） |
| Email（SMTP） | $0 |
| Web Search | $0 |

### 5.4 成本优化

- 默认本地 Ollama → 月 $0
- 智能 routing（简单用 cheap model）→ 月成本降 50%
- LLM 响应缓存（5min TTL）→ 节省 30-50%
- 嵌入本地化 → 1000 笔记 $0
- 批处理 LLM 调用
- prompt 压缩

### 5.5 成本控制

- `~/.qingqiu/config.yaml` 加 `cost.monthly_budget_usd`：超预算告警 + 可选停止云端
- `qingqiu stats cost`：本月 LLM 调用费 / token 用量
- Provider 优先级：本地 > 便宜云端 > 贵云端

### 5.6 你的时间成本

| 任务 | 时间 |
|------|------|
| 每切片验收 | 30min - 2h |
| 每周复盘 | 30min |
| 文档 review | 1h / M |
| **总计你的投入** | **~5-10h / 月** |

---

## 6. 四维权衡偏好

| 维度冲突 | 选择 | 理由 |
|---------|------|------|
| 安全 ↔ 可用性 | 安全 | Confirm 严格 + 会话内可临时免确认 |
| 安全 ↔ 性能 | 性能 | 只对 secret 加密，文件明文 |
| 性能 ↔ 成本 | 成本 | 默认 small 模型 |
| 可用性 ↔ 成本 | 成本 | 单进程 + watchdog |
| 成本 ↔ 安全 | 安全 | 私密信息强制本地 |
| 易用 ↔ 安全 | 安全 | Confirm 不省 |

**总结性偏好：**

1. **安全 > 一切**（P5 / P8 / D-S9 不能妥协）
2. **成本 > 性能**（默认本地 + small 模型）
3. **性能 > 可用性**（缓存 + 懒加载）
4. **可用性 > 易用**（崩溃自愈）

---

## 7. 验证方法

| 维度 | 验证 | 时机 |
|------|------|------|
| 安全 | 渗透自测 + 私密演练 + Confirm 触发率 | 每 M 后 |
| 性能 | pytest-benchmark + qingqiu stats | 每切片 |
| 可用性 | chaos test + 启动失败计数 | M5 / M7 |
| 成本 | qingqiu stats cost 跑一周 | M3 后 |

---

**不在 v1.0：** 多副本 / E2E 加密 / 远程擦除 / SOC2 / YubiKey / 自动化 fuzzing / 火焰图持续监控 / 成本预测 ML。