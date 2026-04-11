# 代码规范（Code Standards）

所有生成的代码必须严格遵守以下规范。规范中的样式写法以 Tailwind CSS 为例，如项目使用其他样式方案，请输出对应语法。

> **与检查点系统的集成**：本文件中的规则 A-H 在 Step 4~10 中执行。代码输出后（CP-10），必须使用下方的**自检清单**逐项验证，结果纳入 CP-7.6 `LayoutVerification` 和 CP-11 `RegressionReport`。

---

## 一、文件与命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件文件（React） | PascalCase.tsx | `UserProfileCard.tsx` |
| 组件文件（Vue） | PascalCase.vue | `UserProfileCard.vue` |
| 页面文件 | PascalCase.tsx / .vue | `DashboardPage.tsx` |
| 工具函数 | camelCase.ts | `formatDate.ts` |
| 类型文件 | camelCase.ts | `userTypes.ts` |
| 常量文件 | camelCase.ts | `apiConstants.ts` |
| CSS 模块 | PascalCase.module.css | `UserCard.module.css`（仅 Tailwind 不够时） |

---

## 二、组件结构模板

根据项目技术栈选择对应模板。

### React + TypeScript 模板

```tsx
import React, { useState, useCallback } from 'react';
// 组件库导入根据实际检测结果生成
// import { Button, Input } from 'tdesign-react';
// import { Button, Input } from 'antd';

// ─── Types ──────────────────────────────────
interface ComponentNameProps {
  /** 属性说明 */
  title: string;
  /** 可选属性 */
  onAction?: () => void;
}

// ─── Constants ──────────────────────────────
const DEFAULT_PAGE_SIZE = 10;

// ─── Component ──────────────────────────────
const ComponentName: React.FC<ComponentNameProps> = ({ title, onAction }) => {
  const [value, setValue] = useState('');

  const handleClick = useCallback(() => {
    onAction?.();
  }, [onAction]);

  return (
    <div className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
      {/* 组件库组件使用 */}
    </div>
  );
};

export default ComponentName;
```

### Vue 3 + TypeScript 模板

```vue
<script setup lang="ts">
import { ref } from 'vue';
// 组件库导入根据实际检测结果生成

interface Props {
  /** 属性说明 */
  title: string;
  /** 可选属性 */
  onAction?: () => void;
}

const props = defineProps<Props>();
const emit = defineEmits<{ action: [] }>();

const value = ref('');
</script>

<template>
  <div class="flex flex-col gap-4 p-6">
    <h2 class="text-xl font-semibold text-gray-900">{{ title }}</h2>
    <!-- 组件库组件使用 -->
  </div>
</template>
```

---

## 三、CSS / 样式规范

以下规范根据项目样式方案自动适配：

### Tailwind CSS（如使用）

#### 类名顺序

```
1. 定位：relative, absolute, fixed, sticky
2. 显示：flex, grid, block, hidden
3. 弹性：flex-row, flex-col, flex-1, flex-wrap
4. 对齐：justify-*, items-*, self-*
5. 间距：gap-*, space-*
6. 尺寸：w-*, h-*, min-*, max-*
7. 边距：m-*, p-*
8. 背景：bg-*
9. 边框：border-*, rounded-*
10. 阴影：shadow-*
11. 文字：text-*, font-*, leading-*, tracking-*
12. 透明度：opacity-*
13. 过渡：transition-*, duration-*
14. 交互：cursor-*, hover:*, focus:*
```

#### 间距规范

```
Tailwind 间距基于 4px：
  0.5 = 2px  1 = 4px    1.5 = 6px  2 = 8px    2.5 = 10px
  3 = 12px   3.5 = 14px 4 = 16px   5 = 20px   6 = 24px
  7 = 28px   8 = 32px   9 = 36px   10 = 40px  11 = 44px
  12 = 48px  14 = 56px  16 = 64px  20 = 80px  24 = 96px
```

#### 间距容差规则（确定性规则，消除 AI 自由度）

**所有间距值必须严格按照以下容差规则转换，不允许 AI 自行"感觉"选择：**

```
规则 1：精确匹配（差值 = 0）
  设计稿值正好是 Tailwind 标准值 → 直接使用
  示例：16px → p-4 ✅

规则 2：容差 ≤ 2px（差值 ≤ 2px）
  取最近的 Tailwind 标准值
  示例：17px → p-4 (16px, 差1px) ✅
  示例：15px → p-4 (16px, 差1px) ✅
  示例：13px → p-3 (12px, 差1px) 或 p-3.5 (14px, 差1px) → 取更小的 p-3 ✅
  示例：18px → p-4 (16px, 差2px) 或 p-5 (20px, 差2px) → 取更小的 p-4 ✅

规则 3：容差 > 2px
  必须使用任意值 [Npx]
  示例：22px → p-[22px] ✅（最近标准值 20px 差 2px 以上）
  示例：38px → p-[38px] ✅（最近标准值 36px=9 和 40px=10，差 2px，取 p-[38px]）

规则 4：容差相等时取较小值
  当设计稿值恰好在两个标准值中间时，取较小的标准值
  示例：14px → p-3 (12px) 和 p-4 (16px) 差都是 2px → 取 p-3.5 (14px)
  如果有精确匹配的半值（如 3.5=14px），优先使用

规则 5：圆角的容差规则
  Tailwind 圆角标准值：
    rounded-sm=2px  rounded=4px  rounded-md=6px  rounded-lg=8px
    rounded-xl=12px  rounded-2xl=16px  rounded-3xl=24px  rounded-full=9999px
  容差 ≤ 1px 取标准值，> 1px 使用 rounded-[Npx]
  
  示例：
    Figma cornerRadius=8  → rounded-lg ✅（精确匹配）
    Figma cornerRadius=9  → rounded-lg ✅（差 1px，容差内）
    Figma cornerRadius=10 → rounded-[10px] ✅（差 2px，超出容差）
    Figma cornerRadius=14 → rounded-[14px] ✅（最近标准值 12px 差 2px）
```

**重要**：此容差规则是硬性约束，不允许 AI 凭"视觉判断"选择更大或更小的值。

#### 阴影精确还原规则（强制规则）

**所有阴影必须从 Figma 节点 effects 数据精确提取，禁止近似匹配 Tailwind 预设阴影。**

```
规则 1：从 effects 精确提取阴影参数
  Figma effects[] 中 type=DROP_SHADOW 或 INNER_SHADOW 的项：
    offset.x → offsetX (px)
    offset.y → offsetY (px)
    radius   → blur (px)
    spread   → spread (px)，Figma 可能不返回此字段，默认为 0
    color    → {r, g, b, a}，转为 rgba()

  转换公式：
    box-shadow: {offsetX}px {offsetY}px {blur}px {spread}px rgba(R,G,B,a)
    内阴影加 inset 前缀

  示例：
    Figma: {type: "DROP_SHADOW", offset: {x:0, y:4}, radius: 12, color: {r:0, g:0, b:0, a:0.08}}
    ✅ shadow-[0px_4px_12px_rgba(0,0,0,0.08)]
    ❌ shadow-md（Tailwind shadow-md = 0 4px 6px -1px rgba(0,0,0,0.1)，参数不同）

规则 2：禁止使用 Tailwind 预设阴影（除非精确匹配）
  Tailwind 的 shadow-sm/md/lg/xl/2xl 各有固定参数值。
  仅当 Figma 阴影参数与 Tailwind 预设参数完全一致时才可使用预设。
  参数不完全一致时，必须使用任意值语法 shadow-[...]。
  
  ❌ "看起来差不多是 shadow-md" → shadow-md
  ✅ 精确计算 → shadow-[0px_4px_12px_rgba(0,0,0,0.08)]

规则 3：多层阴影
  当 effects 中有多个 DROP_SHADOW/INNER_SHADOW 时，用逗号拼接：
  shadow-[0px_4px_12px_rgba(0,0,0,0.08),0px_1px_3px_rgba(0,0,0,0.04)]
  
规则 4：无阴影时禁止添加
  如果 Figma 节点 effects 为空或不含 shadow 类型 → 代码中不添加任何阴影类
  ❌ 禁止因为"卡片通常需要阴影"而自行添加 shadow-sm
```

