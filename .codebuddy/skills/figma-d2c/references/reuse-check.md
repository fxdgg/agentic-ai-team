# 复用检查（Reuse Check）

在生成代码前，必须先检查项目中已有的可复用资源，避免重复创建。目标不是“尽量猜到可复用”，而是“按固定优先级做同样的复用决策”。

---

## 一、复用决策总原则

复用优先级固定为：

1. **`component-map.json` 显式映射**
2. **项目已有组件（名称 / 语义 / 目录命中）**
3. **项目组件库组件**
4. **项目图标库图标**
5. **原生 HTML + CSS 兜底实现**

### 必须遵守的规则

- **禁止跳过显式映射**：`component-map.json` 命中后，不得再自由选择其他组件。
- **禁止因为“看起来差不多”就新建组件**：必须先跑完整个复用优先级链路。
- **歧义默认走严格策略**：如果两个目标都可能复用，优先已有组件；若仍不明确，优先组件库而不是新建。
- **所有 fallback 决策都要写入 Manifest**。

---

## 二、组件复用检查

### 2.1 显式映射检查（最高优先级）

先读取 `component-map.json`，对 Figma 节点做显式匹配：

- `componentKey` 精确命中
- `namePatterns` 顺序命中
- 变体 / props / slot 映射命中

#### 输出规则

```text
✅ 显式映射命中：
  - Button / CTA → Button（from $COMPONENT_LIBRARY）
  - Tabs / TabBar → Tabs（from $COMPONENT_LIBRARY）
```

如果命中：
- 直接使用映射结果；
- 记录命中的规则 `id`；
- 不再进入“模糊猜测”流程。

### 2.2 项目已有组件扫描

若未命中 `component-map.json`，再扫描项目已有组件：

- 常见目录：`src/components/`、`src/pages/`、`src/views/`、`app/`
- 递归搜索组件文件（`.tsx`、`.jsx`、`.vue`）
- 同时记录：
  - 文件名
  - 导出组件名
  - 所在目录
  - 是否为基础组件 / 业务组件

### 2.3 匹配规则

对比 Figma 节点名称 / 组件名称与项目组件：

1. **文件名精确命中**
2. **组件名精确命中**
3. **语义近似命中**（如 `UserCard` ≈ `ProfileCard`）
4. **结构特征近似命中**（仅作辅助，不可直接覆盖更高优先级）

### 2.4 决策规则

- **命中同名组件** → 直接复用
- **命中多个候选组件** → 选择目录更靠近基础组件层的实现（优先 `src/components/`）
- **只命中业务组件** → 仅在输出目标也属于同业务域时复用
- **命中近似组件但 props 不兼容** → 不复用，改用组件库或新建

### 2.5 检查报告

```text
✅ 复用检查完成

显式映射命中：
  - Button → Button（rule: button）

已找到可复用组件：
  - src/components/UserAvatar.tsx → 匹配 Figma "Avatar" 节点
  - src/components/StatCard.tsx → 匹配 Figma "KPI Card" 节点

需要新建组件：
  - SearchBar（Figma "Search Input"）
  - NotificationBell（Figma "Bell Icon"）

Fallback 记录：
  - InfoCard 未命中显式映射与项目组件，降级为组件库 Card
```

---

## 三、组件库复用

> 根据 `project-profile.json` 或技术栈检测结果，自动匹配项目中使用的组件库。如果项目未使用任何组件库，跳过此步骤，使用原生 HTML + CSS 还原。

### 3.1 通用替代规则

| 场景 | 不要手写 | 语义组件 |
|------|---------|---------|
| 按钮 | `<div onClick>` | `<Button>` |
| 输入框 | `<input className="...">` | `<Input>` |
| 弹窗 | 自定义 modal div | `<Dialog>` / `<Modal>` |
| 表格 | `<table>` | `<Table>` |
| 标签页 | 自定义 tab 切换 | `<Tabs>` |
| 加载状态 | 自定义 spinner | `<Loading>` / `<Spin>` |
| 消息提示 | 自定义 toast | `Message` / `message` |
| 分页 | 自定义 pagination | `<Pagination>` |

### 3.2 各组件库名称对照

