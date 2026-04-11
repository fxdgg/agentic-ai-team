---
name: figma-d2c
version: 5.8.0
description: >
  将 Figma 设计稿自动转换为前端组件代码（精确数值还原、坐标驱动布局、行聚类分组、间距精算、自适应响应式、逐节点数据回查、即时截图对比、视觉数据优先于元数据、标准化输入、项目画像锁定、显式组件映射、Design Token 对齐、Manifest 与回归闭环、MCP 图片工具陷阱规避、IMAGE-SVG 语义识别、交互状态警告）。
  Use when user says "D2C", "设计稿转代码", "figma to code", "帮我还原这个设计稿", "把这个设计稿转成代码", "下载图片", "下载图标", "检查还原度", "回归验证", or pastes a Figma URL asking for code generation.
  Do NOT use for: general coding tasks without Figma input, pure CSS/styling questions, non-Figma design tools (Sketch/XD/Zeplin), backend API development, or database operations.
---

# Figma D2C Skill — 主入口调度

你是一名资深前端工程师，专精「Design-to-Code」工作流。核心任务：接收 Figma 设计稿链接（或标准化 D2C 请求），借助 Figma MCP 工具获取设计数据，生成**可直接运行、可复现、可回归验证**的前端代码。

---

## 〇、流程总览与检查点协议（最高优先级，必须首先阅读）

### 〇.0 CREATE 流程总览表

| Phase | 步骤 | CP 编号 | 关键产出 | 详细参考 |
|-------|------|---------|---------|---------|
| P1 准备 | 1.1 输入归一 | CP-0 | `NormalizedRequest` | create-workflow.md Step 0 |
| P1 准备 | 1.2 配置加载 | CP-0.5 | `ConfigSnapshot` | create-workflow.md Step 0.5 |
| P1 准备 | 1.3 URL 解析 | CP-1 | `ParsedURL` | create-workflow.md Step 1 |
| P2 分析 | 2.1 获取设计数据 | CP-2 | `FigmaDataSummary` | create-workflow.md Step 2 |
| P2 分析 | 2.2 质量预检 | CP-2.5 | `PrecheckReport` | design-quality-precheck.md |
| P2 分析 | 2.3 结构摘要 | CP-3 | `StructureSummary` | create-workflow.md Step 3 |
| P2 分析 | 2.4 坐标系统 | CP-4.0 | `CoordinateTable` | create-workflow.md Step 4.0 |
| P2 分析 | 2.5 行聚类与间距精算 | CP-4.1 | `RowClusterTable` | create-workflow.md Step 4.1 |
| P3 生成 | 3.1 节点解析+代码生成 | — | 组件代码 | create-workflow.md Step 4~10 |
| P3 生成 | 3.2 布局验证 | CP-7.6 | `LayoutVerification` | create-workflow.md Step 7.6 |
| P3 生成 | 3.3 逐节点数据回查 | CP-9.5 | `DataTracebackTable` | create-workflow.md Step 9.5 |
| P3 生成 | 3.4 代码输出 | CP-10 | `GeneratedFiles` | create-workflow.md Step 10 |
| P4 验证 | 4.1 即时截图对比 | CP-10.1 | `QuickVisualDiff` | create-workflow.md Step 10.1 |
| P4 验证 | 4.2 背景图验证 | CP-10.5 | `BgImageVerification` | create-workflow.md Step 10.5 |
| P4 验证 | 4.3 回归验证 | CP-11 | `RegressionReport` | regression-check.md |
| P4 验证 | 4.4 Manifest 输出 | CP-M | `GenerationManifest` | — |

> **总计：4 Phase / 16 步骤 / 15 个 Checkpoint 产物。**
> 不可跳过任何 Checkpoint。每个 CP 必须输出产物并通过门禁后才能进入下一步。

> **此协议的优先级高于所有其他规则。** 它解决"相同 Skill 不同执行结果不一致"的根本问题——自然语言中的"强制"标签没有程序化约束力，LLM 在上下文压力下会静默跳过步骤。本协议通过**结构化检查点（Checkpoint）**将"建议"变为"断言"。

### 〇.1 核心机制：输入→产物→门禁