#### 文本样式精确还原规则（强制规则）

**所有文本样式必须从 Figma TEXT 节点数据精确提取，禁止凭经验猜测。**

```
规则 1：字号（fontSize）— 必须精确匹配
  Tailwind 标准字号：
    text-xs=12px  text-sm=14px  text-base=16px  text-lg=18px
    text-xl=20px  text-2xl=24px  text-3xl=30px  text-4xl=36px
    text-5xl=48px  text-6xl=60px
  
  仅当 Figma fontSize 精确等于标准值时才使用预设（容差 = 0）：
    Figma fontSize=14 → text-sm ✅
    Figma fontSize=15 → text-[15px] ✅（不是 text-sm 也不是 text-base）
    Figma fontSize=13 → text-[13px] ✅（不是 text-xs）

规则 2：字重（fontWeight）— 必须精确匹配
  Figma fontWeight 数值映射：
    100=font-thin  200=font-extralight  300=font-light
    400=font-normal  500=font-medium  600=font-semibold
    700=font-bold  800=font-extrabold  900=font-black
  
  必须使用 Figma 返回的精确 fontWeight 值映射，不允许跨级近似。
  如 Figma fontWeight=500 → font-medium，禁止用 font-normal(400) 或 font-semibold(600)

规则 3：行高（lineHeightPx）— 必须精确匹配
  Tailwind 标准行高：
    leading-none=1  leading-tight=1.25  leading-snug=1.375
    leading-normal=1.5  leading-relaxed=1.625  leading-loose=2
  
  由于行高的精确性对文本排列影响很大，必须使用任意值：
    Figma lineHeightPx=22 → leading-[22px] ✅
    ❌ 禁止近似为 leading-normal 或 leading-tight
  
  例外：当 lineHeightPx / fontSize 精确等于标准倍数时可用预设（容差 ≤ 0.01）

规则 4：字间距（letterSpacing）— 必须精确匹配
  如果 Figma letterSpacing 不为 0：
    letterSpacing=0.5 → tracking-[0.5px]
    letterSpacing=-0.2 → tracking-[-0.2px]
  如果 letterSpacing 为 0 或未设置 → 不添加 tracking 类

规则 5：文本对齐 — 必须精确匹配
  textAlignHorizontal:
    LEFT → text-left（可省略，为默认值）
    CENTER → text-center
    RIGHT → text-right
    JUSTIFIED → text-justify

规则 6：文本装饰 — 必须精确匹配
  textDecoration:
    UNDERLINE → underline
    STRIKETHROUGH → line-through
    无/NONE → 不添加
```

#### 透明度精确还原规则（强制规则）

```
规则 1：节点级 opacity — 必须精确匹配
  Figma 节点的 opacity 字段（0~1）：
    opacity=1 → 不添加 opacity 类（默认值）
    opacity=0.8 → opacity-80
    opacity=0.5 → opacity-50
    opacity=0.6 → opacity-[0.6]（非标准 Tailwind 值必须用任意值）
  
  Tailwind 标准 opacity 值：0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
    55, 60, 65, 70, 75, 80, 85, 90, 95, 100
  
  仅当 round(opacity×100) 精确等于标准值时才使用预设。

规则 2：fill 颜色透明度 — 使用 rgba 或 Tailwind 透明度修饰符
  当 fills[].color.a < 1 时：
    a=0.5 → bg-[#XXXXXX]/50 或 bg-[rgba(R,G,B,0.5)]
    a=0.86 → bg-[rgba(R,G,B,0.86)]（非标准透明度必须用 rgba）
```

#### 边框精确还原规则（强制规则）

```
规则 1：边框宽度 — 必须精确匹配
  Figma strokeWeight 值映射：
    0 → 无边框（不添加 border）
    1 → border（Tailwind 默认 1px）
    2 → border-2
    其他值 → border-[Npx]
  
  ❌ Figma strokeWeight=1.5 → border（不精确）
  ✅ Figma strokeWeight=1.5 → border-[1.5px]

规则 2：边框颜色 — 必须精确匹配（同颜色规则）
  从 strokes[].color 精确提取，转换规则同 fills 颜色。
  ❌ 禁止近似为 border-gray-200
  ✅ 必须使用 border-[#XXXXXX]（除非与 Tailwind 预设精确一致）

规则 3：边框样式
  strokeDashes 为空或不存在 → solid（默认，不需要添加）
  strokeDashes 存在 → border-dashed
  
规则 4：单边边框
  当只有部分边有边框时（如仅底部）：
  检查节点的 individualStrokeWeights（top/right/bottom/left）
  仅设置了 bottom=1 → border-b border-[#color]
```

### 非 Tailwind 项目

如项目使用 CSS Modules / SCSS / Less / CSS-in-JS，则：
- 输出对应语法的 CSS 样式
- 类名使用 camelCase（CSS Modules）或 BEM 命名法
- 颜色值使用 CSS 变量或设计 Token（如有）

### 颜色规范

**所有颜色值必须精确还原 Figma 节点数据中的 fills/strokes 颜色，禁止自行近似匹配 Tailwind 内置色板。**

```
颜色值提取与转换规则（确定性规则，零 AI 自由度）：

规则 1：从 Figma 节点数据精确提取颜色
  Figma 返回 fills[].color 格式为 {r, g, b, a}，取值范围 0~1
  转换公式：R = round(r × 255), G = round(g × 255), B = round(b × 255)
  HEX = '#' + R.toString(16).padStart(2,'0') + G.toString(16).padStart(2,'0') + B.toString(16).padStart(2,'0')
  
  示例：{r: 0.098, g: 0.208, b: 0.329, a: 1} → #192F54
  ❌ 禁止近似为 text-gray-800 (#1f2937) 或 text-slate-800 (#1e293b)
  ✅ 必须使用 text-[#192F54]

规则 2：透明色使用 rgba 格式
  当 a < 1 时，必须使用 rgba 格式：
  Figma {r: 0, g: 0, b: 0, a: 0.6} → rgba(0,0,0,0.6)
  → Tailwind: bg-black/60 或 bg-[rgba(0,0,0,0.6)]
  → CSS: background-color: rgba(0,0,0,0.6)
  
  ❌ 禁止将 rgba(0,0,0,0.6) 近似为 text-gray-500
  ✅ 必须使用 text-black/60 或 text-[rgba(0,0,0,0.6)]

规则 3：颜色匹配优先级
  1. 项目 Design Token（token-aliases.json 中精确匹配 rawValue）→ var(--color-xxx)
  2. Figma Variable 引用（boundVariables 非空）→ var(--color-xxx)
  3. Figma 精确值 → bg-[#XXXXXX] / text-[#XXXXXX]（任意值语法）
  
  ⚠️ 关键变更：Tailwind 内置色板（如 gray-100, blue-600）仅当其 HEX 值
  与 Figma 数据精确一致（差值 = 0）时才可使用。差值 > 0 时必须使用任意值。
  
  示例：
    Figma fills color = #F5F7FA
    Tailwind gray-100 = #f3f4f6（差值 ≠ 0）
    ❌ bg-gray-100（颜色不一致）
    ✅ bg-[#F5F7FA]（精确匹配）

规则 4：多个 fills 层的颜色处理
  当 fills 数组有多个项时：
  a. SOLID 类型 → 取其 color 精确值
  b. IMAGE 类型 → 走图片下载流程
  c. GRADIENT 类型 → 走渐变解析流程（规则 F）
  d. 多层叠加 → 走复合视觉效果导出（规则 E）
```

