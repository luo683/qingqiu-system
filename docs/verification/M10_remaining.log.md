# M10 剩余切片 · 验收记录

## 切片范围

PRD §9 自我成长机制 · 5 条学习路径中的剩余 4 个 MVP 切片（S10.2 + S10.3 + S10.5 + S10.6）。

| 维度 | 描述 |
| --- | --- |
| 切片 | M10 自我成长 (S10.2 preference + S10.3 vault_feed + S10.5 conflict + S10.6 growth_config) |
| 分支 | slice/M10r |
| Worktree | `E:\MiniMax Code Work Space\qingqiu-system\.worktrees\slice-M10r` |
| 父切片 | S10.1 Reflector + S10.4 WeeklyReport（已合入，580f511） |
| 后续切片 | M10 完成后 → 5 条学习路径收口（仅剩 S10.7 LLM 增强） |

## 交付物

| 文件 | 角色 |
| --- | --- |
| `src/qingqiu/growth/__init__.py` | public API：导出所有 growth 类（含 4 个新增） |
| `src/qingqiu/growth/config.py` | **修改**：添加 `is_enabled()` 方法（复用既有 `GrowthConfig`） |
| `src/qingqiu/growth/growth_config.py` | **新增**：S10.6 canonical 入口（re-export `GrowthConfig`） |
| `src/qingqiu/growth/preference.py` | **新增**（S10.2）· `PreferenceLearner` · `learn(preference) → personality.yaml` |
| `src/qingqiu/growth/vault_feed.py` | **新增**（S10.3）· `VaultFeeder` + `parse_note(path)` |
| `src/qingqiu/growth/conflict.py` | **新增**（S10.5）· `ConflictDetector` · `detect(history) → L3` |
| `tests/growth/test_preference.py` | **新增** · 13 测试 |
| `tests/growth/test_vault_feed.py` | **新增** · 18 测试 |
| `tests/growth/test_conflict.py` | **新增** · 12 测试 |
| `tests/growth/test_growth_config.py` | **新增** · 15 测试 |
| `scripts/verify_m10_remaining.py` | **新增** · 4 场景 / 31 断言 |
| `docs/verification/M10_remaining.log.md` | **新增** · 本文件 |

**未修改任何已有模块**（除 `config.py` 加 `is_enabled()` + `__init__.py` 加导出）：
`llm/ memory/ cli/ security/ personality/ chat/ planner/ daemon/ router/ voice/ im/ obsidian/ ui/ config/` 全部 0 改动。

## 数据结构

### PreferenceLearner（S10.2）

```python
learner = PreferenceLearner(path=personality_yaml_path, growth=growth_config)
new_prompt = learner.learn("不写 emoji")
# → personality.yaml system_prompt 末尾追加 "- 不写 emoji"（list-style）
# → 幂等：同 preference 重复 learn 不重复追加
# → 平铺 / 嵌套 personality: YAML 格式都支持
```

### VaultFeeder（S10.3）

```python
feeder = VaultFeeder(l2=l2_memory, growth=growth_config)
value = feeder.feed(vault_root)   # Path 或 str
# → 递归扫 vault_root/**/*.md
# → parse_note 解析 frontmatter `tags: [a, b, c]` + 正文 `#tag`
# → 去重 + 字母排序 → join "," → L2.set("auto_concepts", value)
```

### parse_note（独立函数 / S10.3）

```python
def parse_note(path: Path) -> set[str]:
    """frontmatter tags: [...] + 正文 #tag → set (去重)"""
