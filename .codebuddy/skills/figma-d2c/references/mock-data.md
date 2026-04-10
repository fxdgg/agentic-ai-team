# MockData 解析与数据分离规范

将 Figma 设计稿中的展示数据从 UI 组件中完全分离，生成独立的 mockData 文件和 TypeScript 类型定义，使真实开发时只需替换数据源即可。

---

## 一、核心原则

1. **数据与视图分离** — 组件只负责渲染，不硬编码任何业务数据
2. **类型先行** — 先定义 TypeScript 接口，再填充 mock 数据
3. **就近替换** — mock 数据通过 hooks/service 层注入，替换时只改数据源，不改组件
4. **语义化命名** — 数据字段名应反映业务含义，而非设计稿视觉描述

---

## 二、数据识别规则

### 2.1 从 Figma 节点树中识别数据

遍历设计稿节点树时，以下内容应被识别为**业务数据**并提取到 mockData：

| 数据类型 | Figma 特征 | 提取方式 |
|---------|-----------|---------|
| **文本内容** | TEXT 节点的 `characters` 字段 | 直接提取文本值 |
| **列表/重复项** | 同一父节点下 ≥2 个结构相同的兄弟节点 | 提取为数组，每项的差异字段为数据字段 |
| **图片资源** | IMAGE fill 或独立的图片节点 | 提取为 `imageUrl` 字段（mock 阶段使用本地路径或占位图） |
| **数值** | 文本中包含数字（如 "128人已购"、"30分钟"） | 提取为数值字段 + 单位 |
| **状态标识** | 节点名称包含 active/selected/disabled 等关键词 | 提取为 boolean 或 enum 字段 |
| **嵌套结构** | 有层级关系的节点组（如分类 > 子分类 > 商品） | 提取为嵌套对象/数组 |

### 2.2 不应提取的内容

以下内容属于 **UI 结构**，不应作为 mockData 提取：

- 布局方向、间距、颜色等样式属性
- 纯装饰性文本（如分割线、装饰图标）
- 导航菜单的固定文案（如"首页"、"控制台"）→ 归入组件常量
- 空状态占位符

---

## 三、文件输出规范

### 3.1 目录结构

> **适配说明**：以下为默认目录约定。实际生成时应先扫描项目已有目录结构，沿用项目既有约定（如 `views/`、`composables/`、`api/` 等）。

**React 项目（默认）：**

```
src/
├── pages/
│   └── {PageName}/
│       ├── index.tsx              # 页面入口
│       ├── SectionA.tsx           # UI 组件（不含 mockData）
│       ├── SectionB.tsx           # UI 组件
│       └── mock/                  # ← 独立的 mock 目录
│           ├── types.ts           # TypeScript 类型定义
│           ├── {domain}Data.ts    # 业务域 mockData
│           └── index.ts           # 统一导出
├── services/                      # ← 后续真实 API 对接层
│   └── {domain}Service.ts         # API 请求函数（初始为 mock 实现）
└── hooks/                         # ← 数据获取 hooks
    └── use{Domain}Data.ts         # 封装数据获取逻辑
```

**Vue 项目：**

```
src/
├── views/
│   └── {PageName}/
│       ├── index.vue              # 页面入口
│       ├── SectionA.vue           # UI 组件
│       └── mock/
│           ├── types.ts
│           ├── {domain}Data.ts
│           └── index.ts
├── api/                           # ← 后续真实 API 对接层
│   └── {domain}.ts
└── composables/                   # ← 数据获取 composables
    └── use{Domain}Data.ts
```

### 3.2 命名规范（确定性规则）

**为确保不同执行者生成一致的文件名和类型名，命名必须遵循以下模板：**

| 文件类型 | 命名模板 | 示例 |
|---------|---------|------|
| 类型文件 | `types.ts`（固定） | `mock/types.ts` |
| Mock 数据文件 | `{pageName}Data.ts`（页面名小驼峰） | `dashboardData.ts`, `productListData.ts` |
| Service 文件 | `{pageName}Service.ts`（React）或 `{pageName}.ts`（Vue） | `dashboardService.ts` |
| Hook 文件 | `use{PageName}Data.ts`（页面名大驼峰） | `useDashboardData.ts` |

**类型命名模板：**

| 类型用途 | 命名模板 | 示例 |
|---------|---------|------|
| 页面总数据类型 | `{PageName}Data` | `DashboardData` |
| 列表项类型 | `{ItemName}Item` | `CourseItem`, `ChapterItem` |
| 区块 Props | `{ComponentName}Props` | `SidebarProps`, `TopBarProps` |
| 统计数据 | `{Domain}Stats` | `CourseStats`, `UserStats` |
| 配置/选项 | `{Domain}Config` / `{Domain}Option` | `FilterConfig`, `SortOption` |

**常量命名模板：**