### 响应式

```
断点使用 mobile-first：
  默认 → 手机
  sm:  → ≥640px
  md:  → ≥768px
  lg:  → ≥1024px
  xl:  → ≥1280px
  2xl: → ≥1536px

除非设计稿明确包含响应式标注，否则只生成桌面端布局。
```

### 多画板响应式推断

当 Figma 文件中包含多个不同尺寸的画板（Artboard）时，根据画板宽度自动推断响应式断点：

```
画板宽度映射规则：
  ≤ 480px   → 移动端基准（默认样式，无前缀）
  481-768px → 平板端（sm: 或 md: 前缀）
  769-1024px → 小桌面（lg: 前缀）
  ≥ 1025px  → 桌面端（xl: 或 2xl: 前缀）
```

**注意**：此推断的前提是设计师在 Figma 中提供了多端画板。若只有单一尺寸画板，则优先生成桌面端布局，并尝试以下智能响应式推断。

### 单画板响应式推断（智能降级）

当只有单一桌面端画板时，基于 Auto Layout 属性推断响应式行为。**此为渐进增强，不改变桌面端样式，仅添加小屏适配的响应式类名。**

| Auto Layout 特征 | 推断的响应式行为 | 生成的类名 |
|-----------------|----------------|-----------|
| `layoutSizingHorizontal: "FILL"` 且父节点也是 FILL | 使用 `w-full` 而非固定宽度 | `w-full` |
| 水平排列的子 FRAME ≥ 3 个，每个宽度接近 | 小屏自动换行或改为纵向 | `flex-wrap` 或 `lg:flex-row flex-col` |
| 固定宽度 ≥ 1200px 的根容器 | 居中约束 + 最大宽度 | `max-w-7xl mx-auto w-full` |
| 侧边栏(≤300px) + 内容区的二栏布局 | 小屏侧边栏隐藏 | `hidden lg:block`（侧边栏） |
| 图片 `layoutSizingHorizontal: "FILL"` | 自适应宽度 | `w-full object-cover` |
| 水平导航项 ≥ 5 个 | 小屏可滚动 | `overflow-x-auto` 或 `lg:flex hidden`（汉堡菜单） |
| 大标题 `fontSize ≥ 32px` | 小屏字号缩小 | `text-2xl lg:text-4xl` |
| 横向等宽卡片 ≥ 3 个 | 小屏单列或双列 | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` |

**保守原则：**
- 只在高置信度的模式下才添加响应式类名
- 不修改桌面端的视觉效果，仅添加小屏断点的适配
- 如果无法确定是否应该响应式 → 不添加，保持固定布局

---

## 四、TypeScript 规范

### 类型定义

```typescript
// ✅ 使用 interface 定义 props
interface UserCardProps {
  name: string;
  avatar?: string;
  role: 'admin' | 'member' | 'viewer';
  onEdit?: (id: string) => void;
}

// ✅ 使用 type 定义联合类型
type Status = 'active' | 'inactive' | 'pending';

// ❌ 禁止使用 any
// ❌ 禁止使用 @ts-ignore
```

### 事件处理

```typescript
// ✅ 正确：使用 useCallback 包裹
const handleChange = useCallback((value: string) => {
  setValue(value);
}, []);

// ❌ 不要内联复杂逻辑
```

> **JS 项目**：如果项目未使用 TypeScript，则使用 JSDoc 注释标注类型，确保类型信息可读。

---

## 五、Import 规范

```typescript
// 1. 框架核心
import React, { useState, useCallback, useMemo } from 'react';

// 2. 组件库（按项目实际使用的库，按字母排序）
import { Button, Card, Form, Input, Select } from '{detected-component-lib}';

// 3. 图标库（按字母排序）
import { SearchIcon, SettingIcon } from '{detected-icon-lib}';

// 4a. Service / Hook
import { getProductList } from '@/services/productService';
import { useProductData } from '@/hooks/useProductData';

// 4b. 类型（使用 type import）
import type { ProductInfo, Category } from './mock/types';

// 4c. 项目内部组件
import UserAvatar from '@/components/UserAvatar';
import { formatDate } from '@/utils/format';

// 5. 资源文件
import heroImage from '@/assets/images/hero.png';
```

---

## 六、确定性输出规范

为保证“统一输入 → 稳定输出”，以下规则必须固定，不允许不同执行者自由发挥：

### 6.1 节点遍历顺序

```text
所有兄弟节点按以下顺序处理：
  1. y 坐标升序
  2. x 坐标升序
  3. nodeId 字典序