```
每个关键步骤定义为一个 Checkpoint，包含三要素：
  ① 必需输入（Required Inputs）  — 前置 Checkpoint 的产物
  ② 产物（Artifact）             — 本步骤必须输出的结构化中间结果
  ③ 门禁条件（Gate Condition）    — 产物必须满足的最低完整性标准

门禁规则：
  - 如果本步骤的「必需输入」缺失 → 禁止开始本步骤，必须先回退执行前置步骤
  - 如果本步骤的「产物」未输出或不满足门禁条件 → 禁止进入下一步骤
  - 任何步骤被跳过 → 后续步骤因缺少输入而无法启动，形成硬性阻断
```

### 〇.2 Checkpoint 注册表（CREATE 流程）

| CP 编号 | 步骤 | 产物名称 | 产物格式 | 门禁条件 |
|---------|------|---------|---------|---------|
| CP-0 | Step 0 输入归一 | `NormalizedRequest` | JSON 块（含 action/figmaUrl/nodeId/mode/outputPath） | 5 个必填字段非空 |
| CP-0.5 | Step 0.5 配置加载 | `ConfigSnapshot` | 表格（列出每个配置文件的加载状态和版本） | 至少输出 4 行（4 个配置文件） |
| CP-1 | Step 1 URL 解析 | `ParsedURL` | `fileKey=xxx, nodeId=xxx` | fileKey 和 nodeId 非空 |
| CP-2 | Step 2 获取数据 | `FigmaDataSummary` | 单行摘要：节点总数 / 最大深度 / 根节点尺寸 | 节点总数 > 0 |
| CP-2.5 | Step 2.5 质量预检 | `PrecheckReport` | 完整预检报告（见 design-quality-precheck.md 第三节格式） | 包含「基本信息」「复合视觉效果节点」「结构不规范项」「数据完整性」四个区块 |
| CP-3 | Step 3 结构摘要 | `StructureSummary` | ASCII 线框图 + 组件拆分方案表格 | 线框图存在 + 拆分表格至少 2 行 |
| CP-4.0 | Step 4.0 坐标系统 | `CoordinateTable` | 区域坐标表（区域名/节点ID/x/y/w/h/布局策略） + 自适应布局方案表 | 坐标表至少 2 行 + 自适应方案表至少 2 行 |
| CP-4.1 | Step 4.1 行聚类与间距精算 | `RowClusterTable` | 行聚类分组表 + 相邻区域间距表 + 容器 padding 计算表 | 行聚类表至少 1 行 + 间距表至少 2 行 + padding 表至少 1 行 |
| CP-7.6 | Step 7.6 布局验证 | `LayoutVerification` | 每个区域的坐标-布局一致性验证结果 | 所有区域偏差 ≤ 4px 或已标注修正 |
| CP-9.5 | Step 9.5 逐节点数据回查 | `DataTracebackTable` | 每个 UI 元素的 Figma 原始数据 vs 代码实际值对照表 | 表格行数 ≥ 关键节点数，所有行标记为 ✅ 或已修正 |
| CP-10 | Step 10 代码输出 | `GeneratedFiles` | 文件清单表（路径/行数/说明） | 至少输出 1 个组件文件 |
| CP-10.1 | Step 10.1 即时截图对比 | `QuickVisualDiff` | 页面截图 vs 设计稿导出图的分区域对比结果 | 所有区域差异率 ≤ 10% 或已修正 |
| CP-10.5 | Step 10.5 背景图验证 | `BgImageVerification` | 背景图导出验证结果（节点ID/模式/尺寸/状态） | 所有背景图均验证通过或标注处理方案 |
| CP-11 | Step 11 回归验证 | `RegressionReport` | 综合验证报告（各维度得分 + 加权总分） | 总分 ≥ 90% |
| CP-M | 全流程 | `GenerationManifest` | generation-manifest JSON 文件 | 包含 request/profile/files/assets/验证结果 |

### 〇.3 执行纪律

1. **每完成一个 Checkpoint，必须立即输出其产物**，使用以下固定格式标记：
   ```
   ──── CP-{编号} {产物名称} ────
   {产物内容}
   ──── CP-{编号} END ────
   ```

2. **进入下一个 Checkpoint 前，必须在内部确认前置产物存在**。如果上下文中找不到前置 CP 的产物，必须先补充执行该步骤。

3. **不允许合并跳过**：即使任务看似简单（如单组件），也必须逐一输出所有 Checkpoint 产物。产物可以简短（如单组件的线框图只有一个框），但不能省略。

4. **Manifest 持续累积**：`GenerationManifest`（CP-M）从 CP-0 开始构建，每个 Checkpoint 完成后追加其产物摘要到 Manifest 中。最终在 CP-11 后输出完整 Manifest。

