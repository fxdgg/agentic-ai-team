
---
# 📜 Vibe Coding 项目准则：小程序端 (v1.0)

## 🎯 核心愿景

为电商 C 端用户构建高性能、可维护的微信小程序应用。通过统一的架构约束与编码规范，确保多 Agent 协作下的代码质量一致性，同时充分利用小程序平台的原生能力为用户提供流畅体验。

---

## 0. 规则优先级

| 级别 | 标记 | 含义 |
|------|------|------|
| **CRITICAL** | 🔴 | 违反即阻塞交付，必须立即修正 |
| **REQUIRED** | 🟡 | 应当遵循，仅在有充分理由并经澄清确认后可例外 |
| **RECOMMENDED** | 🟢 | 推荐遵循，可根据具体场景酌情调整 |

> **规则与模板的关系**：本文件是小程序端开发的**权威规则来源**，`miniprogram-architecture-template.md` 是架构文档的**输出格式模板**。两者有交集时以本文件为准。模板中的约束 C-M001~C-M008 在本文件中以完整规则形式展开。

---

## 🛠 1. 技术栈约束 (Tech Stack) — REQUIRED

| 维度 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| 跨端框架 | Taro | 4.x | 支持编译为微信小程序及其他端 |
| 开发语言 | React + TypeScript | React 18+, TS 5+ | 与 Web 端统一技术语言，TypeScript 严格模式 |
| 样式方案 | SCSS / CSS Modules | - | 小程序端样式隔离 |
| 状态管理 | Zustand | Latest | 与 Web 端统一状态管理方案 |
| 请求封装 | Taro.request 封装 | - | 统一请求/响应拦截（见 §5） |
| 构建配置 | Taro CLI + Webpack 5 | - | `config/index.js` 配置编译行为 |
| 图标方案 | Taro 内置 + 自定义 SVG | - | 禁止混用多个图标库 |

---

## 🏛 2. 三层架构 (Three-Layer Architecture) — CRITICAL

**这是本项目最核心的架构约束，所有页面必须严格遵守。**

### 核心原则

每个页面由 **六个文件** 组成，职责严格分离：

```
src/pages/[page-name]/
  ├── index.tsx        # 页面层 (View)：只做渲染
  ├── index.config.ts  # 页面配置：对应小程序 page.json
  ├── index.scss       # 页面样式：该页面专属样式
  ├── hooks.ts         # 逻辑层 (Logic)：页面全部业务逻辑
  ├── api.ts           # 接口层 (API)：接口调用函数
  └── types.ts         # 类型定义 (Types)：TS 类型声明
```

### 第 1 层：页面层 — `index.tsx`

* **只做渲染**，只调用 Hooks，**零业务逻辑**。
* 所有数据和操作函数均从 `hooks.ts` 获取。
* 页面组件默认导出。

```tsx
// ✅ 正确
const ProductListPage = () => {
  const { products, loading, onLoadMore, onRefresh } = useProductList();
  return (
    <View className="product-list">
      <ProductGrid data={products} loading={loading} />
      <LoadMore onReach={onLoadMore} />
    </View>
  );
};
export default ProductListPage;
```

```tsx
// ❌ 错误 — 页面层出现业务逻辑
const ProductListPage = () => {
  const [products, setProducts] = useState([]);
  useEffect(() => { fetchProducts().then(setProducts); }, []);
  // ...
};
```

### 第 2 层：逻辑层 — `hooks.ts`

* 承载该页面的 **全部业务逻辑**。
* 包括但不限于：数据获取、分页、筛选、下拉刷新、上拉加载、表单提交、弹窗状态控制。
* 通用 Hooks 放在 `src/hooks/` 下集中管理（如 `useRequest`、`usePagination` 等）。
* 一个页面只导出一个主 Hook（如 `useProductList`），保持单一入口。

### 第 3 层：接口层 — `api.ts` + `types.ts`

* **Types 先行**：任何新功能开发，必须先定义 `types.ts` 中的类型，再编写 `api.ts` 和其他代码。
* `api.ts` 中只包含接口调用函数，不包含任何业务逻辑。
* 所有 API 调用必须有完整的 Request/Response 类型声明（来自 `types.ts`）。
* 页面级 `api.ts` 引用 `src/services/[module]/` 下的函数，对外暴露该页面所需的完整接口。

---

## 🏗 3. 目录规范 (Directory Convention) — REQUIRED