```

### 6.2 Import 顺序

```text
1. 框架核心
2. 组件库
3. 图标库
4. Service / Hook
5. 类型定义
6. 内部组件 / 工具函数
7. 资源文件
```

### 6.3 类名顺序

```text
1. 布局（position / display / flex / grid）
2. 间距（gap / margin / padding）
3. 尺寸（width / height / min / max）
4. 视觉（background / border / radius / shadow）
5. 文本（font / text / leading / tracking）
6. 交互（opacity / transition / hover / focus）
```

### 6.4 文件与资源命名

- 页面入口固定为 `index.tsx` / `index.vue`
- 组件文件固定为 PascalCase
- 资源命名固定为：`<page>-<nodeId>-<purpose>`
- 同一节点重复导出时，必须命中同一个资源名，不得每次随机命名

### 6.5 歧义处理纪律

- 歧义组件优先命中显式映射
- 未命中显式映射时，优先已有组件，再退回组件库
- 只有在以上都失败时才允许原生实现
- 所有 fallback 必须写入 Manifest

## 七、数据层文件规范

### Mock 数据目录

所有从设计稿提取的业务数据必须放入独立的 `mock/` 目录（详见 `mock-data.md`）：

```
src/pages/{PageName}/
├── mock/
│   ├── types.ts         # TypeScript 接口定义
│   ├── {domain}Data.ts  # 按业务域的 mock 数据
│   └── index.ts         # 统一导出
```

### Service 层

```
src/services/
└── {domain}Service.ts   # 异步函数，初始返回 mock，预留 API 结构
```

---

## 八、文件大小限制

- **单文件最大 300 行**
- 超过时按以下优先级拆分：
  1. 可复用 UI 区块 → 独立组件
  2. 业务数据 → `mock/` 目录（必须分离）
  3. 类型定义 → 独立 `types.ts`
  4. 工具函数 → 独立 `utils.ts`

---

## 九、组件拆分确定性规则

**为消除不同人执行 Skill 时拆分结果不一致的问题，组件拆分必须遵守以下硬性规则：**

### 8.1 必须独立拆分的组件（强制规则）

以下 Figma 结构**必须**拆分为独立文件，不允许合并：

| Figma 层级 / 结构特征 | 拆分为 | 命名规则 |
|----------------------|--------|---------|
| 页面顶部的 FRAME（通常含 Logo + 导航 + 用户信息） | `TopBar.tsx` | 固定命名 `TopBar` |
| 次级导航栏（面包屑 / Tab 导航 / 搜索栏等） | `NavBar.tsx` | 固定命名 `NavBar` |
| 左侧/右侧固定宽度的侧边栏 | `Sidebar.tsx` 或 `{Side}Panel.tsx` | 左侧 `Sidebar`，右侧 `{功能名}Panel` |
| 页面主内容区的每个独立功能区块 | `{功能名}.tsx` | 按功能语义命名 |
| 底部栏（含版权、链接等） | `Footer.tsx` | 固定命名 `Footer` |
| 弹窗/抽屉/悬浮层 | `{功能名}Dialog.tsx` / `{功能名}Drawer.tsx` | 按功能命名 |

### 8.2 拆分边界判定规则

```
规则 1：Figma 根节点的直接子 FRAME → 每个子 FRAME 独立为一个组件文件
规则 2：子 FRAME 内代码预估 < 30 行 → 不拆分，内联在父组件中
规则 3：子 FRAME 内包含循环列表 (≥3 重复项) → 拆分为独立组件
规则 4：同一 FRAME 内功能差异明显的区域（如"文章内容"和"评分区"）→ 必须拆分
规则 5：重复出现在不同页面的结构 → 拆分到 src/components/ 作为通用组件
```

### 8.3 页面入口文件模板（强制结构）

页面入口 `index.tsx` 只负责组装子组件，**不包含任何业务 UI 代码**：

```tsx
// src/pages/{PageName}/index.tsx — 此文件为纯组装层
import TopBar from './TopBar';
import NavBar from './NavBar';
import Sidebar from './Sidebar';
import MainContent from './MainContent';
import RightPanel from './RightPanel';
import Footer from './Footer';

const {PageName}Page: React.FC = () => (
  <div className="flex flex-col min-h-screen" data-figmanode="{rootNodeId}">
    <TopBar />
    <NavBar />
    <div className="flex flex-1">
      <Sidebar />
      <MainContent />
      <RightPanel />
    </div>
    <Footer />
  </div>
);

export default {PageName}Page;
```

### 8.4 Figma 坐标到 HTML 布局的转换规则（强制规则）

**此节规则为硬性约束，所有 D2C 代码生成必须遵守。违反这些规则是导致"代码与设计稿不一致"的首要原因。**

#### 规则 A：嵌套关系必须通过坐标包含分析判定

```
在将 Figma 节点树转换为 HTML 之前，必须对每组兄弟节点执行坐标包含分析：

1. 计算每个节点的边界矩形 (x, y, x+w, y+h)
2. 如果节点 B 的中心点落在节点 A 的边界内，或 B 与 A 高度重叠 → B 必须嵌套为 A 的子元素
3. 嵌套后重新计算 B 相对于 A 的偏移量

常见错误案例：
  ❌ 进度条上的圆点作为进度条的兄弟元素独立定位
  ✅ 圆点嵌套在进度条内部，top:50% + translateY(-50%) 垂直居中
  
  ❌ 高亮底色区域与按钮文字作为平级兄弟元素
  ✅ 按钮文字嵌套在高亮底色区域内部

跨模块边界元素判定：
  当元素坐标跨越两个相邻模块边界时，禁止仅凭坐标距离判断归属。
  必须按优先级判定：① 视觉语义关系（与哪个模块内容对齐/并排） > ② Figma 节点层级 > ③ 坐标重叠面积。
  
  ❌ 图标紧邻上方模块底部 → 直接归属上方模块（仅看坐标距离）
  ✅ 图标与下方模块标题水平对齐 → 归属下方模块（视觉语义优先）
```

#### 规则 B：文档流优先于绝对定位

```
判定标准（按优先级）：

1. 顺序堆叠的兄弟元素 → 必须使用文档流（flex-col 或正常流）
   判定条件：A.y + A.height ≈ B.y（误差 ≤ 2px），且 A 和 B 不重叠
   ❌ <div class="absolute top-[60px]">
   ✅ 正常流中顺序排列

2. 等间距排列的同级元素 → 必须使用 flex + gap
   判定条件：相邻元素间距相同
   ❌ 每个元素 absolute + left 精确定位
   ✅ 父容器 flex + gap-N

3. 与其他元素重叠的浮动/覆盖元素 → 使用 absolute 定位
   判定条件：节点与兄弟节点坐标范围有交集

4. 父容器内精确定位的非重叠元素 → 优先 flex/grid 布局，absolute 为最后手段
```

#### 规则 C：容器尺寸与内容尺寸必须分离

```
当一个节点的子节点尺寸小于自身时，必须区分：
  - 外层容器尺寸 → 应用于 button/div 的 width/height
  - 内层内容尺寸 → 应用于 img/svg/text 的 width/height

  ❌ <button><img class="w-9 h-9" /></button>（容器 36px 直接赋给图标）
  ✅ <button style={{width:36,height:36}}><img class="w-4 h-4" /></button>（容器 36px，图标 16px）
```

#### 规则 D：百分比定位必须确认参照物

```
将绝对坐标转为百分比时：
  百分比 = (元素坐标 - 直接父容器起始坐标) / 直接父容器尺寸 × 100%

  ❌ 用页面根节点坐标直接算百分比（参照物错误）
  ✅ 先减去直接父容器的起始坐标，再除以父容器尺寸
```

#### 规则 E：复合视觉效果必须整体导出为图片（禁止 CSS 模拟）

```
判定条件（满足任意一条即适用此规则）：
  1. 单节点 fills 包含 IMAGE + GRADIENT 混合（≥ 2 种类型）
  2. fills 中 IMAGE 类型包含 cropTransform 裁剪矩阵
  3. 单节点 fills 长度 ≥ 3 且包含 IMAGE 和 GRADIENT
  4. GROUP 内多个渐变 RECTANGLE 坐标重叠 > 80%
  5. 节点含非标准 blendMode

处理方式：
  ✅ 使用 download_figma_images 导出整个节点为 PNG @2x
  ✅ 代码中用 <img> 或 CSS background-image 引用
  ❌ 禁止用 CSS linear-gradient + background 多层叠加模拟
  ❌ 禁止在模拟效果不佳时反复调整渐变参数
  ❌ 禁止将复合节点拆解为子层分别导出再叠加

示例（毛玻璃容器 + 复合背景图）：
  <div className="relative rounded-lg overflow-hidden"
    style={{ backdropFilter: 'blur(24px)', boxShadow: '...' }}>
    <img src={bgComposite} alt="" aria-hidden="true"
      className="absolute inset-0 w-full h-full" style={{ objectFit: 'fill' }} />
    <div className="relative z-10">{/* 内容 */}</div>
  </div>
```

#### 规则 F：渐变还原纪律（禁止自由发挥）

```
当节点只有简单渐变（单层标准角度渐变，色标 ≤ 3 个）允许 CSS 还原时，
必须严格遵守以下纪律：