```

### ConflictDetector（S10.5）

```python
detector = ConflictDetector(l3=l3_memory, growth=growth_config)
conflicts = detector.detect([("emoji", "no"), ("emoji", "yes")])
# → L3 写入 conflict_emoji = "no→yes"
# → 返回 [{"key", "old", "new", "conflict_key", "detected_at"}, ...]
```

### GrowthConfig.is_enabled()（S10.6）

```python
gc = GrowthConfig()  # 缺省 enabled=True
gc.is_enabled()  # True（所有 growth 函数的入口短路判定）
```

## MVP 行为

| 触发 | 结果 |
| --- | --- |
| `PreferenceLearner.learn("不写 emoji")` | personality.yaml system_prompt 追加 `- 不写 emoji` |
| 重复 `learn("不写 emoji")` | 不重复追加（幂等） |
| `VaultFeeder.feed(vault_root)` | L2 写入 `auto_concepts = "tag1,tag2,..."`（去重 + 字母排序） |
| `ConflictDetector.detect([(k,v1),(k,v2)])` | L3 写入 `conflict_<k> = v1→v2` |
| `growth.enabled=False` | 所有 growth 函数立即返 None / []，不读不写 |

## 验证结果

### 单元测试

```
$ PYTHONPATH=src/.worktrees/slice-M10r/src uv run pytest tests/growth/ -v
============================= 90 passed in 1.11s ==============================
```

覆盖：

| 测试文件 | 测试数 | 内容 |
| --- | --- | --- |
| `test_reflect.py`（既有） | 13 | Reflector 5 keys 写入 / summarize / 幂等 / None / now 注入 / ReflectKeys |
| `test_weekly.py`（既有） | 19 | GrowthConfig / WeeklyReport / ISO 周 / 时钟注入 / top facts / 多 reflect 累积 |
| `test_preference.py` | 13 | disabled / 空 / 平铺+嵌套 YAML / 幂等 / 累积 / 损坏 / 中文+emoji / 默认文件创建 |
| `test_vault_feed.py` | 18 | disabled / 不存在 / 文件 / frontmatter / inline / 混合 / 递归 / 排序 / 去重 / 自定义 key / parse_note / collect_tags |
| `test_conflict.py` | 12 | disabled / 空 / 单冲突 / 多冲突 / 多 key 独立 / 3-way / 累计 / detected_at / 顺序 |
| `test_growth_config.py` | 15 | re-export / is_enabled / env var / 优先级 / 入口短路 4 类 |
| **总计** | **90** | 32 既有 + 58 新增（远超 ≥15 目标） |

### 全量回归

```
$ PYTHONPATH=src/.worktrees/slice-M10r/src uv run pytest tests/ -q --no-header
======================= 735 passed, 1 warning in 11.56s =======================
```

不回归：原 677（M10 base，含 S10.1+S10.4 全部） + 新 58 = 735（远超 ≥685 目标）。

### 端到端验证脚本

```
$ PYTHONPATH=src/.worktrees/slice-M10r/src uv run python scripts/verify_m10_remaining.py
[verify] M10 剩余切片 · S10.2 + S10.3 + S10.5 + S10.6

[scenario 1] M10-8: 用户说 '不写 emoji' → personality.yaml system_prompt 追加 '不写 emoji'
  [PASS] learn() 返非空 prompt
  [PASS] prompt 含 '不写 emoji'
  [PASS] prompt 含 bullet 风格
  [PASS] prompt 保留原内容
  [PASS] personality.yaml 持久化 '不写 emoji'
  [PASS] 幂等：重复 learn 不重复追加
  [PASS] 第二条 preference '回复简短' 累积

