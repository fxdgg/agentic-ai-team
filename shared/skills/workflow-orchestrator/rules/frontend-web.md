
---
# 📜 Vibe Coding 项目准则：大型电商 Web 端 (v2.0)

## 🎯 核心愿景

从 0 到 1 重构 Web 平台，终结"组件混乱、调试困难、权限错位"的旧时代。通过 **极简的意图输入** 获取 **生产级、高性能、易维护** 的代码。

---

## 🛠 技术栈约束 (Tech Stack)

* **构建工具**: `Vite`。
* **框架**: `React` + `TypeScript`（严格模式）。
* **UI 框架**: `Ant Design (Latest)` + `Tailwind CSS`。
  * *准则*: 使用 AntD 组件处理逻辑与交互，使用 Tailwind 处理布局、间距与微调。
* **状态管理**:
  * **全局状态**: `Zustand` (轻量、响应式)。
  * **页面级逻辑**: 自定义 Hooks 驱动（见三层架构章节）。
  * **复杂业务流程**: `XState` (针对促销引擎、审批流等多步骤状态流转)。
* **交互设计**: 遵循 `ui-ux-pro-max` 交互指南，指导自定义组件的交互与设计。

---

## 🏛 三层架构 (Three-Layer Architecture) — CRITICAL

**这是本项目最核心的架构约束，所有页面必须严格遵守。**

### 核心原则

每个页面由 **四个文件** 组成，职责严格分离：

```
src/pages/[module-name]/[page-name]/
  ├── index.tsx    # 页面层 (View)
  ├── hooks.ts     # 逻辑层 (Logic)
  ├── api.ts       # 接口层 (API)
  └── types.ts     # 类型定义 (Types)
```

### 第 1 层：页面层 — `index.tsx`

* **只做渲染**，只调用 Hooks，**零业务逻辑**。
* 所有数据和操作函数均从 `hooks.ts` 获取。
* 目标：AI 随便改都不会崩。

```tsx
// ✅ 正确
const MyPage = () => {
  const { tableProps, searchProps, handleDelete } = useMyPage();
  return (
    <PageContainer>
      <SearchForm {...searchProps} />
      <DataTable {...tableProps} onDelete={handleDelete} />
    </PageContainer>
  );
};
```

```tsx
// ❌ 错误 — 页面层出现业务逻辑
const MyPage = () => {
  const [data, setData] = useState([]);
  useEffect(() => { fetchList().then(setData); }, []);
  // ...
};
```

### 第 2 层：逻辑层 — `hooks.ts`

* 承载该页面的 **全部业务逻辑**。
* 包括但不限于：表格查询、分页、筛选、表单提交、新增/编辑/删除、弹窗状态控制。
* **所有列表页** 必须使用统一的 `useTable` Hook。
* **所有表单页** 必须使用统一的 `useForm` Hook。
* 通用 Hooks 放在 `src/hooks/` 下集中管理。

### 第 3 层：接口层 — `api.ts` + `types.ts`

* **Types 先行**: 任何新功能开发，必须先定义 `types.ts` 中的类型，再编写 `api.ts` 和其他代码。
* `api.ts` 中只包含接口调用函数，不包含任何业务逻辑。
* 所有 API 调用必须有完整的 Request/Response 类型声明（来自 `types.ts`）。

---

## 🏗 目录规范 (Directory Convention)

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
  │           ├── index.tsx
  │           ├── hooks.ts
  │           ├── api.ts          # 页面级 API（引用 src/api/ 下对应模块）
  │           └── types.ts
  ├── templates/                  # 4 大金刚页面模版（含变体）
  │   ├── BasePage/               # 基础页（含 Loading、Error、Empty 等状态）
  │   │   ├── index.tsx           # 基线模版（不可随意修改）
  │   │   ├── README.md           # 模版说明 + 变体索引
  │   │   └── variants/           # 变体目录
  │   │       └── ErrorWithRetry/ # 示例变体
  │   │           ├── index.tsx
  │   │           └── README.md   # 变体场景说明
  │   ├── FormPage/               # 表单页模版（结构同上）
  │   ├── ListPage/               # 列表页模版（结构同上）
  │   └── MultiTabListPage/       # 复杂多 Tab 列表页模版（结构同上）
  ├── store/                      # Zustand 全局状态
  ├── machines/                   # XState 状态机定义
  ├── styles/                     # 全局样式 & Tailwind 配置
  └── utils/                      # 工具函数