规则 1：色标位置必须严格按 Figma 数据
  Figma 数据：linear-gradient(180deg, rgba(244,248,251,1) 77%, rgba(244,248,251,0.4) 90%, ...)
  ✅ 代码中使用完全相同的色标位置：77%、90%
  ❌ 禁止凭感觉调整为 60%→80% 或 50%→70%

规则 2：终止色必须与相邻区域同色系
  如果渐变终止色（最后一个色标）的色相与相邻元素背景色差异 > 30°（HSL 色相）：
  ✅ 将终止色修正为相邻区域的同色系（保持相同色相，仅透明度为 0）
  示例：相邻区域背景 rgba(240,246,255,0.86) → 终止色应为 rgba(240,246,255,0)
  ❌ 不应使用 rgba(145,147,149,0)（灰色系 ≠ 蓝色系）

规则 3：CSS 还原失败时的止损策略
  如果 CSS 渐变效果经 1 次调整仍与设计稿有明显差异：
  ✅ 立即改为整体导出图片（止损）
  ❌ 禁止继续调整渐变参数进行第 2 次、第 3 次尝试
  （每次调整都是基于猜测，无法保证收敛到正确结果）
```

#### 规则 G：坐标驱动布局（强制规则）

> **此规则解决"忽略坐标信息直接凭感觉用流式布局"导致的布局偏移问题。**

```
核心原则：Figma 返回的坐标数据是布局还原的「黄金标准」，不是可选参考。

规则 1：必须先读坐标，再选布局方案
  ❌ 错误流程：看到多个子元素 → 直接用 flex-col 排列 → 发现间距不对 → 调整 gap
  ✅ 正确流程：读取每个子元素的 (x, y, w, h) → 分析排列关系 → 选择 flex/grid/absolute → 验证

规则 2：坐标交叉验证
  确定布局方案后，必须用坐标反算预期位置，与设计稿对比。
  如果偏差 > 4px → 布局方案有误，必须修正。
  
  示例：
    子元素 A (x:370, y:317) 和 B (x:522, y:325)
    y 值相差仅 8px → 应该是同一行水平排列（flex-row），不是垂直堆叠（flex-col）
    ❌ 错误：放在 flex-col 中，A 在上 B 在下
    ✅ 正确：放在 flex-row 中，A 在左 B 在右，items-center 对齐

规则 3：同行判定标准
  两个元素是否在同一行（应使用 flex-row）：
  - |A.y - B.y| < min(A.h, B.h) / 2 → 同一行
  - |A.y - B.y| > max(A.h, B.h) → 不同行
  - 其他情况 → 检查垂直中心点是否接近

规则 4：间距必须从坐标计算，不能凭感觉
  水平间距 = B.x - (A.x + A.w)
  垂直间距 = B.y - (A.y + A.h)
  
  ❌ 错误："看起来间距差不多 16px" → gap-4
  ✅ 正确：计算 522 - (370+120) = 32px → gap-8

规则 5：设计稿中的重叠/变体识别
  如果两个元素坐标几乎完全相同（x, y, w, h 差异 < 2px），且内容相似：
  → 这是设计稿中的「状态变体」（如 hover/active 状态），只需取一个实现
  ❌ 错误：两个变体都渲染，导致内容重叠
  ✅ 正确：识别为同一元素的不同状态，只渲染默认状态
```

#### 规则 H：自适应转换（强制规则）

> **此规则解决"生成的页面只能在设计稿固定宽度下正确显示"的问题。**

```
核心原则：设计稿是固定宽度的参考，生成的代码必须能在不同屏幕宽度下正常显示。

规则 1：页面根容器禁止固定宽度
  ❌ <div style={{width: 1920}}>
  ❌ <div className="w-[1920px]">
  ✅ <div className="w-full min-h-screen">

规则 2：全宽区域使用 width: 100%
  全宽区域定义：元素宽度 ≈ 设计稿根节点宽度（±5%）
  ❌ <section className="w-[1920px]">
  ✅ <section className="w-full">

规则 3：居中内容区使用 max-width + 居中
  判定条件：左右边距对称（(根宽度 - 元素宽度) / 2 ≈ 元素 x 坐标）
  ❌ <div className="w-[1180px] ml-[370px]">
  ✅ <div className="max-w-[1180px] mx-auto w-full px-4">
  
  ⚠️ 注意：px-4 提供小屏幕下的安全边距（16px），防止内容贴边

规则 4：内容区子元素使用弹性宽度
  当子元素的父容器已经是 max-width 居中时，子元素应跟随父容器弹性伸缩：
  ❌ <div className="w-[1068px]">（固定宽度，小屏溢出）
  ✅ <div className="w-full">（跟随父容器缩放）
  
  例外：以下情况可保留固定宽度：
  - 按钮、头像、图标等小组件（width < 200px）
  - 有明确固定尺寸语义的元素（如 120×120 的封面图）
  - 明确需要固定比例的元素（如 16:9 视频容器，但使用 aspect-ratio）

规则 5：超宽背景处理
  设计稿中宽度超过根节点的装饰性背景（如 2560px 宽的 Hero 背景）：
  ❌ <img style={{width: 2560, marginLeft: -320}}>（固定偏移，小屏异常）
  ✅ 方案一：父容器 overflow-hidden + 图片 object-fit: cover + width: 100%
  ✅ 方案二：背景图用 CSS background: url() center/cover

规则 6：水平定位转换
  设计稿中通过 x 坐标实现的水平定位，必须判断意图后转换：
  ❌ left: 370px（固定定位，小屏偏移）
  ✅ 如果意图是居中 → margin: auto
  ✅ 如果意图是左对齐 → flex 容器内的子元素
  ✅ 如果意图是与其他元素对齐 → 同一 flex 容器中
```

#### 规则 I：图片导出粒度必须向上回溯（强制规则）

> **此规则解决"组合视觉元素只导出了一个子节点图片，丢失了外层装饰效果"的问题。**

```
核心原则：当一个 IMAGE fill 节点是某个视觉组合的一部分时，必须导出父容器而非叶子节点。

规则 1：向上回溯检测
  当扫描到一个包含 IMAGE fill 的节点时，必须向上检查其父节点：
  如果父节点满足以下任意条件 → 导出父节点而非当前节点：
    a. 父节点有 ≥ 2 个子节点，且其他子节点是装饰性 RECTANGLE（fills 为半透明/渐变/纯色）
    b. 父节点的子节点之间有坐标重叠（堆叠效果）
    c. 父节点名称不含 "Frame" / "Group"（说明设计师给了语义命名）

  示例：
    节点 640:1650 (Frame 2119902474) 包含：
      640:1651~1655 — 5 个 RECTANGLE（堆叠书本装饰）
      640:1656 — 1 个 IMAGE fill 图片

    ❌ 错误：扫描到 640:1656 有 IMAGE fill → 只导出 640:1656（丢失书本装饰）
    ✅ 正确：向上检查 640:1650 → 发现有 5 个装饰子节点 → 导出 640:1650 整体

规则 2：导出粒度决策表
  | 场景 | 导出节点 | 原因 |
  |------|---------|------|
  | IMAGE 节点是唯一子节点 | 导出 IMAGE 节点本身 | 无组合效果 |
  | IMAGE 节点有装饰性兄弟节点 | 导出父容器 | 保留组合效果 |
  | IMAGE 节点的父节点有阴影/模糊等 effects | 导出父容器 | 保留视觉效果 |
  | IMAGE 节点的兄弟有坐标重叠 | 导出父容器 | 堆叠效果 |