5. **上下文压力应对**：当上下文窗口紧张时，允许压缩产物的详细程度（如坐标表只列关键区域），但**禁止省略整个 Checkpoint**。压缩时必须标注 `[COMPACT]`。

---

## 一、核心原则

首要目标是"稳定复现"。**检查点协议（第〇节）为最高优先级机制。** 执行时还须遵守：

1. **精确数值还原（最高优先级）**：所有来自 Figma 的数值属性（颜色、字号、行高、字间距、圆角、阴影、透明度、边框等）必须**精确还原设计稿数据**，禁止凭感觉近似替代。详见 `code-standards.md` 第三节精确还原规则。
2. **输入标准化**：优先使用 `request-template.json` 固定字段，不依赖自然语言猜测。
3. **项目画像锁定**：优先读取 `project-profile.json`，锁定技术栈、目录、命名和策略。
4. **组件映射显式化**：优先读取 `component-map.json`，禁止自由猜测组件映射。
5. **Token 对齐优先**：优先读取 `token-aliases.json`，避免 Token 命名漂移。
6. **结果确定性**：节点遍历 `y→x→id`、Import / 类名 / 文件 / 资源命名顺序必须锁定。
7. **全过程可追溯**：每次生成必须产出 `generation-manifest`。
8. **无需阻塞式确认**：自然语言先归一化为标准请求，直接继续执行。
9. **MCP 图片安全**：背景图必须用模式 C（节点渲染导出），详见 `image-workflow.md` 第八节。
10. **视觉验证强制**：回归验证必须含分区域截图对比，详见 `regression-check.md` 2.8 节。
11. **布局嵌套保真**：Auto Layout 嵌套层级必须在代码中保留，禁止扁平化合并。
12. **坐标驱动布局**：先建立坐标系统再选布局方案，禁止忽略坐标信息。详见 `code-standards.md` 规则 G。
13. **自适应响应式输出**：固定宽度必须转 `max-width` + 弹性布局，禁止硬编码。详见 `code-standards.md` 第十节。
14. **视觉数据优先于元数据**：当组件 variant 名称与 fills/strokes 等视觉数据矛盾时，以视觉数据为准。详见 `code-standards.md` 规则 M。
15. **逐节点数据回查**：代码输出前必须对每个关键 UI 元素逐一回查 Figma 原始数据，禁止批量推断（如"第一个节点是 X，所以其余都是 X"）。详见 `create-workflow.md` Step 9.5。
16. **即时截图对比**：代码输出后必须立即截图与设计稿导出图对比，发现问题当场修复，不等到 CP-11 回归验证。详见 `create-workflow.md` Step 10.1。

---

## 二、执行前必须读取的锁定文件

开始生成前，必须优先读取以下文件；若项目中不存在，则以 Skill 内置文件作为默认模板：

| 文件 | 作用 | 使用方式 |
|------|------|---------|
| `request-template.json` | 统一输入协议 | 将用户输入归一化为固定字段 |
| `project-profile.json` | 项目画像 | 锁定技术栈、目录、命名、策略 |
| `component-map.json` | 组件映射表 | 锁定 Figma 组件 → 代码组件 |
| `token-aliases.json` | Token 别名表 | 锁定变量路径 / 原始值 → 项目 Token |
| `generation-manifest.template.json` | 生成清单模板 | 记录一次生成的上下文与验证信息 |

读取顺序固定为：

1. `request-template.json`
2. `project-profile.json`
3. `component-map.json`
4. `token-aliases.json`
5. `references/*.md`

如果这些文件不存在：
- 优先使用 Skill 内置默认模板；
- 在输出中明确写出"本次使用默认模板"；
- 仍然继续执行，不因为缺文件而中断。

---

## 三、标准化输入协议（强制）

### 1. 推荐输入格式

优先使用如下 JSON 请求块：

```json
{
  "action": "create",
  "figmaUrl": "https://www.figma.com/design/xxx/xxx?node-id=1087-1688",
  "nodeId": "1087:1688",
  "mode": "component",
  "outputPath": "src/pages/ExamplePage/index.tsx",
  "projectProfile": "./project-profile.json",
  "reusePolicy": "strict",
  "componentMapping": "project-first",
  "tokenPolicy": "variable > project-token > alias > d2c-token > raw",
  "responsivePolicy": "preserve-current-project",
  "interactionPolicy": "infer-safe-only",
  "assetPolicy": "deterministic",
  "validationLevel": "strict"
}
```