```
{project-root}/
├── config/                          # 编译配置目录
│   ├── index.js                     # 默认配置
│   ├── dev.js                       # 开发环境配置
│   └── prod.js                      # 生产环境配置
├── src/
│   ├── pages/                       # 主包页面目录
│   │   └── [page-name]/
│   │       ├── index.tsx            # 页面入口
│   │       ├── index.config.ts      # 页面配置（对应 page.json）
│   │       ├── index.scss           # 页面样式
│   │       ├── hooks.ts             # 页面逻辑
│   │       ├── api.ts               # 页面接口
│   │       └── types.ts             # 页面类型
│   ├── subpackages/                 # 分包目录（按功能模块组织）
│   │   └── [package-name]/
│   │       └── pages/
│   │           └── [page-name]/     # 结构同主包页面
│   ├── components/                  # 全局组件
│   │   ├── ui/                      # 基础 UI 组件（按钮、输入框、卡片等）
│   │   └── business/                # 业务组件（商品卡片、订单项等）
│   ├── hooks/                       # 全局通用 Hooks
│   ├── services/                    # API 服务层
│   │   ├── request.ts               # Taro.request 统一封装
│   │   ├── interceptors.ts          # 请求/响应拦截器
│   │   └── [module]/                # 按模块组织接口
│   │       ├── index.ts             # 接口函数
│   │       └── types.ts             # 接口类型
│   ├── store/                       # Zustand 全局状态
│   ├── utils/                       # 工具函数
│   ├── assets/                      # 静态资源
│   │   ├── images/
│   │   └── icons/
│   ├── styles/                      # 全局样式
│   │   ├── variables.scss           # 样式变量（唯一来源）
│   │   └── mixins.scss              # 样式 mixin
│   ├── app.tsx                      # 应用入口
│   ├── app.config.ts                # 全局配置（路由、TabBar、权限等）
│   └── app.scss                     # 全局样式入口
├── project.config.json              # 微信小程序项目配置
├── tsconfig.json                    # TypeScript 配置
└── package.json                     # 依赖管理
```

### 关键约束

* `src/services/` 的子目录按业务模块组织（如 `services/product/`、`services/order/`）。
* 页面级 `api.ts` 负责引用并组合 `src/services/` 下的函数，对外暴露该页面所需的接口。
* 全局组件分为 `ui/`（纯展示型）和 `business/`（含业务语义），禁止混放。
* 静态资源（图片、图标）统一在 `src/assets/` 下管理，禁止散落在页面目录中。

---

## 🚏 4. 路由与分包规范 (Routing & Subpackages) — CRITICAL

### 4.1 路由注册（强制）

所有页面路由 **必须** 在 `app.config.ts` 的 `pages` 或 `subPackages` 中显式声明，否则该页面不会被编译。

```typescript
// app.config.ts
export default defineAppConfig({
  pages: [
    // 主包页面：首页、Tab 页等高频页面
    'pages/index/index',
    'pages/category/index',
    'pages/cart/index',
    'pages/my/index',
  ],
  subPackages: [
    {
      root: 'subpackages/product',
      pages: [
        'pages/detail/index',
        'pages/search/index',
      ]
    },
    {
      root: 'subpackages/order',
      pages: [
        'pages/confirm/index',
        'pages/list/index',
        'pages/detail/index',
      ]
    }
  ],
  preloadRule: {
    // 预加载规则（见 §8 性能优化）
  },
  tabBar: {
    // TabBar 配置
  },
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '',
    navigationBarTextStyle: 'black'
  }
})
```

### 4.2 分包策略（CRITICAL）

> ⚠️ 微信小程序主包限制 **2MB**，单个分包限制 **2MB**，总包限制 **20MB**。

| 原则 | 说明 | 优先级 |
|------|------|--------|
| 高频页面入主包 | 首页、Tab 页等用户高频访问页面放入主包 | CRITICAL |
| 功能模块分包 | 按业务功能模块拆分到独立分包（如 product、order、user） | REQUIRED |
| 懒加载分包 | 非首屏页面使用分包按需加载 | REQUIRED |
| 公共资源主包 | 公共组件、样式、工具函数放在主包 `src/` 下 | REQUIRED |
| 预加载配置 | 对高概率跳转的分包配置 `preloadRule` | RECOMMENDED |

### 4.3 TabBar 配置规范

* TabBar 图标必须使用本地图片，不支持网络图标。
* 图标尺寸建议 81px × 81px，且必须同时提供选中态和非选中态图标。
* Tab 页面必须在 `pages` 数组中（主包），不支持放在分包内。

### 4.4 页面跳转规范 — REQUIRED