[scenario 2] M10-9: vault feed → 抓所有 tag → 写入 L2 'auto_concepts'
  [PASS] feed() 返非空
  [PASS] 结果按字母排序
  [PASS] 含 'python'
  [PASS] 含 'fastapi'
  [PASS] 含 'arch'
  [PASS] 含 'mvp'
  [PASS] 含 'security' (from inline #tag)
  [PASS] L2 写入 auto_concepts

[scenario 3] M10-10: 同一 preference 多次不同值 → 触发 conflict (L3)
  [PASS] 返回 2 个冲突 (emoji + tone)
  [PASS] L3 conflict_emoji = no→yes
  [PASS] L3 conflict_tone = formal→casual
  [PASS] L3 无 conflict_lang (单值无冲突)
  [PASS] 冲突 keys = [emoji, tone]
  [PASS] 冲突项含 key/old/new/conflict_key
  [PASS] conflict_key 格式 = conflict_<key>

[scenario 4] M10-11: growth.enabled=False → 所有 growth 函数返 None/empty
  [PASS] PreferenceLearner.learn() 返 None
  [PASS] personality.yaml 未被修改
  [PASS] VaultFeeder.feed() 返 None
  [PASS] L2 未被写入
  [PASS] ConflictDetector.detect() 返 []
  [PASS] L3 未被写入 conflict_*
  [PASS] PreferenceLearner.is_enabled() = False
  [PASS] VaultFeeder.is_enabled() = False
  [PASS] ConflictDetector.is_enabled() = False

[verify] M10 remaining PASS · 31 assertions across 4 scenarios
```

**4/4 场景全部 PASS（31 断言）。**

### CLI 不破坏

原 S10.1+S10.4 verify_m10.py 同步验证通过（29 断言 · 4/4 场景），CLI 入口 `qingqiu --help` 不受影响。

## 关键设计

1. **复用最大化**：
   - `PreferenceLearner` 复用 `qingqiu.personality.DEFAULT_PERSONALITY_PATH` + 自身 YAML 读/写
   - `VaultFeeder` 复用 `qingqiu.memory.l2.L2UserMemory`（key=value 文件）
   - `ConflictDetector` 复用 `qingqiu.memory.l3.L3FactsMemory`（SQLite facts）
   - 4 个新模块全部 `is_enabled()` 短路（统一入口约定）
2. **parse_note 极简实现**：不引入 obsidian 模块依赖（约束禁止跨模块触碰），自含 frontmatter + inline `#tag` 解析
3. **is_enabled() 一致性**：所有 4 个新模块 + WeeklyReport 都在入口先 `is_enabled()` 检查，确保关开关时绝对零副作用
4. **幂等 everywhere**：
   - `learn()` 同 preference 重复不追加（去重）
   - `feed()` 多次写入 L2 覆盖
   - `detect()` 多次写 L3 覆盖（INSERT ON CONFLICT DO UPDATE）
5. **YAML 结构保留**：`PreferenceLearner` 读时识别 `personality:` 嵌套包装，写时原样回写（不破坏既有结构）
6. **frontmatter EOF 兼容**：`_FRONTMATTER_RE` 允许 `---` 行后是换行或 EOF（测试用文件常省略 body）
7. **测试隔离**：每个 test 用 `tmp_path` fixture + `monkeypatch.delenv("QINGQIU_GROWTH_ENABLED")`，verify 脚本用 `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)`（Windows sqlite 锁兼容）
8. **不调 LLM**：4 个新模块全部纯本地操作（YAML / 正则 / 集合运算 / 文件读写 / SQLite）
9. **CLI 入口未破坏**：`__init__.py` 新增 4 个 export，旧 import 路径 `from qingqiu.growth.config import GrowthConfig` 仍兼容
10. **约束遵守**：仅写 `src/qingqiu/growth/` + `tests/growth/` + `scripts/` + `docs/verification/`（**零**触碰其他模块）

## 边界覆盖

- ✅ preference disabled → learn() 返 None，不创建文件
- ✅ preference 空 / 空白 → 返 None
- ✅ preference YAML 损坏 → 返 None，不崩
- ✅ preference 文件不存在 → 自动走 schema default 后追加
- ✅ preference 中文 / emoji → 正确写入不乱码
- ✅ preference 嵌套 personality: YAML → 追加成功，结构保留
- ✅ vault disabled → feed() 返 None
- ✅ vault 不存在 / 是文件 → 返 None
- ✅ vault 为空 → 写空字符串
- ✅ vault frontmatter tags + 正文 #tag → 去重 + 排序
- ✅ vault 递归扫所有子目录
- ✅ conflict disabled → detect() 返 []
- ✅ conflict 空 history → 返 []
- ✅ conflict 同 key 同值 → 不算冲突
- ✅ conflict 同 key 不同值 → 写 L3
- ✅ conflict 多 key 各自独立
- ✅ conflict 多次 detect → L3 覆盖
- ✅ growth.enabled=False → 4 个新模块全部返 None/empty
- ✅ is_enabled() 默认 True
- ✅ env `QINGQIU_GROWTH_ENABLED=false/0/no/off` → 全部识别为关

## 已知后续工作（不在 M10 剩余 MVP 范围）

- **S10.7 LLM 增强**：当前为纯本地；后续可接 LLM 做 preference 语义归一化、conflict 自然语言解释
- **schedule 自动化**：M10 触发靠手工调用 / 外部 import；后续接 cron / hermes 任务总线
- **vault 增量扫描**：当前全量扫，后续可记 mtime 增量
- **conflict UX**：当前写 L3 后无 UI 提示，后续可加通知 / 提问澄清
- **preference 撤销**：当前只追加，后续可加 unlearn / 软删

## Lessons / 注意事项

1. **is_enabled() 命名优于 .enabled 字段**：直接 `if not gc.is_enabled(): return None` 比 `if not gc.enabled` 更易读，且未来如果 enabled 变 property（如带时区 / 带计时器）也能无缝切换
2. **YAML 写入不保留注释**：`yaml.safe_dump` 会丢注释，但 MVP 够用；如要保留可用 ruamel.yaml（MVP 不引入）
3. **frontmatter EOF 兼容**：测试常用 `---\ntags: [x]\n---`（无 body），正则必须允许 `---` 后是 EOF
4. **parse_note inline #tag 字符集**：用 `[A-Za-z0-9_\-/]+` 既能匹配 `python`、`fastapi`，又能正确跳过中文标题（"这是标题" 含空格 + 中文字符）
5. **conflict 顺序 = history 首次出现顺序**：对 UX 重要（用户最后说的 key 排最后 vs 排最前，UX 差别很大）
6. **三方模块互不依赖**：S10.2/S10.3/S10.5 三个模块互不 import，只通过 `growth_config.GrowthConfig` 共享开关；避免隐式耦合
7. **测试时一定 monkeypatch env**：env 跨进程泄漏是 pytest 常见 bug；本批测试全部用 `_isolate_env` autouse fixture 兜底

---

✅ M10 剩余完成 · 735/735 pytest PASS · 90 growth tests (58 新增) · verify_m10_remaining 4/4 PASS