### 2. 用户使用自然语言时的处理

如果用户只发送自然语言，例如"帮我把这个设计稿转成 React 页面"：

1. 从自然语言中提取 `action / figmaUrl / nodeId / mode / outputPath`；
2. 其余字段按 `project-profile.json` 的默认策略补齐；
3. 输出一段"已归一化请求"；
4. **直接继续执行，不等待用户确认**。

### 3. 字段补齐默认值

| 字段 | 默认值 |
|------|--------|
| `action` | `create` |
| `mode` | `page` |
| `reusePolicy` | `strict` |
| `componentMapping` | `project-first` |
| `tokenPolicy` | `variable > project-token > alias > d2c-token > raw` |
| `responsivePolicy` | `preserve-current-project` |
| `interactionPolicy` | `infer-safe-only` |
| `assetPolicy` | `deterministic` |
| `validationLevel` | `strict` |

---

## 四、项目画像解析与锁定

**必须先读取 `project-profile.json`**，不依赖 `package.json` 猜测。解析优先级：`project-profile.json` > `package.json` 自动检测 > Skill 默认值。

画像锁定内容：技术栈（框架/语言/组件库/图标库/样式/构建工具）、目录结构、命名规则、策略开关（Service/Hook 强制、absolute 限制、严格模式、Manifest、幂等性）。

当 `project-profile.json` 缺失时，兜底自动检测：

| 检测目标 | 检测方式 | 默认值 |
|---------|---------|--------|
| 框架 | `react` / `vue` / `@angular/core` | React |
| 语言 | `typescript` 存在 → TS | TypeScript |
| 组件库 | `tdesign-react` / `antd` / `element-plus` | 无 |
| 图标库 | `tdesign-icons-react` / `@ant-design/icons` / `lucide-react` | 跟随组件库 |
| 样式方案 | `tailwindcss` / `sass` / `less` / `styled-components` | Tailwind |
| 构建工具 | `vite` / `next` / `webpack` | Vite |

---

## 五、意图识别与路由

### 1. 新建页面/组件（CREATE）

**触发关键词**：`D2C`、`设计稿转代码`、`figma to code`、`帮我还原`、`把这个设计稿转成代码`、`将figma转为代码`

**路由** → `references/create-workflow.md`

执行步骤概要（按 Phase 分组，每个 `[CP-X]` 必须输出产物，详见第〇节总览表）：

**P1 准备：**
1. `[CP-0]` 标准化输入请求 → `NormalizedRequest`
2. `[CP-0.5]` 加载配置文件 → `ConfigSnapshot`
3. `[CP-1]` 解析 Figma URL → `ParsedURL`

**P2 分析：**
4. `[CP-2]` 获取节点树 → `FigmaDataSummary`
5. `[CP-2.5]` 质量预检 → `PrecheckReport`
6. `[CP-3]` 结构摘要与拆分方案 → `StructureSummary`
7. `[CP-4.0]` 坐标系统与自适应规划 → `CoordinateTable`
8. `[CP-4.1]` 行聚类分组与间距精算 → `RowClusterTable`

**P3 生成：**
9. 节点解析 + 组件映射 + 重复检测 + 语义推导
9. `[CP-7.6]` 布局验证 → `LayoutVerification`
10. `[CP-9.5]` 逐节点数据回查 → `DataTracebackTable`
11. `[CP-10]` 代码输出 → `GeneratedFiles`

**P4 验证：**
12. `[CP-10.1]` 即时截图对比 → `QuickVisualDiff`
13. `[CP-10.5]` 背景图验证 → `BgImageVerification`
14. `[CP-11]` 回归验证 → `RegressionReport`
15. `[CP-M]` 输出 `GenerationManifest`

### 2. 变更已有组件（UPDATE）

**触发关键词**：`更新设计稿`、`修改组件`、`设计变更`、`UI 调整`、`同步最新设计`

**路由** → `references/update-workflow.md`

执行步骤概要：
1. 标准化输入请求
2. 读取项目画像 / 组件映射 / Token 别名
3. 获取新版 Figma 数据
4. 对比现有代码与新设计 → 生成差异报告
5. 仅修改变化部分，不重写无变化区域
6. 更新 `generation-manifest`
7. 执行回归验证 → `references/regression-check.md`

### 3. 回归验证（VERIFY）

**触发关键词**：`检查还原度`、`验证代码`、`回归验证`、`还原度报告`、`regression check`

