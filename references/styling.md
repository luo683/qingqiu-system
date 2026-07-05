# styling.md · 样式规范

> **状态：** v0.3.0
> **本文件性质：** 样式**强制规范**。所有 CSS / Tailwind / 主题必须符合这里的规则。

---

## 1. 设计哲学

详见根目录 [DESIGN.md](../DESIGN.md)。要点：

- **科技感 + 简约大气 + 没有 AI 味**
- **深色主题**（v1.0 唯一）
- **冷青 `#00FFD1` 唯一强调色**（不是紫色、不是蓝色）
- **等宽字体优先**（JetBrains Mono）
- **矩形 + 2px 圆角**（不大圆角）
- **不用渐变 / 不用 emoji / 不用 Glassmorphism / 不用拟物化**

---

## 2. CSS 方法论

**用 Tailwind CSS**（utility-first）。

- ✅ 类名直写在 JSX 上：`className="flex items-center gap-2 px-3 py-2"`
- ✅ 复杂组合用 `@apply`（在 CSS 文件里）
- ❌ 不写 `.css` `.scss`（除非全局 reset）
- ❌ 不写 inline `style={{ ... }}`（除非动态值）

```tsx
// ✅ 推荐
<div className="flex items-center gap-2 px-3 py-2 bg-qq-bg-elevated">

// ❌ 禁止
<div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: 'var(--qq-bg-elevated)' }}>
```

---

## 3. 主题变量

### 3.1 颜色变量（**强约束 · 不可绕开**）

```css
/* globals.css */
:root {
  /* 背景色 */
  --qq-bg:           #0A0E14;  /* 主背景 */
  --qq-bg-elevated:  #131820;  /* 卡片 / 面板 */
  --qq-bg-overlay:   #1B212C;  /* 弹窗 / 浮动层 */
  --qq-border:       #222A36;  /* 默认边框 */
  --qq-border-strong:#3A4452;  /* hover / focus */
  
  /* 文字色 */
  --qq-text-primary:   #E6EDF3;
  --qq-text-secondary: #8B949E;
  --qq-text-tertiary:  #6E7681;
  
  /* 强调色（唯一 · 冷青）*/
  --qq-accent:       #00FFD1;
  --qq-accent-dim:   #00B89C;
  --qq-accent-bg:    #0A2E2A;
  
  /* 状态色（克制用）*/
  --qq-success:      #3FB950;
  --qq-warning:      #D29922;
  --qq-danger:       #F85149;
  --qq-info:         #58A6FF;
}
```

### 3.2 Tailwind 集成

在 `tailwind.config.ts` 引用 CSS 变量：

```typescript
export default {
  theme: {
    extend: {
      colors: {
        'qq-bg':           'var(--qq-bg)',
        'qq-bg-elevated':  'var(--qq-bg-elevated)',
        'qq-accent':       'var(--qq-accent)',
        // ...
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Cascadia Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'none': '0',
        'sm':   '2px',  /* 按钮 / 输入框 */
        'md':   '4px',  /* 卡片 */
        'lg':   '6px',  /* 弹窗 */
      },
    },
  },
}
```

### 3.3 颜色使用规则

| 场景 | 用哪个变量 |
|------|----------|
| 页面背景 | `bg-qq-bg` |
| 卡片 / 面板 | `bg-qq-bg-elevated` |
| 弹窗 / 浮动层 | `bg-qq-bg-overlay` |
| 默认边框 | `border-qq-border` |
| hover / focus 边框 | `border-qq-border-strong` |
| 主要文字 | `text-qq-text-primary` |
| 次要文字 | `text-qq-text-secondary` |
| 三级文字 / placeholder | `text-qq-text-tertiary` |
| 强调 / 链接 / 选中 | `text-qq-accent` 或 `bg-qq-accent` |
| 成功状态 | `text-qq-success` |
| 警告状态 | `text-qq-warning` |
| 危险 / 删除 | `text-qq-danger` |

### 3.4 颜色反例（**禁止**）

- ❌ 用 Tailwind 默认色（`bg-blue-500` / `bg-purple-600`）
- ❌ 自定义颜色（`#abcdef`）
- ❌ 紫色 / 蓝紫色（AI 味）
- ❌ 渐变（`bg-gradient-to-r`）
- ❌ 多色按钮（一个按钮 > 1 个色相）
- ❌ 大色块做装饰背景

---

## 4. 间距 / 尺寸 / 圆角

### 4.1 间距（8px 栅格）

```
4px  - 极小（图标内 padding）
8px  - 小（按钮内 padding）
12px - 中（卡片内 padding）
16px - 大（区块间距）
24px - 极大（页面边距）
32px - 模块间距
48px - 屏幕分区
```

Tailwind 对应：

```html
<div className="p-1">4px</div>
<div className="p-2">8px</div>
<div className="p-3">12px</div>
<div className="p-4">16px</div>
<div className="p-6">24px</div>
<div className="p-8">32px</div>
<div className="p-12">48px</div>
```

### 4.2 圆角

| 元素 | 圆角 | Tailwind |
|------|------|---------|
| 按钮 / 输入框 | 2px | `rounded-sm` |
| 卡片 | 4px | `rounded-md` |
| 弹窗 | 6px | `rounded-lg` |
| 图标容器 | 0 | `rounded-none` |
| ❌ pill 按钮（999px） | ❌ `rounded-full` |

### 4.3 阴影