| 常量用途 | 命名模板 | 示例 |
|---------|---------|------|
| 列表数据 | `{DOMAIN}_LIST` | `COURSE_LIST`, `CHAPTER_LIST` |
| 单例数据 | `{DOMAIN}_INFO` / `{DOMAIN}_STATS` | `COURSE_INFO`, `PAGE_STATS` |
| 配置常量 | `{DOMAIN}_CONFIG` | `FILTER_CONFIG` |
| 导航数据 | `NAV_ITEMS` / `MENU_ITEMS` | `NAV_ITEMS` |

---

## 四、类型定义规范

### 4.1 从 Figma 节点推断类型

根据节点树的层级结构和重复模式，自动推断 TypeScript 接口：

```typescript
// mock/types.ts

/** 商品信息 */
export interface Product {
  /** 商品标题 — 来自 TEXT 节点 */
  title: string;
  /** 价格描述 — 来自 TEXT 节点 */
  price: string;
  /** 商品图片 — 来自 IMAGE fill */
  image: string;
  /** 是否已收藏 — 来自节点名称中的 active 状态 */
  isFavorited?: boolean;
  /** 商品标签 — 来自节点结构差异（如热销/新品） */
  tag?: 'hot' | 'new' | 'sale';
}

/** 分类项 */
export interface Category {
  id: string;
  name: string;
  icon?: string;
  children?: Category[];
}

/** 订单项 */
export interface OrderItem {
  product: Product;
  quantity: number;
  subtotal: string;
}

/** 页面统计信息 */
export interface PageStats {
  totalCount: string;
  activeCount: string;
  growth: number;
}

/** 文章段落内容 */
export interface ContentSection {
  type: 'h2' | 'h3' | 'paragraph';
  content: string;
}
```

### 4.2 类型推断规则

| Figma 节点特征 | 推断为 TypeScript 类型 |
|---------------|---------------------|
| TEXT 节点，内容为纯文本 | `string` |
| TEXT 节点，内容为纯数字 | `number` |
| TEXT 节点，内容为 "xx人" / "xx分钟" 等带单位数值 | `string`（保留格式） 或拆分为 `value: number` + `unit: string` |
| 重复兄弟节点中的差异字段 | 数组元素的字段 |
| 节点名称含 active/selected | `boolean` 可选字段 |
| 嵌套子节点组 | 嵌套 interface |
| IMAGE fill | `string`（图片 URL） |
| 变体属性值 | 联合字面量类型 `'a' \| 'b' \| 'c'` |

---

## 五、Mock 数据文件规范

### 5.1 数据文件模板

```typescript
// mock/productData.ts
import type { Product, Category, PageStats } from './types';

// 从本地资源导入图片（mock 阶段）
import productImg1 from '@/assets/images/product-1.png';
import productImg2 from '@/assets/images/product-2.png';

/**
 * 页面统计信息
 * @source Figma Node 57:1958
 */
export const PAGE_STATS: PageStats = {
  totalCount: '1,280',
  activeCount: '856',
  growth: 12.5,
};

/**
 * 商品列表
 * @source Figma Node 57:1982
 */
export const PRODUCT_LIST: Product[] = [
  {
    title: '智能降噪耳机 Pro',
    price: '¥599',
    image: productImg1,
    isFavorited: true,
    tag: 'hot',
  },
  {
    title: '便携蓝牙音箱',
    price: '¥299',
    image: productImg2,
    tag: 'new',
  },
  // ...更多商品
];

/**
 * 分类列表
 * @source Figma Node 41:44
 */
export const CATEGORIES: Category[] = [
  {
    id: 'cat-1',
    name: '数码电子',
    children: [
      { id: 'cat-1-1', name: '耳机音箱' },
      { id: 'cat-1-2', name: '手机配件' },
    ],
  },
  // ...更多分类
];
```

### 5.2 统一导出入口

```typescript
// mock/index.ts
export * from './types';
export * from './productData';
// 按需导出更多数据文件
```

### 5.3 数据注释规范

每个导出的常量必须添加 JSDoc 注释，包含：
1. **业务含义** — 这是什么数据
2. **@source** — 对应的 Figma 节点 ID，格式 `Figma Node {nodeId}`
3. 可选 **@todo** — 标注后续需要对接的真实 API

```typescript
/**
 * 商品列表数据
 * @source Figma Node 57:1982
 * @todo 替换为 GET /api/products?category={categoryId}
 */
export const PRODUCT_LIST: Product[] = [...];
```

---

## 六、Service 层与 Hook 层（API 对接预留）

### 6.1 Service 层模板

初始生成时使用 mock 数据，预留 API 调用结构：

**React 项目：**