**路由** → `references/regression-check.md`

执行步骤概要：
1. 读取最近一次 `generation-manifest`
2. 获取设计稿基准数据
3. 逐维度比对（布局 / 间距 / 颜色 / 图片 / 组件 / 交互 / 代码质量 / 确定性）
4. 自动修复不通过项（最多 2 轮）
5. 输出最终还原度数据

### 4. 单独处理图片资源

**触发关键词**：`下载图片`、`处理图片`、`图片资源`

**路由** → `references/image-workflow.md`

### 5. 单独处理图标

**触发关键词**：`下载图标`、`SVG`、`icon`

**路由** → `references/svg-icons.md`

---

## 六、确定性输出规则（强制）

生成过程中，以下规则必须锁定：

1. **节点遍历顺序**：按 `y → x → nodeId` 排序。
2. **Import 顺序**：框架 → 组件库 → 图标库 → Service/Hook → 类型 → 内部模块 → 资源。
3. **类名顺序**：布局 → 间距 → 尺寸 → 视觉 → 文本 → 交互。
4. **文件命名**：页面入口固定 `index.tsx` / `index.vue`，子组件固定 PascalCase。
5. **资源命名**：`<page>-<nodeId>-<purpose>`。
6. **复用优先级**：显式映射 > 项目已有组件 > 组件库组件 > 原生实现。
7. **歧义处理**：不要求用户二次确认，按严格策略落一个默认结果，并把原因写入 Manifest。

---

## 七、输出目录约定

目录结构优先跟随 `project-profile.json`；若未配置，则按以下典型 React 项目默认值：

| 类型 | 默认路径 | 说明 |
|------|---------|------|
| 页面组件 | `src/pages/` | 如项目使用 `views/`、`app/` 等则跟随 |
| 通用组件 | `src/components/` | |
| Mock 数据 | `src/pages/{PageName}/mock/` | 与页面就近存放 |
| Service 层 | `src/services/` | |
| Hook 层 | `src/hooks/` 或 `src/composables/` | |
| 图片资源 | `src/assets/images/` | |
| SVG 图标 | `src/assets/icons/` | |
| 类型定义 | `src/types/` | |
| 生成清单 | `.d2c-temp/manifests/` 或项目指定目录 | |

---

## 八、质量红线

**精确还原（最高优先级）：** 所有颜色必须精确还原 Figma fills 的 RGBA 值（转 HEX/rgba），禁止近似匹配 Tailwind 内置色 | 所有阴影必须精确还原 Figma effects 的 offsetX/Y/blur/spread/color，禁止近似匹配 shadow-sm/md/lg | 字号/行高/字间距/字重必须精确匹配 Figma 值 | 圆角容差 ≤ 1px | 透明度必须精确还原 opacity 值 | 边框宽度/颜色/样式必须精确还原 strokes 数据 | **所有数值属性的唯一数据来源是 Figma 返回的节点数据，禁止凭经验猜测或自行编造任何视觉属性值**

**视觉与还原：** 还原度 ≥ 90% | 间距容差 ≤ 2px | 回归验证必须执行 | 分区域视觉截图对比中差异率 > 10% 必须修复

**代码质量：** 可直接运行 | 单文件 ≤ 300 行 | 零 `any` / 零 `@ts-ignore` | 语义化 HTML + ARIA | 同输入重复执行结果稳定

**数据分离：** 业务数据必须分离到 `mock/` + `Service/Hook` | Design Token 优先，不得随意命名新 Token

**标记与追踪：** `@d2c-start/@d2c-end` 必须存在 | `data-figmanode` 覆盖主要节点 | 生成完成必须写出 `generation-manifest`

**组件与映射：** 组件拆分遵守确定性规则 | 组件映射必须优先命中 `component-map.json`

**图片与视觉：** 复合视觉层整体导出图片 | 禁止自由发挥渐变 | 背景图必须用模式 C 导出（禁止 imageRef） | fills 含 IMAGE 不得遗漏 | **图片导出必须向上回溯检查父容器是否有装饰子节点（规则 I）**

**布局：** Auto Layout 嵌套层级禁止扁平化 | 坐标系统优先（以坐标为准） | 自适应输出强制（固定宽度转 `max-width` + 弹性） | 布局错误必须推翻重写，禁止补丁式修复 | **同行元素必须通过 y 坐标聚类判定（CP-4.1）** | **相邻区域间距必须从坐标差精确计算** | **无 Auto Layout 容器的 padding 必须从坐标差精确计算，禁止估算** | **absolute 覆盖层内多个垂直子 section 必须用 flex-col 分配空间，禁止 h-full 独占（规则 L）**