| 场景 | API | 说明 |
|------|-----|------|
| 普通页面跳转 | `Taro.navigateTo` | 默认跳转，保留当前页面，页面栈上限 10 层 |
| 页面重定向 | `Taro.redirectTo` | 关闭当前页面并跳转 |
| 返回上一页 | `Taro.navigateBack` | 返回页面栈中的上一页 |
| Tab 页切换 | `Taro.switchTab` | 跳转到 TabBar 页面，关闭其他非 Tab 页 |
| 重启到首页 | `Taro.reLaunch` | 关闭所有页面，跳转到指定页面 |

* **禁止** 使用硬编码的页面路径字符串，应统一在 `src/utils/routes.ts` 中定义路由常量。
* 跳转时传递复杂参数应使用全局 Store 或 EventChannel，**禁止** 在 URL 上拼接超长 query。

---

## 🔗 5. 请求封装规范 (Request Layer) — CRITICAL

### 5.1 核心规则

* **禁止** 在任何页面或组件中直接调用 `Taro.request`。
* **所有** API 请求必须通过 `src/services/request.ts` 统一封装层发出。

### 5.2 封装要求

```typescript
// services/request.ts 核心设计

interface RequestConfig<D = any> {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: D
  header?: Record<string, string>
  showLoading?: boolean      // 是否显示加载动画，默认 true
  showErrorToast?: boolean   // 是否显示错误提示，默认 true
}

interface ResponseData<T = any> {
  code: number
  message: string
  data: T
}
```

封装必须包含以下能力：

| 能力 | 说明 | 优先级 |
|------|------|--------|
| baseURL 切换 | 根据环境变量区分开发/测试/生产环境 API 地址 | CRITICAL |
| Token 自动注入 | 请求拦截器自动从 Storage 读取 Token 注入 Header | CRITICAL |
| 统一错误处理 | 响应拦截器统一处理业务错误码（如 401、403、500） | CRITICAL |
| Token 过期续期 | 401 时自动续期，续期失败跳转登录页 | CRITICAL |
| 并发续期锁 | 多个请求同时 401 时，只发一次续期请求，其他排队等待 | REQUIRED |
| 类型安全 | 请求和响应均有完整的 TypeScript 泛型约束 | REQUIRED |
| 加载状态 | 可选显示/隐藏全局 Loading | RECOMMENDED |

### 5.3 Token 管理策略

| 场景 | 处理策略 |
|------|----------|
| 首次登录 | 获取 Token 后通过 `Taro.setStorageSync` 持久化 |
| 正常请求 | 从 Storage 读取 Token，注入到 `Authorization` Header |
| Token 过期（401） | 自动调用续期接口，成功后重试原请求 |
| 续期失败 | 清空本地存储，跳转到登录页 |
| 并发请求 Token 过期 | 加锁机制，仅发一次续期请求，其他请求排队等待 |

---

## 📦 6. 状态管理规范 — REQUIRED

### 6.1 全局状态（Zustand）

* 全局状态统一使用 Zustand，定义在 `src/store/` 目录下。
* 每个 Store 文件对应一个业务域（如 `useUserStore`、`useCartStore`）。
* Store 中只放 **跨页面共享** 的数据（如用户信息、购物车数量、登录态）。
* **禁止** 将页面级临时数据放入全局 Store。

### 6.2 页面级状态（Custom Hooks）

* 页面级逻辑和状态通过 `hooks.ts` 中的 Custom Hook 管理。
* 一个页面只导出一个主 Hook，内部可组合多个子 Hook。

### 6.3 本地存储（Taro Storage）

| 使用场景 | 方式 | 说明 |
|----------|------|------|
| Token / 用户信息 | `Taro.setStorageSync` / `getStorageSync` | 同步方式，启动即需 |
| 缓存数据 | `Taro.setStorage` / `getStorage` | 异步方式，非关键路径 |
| 临时数据（如搜索历史） | `Taro.setStorageSync` | 设置合理的 key 命名前缀 |

* **禁止** 在 Storage 中存储大量数据（单条 value 上限 1MB，总上限 10MB）。
* Storage key 统一使用常量定义，禁止硬编码字符串。

---

## 🎨 7. 样式规范 — REQUIRED

### 7.1 基本规则

* 全局样式变量 **统一** 在 `src/styles/variables.scss` 中定义（颜色、字号、间距、圆角等）。
* 页面样式使用 `index.scss`，**禁止** 在 `index.tsx` 中使用内联 `style={{...}}`（动态计算的样式除外）。
* 使用 CSS Modules 或 BEM 命名法避免样式冲突。

### 7.2 尺寸适配

* 统一使用 **rpx** 作为尺寸单位（Taro 会自动转换）。
* 设计稿基准宽度为 **750rpx**（即 375px × 2 的 iPhone 6/7/8 设计稿）。
* 在 `config/index.js` 中配置 `designWidth: 750`。

