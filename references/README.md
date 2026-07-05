# references/ · 清秋前端标准

> **状态：** v0.3.0
> **作者：** Mavis
> **本目录性质：** 所有前端代码（React + Tauri UI）的**强制标准**。任何前端代码改动必须符合这里的规则。

---

## 文件清单

| 文件 | 内容 | 阅读对象 |
|------|------|---------|
| [README.md](./README.md)（本文件） | 索引 + 总原则 | 所有前端开发者 |
| [naming.md](./naming.md) | **命名规则 + 文件大小上限** | 所有 |
| [components.md](./components.md) | 组件规范（结构 / props / state / 事件） | React 开发者 |
| [styling.md](./styling.md) | 样式规范（CSS / Tailwind / 主题） | React 开发者 |
| [testing.md](./testing.md) | 测试规范（Vitest / Playwright） | React 开发者 |

---

## 总原则

1. **科技感 + 简约大气 + 没有 AI 味**（详见根目录 [DESIGN.md §9 反 AI 味清单](../DESIGN.md)）
2. **单一职责**：一个组件 / 一个文件只做一件事
3. **强边界**：通过 props / events 通信，不直接读全局状态
4. **无障碍**：所有交互元素必须有 aria-label，键盘可达
5. **暗色主题优先**（v1.0 唯一主题），未来可选亮色
6. **代码风格统一**（prettier + eslint）

---

## 强约束（**违反的 PR 不许合入**）

- ❌ 不写超过 200 行的 React 组件
- ❌ 不写超过 300 行的 Python 模块
- ❌ 不引未在 TECH-STACK.md 列出的库
- ❌ 不在 UI 代码 / bundle / 配置文件里出现任何 API key
- ❌ 不绕过命名规范
- ❌ 不绕过文件大小上限
- ❌ 不写"一坨"组件（一个文件 5+ 个不相关组件）
- ❌ 不写 emoji 装饰（仅 lucide 图标）

---

## 详细规范

详见各子文件：

- 命名 → [naming.md](./naming.md)
- 组件 → [components.md](./components.md)
- 样式 → [styling.md](./styling.md)
- 测试 → [testing.md](./testing.md)

---

## 规范变更

规范改动必须：

1. 更新对应的 `references/*.md` 文件
2. 在 [CHANGELOG.md](../CHANGELOG.md) 记录
3. 在 [PROJECT.md §6 决策记录](../PROJECT.md) 写决策理由

---

**严格遵循这些标准。** 不符合的代码 = 返工。