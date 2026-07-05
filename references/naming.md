# naming.md · 命名规则 + 文件大小上限

> **状态：** v0.3.0
> **本文件性质：** 强制规范。任何代码 / 文件命名 / 大小不符合这里规则的，**PR 不许合入**。

---

## 1. 命名规则

### 1.1 Python

| 类型 | 风格 | 示例 | 备注 |
|------|------|------|------|
| 模块文件 | snake_case | `task_scheduler.py` | |
| 类 | PascalCase | `TaskScheduler` | |
| 函数 | snake_case | `schedule_task()` | |
| 异步函数 | snake_case + async | `async def fetch_task()` | |
| 变量 | snake_case | `task_id = "TASK-001"` | |
| 常量 | UPPER_SNAKE | `MAX_RETRIES = 3` | |
| 私有函数 / 变量 | _leading_underscore | `_internal_helper()` | |
| 抽象类 | ABC 后缀 | `LLMProvider(ABC)` | |
| Protocol | 后缀 Protocol | `AgentRunner(Protocol)` | |
| 异常 | Error 后缀 | `TaskNotFoundError` | |
| 类型别名 | PascalCase | `TaskDict = dict[str, Any]` | |

### 1.2 React / TypeScript

| 类型 | 风格 | 示例 | 备注 |
|------|------|------|------|
| 组件文件 | PascalCase.tsx | `TaskCard.tsx` | 一个组件一个文件 |
| Hook 文件 | camelCase.ts | `useTaskList.ts` | |
| 类型文件 | camelCase.ts | `types.ts` 或 `<feature>.types.ts` | |
| 函数组件 | PascalCase | `function TaskCard()` | |
| 类型定义 | PascalCase | `TaskCardProps` | |
| 接口 | I 前缀 **不用**（现代 TS 风格） | `TaskCardProps` | ❌ `ITaskCardProps` |
| 变量 | camelCase | `taskId = "TASK-001"` | |
| 常量 | UPPER_SNAKE | `MAX_RETRIES = 3` | |
| 事件处理 | handle + 名词 + 动词 | `handleTaskClick` | |
| 布尔变量 | is/has/should 前缀 | `isLoading` / `hasError` | |
| 私有函数 | _leading | `_formatDate()` | |
| CSS class | kebab-case | `.task-card` | |
| CSS 变量 | --prefix-name | `--qq-accent` | |

### 1.3 文件命名

| 类型 | 命名 | 示例 |
|------|------|------|
| Python 模块 | snake_case.py | `task_scheduler.py` |
| Python 测试 | test_<module>.py | `test_task_scheduler.py` |
| React 组件 | PascalCase.tsx | `TaskCard.tsx` |
| React Hook | use<X>.ts | `useTaskList.ts` |
| React 测试 | <Component>.test.tsx | `TaskCard.test.tsx` |
| 配置文件 | lowercase.yaml / .toml / .json | `config.yaml` |
| 文档 | PascalCase.md | `ARCH.md` |
| 脚本 | snake_case.py 或 .ps1 | `setup_env.py` |

### 1.4 命名反例（**禁止**）

- ❌ `taskCard.tsx`（应该是 `TaskCard.tsx`）
- ❌ `Task_Card.tsx`（下划线）
- ❌ `task-card.tsx`（kebab）
- ❌ `ITaskCardProps`（I 前缀过时）
- ❌ `do_task()` / `processData()` 这种模糊动词
- ❌ 单字母变量（除了循环里的 `i` / `j`）
- ❌ 拼音命名（`renwu_liebiao.py`）
- ❌ 缩写不明（`TskSch.py` 不如 `task_scheduler.py`）

---

## 2. 文件大小上限

| 类型 | 上限（行） | 超出处理 |
|------|----------|---------|
| **Python 模块** | **300** | 拆成多个模块 |
| **React 组件** | **200** | 拆组件 / 提取 hooks |
| **Python 测试文件** | 400 | 拆测试 |
| **React 测试文件** | 300 | 拆测试 |
| **单个 CSS 文件** | 200 | 拆 CSS Modules |
| **Markdown 文档** | 1500 | 拆文档 |
| **单个配置文件** | 200 | 拆配置 / 用 include |