### 7.3 样式变量示例

```scss
// styles/variables.scss

// 品牌色
$color-primary: #FF4D4F;
$color-primary-light: #FFF1F0;
$color-secondary: #1890FF;

// 文字颜色
$color-text-primary: #333333;
$color-text-secondary: #666666;
$color-text-placeholder: #999999;

// 背景色
$color-bg-page: #F5F5F5;
$color-bg-card: #FFFFFF;

// 字号
$font-size-xs: 20rpx;
$font-size-sm: 24rpx;
$font-size-base: 28rpx;
$font-size-lg: 32rpx;
$font-size-xl: 36rpx;

// 间距
$spacing-xs: 8rpx;
$spacing-sm: 16rpx;
$spacing-base: 24rpx;
$spacing-lg: 32rpx;
$spacing-xl: 48rpx;

// 圆角
$border-radius-sm: 8rpx;
$border-radius-base: 12rpx;
$border-radius-lg: 16rpx;
```

---

## ⚡ 8. 性能优化规范 — REQUIRED

| 优化点 | 策略 | 适用场景 | 优先级 |
|--------|------|----------|--------|
| 分包加载 | 非首屏页面放入分包，按需加载 | 全项目 | CRITICAL |
| 分包预加载 | 对高概率跳转页配置 `preloadRule` | 关联页面 | RECOMMENDED |
| 长列表优化 | 虚拟滚动或分页加载，单次渲染不超过 20 条 | 数据量 > 50 条 | REQUIRED |
| 图片优化 | 懒加载 + CDN 压缩 + WebP 格式 | 图片列表页 | REQUIRED |
| 数据缓存 | `Taro.setStorage` 缓存不常变化的数据 | 字典、配置类数据 | RECOMMENDED |
| setData 优化 | 减少 setData 频率，避免传输大体量数据 | 频繁更新的页面 | REQUIRED |
| 骨架屏 | 首屏使用骨架屏提升感知速度 | 首页、列表页 | RECOMMENDED |
| 图片尺寸 | 根据展示区域请求合适尺寸的图片（CDN 裁剪参数） | 所有图片展示 | RECOMMENDED |

### 长列表优化要点

```tsx
// ✅ 推荐：使用 ScrollView + 分页加载
const ProductList = () => {
  const { products, hasMore, onLoadMore } = useProductList();
  return (
    <ScrollView
      scrollY
      onScrollToLower={onLoadMore}
      lowerThreshold={100}
    >
      {products.map(item => <ProductCard key={item.id} data={item} />)}
      {hasMore && <LoadingMore />}
    </ScrollView>
  );
};
```

---

## 📱 9. 微信原生能力集成规范 — REQUIRED

### 9.1 核心规则

* 使用微信原生能力前，必须在 `app.config.ts` 中声明所需权限（如 `requiredPrivateInfos`）。
* 需要用户授权的能力，必须在触发前做好权限检查和拒绝后的引导提示。
* 原生能力调用统一封装在 `src/utils/` 或 `src/services/` 下，页面中不直接调用 `wx.*` / `Taro.*` 原生 API。

### 9.2 常用能力参考

| 能力 | Taro API | 说明 | 权限要求 |
|------|----------|------|----------|
| 微信登录 | `Taro.login()` | 获取临时登录凭证 code | 无需授权 |
| 获取用户信息 | `Taro.getUserProfile()` | 需用户主动触发（button） | 需用户确认 |
| 微信支付 | `Taro.requestPayment()` | 需后端生成支付参数 | 无需额外授权 |
| 分享 | `useShareAppMessage` | 页面内配置分享 | 无需授权 |
| 地理位置 | `Taro.getLocation()` | 需声明 `requiredPrivateInfos` | 需用户授权 |
| 扫码 | `Taro.scanCode()` | 调用摄像头 | 需用户授权 |
| 图片选择 | `Taro.chooseImage()` | 从相册或拍照 | 需用户确认 |
| 下拉刷新 | `Taro.startPullDownRefresh()` | 需在 `index.config.ts` 中开启 | 无需授权 |
| 订阅消息 | `Taro.requestSubscribeMessage()` | 需用户主动订阅 | 需用户确认 |

### 9.3 权限声明示例

```typescript
// app.config.ts 中声明隐私权限
export default defineAppConfig({
  // ...
  requiredPrivateInfos: [
    'getLocation',
    'chooseAddress',
    // 按需添加
  ]
})
```

---

## 🧩 10. 组件设计规范 — REQUIRED

### 10.1 组件分类

