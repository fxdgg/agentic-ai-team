# 变更流程（Update Workflow）

当用户要求更新已有组件以匹配新版 Figma 设计时，执行以下流程。要求变更流程也必须先标准化输入，并复用 `project-profile.json`、`component-map.json`、`token-aliases.json` 与 `generation-manifest`。

---

## Step 0：标准化输入归一

先将用户请求归一化为 `request-template.json` 字段，至少补齐：

- `action = update`
- `figmaUrl`
- `nodeId`
- `outputPath`
- `validationLevel`

缺失的策略字段从 `project-profile.json` 继承，并将归一化结果写入 Manifest。

---

## Step 1：获取新版设计数据

1. 解析用户提供的 Figma 链接
2. 读取 `project-profile.json`、`component-map.json`、`token-aliases.json`
3. 调用 `get_figma_data` 获取最新节点数据
4. 读取目标文件的现有代码

---

## Step 2：生成差异分析报告

对比新 Figma 数据与现有代码，生成结构化差异报告：

### 差异报告模板

```markdown
## 差异分析报告

### 基本信息
- 文件：`src/components/XXX.tsx`
- Figma 节点：`<nodeId>`
- 分析时间：YYYY-MM-DD HH:mm

### 结构变更
| 变更类型 | 位置 | 旧值 | 新值 |
|----------|------|------|------|
| 新增节点 | Header 下第 3 个子元素 | — | SearchInput 组件 |
| 删除节点 | Footer > Links | 4 个链接 | — |
| 移动节点 | Avatar | Header 左侧 | Header 右侧 |

### 样式变更
| 元素 | 属性 | 旧值 | 新值 |
|------|------|------|------|
| 主标题 | fontSize | 24px | 28px |
| 卡片容器 | cornerRadius | 8px | 12px |
| 背景色 | fills | #F5F5F5 | #FAFAFA |

### 组件变更
| 元素 | 变更 | 详情 |
|------|------|------|
| CTA 按钮 | props 变化 | variant: primary → outline |
| 新增 | Alert 组件 | 顶部通知栏 |

### 影响范围
- 修改文件数：N
- 新增文件：列表
- 删除文件：列表

### 建议操作
1. ...
2. ...
```

---

## Step 3：输出差异并继续执行

将差异报告输出给用户，作为变更前摘要记录；**默认直接继续执行修改，不等待用户确认**。只有当检测到“设计变更将覆盖用户逻辑”这类高风险冲突时，才暂停并提示用户手动处理。

---

## Step 4：执行变更

### 4.1 变更原则

1. **最小化修改** — 只改变化的部分，不重写无变化区域
2. **保留自定义逻辑** — 用户手动添加的事件处理、业务逻辑不得覆盖
3. **保持 import 整洁** — 删除不再使用的 import，添加新 import
4. **保留注释** — 用户添加的注释必须保留

### 4.2 基于 AST 的智能代码合并

变更同步的核心难点：如何更新 AI 生成的样式/结构代码，同时不破坏开发者手动添加的业务逻辑。

**必须在逻辑上区分以下两类代码区域：**

**🤖 AI 生成区域（可安全更新）：**
- JSX 结构与 `className` 属性
- Tailwind 类名字符串
- 静态资源 `import` 语句（如 `import xxx from '@/assets/...'`）
- 组件 props 的默认值与类型定义中的样式相关字段
- `data-figmanode` 标记的元素结构

**👤 用户注入区域（必须保留）：**
- `useEffect` / `useCallback` / `useMemo` 等 Hook 逻辑
- `onClick` / `onChange` 等事件处理函数体（非空函数）
- API 调用与异步数据获取（`fetch` / `axios` / 自定义 hooks）
- 条件渲染的业务判断逻辑（`if` / 三元表达式中的非样式判断）
- 开发者添加的注释与 `TODO` 标记
- 自定义的 `interface` 字段（非 AI 原始生成的）

**合并策略：**

1. 定位变更目标：通过 `data-figmanode` 属性或 Figma Node ID 注释，找到代码中对应的 JSX 节点
2. 识别代码归属：检查目标节点及其子树中，哪些是 AI 生成的结构/样式代码，哪些是用户注入的逻辑代码
3. 精确替换：仅修改 AI 生成区域（如 `className` 字符串、JSX 结构、import 路径），完整保留用户注入区域
4. 冲突处理：如果设计变更导致 JSX 结构调整（如节点删除），且该节点内包含用户逻辑，**必须暂停并提示用户手动处理**

**基于 @d2c 标记的精确替换（增强策略）：**

当代码中包含 `@d2c-start/@d2c-end` 和 `@user-zone/@user-zone-end` 标记时，使用以下增强合并策略：

```
1. 扫描代码中的 @d2c-start/@d2c-end 标记对
2. 对每个 @d2c 区域：
   a. 通过 (node: {id}) 关联 Figma 节点
   b. 如果该节点在新设计中有变化 → 重新生成该区域的代码
   c. 如果该节点在新设计中无变化 → 保持不变
3. 对每个 @user-zone/@user-zone-end 区域：
   a. 完整保留，不做任何修改
   b. 即使其前后的 @d2c 区域被替换，也必须保留
4. 新增的 Figma 节点 → 在对应位置插入新的 @d2c 区域
5. 删除的 Figma 节点 → 移除对应的 @d2c 区域，但如果紧邻 @user-zone，需提示用户确认
```

**示例 — 区域级精确替换：**

```tsx
// 变更前
{/* @d2c-start: HeroSection (node: 1:100) */}
<section className="py-12 bg-gray-50">...</section>
{/* @d2c-end: HeroSection */}

{/* @user-zone: 自定义数据加载逻辑 */}
useEffect(() => { fetchData(); }, []);
{/* @user-zone-end */}

// 变更后（设计变更了 HeroSection 的背景色和间距）
{/* @d2c-start: HeroSection (node: 1:100) */}
<section className="py-16 bg-white">...</section>  ← 仅此区域被替换
{/* @d2c-end: HeroSection */}

{/* @user-zone: 自定义数据加载逻辑 */}
useEffect(() => { fetchData(); }, []);  ← 完整保留
{/* @user-zone-end */}
```

**示例 — 圆角从 8px 变更为 12px：**

```
变更前：<div className="flex flex-col gap-4 rounded-lg p-6" data-figmanode="1:234">
变更后：<div className="flex flex-col gap-4 rounded-xl p-6" data-figmanode="1:234">

✅ 仅修改 className 中的 rounded-lg → rounded-xl
✅ 组件内的 useEffect、onClick 等逻辑完整保留
❌ 不会重写整个组件文件
```

### 4.3 变更手法

- 使用精确的 `replace_in_file` 操作，而非整文件重写
- 每次修改附带简短说明
- 修改后验证 TypeScript 编译通过

---

## Step 5：变更总结

输出变更总结：

```markdown
## 变更完成

### 已修改文件
- `src/components/XXX.tsx`：标题字号 24→28，新增搜索框
- `src/components/YYY.tsx`：删除弃用的链接区域

### 新增文件
- `src/components/SearchBar.tsx`：新提取的搜索组件

### 新增依赖
- 无 / 或列出新增的图标库图标、组件库组件等

### 需要关注
- Avatar 位置调整可能影响响应式布局，建议测试移动端

### Manifest 更新
- 记录本次变更命中的节点、修改文件、fallback 决策与回归结果
```
