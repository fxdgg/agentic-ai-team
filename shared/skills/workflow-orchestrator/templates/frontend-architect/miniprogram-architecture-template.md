# 小程序端架构专属模板

> **模板类型**: 平台专属模板（当 `platforms.miniprogram.enabled = true` 时加载）
> **适用平台**: 小程序端（C 端用户应用）
> **使用者**: 资深前端架构师 Agent
> **框架**: Taro 4.x + React + TypeScript
> **参考文档**: https://docs.taro.zone/docs/folder

---

## 使用说明

本模板补充基础模板中小程序端特有的设计内容。使用时将以下各章节内容**合并**到基础模板的对应位置。

---

## 技术栈声明（合并到 §1.1）

| 维度 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| 跨端框架 | Taro | 4.x | 支持编译为微信小程序及其他端 |
| 开发语言 | React + TypeScript | React 18+, TS 5+ | 与 Web 端统一技术语言 |
| 样式方案 | SCSS / CSS Modules | - | 小程序端样式隔离 |
| 状态管理 | Zustand | Latest | 与 Web 端统一状态管理方案 |
| 请求封装 | Taro.request 封装 | - | 统一请求/响应拦截 |
| 构建配置 | Taro CLI + Webpack 5 | - | config/index.js 配置编译行为 |

## 项目结构声明（合并到 §1.2）

```
{project-root}/
├── config/                      # 编译配置目录
│   ├── index.js                 # 默认配置
│   ├── dev.js                   # 开发环境配置
│   └── prod.js                  # 生产环境配置
├── src/
│   ├── pages/                   # 主包页面目录
│   │   └── [page-name]/
│   │       ├── index.tsx        # 页面入口
│   │       ├── index.config.ts  # 页面配置（对应小程序 page.json）
│   │       ├── index.scss       # 页面样式
│   │       ├── hooks.ts         # 页面逻辑（逻辑层）
│   │       ├── api.ts           # 页面接口（接口层）
│   │       └── types.ts         # 页面类型（类型层）
│   ├── subpackages/             # 分包目录（按需）
│   │   └── [package-name]/
│   │       └── pages/
│   │           └── [page-name]/ # 结构同主包页面
│   ├── components/              # 全局组件
│   │   ├── ui/                  # 基础 UI 组件
│   │   └── business/            # 业务组件
│   ├── hooks/                   # 全局 Hooks
│   ├── services/                # API 服务层
│   │   ├── request.ts           # Taro.request 封装
│   │   ├── interceptors.ts      # 请求/响应拦截器
│   │   └── [module]/            # 按模块组织接口
│   │       ├── index.ts         # 接口函数
│   │       └── types.ts         # 接口类型
│   ├── store/                   # Zustand 全局状态
│   ├── utils/                   # 工具函数
│   ├── assets/                  # 静态资源
│   │   ├── images/
│   │   └── icons/
│   ├── styles/                  # 全局样式
│   │   ├── variables.scss       # 样式变量
│   │   └── mixins.scss          # 样式 mixin
│   ├── app.tsx                  # 应用入口
│   ├── app.config.ts            # 全局配置（路由注册、TabBar、权限等）
│   └── app.scss                 # 全局样式
├── project.config.json          # 微信小程序项目配置
├── tsconfig.json                # TypeScript 配置
└── package.json                 # 依赖管理
```

---

## 架构约束（合并到 §1.3）

| # | 约束描述 | 来源 | 优先级 |
|---|----------|------|--------|
| C-M001 | 页面结构遵循 Taro 标准规范（每个页面独立目录） | Taro 文档 | CRITICAL |
| C-M002 | 所有页面路由必须在 `app.config.ts` 的 `pages` / `subPackages` 中声明 | Taro 文档 | CRITICAL |
| C-M003 | 页面逻辑与视图分离（hooks.ts + index.tsx 模式） | 架构约定 | REQUIRED |
| C-M004 | Types 先行：开发顺序 `types.ts` → `api.ts` → `hooks.ts` → `index.tsx` | 架构约定 | REQUIRED |
| C-M005 | 主包大小不超过 2MB，单个分包不超过 2MB | 微信小程序限制 | CRITICAL |
| C-M006 | 全局样式变量统一在 `styles/variables.scss` 中定义 | 架构约定 | REQUIRED |
| C-M007 | API 请求统一通过 `services/request.ts` 封装 | 架构约定 | CRITICAL |
| C-M008 | 禁止在页面中直接调用 `Taro.request`，必须通过服务层 | 架构约定 | CRITICAL |

---

## 页面/路由设计（扩展 §2）

### 2.1 页面路由配置（app.config.ts）

```typescript
// app.config.ts
export default defineAppConfig({
  pages: [
    // 主包页面（首页、Tab 页等高频页面）
    'pages/index/index',
    // ...
  ],
  subPackages: [
    // 分包配置
    {
      root: 'subpackages/{package-name}',
      pages: [
        'pages/{page-name}/index',
        // ...
      ]
    }
  ],
  tabBar: {
    // TabBar 配置（若有）
  },
  window: {
    // 全局窗口配置
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: '{应用名称}',
    navigationBarTextStyle: 'black'
  }
})
```

