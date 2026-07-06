# M10 自我成长 · 验收记录

## 切片范围

PRD §9 自我成长机制 · 5 条学习路径中的 S10.1 + S10.4（2 个 MVP 切片）。

| 维度 | 描述 |
| --- | --- |
| 切片 | M10 自我成长 (S10.1 reflect + S10.4 weekly) |
| 分支 | slice/M10 |
| Worktree | `E:\MiniMax Code WorkSpace\qingqiu-system\.worktrees\slice-M10` |
| 父切片 | M6 记忆 + 人格（依赖 L3 + personality） |
| 后续切片 | S10.2 偏好学习 / S10.3 vault 反哺 / S10.5 偏好冲突检测 |

## 交付物

| 文件 | 行数 | 角色 |
| --- | --- | --- |
| `src/qingqiu/growth/__init__.py` | 15 | public API：导出 Reflector / WeeklyReport / GrowthConfig |
| `src/qingqiu/growth/config.py` | 43 | GrowthConfig 开关（env > 参数 > 默认 True） |
| `src/qingqiu/growth/reflect.py` | 89 | Reflector · 任务统计 → 写入 L3 facts |
| `src/qingqiu/growth/weekly.py` | 177 | WeeklyReport · 每周复盘 → weekly/<ISO_week>.md |
| `tests/growth/__init__.py` | 0 | (空) |
| `tests/growth/test_reflect.py` | 14 测试 | Reflector 单元测试 |
| `tests/growth/test_weekly.py` | 18 测试 | WeeklyReport + GrowthConfig 单元测试 |
| `scripts/verify_m10.py` | 4 场景 / 29 断言 | 端到端真跑验证 |
| `docs/verification/M10_growth.log.md` | 本文件 | 验收记录 |

**未修改任何已有文件**：`llm/ memory/ cli/ security/ personality/ chat/ planner/ daemon/ router/ voice/ im/ obsidian/ ui/` 全部 0 改动。`config/` 也未改动（growth.enabled 走 env var，不污染 Config schema）。

## 数据结构

### ReflectKeys（L3 key 常量）

```python
class ReflectKeys:
    TASK_COUNT_TOTAL = "task_count_total"
    TASK_COUNT_DONE = "task_count_done"
    TASK_COUNT_PENDING = "task_count_pending"
    TASK_COUNT_ARCHIVED = "task_count_archived"
    LAST_REFLECT_AT = "last_reflect_at"
```

### GrowthConfig（开关 + 输出目录）

```python
@dataclass
class GrowthConfig:
    enabled: bool           # env > 参数 > 默认 True
    weekly_dir: Path        # 默认 ~/.qingqiu/memory/weekly/
```

优先级：`QINGQIU_GROWTH_ENABLED` env var > 构造函数参数 > 默认 True（启用）。

## MVP 行为

| 触发 | 结果 |
| --- | --- |
| `Reflector(l3).reflect(tasks)` | 写入 5 条 L3 facts（覆盖式） |
| `WeeklyReport(l3, growth).weekly()` | 生成 `weekly/2026-W27.md`（当前 ISO 周） |
| `growth.enabled=False` | `weekly()` 立即返回 `None`，不创建目录、不写文件 |
| 多次 `reflect` | 最后一次状态覆盖 L3；`weekly` 反映最新值 + top 5 facts |

## 验证结果

### 单元测试

```
$ uv run pytest tests/growth/ -v
============================= 32 passed in 0.69s ==============================
```

覆盖：
- **Reflector**（14 测试）：total/done/pending/archived/last_reflect_at 五项写入、summarize 不写 L3、幂等覆盖、empty/None 列表合法、`now` 参数注入、ReflectKeys 常量稳定、`_iso_utc` 格式正确
- **GrowthConfig**（4 测试）：默认 enabled=True、`QINGQIU_GROWTH_ENABLED=false` 关闭、env > 显式参数优先级、weekly_dir 可注入
- **WeeklyReport**（14 测试）：disabled 返 None + 不创建目录、生成 .md、文件名 = ISO 周、自动 mkdir、`clock` 参数确定性、4 任务计数 + 完成率 + Top L3 facts + last_reflect_at、多 reflect 累积值、top facts 含外部 L3 facts、`iso_week_str` 已知日期、公共 API 完整

