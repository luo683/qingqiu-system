# testing.md · 测试规范

> **状态：** v0.3.0
> **本文件性质：** 测试**强制规范**。所有测试必须符合这里的规则。

---

## 1. 测试策略

### 1.1 测试金字塔

```
        /\
       /  \        E2E（少量 · 关键路径）
      /────\       → Playwright（v2 再考虑，v1 暂不上）
     /      \
    /────────\     集成测试（中等 · 跨模块）
   /          \    → pytest
  /────────────\
 /              \  单元测试（大量 · 纯函数 / 单类）
/________________\ → pytest + Vitest
```

### 1.2 v1.0 测试范围

| 类型 | 工具 | 覆盖目标 |
|------|------|---------|
| **Python 单元测试** | `pytest` + `pytest-asyncio` | LLM 抽象 / Router / Planner / Confirm / 私密识别 / Hermes 协议 / Memory |
| **Python 集成测试** | `pytest`（起 daemon） | IPC 链路 / 文件总线 / vault 索引 |
| **React 组件测试** | `Vitest` + `React Testing Library` | 关键组件渲染 / 交互 / 状态 |
| **性能测试** | `pytest-benchmark` | whisper / TTS / 嵌入 / SQLite |
| **手动 e2e** | 你 + 我 | 真实场景验收（每个 M 结束后） |

**不上自动化 e2e**（Playwright）：单人项目，性价比低。

---

## 2. Python 测试规范

### 2.1 文件命名

```
src/qingqiu/llm/base.py
tests/unit/llm/test_base.py        # 对应测试
```

### 2.2 测试函数命名

```python
def test_<unit>_<scenario>_<expected>():
    """测试 <单元> 在 <场景> 下应该 <期望结果>"""
    
# ✅ 推荐
def test_router_with_greeting_returns_chitchat_intent():
def test_router_with_empty_text_raises_value_error():
def test_confirm_with_dangerous_command_returns_extra_warning():

# ❌ 禁止
def test_router():           # 太宽
def test_it_works():         # 模糊
def test_router_case_1():    # 编号命名
```

### 2.3 测试结构（AAA 模式）

```python
def test_router_with_greeting_returns_chitchat_intent():
    # Arrange（准备）
    router = Router(llm=mock_llm)
    text = "你好"
    
    # Act（执行）
    intent = router.intent(text)
    
    # Assert（断言）
    assert intent.action == "chitchat"
    assert intent.confidence > 0.8
```

### 2.4 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_func()
    assert result == expected
```

### 2.5 Mock

```python
from unittest.mock import AsyncMock, MagicMock

def test_with_mock_llm():
    mock = AsyncMock()
    mock.complete.return_value = '{"action": "test"}'
    
    router = Router(llm=mock)
    intent = router.intent("hi")
    
    mock.complete.assert_awaited_once()
    assert intent.action == "test"
```

### 2.6 Fixture

```python
import pytest

@pytest.fixture
def sample_task():
    return Task(
        id="TASK-001",
        title="测试任务",
        status="PENDING",
    )

def test_task_complete(sample_task):
    sample_task.complete()
    assert sample_task.status == "COMPLETED"
```

### 2.7 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("你好", "chitchat"),
    ("读 file", "code_read"),
    ("删 file", "code_delete"),
])
def test_router_intent_recognition(input, expected):
    router = Router(llm=mock_llm)
    intent = router.intent(input)
    assert intent.action == expected
```

---

## 3. React 测试规范

### 3.1 文件命名

```
src/features/TaskList/TaskCard.tsx
src/features/TaskList/TaskCard.test.tsx    # 同目录 .test.tsx
```

### 3.2 组件测试模板

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { TaskCard } from './TaskCard'

describe('TaskCard', () => {
  const mockTask = {
    id: 'TASK-001',
    title: '测试任务',
    status: 'PENDING' as const,
  }

  it('renders task title', () => {
    render(<TaskCard task={mockTask} onConfirm={vi.fn()} />)
    expect(screen.getByText('测试任务')).toBeInTheDocument()
  })

  it('calls onConfirm when confirm button clicked', async () => {
    const handleConfirm = vi.fn()
    const user = userEvent.setup()
    
    render(<TaskCard task={mockTask} onConfirm={handleConfirm} />)
    await user.click(screen.getByRole('button', { name: '确认' }))
    
    expect(handleConfirm).toHaveBeenCalledWith('TASK-001')
  })

  it('expands detail when expand button clicked', async () => {
    const user = userEvent.setup()
    render(<TaskCard task={mockTask} onConfirm={vi.fn()} variant="full" />)
    
    await user.click(screen.getByRole('button', { name: '展开' }))
    
    expect(screen.getByText(/task 详情/)).toBeVisible()
  })
})
```

### 3.3 Hook 测试

```tsx
import { renderHook, act } from '@testing-library/react'
import { useCounter } from './useCounter'

