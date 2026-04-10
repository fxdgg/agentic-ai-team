# Web 端架构专属模板

> **模板类型**: 平台专属模板（当 `platforms.web.enabled = true` 时加载）
> **适用平台**: Web 端
> **使用者**: 资深前端架构师 Agent
> **权威规则**: `frontend-group/rules/operation-fe-meta-rule.md`

---

## 使用说明

本模板补充基础模板中 Web 端特有的设计内容。使用时将以下各章节内容**合并**到基础模板的对应位置。

---

## 技术栈声明（合并到 §1.1）

> ⚠️ 以下技术栈为**强制约束**，来源于 `operation-fe-meta-rule.md`，不得更改。

| 维度 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| 构建工具 | Vite | Latest | - |
| 框架 | React + TypeScript（严格模式） | React 18+ | - |
| UI 框架 | Ant Design + Tailwind CSS | AntD Latest | AntD 处理逻辑交互，Tailwind 处理布局间距 |
| 全局状态管理 | Zustand | Latest | 轻量、响应式 |
| 页面级逻辑 | 自定义 Hooks | - | 三层架构中的逻辑层 |
| 复杂业务流程 | XState | Latest | 促销引擎、审批流等多步骤状态流转（按需） |

## 项目结构声明（合并到 §1.2）

```
src/
├── api/                        # 全局 API 层（目录结构与 pages 保持一致）
│   ├── [module-name]/
│   │   ├── [page-name].ts      # 接口调用函数
│   │   └── types.ts            # 该模块的类型定义
│   └── common/                 # 公共 API（如 上传、字典 等）
│       ├── index.ts
│       └── types.ts
├── components/
│   └── ui/                     # 基础原子组件（封装后的 AntD）
├── hooks/                      # 全局通用 Hooks（useTable, useForm 等）
├── pages/                      # 页面目录（严格四文件结构）
│   └── [module-name]/
│       └── [page-name]/
│           ├── index.tsx        # 页面层（View）— 只做渲染，零业务逻辑
│           ├── hooks.ts         # 逻辑层（Logic）— 全部业务逻辑
│           ├── api.ts           # 接口层（API）— 引用 src/api/ 下对应模块
│           └── types.ts         # 类型定义（Types）— Types 先行
├── templates/                  # 4 大金刚页面模版（含变体）
│   ├── BasePage/               # 基础页（Loading、Error、Empty 状态）
│   ├── FormPage/               # 表单页模版
│   ├── ListPage/               # 列表页模版
│   └── MultiTabListPage/       # 复杂多 Tab 列表页模版
├── store/                      # Zustand 全局状态
├── machines/                   # XState 状态机定义（按需）
├── styles/                     # 全局样式 & Tailwind 配置
└── utils/                      # 工具函数
```

---

## 三层架构约束（合并到 §1.3）

> ⚠️ **CRITICAL**: 以下约束来自 `operation-fe-meta-rule.md`，违反即视为不可接受。

| # | 约束描述 | 来源 | 优先级 |
|---|----------|------|--------|
| C-A001 | 每个页面必须由 `index.tsx / hooks.ts / api.ts / types.ts` 四文件组成 | operation-fe-meta-rule | CRITICAL |
| C-A002 | `index.tsx`（页面层）只做渲染，零业务逻辑 | operation-fe-meta-rule | CRITICAL |
| C-A003 | `hooks.ts`（逻辑层）承载页面全部业务逻辑 | operation-fe-meta-rule | CRITICAL |
| C-A004 | 开发顺序：`types.ts` → `api.ts` → `hooks.ts` → `index.tsx` | operation-fe-meta-rule | CRITICAL |
| C-A005 | 所有列表页必须使用统一的 `useTable` Hook | operation-fe-meta-rule | REQUIRED |
| C-A006 | 所有表单页必须使用统一的 `useForm` Hook | operation-fe-meta-rule | REQUIRED |
| C-A007 | `src/api/` 的子目录结构必须与 `src/pages/` 保持一致 | operation-fe-meta-rule | REQUIRED |
| C-A008 | 禁止出现超过 300 行的巨型组件 | operation-fe-meta-rule | CRITICAL |
| C-A009 | 禁止在页面层编写任何业务逻辑 | operation-fe-meta-rule | CRITICAL |
| C-A010 | 禁止直接修改基线模版 `src/templates/[Name]/index.tsx` | operation-fe-meta-rule | CRITICAL |