| 语义 | TDesign | Ant Design | Element Plus |
|------|---------|-----------|-------------|
| 按钮 | `Button` | `Button` | `ElButton` |
| 输入框 | `Input` | `Input` | `ElInput` |
| 弹窗 | `Dialog` | `Modal` | `ElDialog` |
| 表格 | `Table` | `Table` | `ElTable` |
| 标签页 | `Tabs` | `Tabs` | `ElTabs` |
| 加载 | `Loading` | `Spin` | `ElLoading` |
| 消息 | `MessagePlugin` | `message` | `ElMessage` |
| 分页 | `Pagination` | `Pagination` | `ElPagination` |

### 3.3 何时允许降级到原生实现

仅在以下情况允许使用原生 HTML：

- 没有可用组件库
- 组件库缺少对应语义组件
- 组件库组件无法满足结构要求且显式映射未指定

> 降级后必须在 Manifest 中记录 `fallback = native-*`。

---

## 四、图标库复用

### 4.1 决策优先级

1. `component-map.json` 中的显式图标映射
2. 项目图标库（`tdesign-icons-react` / `@ant-design/icons` / `lucide-react` 等）
3. 下载 Figma 中的 SVG 资源

### 4.2 常用图标语义对照

| 设计稿描述 | TDesign | Ant Design | Lucide |
|-----------|---------|-----------|--------|
| 搜索 | `SearchIcon` | `SearchOutlined` | `Search` |
| 关闭/叉号 | `CloseIcon` | `CloseOutlined` | `X` |
| 添加/加号 | `AddIcon` | `PlusOutlined` | `Plus` |
| 删除/垃圾桶 | `DeleteIcon` | `DeleteOutlined` | `Trash2` |
| 编辑/铅笔 | `EditIcon` | `EditOutlined` | `Pencil` |
| 更多/三个点 | `MoreIcon` | `MoreOutlined` | `MoreHorizontal` |
| 设置/齿轮 | `SettingIcon` | `SettingOutlined` | `Settings` |
| 用户/头像 | `UserIcon` | `UserOutlined` | `User` |
| 箭头-右 | `ChevronRightIcon` | `RightOutlined` | `ChevronRight` |
| 箭头-下 | `ChevronDownIcon` | `DownOutlined` | `ChevronDown` |

只有在图标库无法匹配时，才下载 Figma 中的 SVG 资源。

---

## 五、Design Token 复用

Token 复用优先级固定为：

1. **Figma Variable 引用**
2. **项目已有 Token**
3. **`token-aliases.json` 中的别名映射**
4. **新提取的 D2C Token**
5. **原始值兜底**

### Tailwind 项目

检查 `tailwind.config.js` / `tailwind.config.ts`：

```js
theme: {
  extend: {
    colors: {
      primary: '...',
      secondary: '...'
    },
    spacing: { ... },
    borderRadius: { ... }
  }
}
```

规则：
- 与项目 Token 命中 → 使用项目 Token 名
- 未命中项目 Token，但命中 `token-aliases.json` → 使用别名结果
- 都未命中 → 再新增 D2C Token

### 非 Tailwind 项目

检查项目中的 CSS 变量 / 主题文件：

- `src/styles/variables.scss`
- `src/styles/variables.css`
- `src/theme/`
- 组件库主题文件

规则：
- 命中已有变量 → 使用已有变量
- 命中别名 → 使用别名变量
- 未命中 → 追加 D2C Token，不覆盖旧定义

---

## 六、Manifest 记录要求

每次复用检查结束后，必须至少记录：

```json
{
  "reusedComponents": [
    {
      "nodeId": "1:234",
      "source": "component-map",
      "ruleId": "button",
      "target": "Button"
    }
  ],
  "fallbacks": [
    {
      "nodeId": "1:345",
      "reason": "no-project-component-found",
      "target": "native-input"
    }
  ]
}
```

---

## 七、一致性红线

1. 同一类 Figma 组件必须优先命中同一条映射规则
2. 已命中的项目组件不得在下一次生成中回退为原生实现
3. Token 决策顺序不得跳级
4. 组件复用过程中的 fallback 必须可追踪
5. 不允许因为不同人的表述方式改变复用结果