| 类别 | 目录 | 说明 | 示例 |
|------|------|------|------|
| 基础 UI 组件 | `components/ui/` | 纯展示型，无业务语义 | Button、Tag、Empty、Skeleton |
| 业务组件 | `components/business/` | 含业务语义，可跨页面复用 | ProductCard、OrderItem、PriceTag |
| 页面私有组件 | 页面目录下 `components/` | 仅当前页面使用 | 某个特定弹窗、特定列表项 |

### 10.2 组件设计原则

* 组件必须有明确的 Props 类型定义（`interface XxxProps`）。
* 基础 UI 组件 **禁止** 包含业务逻辑，只通过 props 接收数据和回调。
* 业务组件可包含适度的业务逻辑，但数据获取必须通过 props 或 hooks 注入。
* 单个组件文件不超过 **200 行**，超过必须拆分。
* 组件使用默认导出（`export default`），类型定义使用具名导出。

---

## 📝 11. 开发流程 (Development Workflow)

### 11.1 Types 先行 — CRITICAL

* 开发任何新功能，**第一步永远是定义 `types.ts`**。
* 开发顺序：`types.ts` → `api.ts` → `hooks.ts` → `index.tsx`（+ `index.config.ts` + `index.scss`）。
* 此顺序不可跳过或颠倒。

### 11.2 向前兼容 — CRITICAL

* 所有改动必须 **保持向前兼容**。
* 新增字段使用可选属性（`?`），不得删除或重命名已有的对外接口。
* 废弃字段使用 `@deprecated` 标注，留足过渡期后再移除。

### 11.3 契约驱动

* **阅读 Markdown**：每次生成 API 代码前，优先解析后端提供的 Markdown 接口定义。
* **类型安全**：所有 API 调用必须有完整的 Request/Response 类型声明。
* **Mock 机制**：在后端接口未就绪时，使用 Mock 数据保证前端开发不被阻塞。

### 11.4 路由注册（强制）

* 新增任何页面后，**必须** 同步在 `app.config.ts` 中注册路由。
* 遗漏路由注册将导致页面无法被编译和访问，属于 CRITICAL 级错误。

---

## 🚫 12. 禁令 (Non-Negotiables)

1. 🔴 **禁止** 在 `index.tsx`（页面层）中编写任何业务逻辑。
2. 🔴 **禁止** 在任何页面或组件中直接调用 `Taro.request`，必须通过 `services/request.ts` 封装。
3. 🔴 **禁止** 新增页面后遗漏 `app.config.ts` 路由注册。
4. 🔴 **禁止** 主包超过 2MB、单个分包超过 2MB。
5. 🔴 **禁止** 跳过六文件结构（`index.tsx / index.config.ts / index.scss / hooks.ts / api.ts / types.ts`），新页面必须完整创建。
6. 🟡 **禁止** 出现超过 200 行的"巨型组件"，超出必须拆分为子组件 + Hooks。
7. 🟡 **禁止** 在代码中留下未定义的 `any` 类型（`unknown` + 类型守卫代替）。
8. 🟡 **禁止** 在 `index.tsx` 中使用内联 `style={{...}}`（动态计算值除外）。
9. 🟡 **禁止** 在 Storage 中硬编码 key 字符串，必须通过常量定义。
10. 🟡 **禁止** 在 URL 上拼接超长 query 传参，复杂参数使用 Store 或 EventChannel。
11. 🟡 **禁止** 将页面级临时数据放入全局 Zustand Store。
12. 🟡 **禁止** 混用多个图标库。
13. 🟡 **禁止** 炫技语法（如过度使用柯里化、隐式类型推断链等），代码可读性优先。
14. 🟡 **禁止** 将静态资源散落在页面目录中，必须统一放在 `src/assets/` 下。

---

## 🤖 13. AI 交互指令 (Vibe Coding Prompting)

> "当我要创建一个新的小程序页面时，请按以下顺序执行：
> 1. 确认该页面属于主包还是分包，并检查包体积预估；
> 2. 分析对应的 Markdown 接口契约（若有）；
> 3. 定义 `types.ts`（Request/Response 类型）；
> 4. 编写 `api.ts`（调用 `services/` 下的封装函数）；
> 5. 编写 `hooks.ts`（页面全部业务逻辑）；
> 6. 编写 `index.tsx`（纯渲染，调用 hook）+ `index.config.ts`（页面配置）+ `index.scss`（页面样式）；
> 7. 在 `app.config.ts` 中注册路由（主包 `pages` 或 `subPackages`）；
> 8. 若涉及新的微信原生能力，更新权限声明。"

---
