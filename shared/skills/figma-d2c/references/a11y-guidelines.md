# 无障碍（Accessibility / a11y）规范

确保 D2C 生成的代码符合 WCAG 2.1 AA 级别标准。

---

## 一、语义化 HTML 标签

### 必须使用语义标签的场景

| Figma 区域特征 | 应使用的 HTML 标签 | 禁止使用 |
|---------------|------------------|---------|
| 页面顶部导航栏 | `<header>` + `<nav>` | 裸 `<div>` |
| 底部信息栏 | `<footer>` | 裸 `<div>` |
| 侧边菜单/导航 | `<aside>` + `<nav>` | 裸 `<div>` |
| 主要内容区域 | `<main>` | 裸 `<div>` |
| 文章/卡片内容 | `<article>` 或 `<section>` | 裸 `<div>` |
| 标题文本 | `<h1>`~`<h6>`（按层级） | `<div>` + font-size |
| 段落文本 | `<p>` | `<span>` |
| 列表/重复项 | `<ul>` / `<ol>` + `<li>` | 多个平级 `<div>` |
| 按钮 | `<button>` 或组件库 `<Button>` | `<div onClick>` |
| 链接 | `<a href>` | `<span onClick>` |

### 标题层级规则

- 每个页面**只有一个** `<h1>`
- 标题层级**不跳级**：`h1 → h2 → h3`，不允许 `h1 → h3`
- 侧边栏/卡片内的标题从 `<h2>` 或 `<h3>` 开始

---

## 二、ARIA 属性规范

### 图片与图标

```tsx
{/* 装饰性图片：添加空 alt */}
<img src={decorBg} alt="" role="presentation" />

{/* 信息性图片：描述性 alt */}
<img src={productCover} alt="智能降噪耳机产品图" />

{/* 可操作图标按钮：必须有 aria-label */}
<button aria-label="关闭对话框" onClick={handleClose}>
  <CloseIcon />
</button>

{/* 纯装饰性图标：用 aria-hidden 隐藏 */}
<ChevronRightIcon aria-hidden="true" />
```

### 表单元素

```tsx
{/* 所有表单控件必须关联 label */}
<label htmlFor="search-input" className="sr-only">搜索商品</label>
<Input id="search-input" placeholder="搜索商品..." />

{/* 或使用 aria-label 替代可视 label */}
<Input aria-label="搜索商品" placeholder="搜索商品..." />

{/* 错误提示关联 */}
<Input aria-describedby="email-error" aria-invalid={hasError} />
<span id="email-error" role="alert">请输入有效的邮箱地址</span>
```

### 交互组件

```tsx
{/* 展开/收起 */}
<button 
  aria-expanded={isOpen}
  aria-controls="sidebar-content"
  onClick={toggle}
>
  菜单
</button>
<div id="sidebar-content" role="region">
  {isOpen && <SidebarContent />}
</div>

{/* Tab 切换 */}
<div role="tablist">
  <button role="tab" aria-selected={active === 'tab1'} aria-controls="panel1">
    商品详情
  </button>
</div>
<div role="tabpanel" id="panel1">内容</div>

{/* 模态对话框 */}
<Dialog
  aria-labelledby="dialog-title"
  aria-describedby="dialog-desc"
>
  <h2 id="dialog-title">确认删除</h2>
  <p id="dialog-desc">此操作不可恢复</p>
</Dialog>
```

---

## 三、键盘导航

### 焦点管理规则

1. 所有可交互元素必须可通过 `Tab` 键访问
2. 自定义可点击元素需要 `tabIndex={0}` + `onKeyDown` 处理 Enter/Space
3. **禁止**使用 `tabIndex` 大于 0 的值
4. 模态框打开时，焦点应锁定在模态框内

```tsx
{/* 可点击卡片的键盘支持 */}
<div
  role="button"
  tabIndex={0}
  className="cursor-pointer"
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
>
  <ProductCard />
</div>
```

---

## 四、颜色与对比度

### 最低对比度要求

| 文本类型 | 最低对比度比 |
|---------|------------|
| 正文文本（< 18px） | 4.5:1 |
| 大文本（≥ 18px 或 14px bold） | 3:1 |
| UI 组件/图形 | 3:1 |

### 常见问题与修正

```tsx
{/* ❌ 灰色文本在白色背景上对比度不足 */}
<p style={{ color: '#c0c0c0' }}>描述文本</p>

{/* ✅ 使用更深的灰色确保对比度 */}
<p style={{ color: '#666666' }}>描述文本</p>

{/* ⚠️ 当 Figma 设计稿颜色对比度不达标时 */}
{/* 在代码注释中标注，但仍按设计稿生成，由设计师决定是否修改 */}
{/* a11y-warning: 文本对比度 2.8:1，低于 WCAG AA 要求的 4.5:1 */}
<p style={{ color: '#c0c0c0' }}>设计稿原始颜色</p>
```

---

## 五、屏幕阅读器辅助

### 仅屏幕阅读器可见的文本

```tsx
{/* Tailwind 项目使用 sr-only */}
<span className="sr-only">当前页码</span>

{/* 非 Tailwind 项目使用自定义类或内联样式 */}
<span style={{
  position: 'absolute',
  width: '1px',
  height: '1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
}}>当前页码</span>

{/* 动态提示 */}
<div aria-live="polite" className="sr-only">
  {statusMessage}
</div>
```

### 跳转链接

页面级组件应在顶部添加跳转链接：

```tsx
<a
  href="#main-content"
  style={{ /* sr-only + focus:visible 样式 */ }}
  className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-white"
>
  跳转到主要内容
</a>
```

> **非 Tailwind 项目**：使用等效 CSS 类实现 screen-reader-only 效果。

---

## 六、D2C 自动生成的 a11y 检查清单

代码生成完成后，自动检查以下项目（在输出时列出未通过项）：

- [ ] 所有 `<img>` 都有 `alt` 属性
- [ ] 所有可点击的非 `<button>`/`<a>` 元素都有 `role` + `tabIndex` + 键盘事件
- [ ] 图标按钮都有 `aria-label`
- [ ] 表单控件都关联了 `label` 或 `aria-label`
- [ ] 标题层级连续且不跳级
- [ ] 页面有且仅有一个 `<h1>`
- [ ] 使用了语义化布局标签（`<header>`, `<main>`, `<footer>`, `<nav>`）