规则 3：验证步骤
  导出图片后，必须将导出结果与 Figma 中该区域的视觉效果对比。
  如果导出图片缺少了设计稿中可见的装饰元素 → 说明导出粒度不够，向上一级重新导出。
```

#### 规则 J：IMAGE-SVG 节点的 fills 语义（强制规则）

> **此规则解决"将 SVG 图标的容器背景色误判为图标填充色"的问题。**

```
核心原则：当节点 type 为 IMAGE-SVG 且 fills 非空时，fills 描述的是承载该 SVG 的容器背景，
         不是 SVG 图形本身的填充色。

规则 1：IMAGE-SVG + fills + borderRadius → 容器样式
  如果节点同时满足：
    - type 为 IMAGE-SVG（SVG 图标组件）
    - fills 不为空（如 #FFFFFF）
    - borderRadius > 0（如 24px）
  → fills 是容器的背景色，borderRadius 是容器的圆角
  → 代码中应生成「容器 div + 内部 SVG 图标」，而非将 fills 作为 SVG 颜色

  示例（chevron-up 图标）：
    节点数据：type=IMAGE-SVG, fills=#FFFFFF, borderRadius=24px,
             effects=boxShadow(0px 3px 7px rgba(55,99,170,0.1))

    ❌ 错误：<ChevronUpIcon style={{ color: '#FFFFFF' }} />
             （把容器背景色当成了图标颜色，图标变白色看不见）
    ✅ 正确：
      <span className="flex items-center justify-center rounded-full bg-white"
            style={{ width: 24, height: 24, boxShadow: '...' }}>
        <ChevronUpIcon size="14px" style={{ color: 'rgba(0,0,0,0.4)' }} />
      </span>

规则 2：判定 SVG 图标本身的颜色
  IMAGE-SVG 节点的实际图标颜色不在 fills 中，应通过以下方式确定：
  a. 查看子节点的 fills（SVG path 的填充色）
  b. 如果子节点也是白色 → 说明设计稿中图标确实是白色（如白底上的白色图标不合理 → 使用灰色兜底）
  c. 兜底色：rgba(0,0,0,0.4)（中灰色，在白色容器上可见）
```

#### 规则 K：交互状态不可推断警告（强制规则）

> **此规则解决"将 hover 态的 fills 当成默认态样式"的问题。**

```
核心原则：Figma 返回的是静态快照数据，fills/strokes/effects 无法区分是
         "默认态样式"还是"hover/active/focus 态样式"。

规则 1：高频误判场景识别
  以下场景中的 fills 很可能是交互态而非默认态，必须标记警告：
  a. 列表项/卡片的浅色背景（如 #F7FAFF, #F5F7FA, rgba(x,x,x,0.03~0.08)）
     → 大概率是 hover 态背景
  b. 按钮的深色背景（比主题色更深 10~20%）
     → 大概率是 hover/active 态
  c. 边框颜色比默认态更深
     → 大概率是 focus 态

