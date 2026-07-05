# components.md · 组件规范

> **状态：** v0.3.0
> **本文件性质：** React 组件**强制规范**。所有前端组件必须符合这里的规则。

---

## 1. 组件结构

### 1.1 标准文件结构

```tsx
// imports
import { useState } from 'react'
import type { TaskCardProps } from './types'

// types
interface LocalState { /* 仅本组件用的类型 */ }

// main component（PascalCase，必须有显式 return type）
export function TaskCard({ task, onConfirm }: TaskCardProps): JSX.Element {
  // 1. hooks（顺序稳定）
  const [expanded, setExpanded] = useState(false)
  
  // 2. derived state
  
  // 3. handlers（handle 前缀）
  const handleClick = () => setExpanded(!expanded)
  
  // 4. effects
  // useEffect(...)
  
  // 5. render
  return (
    <div className="task-card">
      {/* */}
    </div>
  )
}

// 6. subcomponents（仅本文件用的小组件，< 50 行）
function TaskCardHeader({ task }: { task: Task }) { /* */ }
```

### 1.2 必须遵守

- ✅ 一个文件一个组件（**单文件 ≤ 200 行**）
- ✅ 函数组件 + Hooks（不用 class 组件）
- ✅ 显式 return type（`JSX.Element`）
- ✅ props 类型必须显式定义（不内联）
- ✅ 默认 props 用解构默认值，不用 `defaultProps`
- ❌ 不用 `React.FC`（现代 TS 风格）
- ❌ 不用 `class` 组件
- ❌ 不用 `defaultProps`（React 18+ deprecated）
- ❌ 不用 `any`（用 `unknown` + 类型守卫）

---

## 2. Props 规范

### 2.1 Props 接口定义

```typescript
// ✅ 推荐：在组件文件顶部定义
interface TaskCardProps {
  task: Task
  onConfirm: (taskId: string) => void
  onCancel?: (taskId: string) => void  // 可选 props 用 ?
  variant?: 'compact' | 'full'        // 字符串字面量联合，不用 enum
  isLoading?: boolean                  // 布尔用 is/has/should 前缀
}

// ❌ 禁止：内联 props
function TaskCard({ task, onConfirm }: { task: Task; onConfirm: (id: string) => void }) { }

// ❌ 禁止：interface I 前缀
interface ITaskCardProps { }
```

### 2.2 Props 数量

- 一个组件 props ≤ 7 个
- 超 7 个 → 拆组件或用 composition（children / render props）

### 2.3 Props 反例

| 反例 | 为什么错 | 替代 |
|------|---------|------|
| `style?: object` | 太宽 | 用 Tailwind className |
| `onClick: Function` | 模糊 | `onClick: (id: string) => void` |
| `data: any` | any 不行 | `data: Task` |
| `variant: string` | 太宽 | `variant: 'compact' \| 'full'` |

---

## 3. State 规范

### 3.1 State 类型

```typescript
// ✅ 简单 state：直接 useState
const [count, setCount] = useState(0)
const [task, setTask] = useState<Task | null>(null)

// ✅ 复杂 state：用 useReducer
const [state, dispatch] = useReducer(taskReducer, initialState)

// ❌ 禁止：单个大 state 对象（除非真的需要）
const [state, setState] = useState({ count: 0, task: null, loading: false })
```

### 3.2 State 命名

- 状态：`isLoading` / `hasError` / `expanded`
- 更新：`setLoading` / `setExpanded`
- 不写 `data` / `value` 这种泛名

### 3.3 State 提升原则

- 多组件共享 → 提到最近公共父组件
- 全局共享 → 用 Zustand store（[styling.md §3](./styling.md) 暂未定义，待补）

---

## 4. 事件处理

### 4.1 命名

```typescript
// ✅ handle + 名词 + 动词
const handleTaskClick = (id: string) => { /* */ }
const handleConfirmPress = () => { /* */ }
const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => { /* */ }

// ❌ 动词开头
const clickTask = () => { }
const onConfirm = () => { }  // 这是 props 名，不是 handler 名
```

### 4.2 传 props vs 内部 handler

- 业务逻辑（Confirm / Delete）→ 用 props（父组件控制）
- 纯 UI 状态（展开 / 收起）→ 内部 state

```typescript
// ✅ 业务逻辑是 props
<TaskCard onConfirm={handleConfirm} />

// ✅ UI 状态是内部
const [expanded, setExpanded] = useState(false)
```

---

## 5. Hooks 规范

### 5.1 Hook 顺序