```typescript
// services/productService.ts
import {
  PRODUCT_LIST,
  CATEGORIES,
  PAGE_STATS,
} from '@/pages/{PageName}/mock';
import type { Product, Category, PageStats } from '@/pages/{PageName}/mock/types';

/**
 * 获取商品列表
 * @todo 替换为: const res = await fetch(`/api/products?category=${categoryId}`);
 */
export async function getProductList(categoryId?: string): Promise<Product[]> {
  // Mock 实现 — 替换时只需改这里
  return PRODUCT_LIST;
}

/**
 * 获取分类列表
 * @todo 替换为: const res = await fetch('/api/categories');
 */
export async function getCategories(): Promise<Category[]> {
  return CATEGORIES;
}

/**
 * 获取页面统计
 * @todo 替换为: const res = await fetch('/api/stats');
 */
export async function getPageStats(): Promise<PageStats> {
  return PAGE_STATS;
}
```

**Vue 项目：**

```typescript
// api/product.ts
import {
  PRODUCT_LIST,
  CATEGORIES,
} from '@/views/{PageName}/mock';
import type { Product, Category } from '@/views/{PageName}/mock/types';

/**
 * 获取商品列表
 * @todo 替换为: return request.get<Product[]>('/api/products', { params: { categoryId } });
 */
export async function getProductList(categoryId?: string): Promise<Product[]> {
  return PRODUCT_LIST;
}
```

### 6.2 Hook / Composable 层模板

**React（Hook）：**

```typescript
// hooks/useProductData.ts
import { useState, useEffect } from 'react';
import { getProductList, getCategories, getPageStats } from '@/services/productService';
import type { Product, Category, PageStats } from '@/pages/{PageName}/mock/types';

export function useProductData(categoryId?: string) {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [stats, setStats] = useState<PageStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [productList, categoryList, pageStats] = await Promise.all([
          getProductList(categoryId),
          getCategories(),
          getPageStats(),
        ]);
        setProducts(productList);
        setCategories(categoryList);
        setStats(pageStats);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [categoryId]);

  return { products, categories, stats, loading };
}
```

**Vue 3（Composable）：**

```typescript
// composables/useProductData.ts
import { ref, onMounted, watch } from 'vue';
import { getProductList, getCategories } from '@/api/product';
import type { Product, Category } from '@/views/{PageName}/mock/types';

export function useProductData(categoryId?: Ref<string | undefined>) {
  const products = ref<Product[]>([]);
  const categories = ref<Category[]>([]);
  const loading = ref(true);

  async function fetchData() {
    loading.value = true;
    try {
      const [productList, categoryList] = await Promise.all([
        getProductList(categoryId?.value),
        getCategories(),
      ]);
      products.value = productList;
      categories.value = categoryList;
    } finally {
      loading.value = false;
    }
  }

  onMounted(fetchData);
  if (categoryId) watch(categoryId, fetchData);

  return { products, categories, loading };
}
```

### 6.3 组件消费方式

**React：**

```tsx
// pages/{PageName}/ProductList.tsx
import { useProductData } from '@/hooks/useProductData';

const ProductList: React.FC<{ categoryId?: string }> = ({ categoryId }) => {
  const { products, loading } = useProductData(categoryId);

  if (loading) return <div>加载中...</div>;

  return (
    <section>
      {/* 使用 products 渲染 UI */}
    </section>
  );
};
```

**Vue 3：**

```vue
<!-- views/{PageName}/ProductList.vue -->
<script setup lang="ts">
import { useProductData } from '@/composables/useProductData';

const { products, loading } = useProductData();
</script>

<template>
  <div v-if="loading">加载中...</div>
  <section v-else>
    <!-- 使用 products 渲染 UI -->
  </section>
</template>
```

---

## 七、替换真实 API 的操作指南

当后端 API 就绪时，开发者只需执行以下步骤：

### Step 1：更新 Service / API 层

```typescript
// 修改前（Mock）
export async function getProductList(categoryId?: string): Promise<Product[]> {
  return PRODUCT_LIST;
}

// 修改后（真实 API）
export async function getProductList(categoryId?: string): Promise<Product[]> {
  const res = await fetch(`/api/products?category=${categoryId || ''}`);
  return res.json();
}
```

### Step 2：调整类型定义（如有差异）

如果后端返回字段与 mock 类型有差异，在 `types.ts` 中更新接口，TypeScript 编译器会自动标出所有需要适配的位置。

### Step 3：删除 mock 目录（可选）

当所有 API 对接完成后，可安全删除 `mock/` 目录。由于 Service 层已不再引用 mock 数据，删除不会影响运行。

---

## 八、自动生成检查清单

生成代码时，确认以下事项全部满足：

- [ ] 所有业务文本内容已从组件中提取到 `mock/` 目录
- [ ] 所有重复列表数据已提取为数组常量
- [ ] 每个 mock 常量都有 `@source` JSDoc 标注 Figma 节点 ID
- [ ] 每个 mock 常量都有 `@todo` 标注预期的 API 端点
- [ ] `mock/types.ts` 中定义了所有业务实体的 TypeScript 接口
- [ ] Service 层的 `async` 函数签名与未来 API 调用兼容
- [ ] 组件不直接 import mock 数据，而是通过 Service/Hook（Composable）获取
- [ ] `mock/index.ts` 统一导出了所有类型和数据