```css
--qq-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
--qq-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
--qq-shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.6);
```

Tailwind：

```html
<div className="shadow-sm">层 1</div>
<div className="shadow-md">层 2</div>
<div className="shadow-lg">层 3</div>
```

❌ **禁止：** 彩色阴影 / 多重阴影 / 模糊发光 / 长投影

---

## 5. 字体

### 5.1 字体栈

```css
/* 默认 monospace（控制台美学） */
font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', 'SF Mono', monospace;

/* 次选 sans（仅大标题） */
font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
```

### 5.2 字号

| 用途 | 字号 | Tailwind |
|------|------|---------|
| 大数字 / 仪表盘 | 24px / 32px | `text-2xl` / `text-3xl` |
| 极少用的大标题 | 16px / 18px | `text-base` / `text-lg` |
| **UI 默认** | 13px / 14px | `text-sm` |
| 输出 / 代码 / 日志 | 12px / 13px | `text-xs` / `text-sm` |

### 5.3 字体规则

- ✅ **默认 monospace**
- ✅ 大标题才用 sans
- ❌ 不用 outline / shadow / gradient text
- ❌ 不用装饰性字体（手写体 / 衬线 / 卡通）

---

## 6. 动效

| 场景 | 时长 | Tailwind |
|------|------|---------|
| hover / focus | 80ms | `transition-colors duration-75` |
| 状态切换 | 120ms | `transition-all duration-100` |
| 弹窗出现 | 160ms | `transition-all duration-150` |

❌ **禁止：** 弹跳 / 旋转 / 闪烁 / 流光 / 3D 翻转 / 超过 200ms

```html
<button className="transition-colors duration-75 hover:border-qq-accent">
```

---

## 7. 图标

- **库：** `lucide-react`（默认）
- **风格：** outline（线性），1.5px
- **尺寸：** 16 / 20 / 24px
- **颜色：** 默认 `text-qq-text-secondary`，active `text-qq-accent`

```tsx
import { ChevronDown } from 'lucide-react'

<ChevronDown size={16} className="text-qq-text-secondary" />
```

❌ **禁止：** emoji / 装饰图标 / 多色图标

---

## 8. 组件样式模板

### 8.1 Button

```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md'
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
}

export function Button({ variant = 'secondary', size = 'md', children, onClick, disabled }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={[
        'inline-flex items-center gap-2 rounded-sm border transition-colors duration-75',
        'font-mono text-sm',
        size === 'sm' ? 'px-2 py-1' : 'px-3 py-2',
        variant === 'primary' && 'border-qq-accent bg-qq-accent text-qq-bg hover:bg-qq-accent-dim',
        variant === 'secondary' && 'border-qq-border bg-qq-bg-elevated text-qq-text-primary hover:border-qq-accent',
        variant === 'ghost' && 'border-transparent bg-transparent text-qq-text-secondary hover:text-qq-text-primary',
        disabled && 'opacity-50 cursor-not-allowed',
      ].filter(Boolean).join(' ')}
    >
      {children}
    </button>
  )
}
```

### 8.2 Card

```tsx
export function Card({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <div className="rounded-md border border-qq-border bg-qq-bg-elevated p-4">
      {title && <h3 className="mb-2 font-mono text-sm text-qq-text-secondary">{title}</h3>}
      <div className="font-mono text-sm text-qq-text-primary">{children}</div>
    </div>
  )
}
```

### 8.3 Modal / Confirm

```tsx
export function Modal({ open, onClose, children }: ModalProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg border border-qq-border-strong bg-qq-bg-overlay p-6 shadow-lg">
        {children}
      </div>
    </div>
  )
}
```

---

## 9. 全局样式文件

`src/styles/globals.css`：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --qq-bg:           #0A0E14;
  --qq-bg-elevated:  #131820;
  --qq-bg-overlay:   #1B212C;
  --qq-border:       #222A36;
  --qq-border-strong:#3A4452;
  --qq-text-primary:   #E6EDF3;
  --qq-text-secondary: #8B949E;
  --qq-text-tertiary:  #6E7681;
  --qq-accent:       #00FFD1;
  --qq-accent-dim:   #00B89C;
  --qq-accent-bg:    #0A2E2A;
  --qq-success:      #3FB950;
  --qq-warning:      #D29922;
  --qq-danger:       #F85149;
}

html, body {
  background: var(--qq-bg);
  color: var(--qq-text-primary);
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  margin: 0;
  padding: 0;
}

* {
  box-sizing: border-box;
}

/* 滚动条样式（克制） */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: var(--qq-bg);
}
::-webkit-scrollbar-thumb {
  background: var(--qq-border-strong);
  border-radius: 0;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--qq-text-tertiary);
}
```

---

## 10. 验收清单（PR 提交前）

- [ ] 没有渐变（任何 linear-gradient）
- [ ] 没有 emoji
- [ ] 没有大圆角（≤ 6px）
- [ ] 没有 Glassmorphism / 毛玻璃
- [ ] 没有紫色 / 蓝紫色
- [ ] 没有插画 / 拟物化
- [ ] 主色不超过 2 种（accent + 灰阶）
- [ ] 默认字体是 mono
- [ ] 阴影只用三档（sm/md/lg）
- [ ] 动效都 < 200ms
- [ ] 没有用 Tailwind 默认色（必须用 CSS 变量）

---

**样式规范 = 强约束。** 违反 = PR 退回。