规则 2：处理策略
  当检测到上述高频误判场景时：
  a. 不在默认态应用该 fills
  b. 改为 hover: 伪类应用：hover:bg-[#F7FAFF]
  c. 在代码注释中标注：
     {/* ⚠️ 此背景色来自设计稿 fills，疑似 hover 态，已改为 hover 触发 */}

规则 3：确定性兜底
  如果无法确定某个 fills 是默认态还是交互态：
  a. 列表项/可点击行 → 默认无背景，hover 时显示浅色背景
  b. 按钮 → 使用组件库的默认主题色，不使用设计稿中可能的 hover 色
  c. 输入框 → 默认白色背景 + 边框，focus 时加深边框色

规则 4：设计师标注优先
  如果设计稿中通过以下方式明确标注了交互状态，以标注为准：
  a. Figma 变体组件（State=Default / State=Hover）
  b. 节点命名包含状态关键词（如 "row/hover", "btn-active"）
  c. 用户在请求中明确说明
```

#### 规则 L：absolute 覆盖层内部禁止 h-full 独占（强制规则）

> **此规则解决"absolute inset-0 覆盖层内的第一个子容器使用 h-full 独占高度，导致后续子元素被 overflow-hidden 裁切不可见"的问题。**

```
核心原则：当 absolute inset-0 覆盖层内部有多个垂直排列的子 section 时，
         必须使用 flex-col 分配空间，禁止任何子元素使用 h-full 独占高度。

规则 1：覆盖层内多子节点 → 必须 flex-col
  当 absolute inset-0（或 absolute top-0 left-0 w-full h-full）容器内
  有 ≥ 2 个垂直排列的子 div 时：
  ✅ 父容器添加 flex flex-col
  ✅ 第一个子容器用自然高度（不设 h-full）
  ❌ 第一个子容器设 h-full（独占全部高度，后续子元素被挤出）

  示例（Hero 背景上叠加课程信息 + 按钮行）：
    ❌ 错误：
      <div className="absolute inset-0">
        <div className="flex items-start h-full">  ← h-full 独占
          ...课程信息 + 进度...
        </div>
        <div>  ← 被挤到容器外，overflow-hidden 裁切
          <button>繼續學習</button>
        </div>
      </div>
    
    ✅ 正确：
      <div className="absolute inset-0 flex flex-col">  ← flex-col 分配
        <div className="flex items-start">  ← 自然高度
          ...课程信息 + 进度...
        </div>
        <div>  ← 正常排在下方
          <button>繼續學習</button>
        </div>
      </div>

规则 2：overflow-hidden + absolute 组合警告
  当一个容器同时满足以下条件时，必须检查子元素是否可能被裁切：
    a. 容器有 overflow-hidden（或 overflow: hidden）
    b. 容器内有 absolute 定位的子层
    c. absolute 子层内有多个垂直排列的 section
  
  检查项：
    - absolute 子层内是否有 h-full / h-screen 子元素？
    - 如果有 → 后续兄弟元素是否会被挤出 absolute 容器的高度范围？
    - 如果会 → 移除 h-full，改为 flex-col 自然分配

规则 3：单子节点例外
  当 absolute 覆盖层内只有 1 个子节点时，h-full 是合理的：
    ✅ <div className="absolute inset-0">
         <div className="h-full flex items-center justify-center">
           ...居中内容...
         </div>
       </div>
  
  此规则仅在有 ≥ 2 个子节点时生效。
```

#### 规则 M：组件视觉数据优先于 variant 名称（强制规则）

> **此规则解决"Figma 组件 variant 命名与实际视觉效果矛盾时，代码错误地跟随 variant 名称"的问题。**

```
核心原则：当 INSTANCE 节点的 variant 名称（componentProperties 中的 VARIANT 类型字段）
         与该节点的 fills/strokes/effects 等实际视觉数据矛盾时，
         必须以视觉数据为准生成代码。

规则 1：fills 优先于 variant 名称
  如果组件的 variant 字段为 "outline 描边按钮"，但 fills 为 #F2F3FF（浅蓝色实底）：
  ❌ 错误：<Button variant="outline">（生成描边按钮，有边框无背景）
  ✅ 正确：根据 fills=#F2F3FF 生成浅蓝底按钮样式

  判定方法：
    a. 读取 INSTANCE 节点的 fills 数组
    b. 如果 fills 是非白非透明的实色 → 该组件有实色背景，不是"描边"
    c. 如果 fills 是白色 (#FFFFFF) → 可能是真正的描边/幽灵按钮
    d. 以 fills 的实际颜色值决定背景色，而非 variant 名称

规则 2：strokes 优先于 variant 名称
  如果 variant 名称暗示"无边框"，但 strokes 非空 → 代码中必须添加边框

规则 3：尺寸数据优先于 size variant
  如果 variant 的 size="small"，但节点实际尺寸为 40×40（不符合组件库 small 尺寸）：
  → 使用自定义尺寸而非组件库的 size="small"

规则 4：检查流程
  对每个 INSTANCE 节点，必须执行以下对照：
  1. 读取 componentProperties 中所有 VARIANT 类型字段
  2. 读取节点的 fills、strokes、effects、borderRadius
  3. 如果 VARIANT 名称暗示的视觉效果与 fills/strokes 不一致
     → 以 fills/strokes 为准
     → 在 CP-9.5 回查表中标注 "⚠️ variant 名称与视觉数据矛盾，以视觉数据为准"

示例（实际案例）：
  Figma 数据：
    componentProperties: variant 类型 = "outline 描边按钮"
    fills: Brand 品牌/Brand1-Light (#F2F3FF)
    text: "去複習"

  ❌ 错误代码：
    <Button variant="outline" theme="primary" size="small">去複習</Button>
    （TDesign outline 按钮：白底+蓝色边框，与设计稿不一致）

  ✅ 正确代码：
    <span className="px-2 py-0.5 rounded-[3px] bg-[#F2F3FF] text-[12px] text-[#0052D9]">
      去複習
    </span>
    （浅蓝底+蓝色文字，与 fills 数据一致）
```

#### 规则 N：逐节点属性读取禁止批量推断（强制规则）

> **此规则解决"看了第一个同类节点的属性，就假设其余同类节点属性都相同"的问题。**

```
核心原则：即使多个节点看起来结构相同（如多个章节头、多个课时行），
         每个节点的 textStyle/fills/effects 等属性必须独立从 Figma 数据中读取。

规则 1：禁止推断的场景
  以下属性即使在同类节点中也可能不同，必须逐个读取：
  a. textStyle（字号/字重可能不同，如章节一 18px vs 章节二 16px）
  b. fills（背景色可能不同，如已完成 vs 未完成的课时行）
  c. componentProperties（按钮文本可能不同，如"去複習" vs "去學習"）
  d. opacity（某些节点可能有独立透明度）
  e. effects（不同位置的阴影参数可能不同）

规则 2：安全推断的场景
  以下属性在同类节点中通常一致，可以在确认前 2 个节点一致后推断其余：
  a. layoutMode（同类容器的布局方向）
  b. padding（同类容器的内边距）
  c. gap（同类容器的子元素间距）
  但即使是安全推断，也必须在 CP-9.5 回查表中标注 "推断自节点 X"

规则 3：回查验证
  在 CP-9.5 中，必须至少抽检每类节点的首尾两个（第一个和最后一个）：
  - 如果首尾一致 → 中间节点可推断相同
  - 如果首尾不一致 → 必须逐个检查所有节点
```

### 8.5 命名约定

| 类型 | 命名模板 | 示例 |
|------|---------|------|
| 页面数据类型 | `{PageName}Data` | `DashboardData` |
| 区块 Props | `{ComponentName}Props` | `SidebarProps` |
| Mock 数据文件 | `{pageName}Data.ts` | `dashboardData.ts` |
| Service 文件 | `{pageName}Service.ts` | `dashboardService.ts` |
| Hook 文件 | `use{PageName}Data.ts` | `useDashboardData.ts` |
| 类型定义文件 | `types.ts`（统一） | `mock/types.ts` |

---

## 十、自适应响应式布局规范

> **设计稿通常基于固定宽度（如 1920px、1440px）设计，但生成的页面必须自适应不同屏幕宽度。此规范为强制规则。**

### 10.1 页面布局层次模型

```
┌─────────────────────────────────────────────────────┐
│ 视口层 (viewport)：width: 100vw                      │
│   ┌─────────────────────────────────────────────┐   │
│   │ 全宽背景层：width: 100%                      │   │
│   │   ┌───────────────────────────────────┐     │   │
│   │   │ 内容约束层：max-w-[Npx] mx-auto   │     │   │
│   │   │   ┌─────────────────────────┐     │     │   │
│   │   │   │ 弹性内容：w-full / flex │     │     │   │
│   │   │   └─────────────────────────┘     │     │   │
│   │   └───────────────────────────────────┘     │   │
│   └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘

映射关系：
  视口层      → <body> 或页面根容器，w-full min-h-screen
  全宽背景层  → 背景色/背景图容器，w-full overflow-hidden
  内容约束层  → max-w-[{设计稿内容宽度}px] mx-auto w-full px-4
  弹性内容    → 内部元素，w-full 或 flex-1
```

### 10.2 从设计稿坐标推导内容宽度

```
计算方法：
1. 根节点宽度 = 设计稿画布宽度（如 1920px）
2. 内容区域宽度 = 设计稿中最主要内容区域的宽度（如 1180px）
3. 内容区左偏移 = 内容区域的 x 坐标（如 370px）
4. 内容区右边距 = 根节点宽度 - 内容区左偏移 - 内容区宽度

如果 |内容区左偏移 - 内容区右边距| ≤ 10px：
  → 确认为居中布局
  → 代码：max-w-[{内容区宽度}px] mx-auto

如果左右不对称：
  → 可能有侧边栏
  → 代码：flex 布局 + 侧边栏固定宽度 + 主内容 flex-1
```

### 10.3 组件级自适应模板

```tsx
// ✅ 页面根容器
const PageRoot: React.FC = () => (
  <div className="w-full min-h-screen bg-gray-50">
    {/* 全宽背景区域 */}
    <section className="w-full overflow-hidden">
      <div className="relative">
        {/* 超宽背景图：min-width 保证小屏不留白 */}
        <img
          src={heroBg}
          alt=""
          aria-hidden="true"
          className="w-full h-auto object-cover"
          style={{ minWidth: '1200px' }}
        />
        {/* 内容叠加在背景上，居中约束 */}
        <div className="absolute inset-0">
          <div className="max-w-[1180px] mx-auto w-full h-full px-4">
            {/* Hero 内容 */}
          </div>
        </div>
      </div>
    </section>

    {/* 普通全宽区域 */}
    <section className="w-full bg-white">
      <div className="max-w-[1180px] mx-auto w-full px-4 py-8">
        {/* 居中内容 */}
      </div>
    </section>

    {/* 内容列表区域 */}
    <section className="w-full">
      <div className="max-w-[1180px] mx-auto w-full px-4">
        {/* 列表项：w-full 自适应 */}
        <div className="w-full rounded-lg bg-white shadow-sm p-6">
          {/* 卡片内容 */}
        </div>
      </div>
    </section>
  </div>
);
```

### 10.4 禁止的固定宽度模式

```
❌ 以下写法在生成的页面代码中禁止使用：

1. 页面级固定宽度
   ❌ <div style={{width: 1920}}> 或 className="w-[1920px]"
   ❌ <div style={{width: 1440}}> 或 className="w-[1440px]"

2. 内容区固定定位
   ❌ <div style={{marginLeft: 370}}> 或 className="ml-[370px]"
   ❌ <div style={{position: 'absolute', left: 370}}> 用于居中内容

3. 子元素固定宽度（当父容器可缩放时）
   ❌ <div className="w-[1068px]"> 在 max-w-[1180px] 容器内
   ✅ <div className="w-full"> 替代

4. 超宽元素固定偏移
   ❌ <img style={{width: 2560, marginLeft: -320}}>
   ✅ 父容器 overflow-hidden + 图片 w-full object-cover
```

### 10.5 响应式断点策略

```
当设计稿只有单一宽度画板时，使用以下渐进式策略：

1. 默认生成桌面端布局（max-width 约束 + 居中）
2. 添加以下最小化响应式规则：
   - 内容区容器始终有 px-4 水平内边距（小屏安全间距）
   - 超宽背景图使用 object-cover 而非固定偏移
   - 多列布局在小屏下可叠为单列：
     lg:flex-row flex-col（≥1024px 横排，以下竖排）
   - 导航栏在小屏下可折叠：
     hidden lg:flex（≥1024px 显示，以下隐藏）

注意：不做过度的响应式推断。只做「不溢出、不留白、可阅读」的最低保障。
```

---

## 十一、布局错误止损策略

> **当发现布局方案整体错误时，必须立即止损，禁止在错误基础上打补丁。**

### 11.1 识别"基础方案错误"的信号

```
以下情况说明布局基础方案有误，不应继续调整：

信号 1：越改越差
  修改了一个元素的位置 → 影响了相邻元素 → 修复相邻元素 → 又影响其他元素
  → 这是"改 A 坏 B"的恶性循环，说明布局方案本身有问题

信号 2：大量使用 absolute 定位
  如果页面中超过 50% 的元素使用 absolute 定位，且这些元素不是覆盖/悬浮类型
  → 说明应该使用流式布局（flex/grid）而非绝对定位

信号 3：间距与设计稿偏差 > 20px
  多个元素的间距偏差超过 20px，说明容器层级或对齐方式选择错误

信号 4：坐标数据未被使用
  如果生成的代码中没有任何数值来自设计稿坐标（boundingBox 或 locationRelativeToParent），
  说明布局是"凭感觉"写的，必须重新基于坐标数据生成
```

### 11.2 止损处理流程

```
当检测到上述信号时：

1. 停止当前的补丁式修复
2. 回退到 Step 4.0（坐标系统建立）
3. 重新分析区域坐标表
4. 重新确定每个区域的布局方案
5. 重写该区域的代码（而非在旧代码上修补）

⚠️ 关键：
  - 推翻重写 ≠ 重写整个页面，只需重写出问题的区域
  - 重写时复用之前的坐标分析结果，不需要重新获取 Figma 数据
  - 重写后必须执行 7.6 的坐标-布局一致性验证
```

---

## 十二、代码输出自检清单（CP-10 前强制执行）

> **在完成所有组件代码编写后、输出 CP-10 产物前，必须逐项执行以下自检。** 此清单将规则 A-H 转化为可逐条打勾的检查项，防止遗漏。

```
□ [A] 嵌套关系：所有通过坐标包含分析判定的父子关系，在代码中是否正确嵌套？
□ [B] 文档流优先：顺序堆叠的兄弟元素是否使用文档流（非 absolute）？
□ [C] 尺寸分离：容器尺寸与内容尺寸是否正确分离（如 36px 按钮内 16px 图标）？
□ [D] 百分比参照物：所有百分比定位是否基于直接父容器而非根节点？
□ [E] 复合视觉效果：预检标记的复合节点是否全部导出为图片（无 CSS 模拟）？
□ [F] 渐变纪律：简单渐变的色标位置是否严格按 Figma 数据，终止色是否同色系？
□ [G] 坐标驱动：每个区域的布局方案是否基于坐标数据选择（非凭感觉）？
       间距值是否从坐标计算得出（非估算）？
□ [H] 自适应：页面根容器是否 w-full（非固定宽度）？
       内容区是否 max-width + mx-auto（非固定 margin-left）？
       内容子元素是否弹性宽度（非固定值）？
□ [I] 图片粒度回溯：所有导出的图片节点是否向上检查了父容器？
       组合视觉效果的图片是否导出了父容器而非叶子节点？
□ [J] IMAGE-SVG 语义：所有 IMAGE-SVG 节点的 fills 是否作为容器背景色处理？
       SVG 图标的颜色是否来自子节点 fills 而非父节点 fills？
□ [K] 交互状态：列表行/卡片的浅色背景是否标记为 hover 态（非默认态）？
       是否有交互状态无法判定的节点需要标注警告？
□ [L] 覆盖层布局：absolute inset-0 覆盖层内有多个垂直子 section 时，是否使用 flex-col？
       是否有子元素使用 h-full 导致后续兄弟被挤出？
       overflow-hidden 容器内的 absolute 子层是否有子元素被裁切风险？
□ [L-颜色] 精确还原：所有颜色值是否从 Figma fills/strokes 精确提取？
       是否有颜色被近似替换为 Tailwind 内置色板？（禁止）
□ [L-阴影] 精确还原：所有阴影是否从 Figma effects 精确提取为任意值？
       是否有阴影被近似替换为 shadow-sm/md/lg？（禁止，除非参数完全一致）
□ [L-文本] 精确还原：字号/行高/字间距是否精确匹配 Figma 数据？
       非标准字号是否使用 text-[Npx]？行高是否使用 leading-[Npx]？
□ [L-圆角] 精确还原：圆角值是否在 ≤1px 容差内匹配？超出是否用 rounded-[Npx]？
□ [L-边框] 精确还原：边框宽度/颜色是否精确匹配 strokes 数据？
□ [L-透明度] 精确还原：节点 opacity 和 fill 透明度是否精确还原？
□ [CP-4.1] 行聚类：y 坐标接近的兄弟节点是否放入了同一个 flex-row 容器？
□ [CP-4.1] 间距精算：相邻模块之间的间距是否从坐标差精确计算并显式插入？
□ [CP-4.1] padding 精算：无 Auto Layout 容器的 padding 是否从坐标差计算（非估算）？
□ [间距] 所有间距是否符合容差规则（≤2px 取标准值，>2px 用任意值）？
□ [类名] 类名顺序是否为：布局→间距→尺寸→视觉→文本→交互？
□ [Import] Import 顺序是否为：框架→组件库→图标→Service→类型→内部→资源？
□ [行数] 所有文件是否 ≤ 300 行？
□ [标记] 主要组件是否有 @d2c-start/@d2c-end + data-figmanode？
□ [数据来源] 所有视觉属性值（颜色/阴影/字号/圆角/间距/边框等）是否均来自 Figma 节点数据？
       是否有任何值是凭经验编造的？（禁止）
□ [M] 组件视觉数据：所有 INSTANCE 节点的代码样式是否以 fills/strokes 数据为准？
       是否有组件因为 variant 名称（如"outline"）而使用了与 fills 矛盾的样式？（禁止）
□ [N] 逐节点属性：同类节点（多个章节头、多个课时行）的 textStyle/fills 是否逐个读取？
       是否存在"第一个是 X 所以全部是 X"的批量推断？（禁止）
□ [CP-9.5] 数据回查表：是否已输出 DataTracebackTable？所有行是否为 ✅？
```

**如有任何项不通过，必须在输出 CP-10 产物前修复。**