---

## 页面/路由设计（扩展 §2）

### 2.1 路由表

> 根据需求定义新增/修改的路由。

| 路由路径 | 页面组件 | 菜单位置 | 权限码 | 说明 | 关联需求点 |
|----------|----------|----------|--------|------|-----------|
| `/module/page` | `pages/module/page/index.tsx` | {一级菜单} > {二级菜单} | `module:page:view` | {说明} | {US-xxx} |

### 2.2 页面层级

```
{模块名}/
├── list/          # 列表页（入口）
├── detail/        # 详情页
├── create/        # 新增页（表单）
└── edit/          # 编辑页（表单）
```

> 注意：列表/详情/新增/编辑是常见页面模式，但不是强制的。根据实际需求灵活组织。

### 2.3 导航结构

{定义菜单层级和面包屑路径}

---

## 模板选择流程（扩展 §3）

> ⚠️ 本流程来自 `operation-fe-meta-rule.md` §📐 页面模版规范。

在设计每个新增页面时，**必须**按以下流程确定使用哪种页面模板：

### 步骤 1：判断页面类型

| 页面类型 | 匹配特征 | 推荐模板 |
|----------|----------|----------|
| 列表 + CRUD | 表格展示、搜索筛选、分页、增删改查 | `ListPage` |
| 多状态列表 | 列表 + 多个 Tab 切换不同数据源 | `MultiTabListPage` |
| 表单 | 数据录入、校验、提交 | `FormPage` |
| 详情 | 数据展示、无编辑 | `BasePage` |
| 其他 | 不属于上述类型 | `BasePage` + 自定义 |

### 步骤 2：检查现有变体

对于匹配的模板，检查 `src/templates/{TemplateName}/README.md` 中的变体索引：
- 若有匹配变体 → 使用变体
- 若无匹配变体 → 使用基线模板
- 若需扩展基线 → 创建新变体（记录在架构文档中）

### 步骤 3：记录模板选择

| 页面 | 模板 | 变体 | 是否新建变体 | 说明 |
|------|------|------|-------------|------|
| {页面路径} | {ListPage/FormPage/BasePage/MultiTabListPage} | {变体名或"基线"} | {是/否} | {选择原因} |

---

## 权限控制设计（Web 端专有 §）

> 来源: `operation-fe-meta-rule.md` §🔐 权限控制

### 权限设计原则

- **禁止**在页面组件内硬编码权限判断
- **必须**使用 `AccessControl` 包裹器或 `useAccess` Hook
- 权限逻辑与路由配置 `meta.permissions` 深度绑定

### 新增权限码清单

| 权限码 | 说明 | 绑定页面/操作 |
|--------|------|---------------|
| `{module}:{page}:{action}` | {说明} | {页面路径或操作按钮} |

---

## 禁令检查清单（Web 端专有）

> 来源: `operation-fe-meta-rule.md` §🚫 禁令

在输出架构文档前，确认设计不违反以下禁令：

- [ ] 无超过 300 行的巨型组件设计
- [ ] 未混合使用不同图标库（统一 Ant Design Icons）
- [ ] 未绕过权限检查直接展示操作按钮
- [ ] 无未定义的 `any` 类型
- [ ] 页面层 `index.tsx` 无业务逻辑
- [ ] 无超过 3 层的 JSX 嵌套设计
- [ ] 无直接修改基线模版的设计
- [ ] 所有页面遵循四文件结构