### 2.1 拆分指引

#### Python 模块超 300 行

**症状：** 一个 `.py` 文件 > 300 行。

**拆法：**

```
# 原：scheduler.py (500 行)

scheduler/
├── __init__.py
├── core.py        # 主类（200 行）
├── strategy.py    # 策略类（100 行）
├── utils.py       # 工具函数（80 行）
└── types.py       # 类型定义（50 行）
```

#### React 组件超 200 行

**症状：** 一个 `.tsx` 文件 > 200 行。

**拆法：**

```tsx
// 原：TaskPanel.tsx (350 行)

// 拆成：
TaskPanel.tsx              # 主组件（100 行）
├── TaskPanelHeader.tsx    # 子组件（50 行）
├── TaskPanelList.tsx      # 子组件（80 行）
└── TaskPanelFilters.tsx   # 子组件（60 行）

// hooks 拆出来：
useTaskPanel.ts            # 业务逻辑 hook（80 行）
```

#### 测试文件超 400 行

**症状：** `test_X.py` 超过 400 行。

**拆法：**

```
tests/
├── test_task_create.py   # 创建相关
├── test_task_update.py   # 更新相关
└── test_task_query.py    # 查询相关
```

### 2.2 例外情况

| 例外 | 允许 |
|------|------|
| 自动生成的代码 | 不算行数 |
| `__init__.py` 重导出 | 不算 |
| 数据文件（fixture） | 不算 |
| 长字符串常量文件 | 不算 |

任何"超长但合理"的场景 → 提 PR 说明理由 + 团队 review。

---

## 3. 目录结构命名

| 目录 | 命名 | 示例 |
|------|------|------|
| Python 包 | snake_case | `qingqiu/core/` |
| React 组件目录 | PascalCase（顶层） / camelCase（子） | `components/TaskPanel/` |
| 工具目录 | _utils 后缀或 utils 目录 | `src/utils/` |
| 测试目录 | tests/ 或 __tests__/ | `src/__tests__/` |
| 配置目录 | config/ 或 settings/ | `config/` |
| 资源目录 | assets/ | `assets/` |
| 类型目录 | types/ | `types/` |

### 3.1 推荐目录结构（清秋前端）

```
src/
├── components/          # 通用组件
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── index.ts
│   ├── Card/
│   └── ...
├── features/            # 业务功能组件
│   ├── TaskList/
│   │   ├── TaskList.tsx
│   │   ├── TaskCard.tsx
│   │   ├── useTaskList.ts
│   │   └── index.ts
│   ├── KnowledgeGraph/
│   └── ...
├── hooks/               # 全局 hooks
├── lib/                 # 工具库
├── types/               # 全局类型
├── styles/              # 全局样式
├── App.tsx
└── main.tsx
```

---

## 4. 文件命名反例（**禁止**）

- ❌ `temp.py` / `test123.tsx` / `asdf.md`
- ❌ 中文文件名
- ❌ 空格文件名（`my file.tsx`）
- ❌ 大小写混乱（`TaskCard.TSX` / `taskcard.tsx`）
- ❌ 同名不同后缀（`config.json` + `config.yaml` 同时存在）

---

## 5. Git Commit 风格（Conventional Commits）

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type：**

| type | 含义 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 |
| `docs` | 文档 |
| `style` | 格式（不影响代码） |
| `refactor` | 重构（既不新功能也不修 bug） |
| `perf` | 性能 |
| `test` | 测试 |
| `chore` | 构建 / 工具 |
| `revert` | 回滚 |

**scope（可选）：** `core` / `agents` / `voice` / `ui` / `docs` / `references` 等

**示例：**

```
feat(core): add Router intent recognition

- LLM JSON mode output
- Rule-based fallback
- 10 sample intents tested

S2.2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

**命名 / 大小 / 目录 / commit 风格** = 强约束。违反 = PR 退回。