```

**关键约束**:
* `src/api/` 的子目录结构 **必须与** `src/pages/` 保持一致。
* 页面级 `api.ts` 负责引用并组合 `src/api/` 下的函数，对外暴露该页面所需的完整接口。

---

## 📐 页面模版规范 (Page Templates)

### 1. 基础页 (`BasePage`)

* 统一提供 **Loading 状态**（骨架屏或 Spin）。
* 统一提供 **Error 状态**（错误提示 + 重试操作）。
* 统一提供 **Empty 状态**（空数据占位）。
* 所有页面必须继承基础页的状态处理。

### 2. 表单页 (`FormPage`)

* 必须支持：自动 Loading 状态、校验反馈、回车提交。
* 统一使用 `useForm` Hook 管理表单逻辑。

### 3. 列表页 (`ListPage`)

* 必须集成：分栏排序、自适应分页、搜索参数同步至 URL。
* 统一使用 `useTable` Hook 管理表格逻辑。
* **横向溢出防护**: 当 Table 各列设置了固定 `width` 时，**必须**同时设置 `scroll={{ x: 'max-content' }}`，
  防止列宽总和超出容器宽度时表格溢出 Card/Panel 边界。
  * 推荐做法：所有列表页的 `<Table>` 默认加上 `scroll={{ x: 'max-content' }}`，即使当前列宽总和未超出容器。
  * 禁止做法：在不设置 `scroll.x` 的情况下，为 Table 的多个列设置固定 `width` 且总和超过 900px。

### 4. 复杂多 Tab 列表页 (`MultiTabListPage`)

* 每个 Tab 独立数据源、独立筛选条件。
* Tab 切换不丢失已有状态。

### 5. 模版变体沉淀机制 — CRITICAL

**核心原则：基线模版不可变（Immutable Base），扩展需求通过派生变体（Variant）沉淀。**

#### 为什么

直接修改基线模版会影响所有已使用该模版的页面，引入不可控的回归风险。通过变体机制，每种业务场景的定制都被隔离保存，可复用、可追溯。

#### 规则

1. **禁止直接修改基线模版**：`src/templates/[TemplateName]/index.tsx` 是基线，任何需求若需要扩展模版能力，**必须**在 `variants/` 下新建变体，不得直接改动基线文件。
2. **变体目录结构**：
   ```
   src/templates/[TemplateName]/
     ├── index.tsx              # 基线模版（不可修改）
     ├── README.md              # 模版总览 + 所有变体索引
     └── variants/
         └── [VariantName]/     # 变体名（PascalCase，语义化命名）
             ├── index.tsx      # 变体实现
             └── README.md      # 变体说明文档（必须）
   ```
3. **变体 README.md 必须包含**：
   * **适用场景**：描述该变体解决什么业务问题。
   * **与基线的差异**：列出相对于基线模版新增/调整了哪些能力。
   * **使用示例**：给出简短的引用代码。
4. **模版总览 README.md**：每个模版根目录的 `README.md` 必须维护一份 **变体索引表**，列出所有已有变体及其适用场景摘要，方便快速检索。
5. **变体可继承基线**：变体实现应尽量复用基线模版的逻辑（通过组合或包裹），避免完全重写。

#### AI 编码时的模版选择流程

当 AI 需要使用页面模版时，**必须按以下顺序执行**：

1. **扫描模版目录**：先读取对应模版的 `README.md`（含变体索引）。
2. **匹配现有变体**：判断当前需求是否与某个已有变体匹配，若匹配则直接使用。
3. **使用基线模版**：若无匹配变体且需求无需扩展，直接使用基线模版。
4. **创建新变体**：若需求需要扩展基线能力且无现有变体可用，则：
   * 在 `variants/` 下新建变体目录。
   * 编写变体 `index.tsx` 和 `README.md`。
   * 更新模版根目录 `README.md` 的变体索引表。

---

## 🔄 状态机 (XState)

* 针对**促销引擎配置**与**多级审批**等复杂业务流程，禁止使用散乱的 `Boolean` 变量。
* 必须定义显式的 `State`（如 `draft`, `validating`, `pending_approval`）及 `Events`。
* 状态机定义统一放在 `src/machines/` 目录。

---

## 🔐 权限控制 (Auth Control)

* **禁止**在页面组件内硬编码权限判断。
* **必须**使用 `AccessControl` 包裹器或 `useAccess` Hook。
* 权限逻辑与路由配置 `meta.permissions` 深度绑定。

---

## 🎨 UI/UX 规范 (Design Standards)

* **统一设计标准**: 全项目遵循统一的视觉与交互规范，任何自定义组件须参照 `ui-ux-pro-max` 指南。
* **原子化**: 间距、颜色必须使用 Tailwind 变量，**禁止**内联 `style={{...}}`。
* **表单一致性**: 所有表单页面必须支持：自动 Loading 状态、校验反馈、回车提交。
* **列表标准**: 必须集成：分栏排序、自适应分页、搜索参数同步至 URL。

---

## 📝 开发流程 (Development Workflow)

### 1. Types 先行 — CRITICAL

* 开发任何新功能，**第一步永远是定义 `types.ts`**。
* 先确定 Request/Response 类型 → 再写 `api.ts` → 再写 `hooks.ts` → 最后写 `index.tsx`。

### 2. 向前兼容 — CRITICAL

* 所有改动必须 **保持向前兼容**。
* 新增字段使用可选属性（`?`），不得删除或重命名已有的对外接口。
* 废弃字段使用 `@deprecated` 标注，留足过渡期后再移除。

### 3. 契约驱动

* **阅读 Markdown**: 每次生成 API 代码前，优先解析后端提供的 Markdown 接口定义。
* **类型安全**: 所有 API 调用必须有完整的 Request/Response 类型声明。
* **Mock 机制**: 本地开发默认开启 `MSW` (Mock Service Worker)，确保脱离后端也能跑通全流程。

---

## 🔌 第三方 CDN SDK 接入规范 (External SDK Integration) — CRITICAL

**背景**: 项目曾因天御验证码 SDK 接入不当导致线上加载失败，耗费大量排查时间。以下规则从此次经验中提炼，适用于所有通过 `<script>` 标签引入的第三方 CDN SDK。

### 规则

1. **接入前必须验证 SDK 地址的有效性** — MANDATORY
   - 在编码引入任何第三方 CDN SDK **之前**，必须先通过 HTTP 请求验证地址是否可用：
     - 发送 GET 请求确认返回 **HTTP 2xx 状态码**且内容为有效 JS；
     - 仅 HEAD 请求返回 200 不够（部分 CDN 的 HEAD 和 GET 行为不一致）；
     - 如果返回 404、403 或其他非 2xx 状态码，即使响应体包含内容，也**不得使用**该地址，必须查阅官方最新文档获取正确地址。
   - 当 SDK 存在版本迭代（如 v1.0 → v2.0），旧地址可能随时下线，**禁止**复用历史代码中的旧地址而不验证。

2. **严格遵循官方文档的引入方式**
   - `<script>` 标签的属性（如 `crossorigin`、`defer`、`async` 等）必须与官方文档示例**完全一致**，不得自行添加或省略。
   - 典型反例：官方未要求 `crossorigin="anonymous"`，自行添加后会触发浏览器 CORS 校验，若 CDN 返回非 2xx 状态码则脚本被拒绝执行。

3. **必须实现容灾回调（loadErrorCallback）**
   - 任何 CDN 外链 SDK 都存在加载失败的可能（网络波动、CDN 故障、防火墙拦截）。
   - **禁止**仅弹出错误提示就终止流程（如 `message.error('加载失败，请刷新')`）。
   - **必须**实现容灾回调：生成容灾凭证（如 `trerror_1001_` 前缀的 ticket），让后端根据凭证格式判断是否降级放行，保证业务不被阻塞。

4. **SDK 地址必须加注版本与验证日期**
   - 在 `index.html` 的 SDK 引入注释中标注：SDK 版本号、官方文档链接、最近一次验证可用的日期。
   - 第三方 CDN 地址可能因厂商升级而失效（如腾讯天御 1.0 `TCaptcha.js` → 2.0 `TJCaptcha.js`），注释有助于后续排查。
   - 示例：
     ```html
     <!-- 腾讯云天御验证码 SDK v2.0 | 文档: https://cloud.tencent.com/document/product/1110/36841 | 验证日期: 2026-03-18 -->
     <script src="https://turing.captcha.qcloud.com/TJCaptcha.js"></script>
     ```

5. **AppId / Key 等配置值禁止使用占位符提交**
   - 环境变量文件中的 SDK 配置（如 `VITE_CAPTCHA_APP_ID`）禁止以 `your_xxx_here`、`placeholder`、`TODO` 等占位符形式提交到代码仓库。
   - 必须在 `.env.example` 中保留占位符示例，在 `.env.development` 和 `.env.production` 中填入实际值。

---

## 🚫 禁令 (Non-Negotiables)

1. **禁止** 出现超过 300 行的"巨型组件"。拆分为子组件 + Hooks。
2. **禁止** 混合使用不同的图标库（统一使用 Ant Design Icons）。
3. **禁止** 绕过权限检查直接展示操作按钮。
4. **禁止** 在代码中留下未定义的 `any` 类型。
5. **禁止** 在 `index.tsx`（页面层）中编写任何业务逻辑。
6. **禁止** 超过 3 层的 JSX 嵌套（组件嵌套过深必须提取子组件）。
7. **禁止** 炫技语法（如过度使用柯里化、隐式类型推断链等），代码可读性优先。
8. **禁止** 跳过四文件结构，任何页面都必须包含 `index.tsx / hooks.ts / api.ts / types.ts`。
9. **禁止** 直接修改 `src/templates/[TemplateName]/index.tsx` 基线模版，扩展需求必须通过创建变体实现。
10. **禁止** 在不设置 `scroll.x` 的情况下为 `<Table>` 的列定义固定 `width` 且列宽总和超过容器宽度。所有多列表格必须设置 `scroll={{ x: 'max-content' }}`。

---

## ⚠️ AntD 组件陷阱清单（CRITICAL）

以下为 antd 高频踩坑点，开发时必须遵守：

| # | 场景 | 约束 | 错误示例 | 正确做法 |
|---|------|------|---------|---------|
| 1 | `Form.Item` + `name` | 带 `name` 的 `Form.Item` **有且仅有一个**直接子元素 | `<Form.Item name="x"><Upload/><Image/></Form.Item>` | 将额外元素移出 `Form.Item`，或拆分为隐藏字段 + 展示层 |
| 2 | `Upload` 自定义上传 | 使用 `customRequest` 时 `Form.Item` 不应同时绑定 `name`（会覆盖 `fileList`） | `<Form.Item name="file"><Upload customRequest={...}/></Form.Item>` | 用 `hidden` 隐藏字段做校验，Upload 放在不带 `name` 的 `Form.Item` 中 |
| 3 | `Upload` 的 `fileList` | `fileList` 中的 `url` 字段必须为 **string 类型**，非字符串会导致 antd 内部 `extname()` 白屏 | `url: someObject` 或 `url: undefined` | 构造 `fileList` 前用 `typeof url === 'string'` 校验 |

---

## 🤖 AI 交互指令 (Vibe Coding Prompting)

> "当我要创建一个新功能时，请按以下顺序执行：
> 1. **扫描模版**：先阅读 `src/templates/` 下相关模版的 `README.md`，判断是否有可直接复用的基线或变体；
> 2. 分析对应的 Markdown 接口契约；
> 3. 定义 `types.ts`（Request/Response 类型）；
> 4. 如涉及复杂状态流转，告诉我你打算定义的 XState 状态机逻辑，得到我确认后再继续；
> 5. 按照三层架构依次生成 `api.ts` → `hooks.ts` → `index.tsx`；
> 6. 如果过程中需要扩展模版，创建新变体并更新变体索引。"

---