describe('useCounter', () => {
  it('increments', () => {
    const { result } = renderHook(() => useCounter())
    act(() => result.current.increment())
    expect(result.current.count).toBe(1)
  })
})
```

---

## 4. 性能测试（pytest-benchmark）

```python
def test_whisper_transcription_speed(benchmark):
    audio = load_test_audio("test_10s.wav")
    
    result = benchmark(whisper.transcribe, audio)
    
    assert result is not None
    # 自动断言：跑多次取中位数

def test_sqlite_query_speed(benchmark):
    db = setup_test_db()
    benchmark(db.query_tasks, status="PENDING")
```

**基线记录：** 每个性能关键函数跑一次 `pytest-benchmark`，基线存 `benchmarks/` 目录。

**回归检测：** 后续切片导致回归 > 20% 必须修复。

---

## 5. 验收脚本（每个切片必做）

每个切片完成时跑一个验收命令，**能跑通 = 切片完成**。

### 5.1 验收命令示例

```bash
# S1.1：CLI 骨架
uv run qingqiu --version       # 输出版本号
uv run qingqiu --help          # 输出帮助

# S1.2：LLM 抽象层
uv run qingqiu llm test anthropic   # 测试 anthropic provider
uv run qingqiu llm test ollama      # 测试 ollama provider

# S3.4：语音 → CLI 链路
uv run qingqiu voice test "读 file 写 hello"

# S5.5：私密处理
uv run qingqiu security test-private
```

### 5.2 验收脚本

每个 slice 配套一个 `scripts/verify_s<n>_<m>.sh`（或 `.ps1`）：

```bash
#!/bin/bash
# scripts/verify_s1_1.sh
set -e
echo "[verify] S1.1: 项目骨架与配置入口"

uv run qingqiu --version || (echo "FAIL: version not working" && exit 1)
uv run qingqiu --help || (echo "FAIL: help not working" && exit 1)

echo "[verify] S1.1 PASS"
```

---

## 6. 测试覆盖率

### 6.1 v1.0 不强制覆盖率

单人项目，性价比低。但**关键路径必须有测试**：

- LLM 抽象层：每个 provider 必须有 test
- Router / Planner / Confirm：必须有 test
- 私密识别三道闸：必须有 test
- Hermes 协议：必须有 test（向后兼容）
- Memory L1/L2/L3：必须有 test

### 6.2 看覆盖率（参考）

```bash
uv run pytest --cov=qingqiu --cov-report=term-missing
```

---

## 7. 测试数据

### 7.1 Fixture 文件

```
tests/
├── fixtures/
│   ├── sample_vault/        # 测试用 vault
│   ├── sample_voice.wav     # 测试用音频
│   └── sample_tasks.json    # 测试用任务
```

### 7.2 临时数据

用 `tmp_path` fixture（pytest 内置）：

```python
def test_creates_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    create_config(config_path)
    assert config_path.exists()
```

---

## 8. CI / CD

### 8.1 v1.0 不上 CI

单人项目，本地跑测试就行。

### 8.2 v2 考虑

- GitHub Actions
- 跑 pytest + Vitest
- 自动 lint + type check

---

## 9. 测试反例（**禁止**）

```python
# ❌ 无断言
def test_something():
    do_thing()

# ❌ 测实现细节
def test_private_method():
    obj._private_method()  # 不应该测私有

# ❌ 测试依赖外部服务（无 mock）
def test_real_llm_call():
    response = openai.Completion.create(...)  # 慢 + 不稳定

# ❌ 测试代码有逻辑
def test_with_logic():
    if some_condition:
        assert ...
    # 拆分测试
```

---

## 10. 验收清单（PR 提交前）

- [ ] 所有新代码有对应测试
- [ ] 所有测试通过
- [ ] 关键路径无 mock 缺失
- [ ] 验收脚本能跑通
- [ ] 没有跳过测试（`@pytest.mark.skip` 除非有明确理由）
- [ ] 没有 print 调试（用 `assert` 或日志）

---

**测试规范 = 强约束。** 违反 = PR 退回。