### 全量回归

```
$ uv run pytest tests/ -q --no-header
============================= 508 passed in 9.58s =============================
```

不回归：原 476（M9 base，含 S5.5+S6.5+其它） + 新 32 = 508。

### 端到端验证脚本

```
$ uv run python scripts/verify_m10.py
[verify] M10 自我成长 · S10.1 reflect + S10.4 weekly

[scenario 1] M10-1: reflect(任务列表) → L3 新增 5 facts
  [PASS] reflect 写入 5 条 facts
  [PASS] task_count_total = 6
  [PASS] task_count_done = 2
  [PASS] task_count_pending = 3
  [PASS] task_count_archived = 1
  [PASS] last_reflect_at 非空

[scenario 2] M10-2: weekly() → 生成 weekly/<ISO_week>.md 含任务汇总 + L3 top facts
  [PASS] weekly() 返回 Path
  [PASS] 文件存在
  [PASS] 文件名为 2026-W27.md
  [PASS] 含「任务汇总」section
  [PASS] 含总计行 | 3 |
  [PASS] 含已完成行
  [PASS] 含待办行
  [PASS] 含已归档行
  [PASS] 含完成率
  [PASS] 含 Top L3 facts section
  [PASS] top facts 含 user_pref_no_emoji
  [PASS] top facts 含 favorite_tone
  [PASS] top facts 至少含 1 个 reflect key

[scenario 3] M10-3: growth.enabled = false → weekly() 不生成
  [PASS] weekly() 返 None
  [PASS] weekly_dir 未被创建

[scenario 4] M10-4: 多次 reflect → 累积 facts，weekly 输出反映全部
  [PASS] weekly() 返 Path
  [PASS] 最终 total=5 反映在 markdown
  [PASS] 最终 done=2
  [PASS] 最终 archived=3
  [PASS] 最终 pending=0
  [PASS] L3 总事实数 = 8
  [PASS] last_reflect_at 在 markdown
  [PASS] fact_a 出现

[verify] M10 PASS · 29 assertions across 4 scenarios
```

4/4 场景全部 PASS。

### CLI 不破坏

```
$ uv run qingqiu --help
usage: qingqiu [-h] [-V] [-v] [--json] [--no-color] [--config CONFIG]
               <subcommand> ...
清秋 · 本地优先的个人 AI 助理
positional arguments:
  <subcommand>
    ask            单次提问
    chat           交互模式
    task           任务管理
    status         健康状态
    memory         记忆管理
    config         查看和管理配置
    llm            LLM provider 管理
```

## 关键设计

1. **最小复用**：
   - 完全复用 `qingqiu.memory.l3.L3FactsMemory`（SQLite facts）
   - 不修改 personality.py / memory/ / cli/ / config/ schema
2. **开关优先级**：env `QINGQIU_GROWTH_ENABLED` > 构造参数 > 默认 True
   - 测试隔离：每个 test 用临时 `tmp_path` db，不污染 `~/.qingqiu/memory/`
   - 生产可用：用户改 env var 即可全网生效
3. **不调 LLM**：纯统计方法（`done/pending/archived` 按 status 字段匹配）
4. **幂等覆盖**：L3 facts 用 `INSERT ON CONFLICT DO UPDATE`（来自 l3.py），多次 reflect 只更新值不新增 key
5. **ISO 周命名**：`YYYY-Www`（如 `2026-W27`），用 `datetime.isocalendar()` 计算
6. **Top N by recency**：top 5 facts 按 `updated_at` 倒序（多次 reflect 后旧 facts 仍可见，但被新写的挤到后面）
7. **多 reflect 累积**：final state 由最近一次 reflect 决定；weekly 读取最新 + 列表前 5 全部展示
8. **测试隔离**：每个 test 用 `tmp_path` fixture，临时 SQLite db + 临时 weekly_dir；verify_m10.py 用 `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)`（Windows 文件锁兼容）
9. **clock 可注入**：`WeeklyReport(clock=lambda: ts)` 让 ISO 周确定性，方便测试 2026-W27 这种已知日期
10. **growth.enabled 默认 True**：避免"未配置 = 不工作"的隐式陷阱；用户想关 → 显式设 env var

## 周报 markdown 模板

