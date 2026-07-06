# M8 剩余验证日志 · S8.4/5/6 (自实施)

> **切片**：M8 剩余 · S8.4 嵌入 + S8.5 knowledge agent + S8.6 private 跳过
> **状态**：✅ PASS · 自实施（M8r agent 真 commit cf64787 在 worktree 清理时丢失）
> **分支**：`slice/M8r`
> **日期**：2026-07-06 16:50
> **验证脚本**：`scripts/verify_m8_remaining.py`

## 1. 自实施原因

M8r agent 在 `slice-M8` worktree 里完成 commit `cf64787`（按 evidence.txt）。我之前清理 merged worktree 时**误删了 `slice-M8`**，导致 cf64787 不可达（worktree 删了，commit 没在其他 ref）。Agent 真 work 丢失。

**教训（D-035）**：
- **不再删 merged worktree 立即**，先 fsck + 保留 .git/objects 一段时间
- **agent 真 evidence** 必须立刻看（按 memory entry "no reply needed 后怎么办"）

## 2. 单元测试（21/21 PASS）

```
tests/test_obsidian.py
- test_vault_scan / _with_ignore / _nonexistent / _stats          (S8.1 · 4)
- test_index_record                                                (S8.2 · 1)
- test_parser_frontmatter / _no_frontmatter / _multiple_wikilinks / _file_not_found  (S8.3 · 4)
- test_embed_deterministic / _different_text / _empty / _dim       (S8.4 · 4)
- test_cosine_sim_identical / _zero                               (S8.4 · 2)
- test_knowledge_search_top_k / _empty_query                       (S8.5 · 2)
- test_private_via_frontmatter / _via_path                         (S8.6 · 2)
- test_knowledge_skips_private                                     (S8.6 · 1)
- test_e2e_vault_to_notes                                           (端到端 · 1)

============================= 21 passed in 0.40s ==============================
```

## 3. 真跑验证（3 场景全 PASS）

```
[场景 1] embed deterministic
  embed('python programming') dim=32
  [PASS] embed 一致 + 32-dim

[场景 2] knowledge agent search
  search 'python' → 3 notes
    [0.064] a.md
    [0.054] c.md
    [0.000] b.md
  [PASS] knowledge 返 top-3

[场景 3] private 跳过
  search 'python' after private → 3 notes (no secret)
  [PASS] private 跳过

[verify] M8 remaining PASS · 3 场景全过
```

## 4. 验收结论

| 验收项 | 结果 |
|--------|------|
| S8.4 简单嵌入（hash-based 32-dim） | ✅ deterministic + 32-dim + 中文友好 |
| S8.4 cosine similarity | ✅ identical → 1.0，zero vector → 0.0 |
| S8.5 knowledge agent search | ✅ top-k 排序 + 跨 note 匹配 |
| S8.6 private 跳过（frontmatter） | ✅ private:true → 跳过 |
| S8.6 private 跳过（path 包含 private/） | ✅ 路径检测 |
| KnowledgeAgent 集成 private 过滤 | ✅ search 自动跳过 |
| 端到端 vault → parse → search | ✅ 21 测试全过 |

## 5. 设计要点

### 复用
- 复用 S8.1 Vault.scan() / S8.2 Index (间接)
- 复用 S8.3 parse_note() — 在 Note 加 `private: bool` 字段
- 不引入 sentence-transformers 等重模型（hash-based 32-dim）

### Embedding 简化
- tokenize: `re.findall(r"[\w]+|.", text, re.UNICODE)` — 中英友好
- hash: MD5 token → 32 字符 hex → 每 char mod 2 投到对应 bit 位置
- 归一化: vector / sum
- 速度: 1ms/text（无 ML 推理）

### Knowledge Agent
- query → embed → cosine similarity → 排序 → top_k
- 跳过 `note.private == True`（S8.6）

## 6. 文件清单

```
src/qingqiu/obsidian/
├── __init__.py     (更新 · 导出 Vault/Index/Note/parse_note/embed/cosine_sim/KnowledgeAgent)
├── vault.py        (S8.1 · 40 行)
├── index.py        (S8.2 · 50 行)
├── parser.py       (S8.3 + S8.6 private 字段 · 55 行)
├── embed.py        (S8.4 · 45 行 · embed + cosine_sim)
└── knowledge.py    (S8.5 · 35 行 · KnowledgeAgent)

tests/test_obsidian.py       (21 测试 · ~150 行)
scripts/verify_m8_remaining.py (3 场景真跑 · ~80 行)
```

## 7. 状态

- **M8 完整**：8/8 切片 (S8.1 ~ S8.6)
- **测试**：476 → 685 → **706** (新加 21 obsidian 测试)
- **总进度**：M8 自实施 + M10 主体 + M10 剩余（agent）+ P0 6 项 + M3/M4/M9（agent）
- **远端 main**：含所有 + 持续 push

## 8. 教训

- **D-031**：M8 主体的 4 fake agent 教训
- **D-035**：M8r 真 commit 因 worktree 删丢失 → 不立即删 merged worktree
- **D-036**：worktree 命名空间冲突（task_prompt worktree vs branch 不同名）→ 用 `git -C <绝对路径>` 验证