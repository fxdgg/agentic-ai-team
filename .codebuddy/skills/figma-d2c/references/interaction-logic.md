# 交互逻辑与状态管理规范

从 Figma 设计稿推断交互逻辑，并生成合理的状态管理代码。

---

## 一、交互推断规则

根据 Figma 节点类型和名称推断交互行为：

### 1.1 按钮交互

| Figma 特征 | 推断的交互 | 代码生成 |
|-----------|-----------|---------|
| Button / CTA | 点击事件 | `onClick` 处理器 |
| 名称含 submit / 提交 | 表单提交 | `onSubmit` + loading 状态 |
| 名称含 cancel / 取消 | 取消操作 | `onClick` 导航/关闭 |
| 名称含 delete / 删除 | 确认删除 | `onClick` + 确认弹窗 |
| 名称含 edit / 编辑 | 进入编辑 | `onClick` 切换编辑状态 |

### 1.2 表单交互

| Figma 特征 | 推断的交互 | 代码生成 |
|-----------|-----------|---------|
| Input / TextField | 输入绑定 | `value` + `onChange` / `v-model` |
| Select / Dropdown | 选择绑定 | `value` + `onChange` / `v-model` |
| Checkbox | 勾选绑定 | `checked` + `onChange` / `v-model` |
| Radio | 单选绑定 | `value` + `onChange` / `v-model` |
| Switch / Toggle | 开关绑定 | `value` + `onChange` / `v-model` |
| Form 容器 | 表单提交 | `Form` + `onSubmit` + 校验 |

### 1.3 导航交互

| Figma 特征 | 推断的交互 | 代码生成 |
|-----------|-----------|---------|
| Tabs | Tab 切换 | `value` + `onChange` |
| Menu / Nav | 导航切换 | `value` + `onChange` |
| Pagination | 翻页 | `current` + `onChange` |
| Breadcrumb | 面包屑导航 | 静态展示或 `onClick` |

### 1.4 隐含交互

| Figma 特征 | 推断的交互 | 代码生成 |
|-----------|-----------|---------|
| 可点击的卡片 | hover 效果 + 点击 | hover 样式 + `onClick` |
| 有 hover variant | hover 态样式 | CSS hover 伪类 |
| 关闭按钮（×） | 关闭/隐藏 | `onClick` + 状态切换 |
| 展开/收起箭头 | 折叠展开 | 折叠组件 或自定义 toggle |

### 1.5 复合模式匹配（高级推断）

以下规则用于处理需要结合多个节点特征才能判定的复杂交互场景：

#### Button + Icon 子节点判断

当节点名称包含 `"Button"` 且子节点中包含 `"Icon"` 类型节点时：

1. 查询项目组件库中 `Button` 组件的 `icon` 属性定义
2. 判断图标位置：
   - 图标在文本**左侧** → 使用 `icon` 属性（如 `<Button icon={<SearchIcon />}>搜索</Button>`）
   - 图标在文本**右侧** → 使用 `suffix` 属性或作为子元素
   - **仅图标无文本** → 使用图标按钮形态（如 `shape="circle"` + `icon`）
3. 图标来源优先匹配项目图标库，未命中则作为自定义 SVG 处理

#### 折叠/展开推断

当一组兄弟 FRAME 节点中包含以下特征时，自动推断为"折叠/展开"交互：

| 触发特征 | 推断结果 |
|---------|---------|
| 子节点含 `ChevronDown` / `ChevronUp` / `Arrow` 图标 | 生成 toggle 状态管理 |
| 节点名含 `Collapse` / `Accordion` / `Expandable` | 优先映射组件库的折叠组件 |
| 重复的标题+内容结构 ≥ 2 组，且标题旁有箭头图标 | 生成折叠面板 + `map()` 循环 |

**React 示例：**

```tsx
const [expandedKeys, setExpandedKeys] = useState<string[]>(['section-1']);

{/* 如有组件库折叠组件则优先使用，否则自行实现 */}
<div className="accordion">
  {sections.map((section) => (
    <div key={section.id}>
      <button
        onClick={() => toggleExpand(section.id)}
        aria-expanded={expandedKeys.includes(section.id)}
      >
        {section.title}
      </button>
      {expandedKeys.includes(section.id) && (
        <div>{section.content}</div>
      )}
    </div>
  ))}
</div>
```

#### Tabs 模式匹配

当节点名称或结构匹配以下模式时，优先映射为组件库 Tabs 组件：