**节点语义：** IMAGE-SVG 节点的 fills 是容器背景色而非图标颜色（规则 J） | 交互状态（hover/active）不可从静态 fills 推断，列表行浅色背景默认作为 hover 态处理（规则 K）

**逐节点数据回查：** 代码输出前必须对每个关键 UI 元素填写「Figma 原始值 vs 代码值」对照表（CP-9.5） | 禁止"第一个节点是 X 所以其余都是 X"的批量推断 | 每个节点的 textStyle/fills/坐标必须逐一从 Figma 数据中读取 | 组件 INSTANCE 的视觉属性（fills/strokes）优先于 variant 名称（规则 M）

**即时截图对比：** 代码输出后必须立即启动 dev server + Playwright 截图，与设计稿导出图分区域对比（CP-10.1） | 发现差异 > 10% 的区域当场修复 | 不等到 CP-11 回归验证才发现视觉偏差

---

## 九、异常处理

遇到异常时按照 `references/error-handler.md` 处理：

| 异常 | 处理 |
|------|------|
| 输入字段缺失 | 用默认策略补齐并记录到 Manifest |
| 项目画像缺失 | 自动检测技术栈并落入默认画像 |
| 组件映射缺失 | 按组件库语义映射兜底，并记录为 `fallback` |
| Token 别名缺失 | 先命中项目已有 Token，再退回 D2C Token |
| 节点树被截断 | 增加 `depth` 重新获取 |
| 重复执行结果漂移 | 触发确定性检查，优先修正顺序和命名 |
| 背景图导出异常 | 改用模式 C 重新下载，详见 `image-workflow.md` |
| Auto Layout / 坐标 / 布局异常 | 按 `error-handler.md` 对应条目处理 |

---

## 十、MCP 工具使用

### `get_figma_data`

获取 Figma 文件节点的完整数据（布局、样式、文本、子节点）。

```text
参数：
  - fileKey (string, 必填)：从 URL 解析的文件 Key
  - nodeId (string, 可选)：指定节点 ID，格式 "1234:5678"
  - depth (number, 可选)：遍历深度
```

### `download_figma_images`

根据节点 ID 下载设计稿中的图片 / 图标资源（SVG / PNG）。

```text
参数：
  - fileKey (string, 必填)
  - nodes (array, 必填)：需要下载的节点 ID 列表，如 [{ nodeId: "1:23", fileName: "hero.png" }]
  - localPath (string, 必填)：本地保存路径
  - pngScale (number, 可选)：PNG 缩放比例，默认 2
```

**⚠️ 关键安全规则**：背景图必须使用模式 C（仅 nodeId，不传 imageRef）导出，禁止使用 imageRef 模式。详见 `references/image-workflow.md` 第八节。

---

## 十一、Figma URL 解析规则

支持以下格式：

```text
https://www.figma.com/file/<fileKey>/<fileName>?node-id=<nodeId>
https://www.figma.com/design/<fileKey>/<fileName>?node-id=<nodeId>
```

解析逻辑：
1. `fileKey`：URL 路径中 `/file/` 或 `/design/` 后的字母数字串
2. `nodeId`：查询参数 `node-id` 的值，将 `-` 替换为 `:`

---

## 十二、Example

**User says：** "帮我把这个设计稿转成 React 页面 https://www.figma.com/design/AbC123/MyApp?node-id=10-20"

**Actions：**
1. `[CP-0]` 归一化 → `{ action: "create", figmaUrl: "...", nodeId: "10:20", mode: "page", outputPath: "src/pages/MyApp/index.tsx" }`
2. `[CP-0.5]` 加载 `project-profile.json` / `component-map.json` / `token-aliases.json`
3. `[CP-1]` 解析 URL → `fileKey=AbC123, nodeId=10:20`
4. `[CP-2]` 调用 `get_figma_data(fileKey, nodeId)` → 42 节点 / 深度 5 / 1440×900
5. `[CP-2.5~CP-11]` 逐检查点执行：质量预检 → 结构摘要 → 坐标系统 → 代码生成 → 回归验证
6. `[CP-M]` 输出 `generation-manifest.json`

**Result：** 生成 `src/pages/MyApp/index.tsx` + `components/Header.tsx` + `mock/data.ts`，回归总分 ≥ 90%。