```markdown
# 周报 · 2026-W27

- 生成时间：2026-07-05T12:00:00Z
- L3 总事实数：8

## 任务汇总

| 状态 | 数量 |
|------|------|
| 总计 | 5 |
| 已完成 | 2 |
| 待办 | 0 |
| 已归档 | 3 |
| 完成率 | 40.0% |

## Top 5 L3 事实（按更新时间倒序）

- `last_reflect_at` = 2026-07-05T...
- `task_count_archived` = 3
- `task_count_pending` = 0
- `task_count_done` = 2
- `task_count_total` = 5
```

## 边界覆盖

- ✅ reflect 写满 5 条 facts（total / done / pending / archived / last_reflect_at）
- ✅ done 状态严格匹配 `status == "done"`（archived / pending 单独计）
- ✅ empty / None 任务列表合法（写入全 0 + 当前时间戳）
- ✅ `summarize()` 不触发任何 `l3.set`（纯统计）
- ✅ 幂等覆盖：第二次 reflect 同 key 覆盖，key 数量不变（5）
- ✅ `now` 参数可注入（确定性时间戳测试）
- ✅ `growth.enabled=False` → weekly() 返 None 且不创建目录
- ✅ `growth.enabled=True` → 自动创建嵌套目录（mkdir parents=True）
- ✅ ISO 周命名（YYYY-Www）
- ✅ Top 5 facts 按 updated_at 倒序 + 含 reflect + 外部 L3 facts 混合
- ✅ 多次 reflect 后 weekly 输出反映最终累积状态
- ✅ 完成率 = done / total * 100（total=0 时返回 0.0% 避免除零）
- ✅ CLI 入口未破坏（qingqiu --help 仍可用）

## 已知后续工作（不在 M10 MVP 范围）

- **S10.2 偏好学习**：用户纠正 → personality.yaml 自动更新
- **S10.3 vault 反哺**：核心概念 → L2 user.md
- **S10.5 偏好冲突检测**：冲突偏好触发提问而非自作主张
- **S10.6 growth.enabled 持久化**：当前走 env var；后续可写 config.yaml 或 L3 fact
- **weekly 报告 LLM 增强**：纯统计模板 → LLM 总结（"本周亮点 / 风险 / 建议"）
- **调度器**：M10 MVP 触发靠手工；后续接 cron / hermes 任务总线
- **历史周报汇总**：每月/季度合并 weekly → 长期趋势

## Lessons / 注意事项

1. **done 状态严格匹配**：`status == "done"` 是唯一"完成"状态。`archived` 单独计（已归档但不算完成率分子），`pending` 算未完成。其他 status（`completed` / 自定义）会被忽略。
2. **完成率口径**：分子 = done，分母 = total；archived **不计入**完成率（避免"归档=完成"的混淆）。
3. **top facts 数量 = 实际数量**：如果 L3 不足 5 条，markdown 标题写 `Top 3` 而不是 `Top 5`（实际渲染）。
4. **Windows sqlite 锁**：`tempfile.TemporaryDirectory()` 退出时会触发 PermissionError，因为 SQLite 文件被 Windows 短时间持有。verify_m10.py 用 `ignore_cleanup_errors=True` 跳过清理（tmp 文件会被系统自动清理）。
5. **env vs 参数**：测试 fixture 一定要 monkeypatch `QINGQIU_GROWTH_ENABLED`，否则环境变量会跨测试泄漏。
6. **多次 reflect 不累积 history**：每次 reflect 全量覆盖（total/done/pending/archived），不是增量累积。如果产品要 history，需要单独 `reflect_history` 方法（M10 后续切片）。
7. **growth.enabled 默认 True**：避免破坏性默认。如果用户明确想关 → 设 `QINGQIU_GROWTH_ENABLED=false`。
8. **不加 personality 段**：MVP 模板只含任务汇总 + top L3 facts；personality 偏好变化分析是 S10.2 范围。
9. **并行 agent 风险**：本次 M10 父会话派了 9+ 个 sibling sessions 同时跑同一 worktree。文件被多个 worker 反复覆盖。最终采纳 on-disk 版本（config.py + reflect.py + weekly.py），重写 tests 对齐 API。

---

✅ M10 完成 · 508/508 pytest PASS · 32 growth tests · 4 verify scenarios PASS