### 2.2 页面路由表

| 页面路径 | 所属包 | 页面标题 | 是否 Tab 页 | 说明 | 关联需求点 |
|----------|--------|----------|-------------|------|-----------|
| `pages/{name}/index` | 主包 | {标题} | 是/否 | {说明} | {US-xxx} |
| `subpackages/{pkg}/pages/{name}/index` | 分包-{pkg} | {标题} | 否 | {说明} | {US-xxx} |

### 2.3 TabBar 设计（若有）

| Tab | 图标 | 选中图标 | 页面路径 | 说明 |
|-----|------|----------|----------|------|
| {Tab 名} | {icon 路径} | {selected icon 路径} | {页面路径} | {说明} |

### 2.4 分包策略

> ⚠️ **CRITICAL**: 微信小程序主包限制 2MB，需合理规划分包。

#### 分包原则

| 原则 | 说明 |
|------|------|
| 高频页面入主包 | 首页、Tab 页等用户高频访问的页面放入主包 |
| 功能模块分包 | 按业务功能模块拆分到独立分包 |
| 懒加载分包 | 非首屏页面使用分包按需加载 |
| 公共资源主包 | 公共组件、样式、工具函数放在主包 |

#### 分包规划

| 分包名称 | 根路径 | 包含页面 | 预估大小 | 说明 |
|----------|--------|----------|----------|------|
| 主包 | `pages/` | {列出主包页面} | {KB} | 核心页面 |
| {分包名} | `subpackages/{name}/` | {列出分包页面} | {KB} | {说明} |

---

## 请求封装设计（扩展 §5）

### Taro.request 封装

```typescript
// services/request.ts 设计说明

/**
 * 封装要求：
 * 1. 统一 baseURL 配置（区分开发/生产环境）
 * 2. 请求拦截：自动注入 Token、租户 ID 等通用 Header
 * 3. 响应拦截：统一处理错误码、Token 过期自动续期
 * 4. 类型安全：请求和响应均有 TypeScript 类型约束
 */

interface RequestConfig {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
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

### Token 管理与自动续期

| 场景 | 处理策略 |
|------|----------|
| 首次登录 | 获取 Token 后存储到 `Taro.setStorageSync` |
| 正常请求 | 从 Storage 读取 Token，注入到 Header |
| Token 过期（401） | 自动调用续期接口，成功后重试原请求 |
| 续期失败 | 跳转到登录页，清空本地存储 |
| 并发请求 Token 过期 | 加锁机制，只发一次续期请求，其他请求排队等待 |

---

## 小程序原生能力集成（小程序端专有 §）

> 根据需求列出涉及的微信原生能力。

### 涉及的原生能力

| 能力 | API | 使用场景 | 权限要求 | 关联需求点 |
|------|-----|----------|----------|-----------|
| {能力名} | `wx.{api}` 或 `Taro.{api}` | {场景说明} | {是否需要用户授权} | {US-xxx} |

### 常见原生能力参考

| 能力 | Taro API | 说明 |
|------|----------|------|
| 微信登录 | `Taro.login()` | 获取临时登录凭证 code |
| 获取用户信息 | `Taro.getUserProfile()` | 需用户主动触发 |
| 微信支付 | `Taro.requestPayment()` | 需后端生成支付参数 |
| 分享 | `useShareAppMessage` | 页面内配置分享 |
| 地理位置 | `Taro.getLocation()` | 需用户授权 |
| 扫码 | `Taro.scanCode()` | 调用摄像头 |
| 图片选择 | `Taro.chooseImage()` | 从相册或拍照 |
| 下拉刷新 | `Taro.startPullDownRefresh()` | 需在页面配置中开启 |

---

## 性能优化策略（小程序端专有 §）

| 优化点 | 策略 | 适用场景 |
|--------|------|----------|
| 首屏加载 | 分包加载、预加载 | 非首屏页面 |
| 长列表 | 虚拟滚动 / 分页加载 | 数据量 > 100 条 |
| 图片加载 | 懒加载 + CDN 压缩 | 图片列表页 |
| 数据缓存 | Taro.setStorage 本地缓存 | 不常变化的数据 |
| setData 优化 | 减少 setData 频率和数据量 | 频繁更新的页面 |
| 预加载 | 页面预加载（preloadRule） | 高概率跳转的下一页 |

---

## 禁令检查清单（小程序端专有）

在输出架构文档前，确认设计不违反以下规则：

- [ ] 主包大小预估不超过 2MB
- [ ] 单个分包大小预估不超过 2MB
- [ ] 未在页面中直接调用 `Taro.request`（统一通过服务层）
- [ ] 所有页面路由已在 `app.config.ts` 中声明
- [ ] 需要用户授权的能力已标注
- [ ] 页面结构遵循独立目录模式
- [ ] Types 先行原则已体现在开发顺序中