| 触发特征 | 推断结果 |
|---------|---------|
| 节点名匹配 `Tab` / `Tabs` / `TabBar` / `TabPanel` | 映射为 Tabs + TabPanel |
| 一组水平排列的文本节点，其中一个有高亮/下划线样式 | 推断为 Tab 切换，高亮项为默认激活 Tab |
| 多个同级容器，仅一个 `visible: true` 或非 `opacity: 0` | 推断为 Tab 面板，可见的为默认面板 |

**React 示例：**

```tsx
const [activeTab, setActiveTab] = useState('tab1');

<Tabs value={activeTab} onChange={(val) => setActiveTab(val as string)}>
  <TabPanel value="tab1" label="商品详情">
    <ProductDetail />
  </TabPanel>
  <TabPanel value="tab2" label="用户评价">
    <ReviewList />
  </TabPanel>
</Tabs>
```

**Vue 3 示例：**

```vue
<template>
  <Tabs v-model="activeTab">
    <TabPanel value="tab1" label="商品详情">
      <ProductDetail />
    </TabPanel>
    <TabPanel value="tab2" label="用户评价">
      <ReviewList />
    </TabPanel>
  </Tabs>
</template>

<script setup lang="ts">
import { ref } from 'vue';
const activeTab = ref('tab1');
</script>
```

**注意**：以上复合模式匹配在 `interaction-logic.md` 中编码为确定性规则，确保 AI 不是随意猜测，而是基于可追溯的模式进行推断。

### 1.6 hover 效果生成规则（强制）

**为确保交互还原的一致性，以下 hover 效果为强制生成规则：**

| 元素类型 | 必须添加的 hover 效果 |
|---------|---------------------|
| 所有 `<Button>` / `<button>` | `hover:opacity-80` 或组件库自带 hover（无需额外添加） |
| 可点击的卡片 | `hover:shadow-md cursor-pointer transition-shadow` |
| 导航链接 / 菜单项 | `hover:text-primary hover:bg-gray-50` |
| 图标按钮 | `hover:bg-gray-100 rounded cursor-pointer transition-colors` |
| 列表项（含 onClick） | `hover:bg-gray-50 cursor-pointer transition-colors` |
| Tab 标签（非激活态） | `hover:text-primary cursor-pointer` |

**此规则消除了"hover 效果需手动添加"的不确定性。**

---

## 二、状态管理模式

### 2.1 简单组件状态

**React（useState）：**

```tsx
const [inputValue, setInputValue] = useState('');
const [isOpen, setIsOpen] = useState(false);
const [activeTab, setActiveTab] = useState('tab1');
const [selectedItems, setSelectedItems] = useState<string[]>([]);
```

**Vue 3（ref）：**

```vue
<script setup lang="ts">
import { ref } from 'vue';

const inputValue = ref('');
const isOpen = ref(false);
const activeTab = ref('tab1');
const selectedItems = ref<string[]>([]);
</script>
```

### 2.2 表单状态

> 根据项目组件库自动选择表单组件。无组件库时使用原生 `<form>` + 手动校验。

**React + 组件库示例：**

```tsx
// 以通用 Form 组件为例（具体 API 取决于组件库）
const handleSubmit = async (values: Record<string, unknown>) => {
  console.log('表单提交:', values);
  // TODO: 调用 API 提交数据
};

<Form onSubmit={handleSubmit}>
  <FormItem label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
    <Input placeholder="请输入用户名" />
  </FormItem>
  <FormItem>
    <Button type="submit">提交</Button>
  </FormItem>
</Form>
```

### 2.3 加载状态

```tsx
const [loading, setLoading] = useState(false);

const handleFetch = async () => {
  setLoading(true);
  try {
    // TODO: API 调用
  } finally {
    setLoading(false);
  }
};

<Button loading={loading} onClick={handleFetch}>加载数据</Button>
```

### 2.4 列表 + 分页状态

```tsx
const [currentPage, setCurrentPage] = useState(1);
const [pageSize, setPageSize] = useState(10);

<Table
  data={dataSource}
  columns={columns}
  pagination={{
    current: currentPage,
    pageSize,
    total: 100,
    onChange: (pageInfo) => {
      setCurrentPage(pageInfo.current);
      setPageSize(pageInfo.pageSize);
    },
  }}
/>
```

---

## 三、事件处理命名规范

```
handleXxx — 组件内部事件处理
onXxx    — 暴露给父组件的回调 props

示例：
  handleClick     — 按钮点击
  handleChange    — 输入变化
  handleSubmit    — 表单提交
  handleClose     — 关闭弹窗
  handleSelect    — 选择项目
  handleDelete    — 删除操作
  handleToggle    — 切换状态
  handlePageChange — 翻页
```