```typescript
function Component() {
  // 1. useState
  const [a, setA] = useState(0)
  
  // 2. useReducer
  const [b, dispatch] = useReducer(reducer, 0)
  
  // 3. useContext
  const ctx = useContext(MyContext)
  
  // 4. useRef
  const ref = useRef<HTMLDivElement>(null)
  
  // 5. useMemo / useCallback
  const value = useMemo(() => a * 2, [a])
  
  // 6. useEffect
  useEffect(() => { /* */ }, [])
  
  // 7. 自定义 hooks
  const { data } = useMyHook()
}
```

### 5.2 自定义 Hooks

```typescript
// ✅ 文件名 useXxx.ts，函数名 useXxx
// src/hooks/useTaskList.ts
export function useTaskList(projectId: string): {
  tasks: Task[]
  isLoading: boolean
  error: Error | null
  refresh: () => void
} {
  // ...
}
```

### 5.3 Hooks 反例

- ❌ 条件调用 hooks（`if (cond) { useState(...) }`）
- ❌ 循环里调用 hooks
- ❌ 不用 `useCallback` / `useMemo` 包所有函数（性能过度优化）

---

## 6. 组件分类

### 6.1 通用组件（components/）

无业务逻辑，可在任何项目复用：

- `Button` / `Input` / `Select` / `Checkbox`
- `Card` / `Modal` / `Drawer`
- `Tooltip` / `Toast` / `Popover`
- `Tabs` / `Accordion` / `Dropdown`
- `Progress` / `Spinner` / `Skeleton`
- `Avatar` / `Badge` / `Tag`

### 6.2 业务组件（features/）

有业务逻辑，依赖清秋后端：

- `TaskCard` / `TaskList` / `TaskDetail`
- `KnowledgeGraph` / `GraphNode`
- `ConfirmDialog` / `ConfirmInline`
- `VoiceIndicator` / `TranscriptionView`
- `PrivateAlert` / `RedactionView`

### 6.3 页面组件（pages/）

路由对应的顶层组件：

- `Dashboard` / `Tasks` / `Graph` / `Settings`

---

## 7. 组件文件模板

```tsx
import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { Task } from '@/types'

interface TaskCardProps {
  task: Task
  onConfirm: (taskId: string) => void
  variant?: 'compact' | 'full'
}

export function TaskCard({ task, onConfirm, variant = 'compact' }: TaskCardProps): JSX.Element {
  const [expanded, setExpanded] = useState(false)

  const handleClick = () => setExpanded(!expanded)
  const handleConfirm = () => onConfirm(task.id)

  return (
    <div className="task-card">
      <button onClick={handleClick} aria-label={expanded ? '收起' : '展开'}>
        <ChevronDown className={expanded ? 'rotate-180' : ''} size={16} />
        <span>{task.title}</span>
      </button>
      
      {expanded && variant === 'full' && (
        <div className="task-card__detail">
          {/* task 详情 */}
        </div>
      )}
      
      <button onClick={handleConfirm} aria-label="确认">
        确认
      </button>
    </div>
  )
}
```

---

## 8. 可访问性（**必做**）

- ✅ 所有交互元素有 `aria-label`
- ✅ 所有图片有 `alt`
- ✅ 表单 input 关联 `<label>`
- ✅ 键盘可达（Tab 顺序合理，Enter / Space 触发按钮）
- ✅ 颜色对比度 ≥ 4.5:1
- ❌ 不用 `div` 替代 `button`
- ❌ 不用纯颜色传达信息（图标 + 文字配合）

详见后续 v0.4 引入的 [accessibility.md](./accessibility.md)（如需要）。

---

## 9. 性能规则

- ✅ 大列表用虚拟滚动（> 100 项考虑）
- ✅ 重组件用 `React.memo`
- ✅ 稳定引用用 `useCallback` / `useMemo`
- ❌ 不在 render 里定义大对象/数组
- ❌ 不每帧都 setState

---

## 10. 反例清单（**禁止**）

```tsx
// ❌ 用 React.FC
const TaskCard: React.FC<Props> = ({ task }) => { }

// ❌ 内联 props 类型
function TaskCard({ task }: { task: Task }) { }

// ❌ any
function process(data: any) { }

// ❌ class 组件
class TaskCard extends React.Component { }

// ❌ 嵌套地狱
<TaskCard><div><span><b>...</b></span></div></TaskCard>

// ❌ 一文件多组件
function TaskCard() { }
function TaskList() { }
function TaskDetail() { }
```

---

**组件规范 = 强约束。** 违反 = PR 退回。