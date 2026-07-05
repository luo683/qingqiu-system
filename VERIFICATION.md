# VERIFICATION · 清秋验收纪律

> **状态：** v0.3.0 · 2026-07-05 立规则
> **作者：** Mavis（用户明确要求）
> **本文件性质：** **强约束**。违反 = slice 不算完成 = 不许 commit / merge。

---

## 1. 核心规则（一句话）

**每个 slice 完成后，必须真实端到端跑通功能。不是 mock 通过、不是代码读完说"应该能跑"、不是单元测试绿了就完事 —— 必须真打、看到真实输出、记录证据。**

---

## 2. 为什么这条规则存在

S1.2 期间我们犯了一个典型错误：

> 写了 45 个 mock 测试，**全部通过**，git 提交了 "S1.2 完成 ✅"。
> 用户问"之前做的功能可以实现吗"，才发现**没有任何一个 provider 真的打过 API**。
> 我们的"完成"是建立在 mock 上的假完成。

这条规则就是把这个教训固化：**mock 通过 ≠ 真跑通**。

---

## 3. 每个 slice 的验收清单（强制 5 步）

每个 slice 完成时，**必须**按顺序跑完这 5 步才算"完成"：

### Step 1 · 单元测试（必须有，但不够）

```bash
uv run pytest tests/ -v
```

✅ 绿了再走 Step 2。

### Step 2 · 端到端验收脚本（`scripts/verify_s<n>_<m>.sh`）

```bash
bash scripts/verify_s<n>_<m>.sh
```

✅ 脚本里所有步骤都通过。

### Step 3 · **真实环境跑一次（这是关键）**

- **代码类 slice**：真跑 `qingqiu <子命令>`，看到真实输出（不是 mock 的）
- **LLM 类 slice**：真打 API，至少一个 provider 返回真实响应
- **语音类 slice**：真录音 → whisper 转写 → 看到转写文字
- **Obsidian 类 slice**：真扫一个 vault → 看到 wikilink / 标签解析结果
- **UI 类 slice**：截图 + Tauri 窗口实测

**"真"的定义：** 调用真实服务、看到真实响应、记录下来。

### Step 4 · 记录证据

每次真跑后，在 commit message 里**明确写**：

```
feat(core): S<n>.<m> ...

真跑验证（[日期] [环境]）：
- 命令：qingqiu llm test anthropic
- 输入：ANTHROPIC_API_KEY=<有>
- 输出：Hello from anthropic
- 响应时长：1.2s
- token 用量：input=8, output=4
```

或者在 `docs/verification/S<n>_<m>.log` 里附完整输出。

### Step 5 · 用户验收

告诉用户"真跑通了"，等用户确认。

---

## 4. 三种"真跑"的环境选择

按从轻到重：

| 方式 | 成本 | 适用场景 |
|------|------|---------|
| **本地 Ollama** | ~5GB 下载 + 后台跑服务 | LLM / 嵌入 / 不想花 API 钱 |
| **云端 API** | 每次几美分 | 不想本地跑 / 测生产级 provider |
| **混合** | 取决于 | Ollama 跑默认，复杂任务切云端 |

### 4.1 本地 Ollama 启动步骤

```powershell
# 1. 下载安装 Ollama（https://ollama.com/download）
winget install Ollama.Ollama

# 2. 启动服务（后台跑）
ollama serve

# 3. 下载模型（首次 ~5GB）
ollama pull llama3.1
ollama pull nomic-embed-text

# 4. 验证
curl http://127.0.0.1:11434/api/version

# 5. 跑清秋测试
uv run qingqiu llm test ollama
```

### 4.2 云端 API 启动步骤

```powershell
# 1. 注册 / 充值（最小 $5）
#    - Anthropic: https://console.anthropic.com/
#    - OpenAI:    https://platform.openai.com/

# 2. 生成 API key

# 3. 设环境变量（PowerShell 当前 session）
$env:ANTHROPIC_API_KEY = "sk-ant-xxx"
# 或 OpenAI
$env:OPENAI_API_KEY = "sk-xxx"

# 4. 跑清秋测试
uv run qingqiu llm test anthropic
```

---

## 5. 真实跑不通时怎么办

**不要**：跳过这一步、隐藏问题、用 mock 凑数。

**要**：
1. 立刻告诉用户"X 切片真跑失败了"
2. 把失败原因写进 PROJECT.md §4 已知问题
3. 在 commit 里用 `!` 标记（`feat!: S1.2 partial ...`）
4. 切片状态标 `[!] blocked`

**绝不**："看似通过了" "应该没问题" "下次再说"。

---

## 6. 真跑证据存哪

```
docs/verification/
├── S1.1_cli.log          # S1.1 CLI 真跑输出
├── S1.2_llm_ollama.log   # S1.2 Ollama 真跑输出
├── S1.2_llm_anthropic.log # S1.2 Anthropic 真跑输出
└── ...
```

格式：

```markdown
# S<n>.<m> 真跑日志

## 环境
- 日期：2026-07-05
- Python：3.12.11
- Ollama：0.5.x
- 模型：llama3.1 / nomic-embed-text

## 命令
\`\`\`
qingqiu llm test ollama
\`\`\`

## 输出
\`\`\`
[test] 初始化 ollama provider ...
[test] 初始化 OK (default_model=llama3.1)
[test] 发送测试 prompt ...
[OK] ollama 响应：
  content: 'Hello from ollama'
  model: llama3.1
  usage: input=8, output=4
\`\`\`

## 结论
✅ 通过
```

---

## 7. 与 AGENTS.md / PROJECT.md / CHANGELOG.md 的关系

- **AGENTS.md §2.9** 加本规则（"必须真跑，不只 mock"）
- **PROJECT.md §6 决策记录** 加 D-011
- **CHANGELOG.md** 每个 slice 条目加"真跑证据"
- 每个 commit message 加 "真跑验证" 段

---

## 8. 例外情况

只有这 3 种情况可以"暂时不真跑"：

1. **环境不可用**（如网络隔离、不允许装服务）—— 必须有用户确认 + 文档化
2. **依赖外部资源**（如真 Obsidian vault、用户机器配置）—— 列出"待用户配合真跑"
3. **纯文档 slice**（如更新 PRD/CHANGELOG）—— 文档一致性由 git diff 验证

**任何例外都必须在 commit message 里写明"为什么这次不真跑"。**

---

## 9. 历史教训

| 日期 | 切片 | 教训 |
|------|------|------|
| 2026-07-05 | S1.2 | mock 通过 45/45 测试但没真打过 API，被用户问 "之前做的功能可以实现吗" 时才发现 |

---

**这条规则不妥协。** 任何违反的 PR = 退回重做。

🤖 Generated with Claude Code