---

## 四、TODO 标注

对于需要对接真实 API 的交互逻辑，使用 TODO 注释标注：

```tsx
const handleSubmit = async (values: FormValues) => {
  // TODO: 对接真实 API
  // POST /api/users { ...values }
  console.log('提交数据:', values);
};
```

---

## 五、Figma 变体与组件状态映射

当 Figma 组件有 variants 时（如 state=default/hover/active/disabled）：

```tsx
// Figma 组件变体 → 条件渲染
interface ButtonProps {
  state?: 'default' | 'hover' | 'active' | 'disabled';
}

// 通常不需要手动管理 hover/active，CSS 处理即可
// disabled 状态通过 props 传递
<Button disabled={isDisabled}>确认</Button>
```

---

## 六、过渡动画规则

### 6.1 强制过渡（所有项目必须遵守）

**任何涉及视觉状态变化的元素，必须添加对应的过渡动画类名：**

| 交互类型 | Tailwind 过渡类名 | CSS 等效 |
|---------|------------------|---------|
| hover 颜色/透明度变化 | `transition-colors duration-200` | `transition: color 200ms, background-color 200ms` |
| hover 阴影变化 | `transition-shadow duration-200` | `transition: box-shadow 200ms` |
| hover 缩放/位移 | `transition-transform duration-200` | `transition: transform 200ms` |
| 展开/折叠内容 | `transition-all duration-300 ease-in-out` | `transition: all 300ms ease-in-out` |
| 弹窗/抽屉出现 | `transition-opacity duration-200` + transform | `transition: opacity 200ms, transform 200ms` |
| Tab 切换下划线 | `transition-all duration-200` | `transition: all 200ms` |
| 侧边栏展开/收起 | `transition-[width] duration-300 ease-in-out` | `transition: width 300ms ease-in-out` |
| 进度条变化 | `transition-[width] duration-500 ease-out` | `transition: width 500ms ease-out` |

**此规则消除了"过渡动画是否需要添加"的不确定性。所有视觉状态变化都必须有过渡。**

### 6.2 Figma 原型交互映射（如设计稿包含原型交互）

当 Figma 设计稿包含原型交互（prototype interactions）信息时，按以下规则映射为 CSS 动画：

| Figma 原型动画 | CSS/Tailwind 实现 | 说明 |
|---------------|------------------|------|
| Smart Animate | `transition-all duration-300` + 对应属性变化 | 自动插值，用 transition 模拟 |
| Move In (Right) | `translate-x-full → translate-x-0` | 从右侧滑入 |
| Move In (Bottom) | `translate-y-full → translate-y-0` | 从底部滑入 |
| Move Out (Left) | `translate-x-0 → -translate-x-full` | 向左滑出 |
| Dissolve | `opacity-0 → opacity-100` | 淡入淡出 |
| Scale (Push) | `scale-95 opacity-0 → scale-100 opacity-100` | 缩放弹入 |

### 6.3 常用预设动画类

| 场景 | Tailwind 类名 | 适用情况 |
|------|-------------|---------|
| 加载旋转 | `animate-spin` | Spinner/加载图标 |
| 骨架屏脉冲 | `animate-pulse` | Skeleton 占位 |
| 轻微弹跳 | `animate-bounce` | 提示箭头/注意力引导 |
| 入场淡入 | `animate-in fade-in` | 内容首次显示（需 tailwindcss-animate） |
| 侧边栏滑入 | `animate-in slide-in-from-left` | 左侧面板展开（需 tailwindcss-animate） |
| 下拉菜单 | `animate-in fade-in zoom-in-95` | 弹出菜单（需 tailwindcss-animate） |

### 6.4 动画性能原则

- **优先使用** `transform`（translate/scale/rotate）和 `opacity` 做动画 → GPU 加速，不触发重排
- **避免动画化** `width`、`height`、`top`、`left`、`margin` → 触发重排，性能差
- 如果必须动画化尺寸变化，使用 `max-height` 替代 `height`（折叠面板常用技巧）

**折叠面板推荐实现（避免 height 动画）：**

```tsx
<div
  className={cn(
    'overflow-hidden transition-[max-height] duration-300 ease-in-out',
    isExpanded ? 'max-h-[500px]' : 'max-h-0'
  )}
>
  {/* 折叠内容 */}
</div>
```
