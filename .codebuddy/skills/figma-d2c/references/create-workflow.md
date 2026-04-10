# 新建流程（Create Workflow）

当用户提供 Figma 链接要求转换为代码时，严格按照以下流程执行。核心要求是：**先统一输入和项目约束，再生成代码；先锁定复用与 Token 决策，再输出产物。**

> **⚠️ 检查点执行协议生效**：本流程中每个 `[CP-X]` 标记的步骤，都必须输出对应的结构化产物，并用 `──── CP-X ... ────` 格式标记。后续步骤的「必需输入」如果缺失，必须先回退执行前置步骤。详见 `SKILL.md` 第〇节。

---

## Step 0：标准化输入归一 `[CP-0]`

> **Checkpoint CP-0** | 必需输入：用户消息（Figma 链接或自然语言） | 产物：`NormalizedRequest` | 门禁：5 个必填字段非空

在开始解析 Figma URL 之前，必须先将用户请求归一化为 `request-template.json` 的固定字段：

```json
{
  "action": "create",
  "figmaUrl": "https://www.figma.com/design/xxx/xxx?node-id=1087-1688",
  "nodeId": "1087:1688",
  "mode": "page",
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

处理规则：

1. 用户使用自然语言时，先抽取 `figmaUrl`、`nodeId`、`outputPath` 等关键字段；
2. 缺失字段按 `project-profile.json` 默认值补齐；
3. 输出"已归一化请求"后直接继续执行，不等待用户确认；
4. 本次归一化结果必须写入 `generation-manifest`。

**📋 CP-0 产物输出（必须）：**

```
──── CP-0 NormalizedRequest ────
{
  "action": "create",
  "figmaUrl": "{实际URL}",
  "nodeId": "{实际nodeId}",
  "mode": "{page|component}",
  "outputPath": "{实际路径}"
}
──── CP-0 END ────
```

---

## Step 0.5：读取锁定配置 `[CP-0.5]`

> **Checkpoint CP-0.5** | 必需输入：CP-0 `NormalizedRequest` | 产物：`ConfigSnapshot` | 门禁：至少输出 4 行（4 个配置文件的加载状态）

在真正访问 Figma 前，必须按顺序读取以下文件：

1. `project-profile.json`
2. `component-map.json`
3. `token-aliases.json`
4. `generation-manifest.template.json`

执行规则：

- `project-profile.json` 锁定技术栈、目录、命名和生成策略；
- `component-map.json` 锁定组件复用的优先级与 props 映射；
- `token-aliases.json` 锁定 Token 的命名和映射；
- 如果文件缺失，使用 Skill 默认模板继续执行，并在 Manifest 记录 `usedDefaultTemplate: true`。

**📋 CP-0.5 产物输出（必须）：**

```
──── CP-0.5 ConfigSnapshot ────
| 配置文件 | 状态 | 版本/来源 |
|---------|------|----------|
| project-profile.json | ✅ 已加载 / ⚠️ 使用默认模板 | {版本或路径} |
| component-map.json   | ✅ 已加载 / ⚠️ 使用默认模板 | {映射规则数} |
| token-aliases.json   | ✅ 已加载 / ⚠️ 使用默认模板 | {别名数} |
| generation-manifest.template.json | ✅ 已加载 | {模板版本} |
──── CP-0.5 END ────
```

---

## Step 1：解析 Figma URL `[CP-1]`

> **Checkpoint CP-1** | 必需输入：CP-0 `NormalizedRequest`（含 figmaUrl） | 产物：`ParsedURL` | 门禁：fileKey 和 nodeId 非空

从用户消息中提取 Figma 链接，解析出 `fileKey` 和 `nodeId`：

```
URL 格式：
  figma.com/(file|design)/<fileKey>/<name>?node-id=<nodeId>

解析规则：
  - fileKey = 路径中 /file/ 或 /design/ 后的字母数字串
  - nodeId = 查询参数 node-id 的值，将 '-' 替换为 ':'
```

如果用户未提供 `node-id`，询问用户具体需要转换哪个页面/组件。

**📋 CP-1 产物输出（必须）：**

```
──── CP-1 ParsedURL ────
fileKey = {实际fileKey}
nodeId  = {实际nodeId}
──── CP-1 END ────
```

---

## Step 2：获取设计数据 `[CP-2]`

> **Checkpoint CP-2** | 必需输入：CP-1 `ParsedURL`（fileKey + nodeId） | 产物：`FigmaDataSummary` | 门禁：节点总数 > 0

调用 MCP 工具 `get_figma_data`：

```
get_figma_data({
  fileKey: "<解析出的 fileKey>",
  nodeId: "<解析出的 nodeId>"  // 可选
})
```

检查返回数据是否有效：
- 节点树存在且非空
- 至少有一层子节点
- 如无效 → 触发 `error-handler.md` 异常处理

**📋 CP-2 产物输出（必须）：**

```
──── CP-2 FigmaDataSummary ────
节点总数：{N} 个
最大深度：{N} 层
根节点尺寸：{W}×{H}
根节点类型：{FRAME/GROUP/...}
直接子节点数：{N} 个
──── CP-2 END ────
```

---

## Step 2.5：设计稿质量预检 `[CP-2.5]`

> **Checkpoint CP-2.5** | 必需输入：CP-2 `FigmaDataSummary`（确认节点树有效） | 产物：`PrecheckReport` | 门禁：报告包含「基本信息」「复合视觉效果节点」「结构不规范项」「数据完整性」四个区块

在代码生成前，**必须先执行**设计稿质量预检，按照 `design-quality-precheck.md` 规范：

1. **识别复合视觉效果节点** — 遍历节点树，检测含 cropTransform、多 fill 叠加（IMAGE + 渐变 ≥ 2 层）、非标准混合模式的节点
2. **检查设计稿结构规范性** — GROUP vs FRAME、Auto Layout 覆盖率、渐变终止色一致性
3. **检查数据完整性** — 节点树是否被截断、图片引用是否完整
4. **输出预检报告** — 列出所有复合视觉效果节点和不规范项
5. **制定处理策略** — 复合视觉效果节点标记为"整体导出图片"，简单渐变标记为"CSS 还原"
6. **识别背景图节点** — 遍历所有 fills 含 IMAGE 类型的容器节点，按 `design-quality-precheck.md` 第七节的背景图专项预检规则处理
7. **验证 Auto Layout 嵌套层级** — 检查所有嵌套的 Auto Layout 容器（特别是外层 VERTICAL 内含 HORIZONTAL 子容器的情况），标记需要在代码中保留嵌套 flex 容器的节点

**此步骤的核心价值**：提前判断哪些节点不能用 CSS 还原，避免在代码生成阶段反复试错 CSS 渐变和层叠效果。

**预检后立即处理**：
- 复合视觉效果节点 → 立即加入 `download_figma_images` 队列，与 Step 7（图片处理）合并执行
- 背景图节点 → 标记为"节点渲染模式导出"（模式 C），检查 `clipContent` 属性，如为 true 则标记高风险
- 节点树被截断 → 立即用更大的 `depth` 参数重新获取
- Auto Layout 嵌套节点 → 在结构摘要中明确标注需要保留的嵌套容器层级

**📋 CP-2.5 产物输出（必须）：**

完整预检报告必须包含以下四个区块（格式见 `design-quality-precheck.md` 第三节）：
1. 📊 基本信息（节点总数、最大深度、Auto Layout 覆盖率）
2. 🎨 复合视觉效果节点（列表，可为空但必须输出"无"）
3. ⚠️ 结构不规范项（列表，可为空但必须输出"无"）
4. ✅ 数据完整性（节点树/图片引用/文本内容完整性）

```
──── CP-2.5 PrecheckReport ────
{完整预检报告内容}
──── CP-2.5 END ────
```

---

## Step 3：输出结构摘要与组件拆分方案 `[CP-3]`

> **Checkpoint CP-3** | 必需输入：CP-2.5 `PrecheckReport` | 产物：`StructureSummary` | 门禁：ASCII 线框图存在 + 拆分方案表格至少 2 行

在生成代码前，**必须先**输出结构摘要，包含 ASCII 线框图和组件拆分方案。**输出后无需等待用户确认，直接继续下一步**（除非用户主动中断）。

### 3.1 ASCII 线框图

```
┌─────────────────────────────────────────────┐
│  Header                                     │
│  ┌──────┐  ┌────────────────────┐  ┌─────┐ │
│  │ Logo │  │     Navigation     │  │ CTA │ │
│  └──────┘  └────────────────────┘  └─────┘ │
├─────────────────────────────────────────────┤
│  Hero Section                               │
│  ┌─────────────────┐  ┌──────────────────┐  │
│  │                  │  │   Title          │  │
│  │   Hero Image     │  │   Subtitle       │  │
│  │                  │  │   [Button]       │  │
│  └─────────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────┤
│  Content Area                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │Card 1│ │Card 2│ │Card 3│ │Card 4│ ×N    │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
└─────────────────────────────────────────────┘
```

规则：
- 使用 `┌ ┐ └ ┘ ─ │ ├ ┤` 绘制边框
- 标注每个区域的语义名称
- 重复元素标注 `×N`（表示通过 `map()` 循环渲染）
- 标注哪些是组件库组件（如 `[Button]`、`[Input]`）

### 3.2 组件拆分方案（必须输出）

线框图后**必须**紧跟输出组件拆分方案表格，遵循 `code-standards.md` 第八节的拆分规则：

```
📦 组件拆分方案：
  文件路径                              | 对应区域        | 预估行数 | 说明
  src/pages/{Page}/index.tsx           | 页面入口（组装） | ~30行    | 纯组装层，不含 UI 代码
  src/pages/{Page}/TopBar.tsx          | 顶部栏          | ~60行    | Logo + 导航 + 用户区
  src/pages/{Page}/NavBar.tsx          | 次级导航        | ~40行    | 面包屑 + 搜索
  src/pages/{Page}/Sidebar.tsx         | 左侧边栏        | ~120行   | 目录树 + 折叠交互
  src/pages/{Page}/MainContent.tsx     | 主内容区        | ~150行   | 文章内容
  src/pages/{Page}/RightPanel.tsx      | 右侧面板        | ~80行    | 推荐课程
  src/pages/{Page}/mock/types.ts       | 类型定义        | ~50行    | 业务实体接口
  src/pages/{Page}/mock/{page}Data.ts  | Mock数据        | ~80行    | 含 @source 标注
```

**此表格确保不同执行者对拆分结果达成一致。**

### 3.3 流程继续

输出结构摘要和拆分方案后，**直接进入 Step 4**，不等待用户响应。如果用户在后续回复中要求调整结构，按 `update-workflow.md` 处理。

**📋 CP-3 产物输出（必须）：**

结构摘要必须包含：① ASCII 线框图 ② 组件拆分方案表格（至少 2 行）。

```
──── CP-3 StructureSummary ────
{ASCII 线框图}

📦 组件拆分方案：
  文件路径 | 对应区域 | 预估行数 | 说明
  ...      | ...     | ...     | ...
──── CP-3 END ────
```

---

## Step 4.0：坐标系统建立与自适应布局规划 `[CP-4.0]`

> **Checkpoint CP-4.0** | 必需输入：CP-3 `StructureSummary` + CP-2 Figma 数据 | 产物：`CoordinateTable` | 门禁：坐标表至少 2 行 + 自适应方案表至少 2 行

> **此步骤是 解决"忽略坐标信息导致布局偏移"和"固定宽度页面不可缩放"两大高频问题。**

### 4.0.1 坐标系统建立

在递归解析节点树之前，**必须先建立全局坐标系统**：

```
流程：
1. 读取根节点的 boundingBox（整体画布尺寸，如 1920×2359）
2. 记录根节点坐标作为原点 (rootX, rootY)
3. 对根节点的每个直接子节点，提取 locationRelativeToParent 坐标
4. 建立「区域坐标表」：

📐 坐标系统（根节点 1920×2359）：
  区域名称     | 节点ID    | x    | y    | w    | h    | 布局策略
  导航栏       | 389:100  | 0    | 0    | 1920 | 60   | 全宽 flex-row
  Hero 背景    | 389:200  | -320 | 60   | 2560 | 400  | 超宽背景 overflow-hidden
  课程信息     | 389:210  | 370  | 140  | 1180 | 220  | 内容区 flex-col
  进度圆环     | 389:220  | 1390 | 147  | 160  | 160  | 独立定位
  课程简介     | 389:300  | 0    | 460  | 1920 | 192  | 全宽容器
  课程列表     | 389:400  | 370  | 692  | 1180 | 1100 | 内容区 flex-col
  底部背景     | 389:500  | 0    | 1872 | 1921 | 487  | 全宽背景

5. 标注每个区域的坐标关系：
   - 是否为全宽区域（w ≈ 根节点宽度 ± 偏移）
   - 是否为内容区域（w < 根节点宽度，需要水平居中）
   - 是否有超宽溢出（x < 0 或 x + w > 根节点宽度）
   - 是否与其他区域有坐标重叠（需要绝对定位）
```

### 4.0.2 自适应布局规划

**设计稿是固定宽度，但生成的页面必须自适应屏幕。** 基于坐标系统表，将固定宽度转换为自适应布局方案：

```
转换规则（按区域类型）：

规则 1：全宽背景区域（w ≈ 根节点宽度 或 w > 根节点宽度）
  设计稿：固定 1920px 或超宽 2560px
  → 代码：width: 100%（撑满视口），overflow: hidden（裁切超宽部分）
  → 背景图：width: 100%, min-width: {设计稿宽度}px（保证小屏不留白）

规则 2：居中内容区域（x > 0 且 x + w < 根节点宽度）
  设计稿：固定宽度 1180px，左偏移 370px
  → 代码：max-width: {设计稿内容宽度}px, margin: 0 auto, width: 100%
  → 内容撑满容器，超过 max-width 时居中，小于时 100% 填充
  → 计算方式：左右边距 = (根节点宽度 - 内容宽度) / 2
    若 左偏移 ≈ (根节点宽度 - 内容宽度) / 2 → 确认为居中布局

规则 3：内容区内的子元素
  设计稿：子元素有固定宽度（如 1068px、1020px）
  → 代码：width: 100% 或 flex-1（相对于父容器弹性伸缩）
  → 仅在子元素宽度与父容器宽度差值较大时才保留固定宽度

规则 4：超宽装饰元素（x < 0，即从画布左侧溢出）
  设计稿：w=2560, x=-320（居中裁切）
  → 代码：父容器 overflow-hidden + width:100%
  → 图片：width: max(100%, {设计稿原始宽度}px), 居中对齐

规则 5：页面根容器
  设计稿：固定 1920×N
  → 代码：width: 100%, min-height: 100vh（撑满视口）
  → 禁止 width: 1920px 硬编码
```

**自适应布局规划输出（必须在代码生成前确认）：**

```
📱 自适应布局方案：
  设计稿基准宽度：1920px
  内容区最大宽度：1180px（居中）

  区域            | 设计稿宽度 | 自适应策略          | CSS 实现
  页面根容器      | 1920px    | 全宽               | w-full min-h-screen
  全宽背景区      | 1920~2560 | 全宽 + 溢出裁切     | w-full overflow-hidden
  内容容器        | 1180px    | max-width + 居中   | max-w-[1180px] mx-auto w-full px-4
  内容子元素      | 1068px    | 弹性宽度           | w-full
  超宽背景图      | 2560px    | min-width + 居中   | min-w-[2560px] left-1/2 -translate-x-1/2
```

### 4.0.3 坐标系统 → 布局方案的决策树

```
对每个区域/容器节点，依次判断：

1. 该区域是否有 Auto Layout？
   ├── 有 → 以 Auto Layout 属性（layoutMode / itemSpacing / padding）为主
   │         但必须用坐标交叉验证：子元素的实际坐标间距是否与 itemSpacing 一致
   │         如果不一致 → 以坐标为准（设计师可能手动调整了位置）
   └── 无 → 纯坐标驱动，进入步骤 2

2. 子元素之间的坐标关系分析：
   a. 所有子元素垂直堆叠（y[i+1] ≈ y[i] + h[i]）→ flex-col + gap
   b. 所有子元素水平排列（x[i+1] ≈ x[i] + w[i]）→ flex-row + gap
   c. 子元素有坐标重叠 → relative 容器 + absolute 定位
   d. 子元素不规则分布 → 分组（按 y 坐标聚类为"行"，行内按 x 排序）

3. 该区域是否需要自适应？（规则见 4.0.2）
   ├── 全宽区域 → width: 100%
   ├── 居中内容区 → max-width + mx-auto
   └── 固定小元素（如按钮、图标）→ 保持固定尺寸

⚠️ 关键约束：
  - 禁止在没有分析坐标的情况下直接使用流式布局
  - 禁止用 absolute 定位所有元素（除非确认是覆盖/悬浮元素）
  - 当坐标分析结果与 Auto Layout 矛盾时，输出警告并以坐标为准
```

**📋 CP-4.0 产物输出（必须）：**

必须同时输出两个表格：① 区域坐标表 ② 自适应布局方案表。

```
──── CP-4.0 CoordinateTable ────
📐 坐标系统（根节点 {W}×{H}）：
  区域名称 | 节点ID | x | y | w | h | 布局策略
  ...      | ...   | . | . | . | . | ...

📱 自适应布局方案：
  设计稿基准宽度：{W}px
  内容区最大宽度：{cW}px（居中）

  区域 | 设计稿宽度 | 自适应策略 | CSS 实现
  ...  | ...       | ...       | ...
──── CP-4.0 END ────
```

---

## Step 4.1：行聚类分组与间距精算 `[CP-4.1]`

> **Checkpoint CP-4.1** | 必需输入：CP-4.0 `CoordinateTable` + CP-2 Figma 数据 | 产物：`RowClusterTable` | 门禁：行聚类表至少 1 行 + 相邻间距表至少 2 行 + padding 计算表至少 1 行

> **此步骤解决三大高频问题：① 同行元素被错误垂直堆叠 ② 相邻模块间距丢失 ③ 无 Auto Layout 容器的 padding 不精确。**

### 4.1.1 行聚类分组（强制，解决"同行判定失败"）

**对每个无 Auto Layout 的容器节点的直接子节点，必须执行 y 坐标聚类：**

```
算法：
1. 取所有直接子节点的 (nodeId, x, y, w, h)
2. 按 y 坐标升序排序
3. 执行聚类：
   对于相邻节点 A 和 B（按 y 排序后）：
   如果 |A.y - B.y| < min(A.h, B.h) / 2
     → A 和 B 归入同一行（同一个 flex-row 容器）
   否则
     → A 和 B 属于不同行（不同的 flex-row 或独立节点）
4. 每一行内的节点按 x 坐标升序排列
5. 输出行聚类表

⚠️ 关键：此算法必须在代码生成之前执行。
  禁止跳过聚类直接将所有子节点放入 flex-col。
  禁止仅依赖 Figma 节点树的层级关系判断排列方向。

示例：
  根节点子节点坐标：
    389:310 (繼續學習按钮)  y=317 h=40
    389:278 (播放信息 GROUP) y=325 h=24

  聚类判定：|317-325| = 8 < min(40,24)/2 = 12
  → 同一行 → 代码中包裹在同一个 flex-row 容器中

反例（之前的错误）：
  ❌ 两个节点按 y 排序后直接放入 flex-col → 变成上下排列
  ✅ 聚类发现 y 差 < 阈值 → 放入 flex-row → 水平排列
```

### 4.1.2 相邻区域间距精算（强制，解决"模块间间距丢失"）

**对 CP-4.0 坐标表中的每对相邻区域，必须计算并记录间距：**

```
算法：
1. 将坐标表中的区域按 y 坐标升序排序
2. 对每对相邻区域 (A, B)：
   verticalGap = B.y - (A.y + A.h)
3. 如果 verticalGap > 0 → 记录到间距表
4. 如果 verticalGap > 8px → 代码中必须显式插入间距（spacer div 或 margin）

⚠️ 此间距不会被任何 Auto Layout 的 gap 属性覆盖，
   因为这是根节点级的子元素间距，根节点通常没有 Auto Layout。

示例：
  课程简介区 (y:460, h:192) → 底部 y=652
  课程列表区 (y:692)
  → 间距 = 692 - 652 = 40px
  → 代码中必须在两个组件之间插入 h-10（40px）

间距表输出格式：
  区域A → 区域B | 间距 | 代码实现
  课程简介 → 课程列表 | 40px | h-10 spacer div
  课程列表 → 底部装饰 | 80px | mb-20
```

### 4.1.3 容器 padding 精算（强制，解决"padding 不精确"）

**对每个无 Auto Layout 的容器节点，必须通过坐标差计算精确 padding：**

```
算法：
1. 取容器节点的 (cx, cy, cw, ch)
2. 取容器内第一个子节点（按 y 最小）的 (fx, fy)
3. 取容器内最后一个子节点（按 y+h 最大）的 (lx, ly, lw, lh)
4. 计算：
   padding-top    = fy - cy
   padding-left   = min(所有子节点 x) - cx
   padding-bottom = (cy + ch) - (ly + lh)
   padding-right  = (cx + cw) - max(所有子节点 x + w)

⚠️ 禁止使用"看起来差不多"的标准 Tailwind 值代替精确计算。
   只有当计算值与标准值差 ≤ 2px 时才可以用标准值。

示例：
  容器 405:2487 (x:370, y:692, w:1180, h:1100)
  第一个子元素 405:2492 (x:426, y:748)
  → padding-left = 426 - 370 = 56px
  → padding-top  = 748 - 692 = 56px
  → 代码：p-[56px]  （不是 p-6 或 p-8）

padding 计算表输出格式：
  容器节点 | 子元素范围 | pt | pr | pb | pl | 代码
  405:2487 | 405:2492~418:2768 | 56px | 56px | 56px | 56px | p-[56px]
```

**📋 CP-4.1 产物输出（必须）：**

```
──── CP-4.1 RowClusterTable ────
📊 行聚类分组：
  容器 | 行号 | 节点列表(按x排序) | y范围 | 布局
  {容器ID} | 行1 | {nodeA}, {nodeB} | y=317~325 | flex-row gap-4
  {容器ID} | 行2 | {nodeC} | y=460 | 独立节点
  ...

📏 相邻区域间距表：
  区域A → 区域B | A底部y | B顶部y | 间距 | 代码实现
  ...

📐 容器 padding 计算表：
  容器节点 | pt | pr | pb | pl | 代码
  ...
──── CP-4.1 END ────
```

---

## Step 4：节点树递归解析

逐层遍历 Figma 节点树，对每个节点执行：

### 4.1 节点类型判定

| Figma 类型 | 转换为 |
|------------|--------|
| FRAME | `<div>` with flex layout |
| GROUP | `<div>` wrapper |
| TEXT | `<span>` 或 `<p>`（根据上下文） |
| RECTANGLE | `<div>` styled box |
| ELLIPSE | `<div className="rounded-full">` 或 `<Avatar>` |
| LINE | `<Divider>` 或 `<hr>` |
| VECTOR | 下载为 SVG → `<img>` 或内联 SVG |
| INSTANCE | 匹配组件库组件 → 见 Step 5 |
| COMPONENT | 提取为可复用组件 |
| COMPONENT_SET | 带变体 → 映射为 props |

### 4.1.1 COMPONENT_SET 变体映射

当遇到 `COMPONENT_SET` 类型节点时，Figma 的变体属性（Variant Properties）映射为组件 Props：

**解析流程：**

1. 读取 `componentPropertyDefinitions` 获取变体维度
2. 每个变体维度映射为一个 prop
3. 变体值映射为 TypeScript 联合类型（或 JSDoc 注释）

**映射规则：**

| Figma 变体属性 | 组件 Props |
|---------------|------------|
| `Size=S/M/L/XL` | `size?: 'small' \| 'medium' \| 'large' \| 'xlarge'` |
| `State=Default/Hover/Active/Disabled` | `state?: 'default' \| 'hover' \| 'active' \| 'disabled'` |
| `Type=Primary/Secondary/Text` | `variant?: 'primary' \| 'secondary' \| 'text'` |
| `Icon=True/False` | `showIcon?: boolean` |

**生成示例：**

```tsx
interface ProductCardProps {
  /** 来自 Figma 变体: Size */
  size?: 'small' | 'medium' | 'large';
  /** 来自 Figma 变体: State */
  state?: 'default' | 'hover' | 'active';
  /** 业务数据 */
  title: string;
  description: string;
}

const sizeClassMap: Record<string, string> = {
  small: 'w-[240px] p-3 text-sm',
  medium: 'w-[320px] p-4 text-base',
  large: 'w-[400px] p-6 text-lg',
};

const ProductCard: React.FC<ProductCardProps> = ({
  size = 'medium',
  state = 'default',
  title,
  description,
}) => (
  <div className={`rounded-xl ${sizeClassMap[size]}`} data-figmanode="1:100">
    <h3>{title}</h3>
    <p>{description}</p>
  </div>
);
```

**处理优先级：**
1. 如果变体属性与组件库原生 props 直接对应（如 `Size` → `size` prop），优先使用组件库原生 props
2. 如果是自定义变体，生成 classMap 查找表 + 条件类名

### 4.2 布局解析

```
layoutMode:
  "HORIZONTAL" → flex flex-row
  "VERTICAL"   → flex flex-col
  无 Auto Layout → relative + absolute 定位

primaryAxisAlignItems:
  "MIN" → justify-start    "CENTER" → justify-center
  "MAX" → justify-end      "SPACE_BETWEEN" → justify-between

counterAxisAlignItems:
  "MIN" → items-start   "CENTER" → items-center   "MAX" → items-end

itemSpacing → gap-{n}   (值 ÷ 4，映射 Tailwind 间距)
padding → px-{n} py-{n} 或 p-{n}
```

> **注意**：以上 Tailwind 类名适用于使用 Tailwind CSS 的项目。如项目使用其他样式方案，则输出对应的 CSS 属性（`display: flex; flex-direction: row;` 等）。

### 4.3 尺寸解析

```
layoutSizingHorizontal:
  "FILL" → w-full 或 flex-1
  "HUG"  → w-auto
  "FIXED" → w-[{n}px]

layoutSizingVertical:
  "FILL" → h-full
  "HUG"  → h-auto
  "FIXED" → h-[{n}px]

minWidth / maxWidth → min-w-[{n}px] / max-w-[{n}px]
```

### 4.4 样式解析（精确还原）

**所有样式值必须从 Figma 节点数据精确提取，严格遵守 `code-standards.md` 第三节精确还原规则。**

```
fills[0].color {r,g,b,a} → 精确转 HEX → bg-[#XXXXXX]
  ⚠️ ��禁止近似匹配 Tailwind 内置色板，必须使用精确 HEX 值
  仅当 HEX 值与 Tailwind 预设完全一致时才可使用预设名

strokes[0].color → 精确转 HEX → border-[#XXXXXX]
strokeWeight → border（1px）/ border-2 / border-[Npx]

cornerRadius → 容差 ≤ 1px 取标准值，> 1px 用 rounded-[Npx]
  ⚠️ ��圆角容差从 2px 收紧至 1px

opacity → opacity-{N} 或 opacity-[N]（精确匹配）

effects (shadow) → 精确提取 offset/blur/spread/color
  ⚠️ ��禁止近似匹配 shadow-sm/md/lg，必须用 shadow-[精确值]
  格式：shadow-[{offsetX}px_{offsetY}px_{blur}px_{spread}px_rgba(R,G,B,a)]
```

### 4.4.1 渐变样式解析

当 `fills[].type` 不是 `SOLID` 时，按以下规则转换：

```
fills[].type:
  "GRADIENT_LINEAR" → 线性渐变
    gradientHandlePositions → 计算角度
    gradientStops[].color → 色值序列
    → Tailwind: bg-gradient-to-{方向} from-[#xxx] via-[#xxx] to-[#xxx]
    → CSS: background: linear-gradient({angle}deg, #xxx 0%, #xxx 50%, #xxx 100%)

  "GRADIENT_RADIAL" → 径向渐变
    → Tailwind: bg-[radial-gradient(circle,#xxx_0%,#xxx_100%)]
    → CSS: background: radial-gradient(circle, #xxx 0%, #xxx 100%)

  "GRADIENT_ANGULAR" → 角度渐变（锥形渐变）
    → Tailwind: bg-[conic-gradient(from_{angle}deg,#xxx_0%,#xxx_100%)]
    → CSS: background: conic-gradient(from {angle}deg, #xxx 0%, #xxx 100%)

  "IMAGE" → 背景图片
    → 将节点加入图片下载队列
    → Tailwind: bg-[url('/path/to/image.png')] bg-cover bg-center
    → CSS: background: url('/path/to/image.png') center/cover
```

**Tailwind 渐变方向映射（仅 Tailwind 项目使用）：**

| gradientHandlePositions 角度范围 | Tailwind 前缀 |
|-------------------------------|-------------|
| 0° (→) | `bg-gradient-to-r` |
| 90° (↓) | `bg-gradient-to-b` |
| 180° (←) | `bg-gradient-to-l` |
| 270° (↑) | `bg-gradient-to-t` |
| 其他角度 | 使用任意值 `bg-[linear-gradient(...)]` |

**⚠️ 复合视觉效果判定（优先级高于渐变解析）：**

在解析 fills 数组时，**必须先**执行以下判定：

1. 如果 fills 数组包含 IMAGE + GRADIENT 混合（≥ 2 种类型），或 IMAGE 包含 `cropTransform` → **整体导出为图片**，不执行 CSS 渐变解析
2. 如果 fills 数组长度 ≥ 3 且包含 IMAGE → **整体导出为图片**
3. 只有单层简单渐变（无 IMAGE 混合、标准角度、色标 ≤ 3 个）才用 CSS 还原

详见 `design-quality-precheck.md` 和 `code-standards.md` 规则 E。

### 4.4.2 模糊与特效解析

```
effects[].type:
  "LAYER_BLUR"
    radius → Tailwind: blur-[{radius}px]  /  CSS: filter: blur({radius}px)

  "BACKGROUND_BLUR"
    radius → Tailwind: backdrop-blur-[{radius}px]  /  CSS: backdrop-filter: blur({radius}px)
    ⚠️ 通常配合半透明背景使用（毛玻璃效果）

  "DROP_SHADOW"
    → Tailwind: shadow-sm/md/lg/xl/2xl 或 shadow-[自定义]
    → CSS: box-shadow: {offsetX}px {offsetY}px {blur}px rgba(r,g,b,a)

  "INNER_SHADOW"
    → Tailwind: shadow-inner 或 shadow-[inset_自定义]
    → CSS: box-shadow: inset {offsetX}px {offsetY}px {blur}px rgba(r,g,b,a)
```

**毛玻璃效果组合示例：**

```tsx
{/* Figma: Background Blur = 20, Fill = White 30% opacity */}
<div className="bg-white/30 backdrop-blur-xl border border-white/20 rounded-2xl">
  {/* 内容 */}
</div>
```

### 4.5 文本解析

```
characters → 文本内容
fontSize → 精确匹配标准值时用预设（如 14→text-sm），否则用 text-[{n}px]
  ⚠️ ��fontSize=15 → text-[15px]（非 text-sm），fontSize=13 → text-[13px]（非 text-xs）
fontWeight → 按数值精确映射：400→font-normal, 500→font-medium, 600→font-semibold, 700→font-bold
textAlignHorizontal → text-left/center/right/justify
lineHeightPx → leading-[{n}px]（必须用任意值精确匹配，禁止近似 leading-normal/tight）
letterSpacing → tracking-[{n}px]（非 0 时必须设置）
text color: fills[0].color → 精确转 HEX → text-[#XXXXXX]
  ⚠️ ��禁止近似匹配 text-gray-xxx，必须使用精确值
textDecoration → underline / line-through（从 Figma 数据读取，不自行添加）
```

### 4.6 Figma Variables 解析（如有）

当节点样式引用了 Figma Variables（`boundVariables` 字段非空）时，将变量引用映射为 CSS 变量，而非硬编码具体值。

**检测规则：**

```
如果节点包含以下字段，表示引用了 Figma Variable：
  fills[0].boundVariables.color → 颜色变量
  strokes[0].boundVariables.color → 边框颜色变量
  boundVariables.itemSpacing → 间距变量
  boundVariables.paddingLeft/Right/Top/Bottom → 内边距变量
  boundVariables.cornerRadius → 圆角变量
```

**映射规则：**

| Figma Variable 类型 | 变量名处理 | 输出（Tailwind） | 输出（CSS） |
|---------------------|-----------|-----------------|------------|
| COLOR | `brand/primary` → `--color-brand-primary` | `bg-[var(--color-brand-primary)]` | `background: var(--color-brand-primary)` |
| COLOR | `text/secondary` → `--color-text-secondary` | `text-[var(--color-text-secondary)]` | `color: var(--color-text-secondary)` |
| FLOAT (spacing) | `spacing/lg` → `--spacing-lg` | `gap-[var(--spacing-lg)]` | `gap: var(--spacing-lg)` |
| FLOAT (radius) | `radius/md` → `--radius-md` | `rounded-[var(--radius-md)]` | `border-radius: var(--radius-md)` |

**变量名转换规则：**
1. Figma 变量路径中的 `/` 替换为 `-`
2. 统一转为 kebab-case
3. 按类型添加前缀：颜色 `--color-`、间距 `--spacing-`、圆角 `--radius-`、字体 `--font-`

**全局变量声明生成：**

当页面中收集到 Variables 引用时，在输出代码的同时，生成对应的 CSS 变量声明文件或追加到已有的 Token 文件中：

```css
/* src/styles/figma-tokens.css — 从 Figma Variables 自动生成 */
:root {
  --color-brand-primary: #1677ff;
  --color-brand-secondary: #52c41a;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #666666;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

**优先级：**
1. Figma Variable 引用 → 使用 CSS 变量（最高优先级）
2. 无 Variable 引用但匹配项目已有 Token → 使用项目 Token
3. 都不匹配 → 使用具体值（如 `bg-[#1677ff]`）

---

## Step 5：组件智能识别与映射

对 Figma `INSTANCE` 节点，必须优先按 `component-map.json` 执行**显式映射**，而不是直接根据 `componentName` 模糊猜测。

### 映射策略

执行优先级固定为：

1. `component-map.json` 中的 `componentKey` 精确匹配
2. `component-map.json` 中的 `namePatterns` 顺序匹配
3. 项目已有组件复用（详见 `reuse-check.md`）
4. 项目实际使用的组件库映射
5. 原生 HTML + CSS 兜底

根据 `project-profile.json` 或技术栈检测结果，选择对应的组件映射表：

#### 通用 Figma 关键词 → 组件映射

| Figma 关键词（不区分大小写） | 语义 |
|------------------------------|------|
| button, btn, cta | 按钮 |
| input, textfield, search | 输入框 |
| textarea, multiline | 多行输入 |
| select, dropdown, picker | 选择器 |
| checkbox, check | 复选框 |
| radio | 单选框 |
| switch, toggle | 开关 |
| tag, chip, label | 标签 |
| card, panel | 卡片 |
| avatar, profilepic | 头像 |
| table, datagrid | 表格 |
| image, img, photo | 图片 |
| badge, dot | 徽标 |
| tooltip, tip | 文字提示 |
| progress, progressbar | 进度条 |
| menu, nav, sidebar | 菜单/导航 |
| tabs, tabbar | 标签页 |
| breadcrumb | 面包屑 |
| pagination, pager | 分页 |
| alert, banner, notice | 提示 |
| dialog, modal, popup | 对话框 |
| drawer, slidepanel | 抽屉 |
| form, formgroup | 表单 |
| upload, fileupload | 上传 |
| datepicker, calendar | 日期选择 |
| rate, star, rating | 评分 |
| skeleton, placeholder | 骨架屏 |
| statistic, metric, kpi | 统计数值 |

#### 组件库映射表

根据检测到的组件库，将上述语义映射为具体组件：

**TDesign React**：`Button`, `Input`, `Select`, `Checkbox`, `Radio`, `Switch`, `Tag`, `Card`, `Avatar`, `Table`, `Image`, `Badge`, `Tooltip`, `Progress`, `Menu`, `Tabs`, `Breadcrumb`, `Pagination`, `Alert`, `Dialog`, `Drawer`, `Form` + `FormItem`, `Upload`, `DatePicker`, `Rate`, `Skeleton`, `Statistic`

**Ant Design**：`Button`, `Input`, `Select`, `Checkbox`, `Radio`, `Switch`, `Tag`, `Card`, `Avatar`, `Table`, `Image`, `Badge`, `Tooltip`, `Progress`, `Menu`, `Tabs`, `Breadcrumb`, `Pagination`, `Alert`, `Modal`, `Drawer`, `Form` + `Form.Item`, `Upload`, `DatePicker`, `Rate`, `Skeleton`, `Statistic`

**Element Plus (Vue)**：`ElButton`, `ElInput`, `ElSelect`, `ElCheckbox`, `ElRadio`, `ElSwitch`, `ElTag`, `ElCard`, `ElAvatar`, `ElTable`, `ElImage`, `ElBadge`, `ElTooltip`, `ElProgress`, `ElMenu`, `ElTabs`, `ElBreadcrumb`, `ElPagination`, `ElAlert`, `ElDialog`, `ElDrawer`, `ElForm` + `ElFormItem`, `ElUpload`, `ElDatePicker`, `ElRate`, `ElSkeleton`, `ElStatistic`

**无组件库**：使用原生 HTML 标签 + CSS 类还原视觉效果。

### 5.2 结构模式匹配（名称匹配失败时的兜底策略）

当 `componentName` 无法命中组件库映射时，通过**子节点结构特征**推断组件类型：

| 子节点结构特征 | 推断组件 | 说明 |
|--------------|---------|------|
| ELLIPSE(≤48px) + TEXT(名称) + TEXT(描述) | Avatar + 用户信息卡 | 小圆形+文本组合 |
| IMAGE + TEXT(标题) + TEXT(描述) + INSTANCE(button) | Card 卡片 | 图文+操作的经典卡片结构 |
| 横向排列的 TEXT ≥ 3 个 + 下方对应内容区域 | Tabs 标签页 | 多文本标签+面板 |
| TEXT(标题) + LINE + TEXT(内容) 重复 ≥ 2 组 | Collapse 折叠面板 | 标题+分割线+内容的重复模式 |
| RECTANGLE(小圆) + TEXT 横向排列 ≥ 2 组 | Steps 步骤条 | 圆点+文本的序列 |
| 等宽 FRAME 网格排列 (rows × cols) | Grid 网格 / 卡片列表 | 均匀分布的子元素 |
| FRAME 内含 RECTANGLE(0宽度/1px) 分隔的多段内容 | Divider 分割的内容区 | 分割线分隔的区块 |
| 横向排列的 ELLIPSE(≤12px) ≥ 3 个 | Pagination 分页指示器 | 小圆点序列 |
| RECTANGLE(窄高比 ≥ 10:1) + RECTANGLE(更窄,颜色不同) | Progress 进度条 | 背景条+进度条组合 |
| TEXT(数值,fontSize≥24) + TEXT(描述,fontSize≤14) | Statistic 统计数值 | 大数字+小描述 |
| ELLIPSE(≤16px) + TEXT 横向排列，ELLIPSE 有 fills | Radio/Checkbox 选项 | 圆/方标记+文本 |
| RECTANGLE(宽≤50,高≤28,cornerRadius≥14) + ELLIPSE 子节点 | Switch 开关 | 胶囊形+圆形滑块 |

**执行优先级**：
1. 先执行关键词匹配（Step 5.1）
2. 关键词匹配未命中 → 执行结构模式匹配（Step 5.2）
3. 结构模式也未命中 → 使用 `<div>` + CSS 还原视觉效果

**注意**：结构模式匹配是确定性规则，基于可量化的子节点特征判断，不依赖 AI 的"感觉"。

---

### 图标映射规则

1. 名称包含 `icon` / `Icon` → 优先从项目图标库匹配
2. 各图标库常用图标：
   - **tdesign-icons-react**：`SearchIcon`, `CloseIcon`, `AddIcon`, `DeleteIcon`, `EditIcon`, `MoreIcon`, `ChevronRightIcon` 等
   - **@ant-design/icons**：`SearchOutlined`, `CloseOutlined`, `PlusOutlined`, `DeleteOutlined`, `EditOutlined` 等
   - **lucide-react**：`Search`, `X`, `Plus`, `Trash2`, `Edit`, `MoreHorizontal`, `ChevronRight` 等
3. 无法匹配 → 调用 `download_figma_images` 下载为 SVG

---

## Step 6：重复元素检测

同一父节点下 ≥ 3 个结构相同的兄弟节点 → 自动转为循环渲染。

判定"结构相同"：
- 相同 Figma 节点类型
- 相同的子节点数量和层级
- 相同的样式属性集（忽略具体值差异）

生成代码（React 示例）：
```tsx
const items = [
  { title: 'xxx', desc: 'yyy', icon: '...' },
  // ... 从设计稿数据提取
];

{items.map((item, index) => (
  <div key={index} className="...">
    {/* 单项内容 */}
  </div>
))}
```

Vue 示例：
```vue
<div v-for="(item, index) in items" :key="index" class="...">
  <!-- 单项内容 -->
</div>
```

---

## Step 7：节点层级语义推导（关键步骤）

**此步骤是防止"代码与设计稿不一致"的核心环节**，必须在代码生成前完成。Figma 中所有元素都有绝对坐标，但 HTML/CSS 有文档流、嵌套、flex 等语义概念，不能机械搬运坐标。

### 7.1 父子嵌套关系推导（坐标包含分析）

**对每个节点，必须通过坐标比较判断它与其他节点的包含关系：**

```
推导规则：

规则 1：坐标包含 → 父子关系
  如果节点 A 的边界完全包含节点 B（B.x ≥ A.x && B.y ≥ A.y && B.x+B.w ≤ A.x+A.w && B.y+B.h ≤ A.y+A.h），
  且 A 和 B 在 Figma 层级中是兄弟关系 → 代码中 B 必须嵌套在 A 内部。

  示例：进度条 (x:325, y:1028, w:1591, h:4) 包含圆点 (x:445, y:1024, w:12, h:12)
  → 圆点 y:1024 在进度条 y:1028 附近且垂直居中 → 圆点必须嵌套在进度条内部

规则 2：坐标居中 → 嵌套 + 居中对齐
  如果节点 B 的中心点在节点 A 的某条轴线上 → B 是 A 的子元素且居中对齐。
  
  示例：圆点中心 y=1030，进度条中心 y=1030 → 圆点在进度条内垂直居中
  → 代码：top: 50%; transform: translateY(-50%)

规则 3：容器与内容尺寸分离
  如果一个节点（容器）的尺寸大于其子节点（内容），必须区分「触摸区域」和「视觉元素」。
  容器尺寸 → 外层 div/button 的 width/height
  内容尺寸 → 内部 img/icon/text 的 width/height
  
  示例：全屏按钮容器 36×36，内部图标 16×16
  → <button style={{width:36,height:36}}><img className="w-4 h-4" /></button>
  ❌ 错误：<button><img className="w-9 h-9" /></button>（把容器尺寸直接赋给图标）

规则 4：高亮/底色区域包裹内容
  如果一个 RECTANGLE/FRAME（低 opacity 背景色）的坐标包含相邻的文本/图标节点，
  该 RECTANGLE 应作为可点击容器，文本/图标嵌套在其内部。
  
  示例：高亮区域 (x:16,y:6,w:72,h:32) 包含按钮内容 (x:24,y:12)
  → 高亮区域作为 <div role="button">，按钮内容嵌套在内部
  ❌ 错误：高亮区域和按钮内容作为平级兄弟元素

规则 5：跨模块边界元素 → 按视觉语义归属判断
  当一个元素的坐标跨越两个相邻模块的边界时（如元素底部超出模块 A 进入模块 B），
  禁止仅凭绝对坐标距离判断归属，必须综合以下三个维度判定：

  判定优先级：
  1. 视觉语义关系（最高优先级）：元素与哪个模块的内容存在对齐、并排、嵌套等布局关系
  2. Figma 节点层级：元素在节点树中属于哪个父节点组
  3. 坐标重叠面积：元素与哪个模块的重叠面积更大（仅作辅助参考）

  示例：图标 (x:372, y:500, w:114, h:110)
    模块 A（Hero 背景）：y:60~460
    模块 B（课程简介白色区域）：y:460~652，内含标题 (x:518, y:508) 和正文 (x:518, y:556)

    坐标分析：图标 y:500 落在模块 B 内部，底部超出 Hero 区域 40px
    视觉语义：图标与"课程简介"标题水平并排对齐 → 属于模块 B
    → 图标归属模块 B（课程简介），在 B 组件中渲染

  ❌ 错误：图标紧邻 Hero 背景底部 → 归属 Hero 模块（仅看坐标距离，忽略视觉语义）
  ✅ 正确：图标与"课程简介"标题水平对齐 → 归属课程简介模块
```

### 7.2 文档流 vs 绝对定位选择

**不能因为 Figma 有绝对坐标就用 CSS absolute 定位，必须判断语义化布局意图：**

```
判定规则：

规则 1：顺序堆叠 → 文档流（禁止 absolute）
  如果同级兄弟节点在垂直方向依次排列（A.y + A.h ≈ B.y），且不重叠 → 使用正常文档流。
  
  示例：背景图 (y:0, h:60) + 导航栏 (y:60, h:44)
  → <header><img /><nav /></header>（正常流堆叠）
  ❌ 错误：<div class="relative"><img /><nav class="absolute top-[60px]" /></div>

规则 2：覆盖/悬浮 → absolute 定位
  如果节点与其他节点在同一区域重叠（坐标范围有交集） → 使用 absolute 定位。
  
  示例：控制栏覆盖在视频画面底部 → absolute bottom-0

规则 3：固定位置元素 → absolute 定位
  如果节点需要相对父容器精确定位，且父容器内有其他重叠元素 → absolute。
  
  示例：进度条在控制栏内 top:28px → absolute top-[28px]

规则 4：flex 子元素的等间距排列 → flex + gap
  如果同级兄弟节点等间距排列 → 父容器 flex + gap-N
  ❌ 错误：每个子元素 absolute + left 精确定位
```

### 7.3 百分比定位参照物确认

**当需要将绝对坐标转为百分比时，必须确认正确的参照物：**

```
规则：
  百分比 = (节点坐标 - 父容器起始坐标) / 父容器尺寸 × 100%

  示例：
    圆点 x=445，进度条 x=325，进度条 width=1591
    → left = (445 - 325) / 1591 × 100% ≈ 7.5%
  
  ❌ 错误：直接用页面根坐标算百分比 → left = 445 / 1920 × 100% ≈ 23.2%（参照物错误）
```

### 7.4 绝对定位处理（仅在 7.2 判定为需要 absolute 时使用）

对于未使用 Auto Layout 且有 Constraints 的节点：

```tsx
{/* 父容器 */}
<div className="relative w-[{width}px] h-[{height}px]">
  {/* 子节点根据 constraints 计算 top/left/right/bottom */}
  <div className="absolute top-[{y}px] left-[{x}px]">
    ...
  </div>
</div>
```

### 7.5 自适应布局转换（强制规则）

**在确定元素的布局方式后，必须将设计稿的固定宽度转换为自适应宽度。此步骤对每个节点生成的 CSS 都适用。**

```
转换规则（逐节点应用）：

规则 1：页面根容器
  设计稿 width: 1920px
  ❌ 代码：width: 1920px / w-[1920px]
  ✅ 代码：width: 100% / w-full + min-height: 100vh

规则 2：全宽区域（宽度 ≈ 设计稿根宽度 ±5%）
  设计稿 width: 1920px（与根节点等宽）
  ❌ 代码：width: 1920px
  ✅ 代码：width: 100% + 内容居中

规则 3：居中内容区域
  判定条件：x > 0 且 (根节点宽度 - 元素宽度 - x) ≈ x（左右对称）
  设计稿 width: 1180px, x: 370px (370 + 1180 + 370 = 1920)
  ❌ 代码：width: 1180px + margin-left: 370px
  ✅ 代码：max-width: 1180px + margin: 0 auto + width: 100% + padding: 0 16px

规则 4：内容区子元素（父容器已设为 max-width 居中）
  设计稿 width: 1068px（内容区宽 1180px 的子元素）
  ❌ 代码：width: 1068px
  ✅ 代码：width: 100%（继承父容器宽度）或 flex: 1
  ❌ 例外：固定尺寸小组件（按钮、头像、图标等 width < 200px）可保留固定宽度

规则 5：超宽背景（宽度 > 设计稿根宽度）
  设计稿 width: 2560px, x: -320px
  ❌ 代码：width: 2560px + left: -320px（固定偏移，小屏下溢出）
  ✅ 代码：父容器 width: 100% + overflow: hidden
           图片 min-width: 2560px + position: absolute + left: 50% + transform: translateX(-50%)
           或 width: max(100%, 2560px) + 居中

规则 6：间距和内边距
  设计稿的内边距用实际 px 值
  但水平方向的大间距（如 x: 370px 形成的左侧空白）必须通过 margin: auto 居中实现
  而非硬编码 padding-left: 370px
```

**⚠️ 自适应转换的边界：**
- 高度一般保留固定值（垂直方向不需要自适应）
- 圆角、阴影、字体大小保留固定值
- 只有**水平方向**的宽度、间距、定位需要做自适应转换
- 当屏幕宽度 < 设计稿内容区宽度时，内容区 width:100% + padding:0 16px 保证不溢出

### 7.6 坐标-布局一致性验证 `[CP-7.6]`

> **Checkpoint CP-7.6** | 必需输入：CP-4.0 `CoordinateTable` + 代码中各区域的布局方案 | 产物：`LayoutVerification` | 门禁：所有区域偏差 ≤ 4px 或已标注修正方案

**在为每个区域确定布局方案后，必须用坐标数据交叉验证：**

```
验证流程：

1. 计算代码中元素的预期位置（基于 flex/grid/absolute 布局）
2. 对比设计稿坐标数据中元素的实际位置
3. 如果偏差 > 4px → 标记为需要修正

示例：
  设计稿坐标：按钮 x:370, y:317；最近学习 x:522, y:325
  代码布局方案：flex-col 垂直堆叠
  验证：flex-col 会让两个元素上下排列，但坐标显示它们 y 值接近（317 vs 325）
       → 不应该是垂直堆叠，应该是水平排列（flex-row）
       → 修正布局方案

⚠️ 此验证是防止"布局方案与坐标矛盾"的关键检查点
```

**📋 CP-7.6 产物输出（必须）：**

```
──── CP-7.6 LayoutVerification ────
📏 坐标-布局一致性验证：
  区域 | 布局方案 | 验证结果 | 最大偏差 | 状态
  {区域名} | {flex-row/col/...} | {通过/修正} | {N}px | ✅/⚠️ 已修正
  ...
──── CP-7.6 END ────
```

---

## Step 8：data-figmanode 追踪标记与代码区域标记

### 8.1 data-figmanode 属性

**每个从 Figma 节点生成的 JSX/模板元素，必须添加 `data-figmanode` 属性**，用于后续变更同步时精确定位：

```tsx
{/* 属性值为 Figma 节点的 Node ID */}
<div className="flex flex-col gap-4 p-6" data-figmanode="1:234">
  <h2 className="text-xl font-semibold" data-figmanode="1:235">标题文本</h2>
  <p className="text-sm text-gray-500" data-figmanode="1:236">描述文本</p>
  <Button data-figmanode="1:237">操作按钮</Button>
</div>
```

规则：
1. **所有**从 Figma 节点直接映射的元素都必须携带此属性
2. 属性值格式：`"<数字>:<数字>"`，对应 Figma 节点树中的 `id` 字段
3. 通过循环渲染的元素，只在模板层级标记，不需要每个列表项都带不同 ID
4. 纯逻辑包装层（如 `<Fragment>`、条件渲染的 wrapper）不需要标记
5. 此属性在**开发模式**保留，**生产构建**时可通过插件自动移除

**重要**：此属性是 `update-workflow.md` 中 AST 智能合并的定位基础，缺少它会导致变更流程无法精确匹配节点。

### 8.2 代码区域边界标记（@d2c 标记）

**在生成代码时，使用注释标记 AI 生成区域的边界**，用于变更流程中精确区分 AI 生成代码和用户手动添加的代码：

```tsx
{/* @d2c-start: TopBar (node: 1:234) */}
<header className="flex items-center h-16 px-6 bg-white border-b" data-figmanode="1:234">
  <Logo />
  <Navigation />
  <UserActions />
</header>
{/* @d2c-end: TopBar */}

{/* @user-zone: 自定义搜索逻辑 */}
{/* 用户在此区域添加的代码，变更时不覆盖 */}
{/* @user-zone-end */}
```

**标记规则：**

| 标记 | 用途 | 变更时行为 |
|------|------|----------|
| `@d2c-start: {Name} (node: {id})` | AI 生成区域开始 | 可安全替换为新设计 |
| `@d2c-end: {Name}` | AI 生成区域结束 | 与 start 配对 |
| `@user-zone: {描述}` | 用户手动代码区域开始 | **禁止覆盖** |
| `@user-zone-end` | 用户手动代码区域结束 | 与 user-zone 配对 |

**使用场景：**
- 每个子组件的 JSX 根元素前后添加 `@d2c-start/@d2c-end`
- 用户如需在组件中添加自定义逻辑，可在 `@d2c-end` 后插入 `@user-zone` 块
- 变更流程（`update-workflow.md`）识别这些标记，精确替换 AI 区域、保留用户区域

**注意**：此标记为注释形式，不影响代码运行和构建。

---

## Step 9：MockData 解析与数据分离

按照 `mock-data.md` 规范，将设计稿中的业务数据从 UI 组件中完全分离：

1. **识别业务数据** — 遍历节点树，将文本内容、重复列表、数值、图片路径等识别为 mockData
2. **定义类型** — 在 `mock/types.ts` 中定义所有业务实体接口
3. **生成 mock 数据文件** — 在 `mock/` 目录下按业务域生成数据文件，每个常量标注 `@source` 和 `@todo`
4. **生成 Service 层** — 在 `services/` 下生成异步函数，初始返回 mock 数据，预留 API 调用结构
5. **生成 Hook 层（可选）** — 当页面数据较多时，封装数据获取 hooks
6. **组件通过 Service/Hook 获取数据** — 组件内不直接 import mock 常量

---

## Step 9.5：逐节点数据回查 `[CP-9.5]`

> **Checkpoint CP-9.5** | 必需输入：CP-7.6 `LayoutVerification` + 已生成的组件代码 + CP-2 Figma 原始数据 | 产物：`DataTracebackTable` | 门禁：表格行数 ≥ 关键节点数，所有行标记为 ✅ 或已修正

> **此步骤解决三大高频问题：① 批量推断导致属性值不准确 ② 组件 variant 名称与视觉效果矛盾 ③ 节点坐标在代码中未被遵守。**

### 9.5.1 为什么需要此步骤

以下是实际 D2C 中反复出现的错误模式：

```
错误模式 1：批量推断
  看到第一个章节头 textStyle=Title/Large(18px) → 假设所有章节头都是 18px
  实际上第二、三章节是 Title/Medium(16px)
  → 必须逐个节点回查 textStyle

错误模式 2：信元数据不信视觉数据
  组件 variant 名称为 "outline 描边按钮" → 使用 Button variant="outline"
  但实际 fills 是 #F2F3FF（浅蓝背景），视觉上不是描边效果
  → 必须以 fills 数据为准，而非 variant 名称

错误模式 3：坐标写了但没用
  CP-4.0 坐标表中分割线 y=642，但代码中放在了标题和描述之间
  → 必须逐个检查坐标是否在代码中被正确使用
```

### 9.5.2 回查流程（强制，逐节点执行）

**对已生成代码中的每个关键 UI 元素，必须从 Figma 原始数据中逐一读取以下属性并与代码比对：**

```
对每个元素执行以下检查：

1. 文本节点：
   □ Figma textStyle (fontFamily/fontSize/fontWeight/lineHeight) vs 代码中的 text-[]/font-/leading-[]
   □ Figma fills color vs 代码中的 text-[#xxx]
   □ Figma characters vs 代码中渲染的文本内容

2. 容器/区域节点：
   □ Figma fills vs 代码中的 bg-[#xxx]（注意：fills 可能有多层，必须看完整数组）
   □ Figma 坐标 (x, y) vs 代码中的位置实现（flex 顺序/margin/padding）
   □ Figma borderRadius vs 代码中的 rounded-[]
   □ Figma effects (shadow) vs 代码中的 shadow-[]

3. 组件实例 (INSTANCE)：
   □ Figma fills/strokes 的**实际视觉值** vs 代码中组件的 variant/theme/样式
   □ ⚠️ 关键：如果 Figma variant 名称（如"outline"）与 fills 视觉效果矛盾
     → 以 fills 数据为准（规则 M）
   □ Figma componentProperties 中的 text 值 vs 代码中渲染的文本

4. 图标/SVG 节点：
   □ Figma opacity vs 代码中的 opacity
   □ 图标类型匹配（check-circle vs play-circle 等）

⚠️ 关键纪律：
  - 禁止"看了第一个节点就推断其余相同"
  - 每个节点必须独立从 Figma 数据中读取属性
  - 即使 10 个课时行结构相同，也必须检查它们的 textStyle/fills 是否真的都相同
```

### 9.5.3 回查表输出格式

```
──── CP-9.5 DataTracebackTable ────
📋 逐节点数据回查表：

| 元素 | 节点ID | 属性 | Figma 原始值 | 代码实际值 | 一致？ |
|------|--------|------|-------------|----------|-------|
| 章节一标题 | 405:2495 | textStyle | Title/Large (18px/600) | text-[18px] font-semibold | ✅ |
| 章节二标题 | 405:2523 | textStyle | Title/Medium (16px/600) | text-[16px] font-semibold | ✅ |
| 章节三标题 | 418:2738 | textStyle | Title/Medium (16px/600) | text-[16px] font-semibold | ✅ |
| 去複習按钮 | 418:2694 | fills | #F2F3FF (Brand1-Light) | bg-[#F2F3FF] | ✅ |
| 去複習按钮 | 418:2694 | variant | "outline 描边" | ⚠️ 视觉为浅蓝底 → 不用 outline | ✅ 已修正 |
| 分割线 | 495:201 | 坐标 y | 642 (简介区底部) | 放在简介区底部 | ✅ |
| ... | ... | ... | ... | ... | ... |

不一致项修正记录：
  序号 | 元素 | 问题 | 修正方案
  （如有修正则列出，无则输出"无需修正"）

──── CP-9.5 END ────
```

### 9.5.4 门禁条件

```
CP-9.5 门禁：
1. 回查表行数 ≥ 页面中关键 UI 元素数量（文本节点+容器+组件实例+图标）
2. 所有行的"一致？"列为 ✅ 或 "✅ 已修正"
3. 不一致项已在代码中修正（修正记录非空时）

未通过门禁 → 禁止输出 CP-10，必须先修正不一致项
```

---

## Step 10：代码输出 `[CP-10]`

> **Checkpoint CP-10** | 必需输入：CP-4.0 `CoordinateTable` + CP-7.6 `LayoutVerification` + CP-9.5 `DataTracebackTable` | 产物：`GeneratedFiles` | 门禁：至少输出 1 个组件文件

按照 `code-standards.md` 规范输出，并遵守 的固定输出合同：

1. 生成组件文件代码（UI 组件，不含硬编码数据）
2. 生成 `mock/` 目录文件（类型 + 数据 + 统一导出）
3. 生成 `services/` 文件（API 对接预留层）
4. 如有需要，生成 `hooks/` 文件（数据获取逻辑）
5. 列出所有需要的图片资源及下载命令
6. 列出需要调用 `download_figma_images` 的节点清单
7. 输出组件使用方式和 props 接口
8. 说明后续替换真实 API 的方法
9. 生成一份 `generation-manifest`，至少包含：
   - 归一化请求
   - 命中的 `project-profile` / `component-map` / `token-aliases` 版本
   - 生成文件清单
   - 资源清单
   - 复用命中 / fallback 记录
   - Token 决策记录
   - 回归验证结果入口

### 10.1 输出顺序锁定

为保证同输入多次执行结果一致，以下顺序必须固定：

- 节点遍历：`y → x → nodeId`
- Import：框架 → 组件库 → 图标库 → Service/Hook → 类型 → 内部模块 → 资源
- 类名：布局 → 间距 → 尺寸 → 视觉 → 文本 → 交互
- 资源命名：`<page>-<nodeId>-<purpose>`

**📋 CP-10 产物输出（必须）：**

```
──── CP-10 GeneratedFiles ────
📄 生成文件清单：
  文件路径 | 行数 | 类型 | 说明
  {path}  | {N}  | 组件/Mock/Service/类型 | {说明}
  ...

📦 资源下载清单：
  节点ID | 文件名 | 下载模式 | 用途
  ...
──── CP-10 END ────
```

---

## Step 10.1：即时截图对比 `[CP-10.1]`

> **Checkpoint CP-10.1** | 必需输入：CP-10 `GeneratedFiles`（代码已写入文件系统） | 产物：`QuickVisualDiff` | 门禁：所有区域差异率 ≤ 10% 或已修正

> **此步骤解决"代码输出后直到 CP-11 才发现视觉偏差"的延迟问题。将截图对比从最终验证环节前置到代码输出后立即执行。**

### 10.1.1 为什么需要此步骤

CP-11 回归验证包含 9+ 个维度，是一个重量级检查。在实际执行中，LLM 往往在 CP-11 时才第一次看到渲染结果，此时要修复已经很晚了。

即时截图对比是一个**轻量级视觉冒烟测试**：代码写完 → 立即截图 → 与设计稿对比 → 发现明显偏差 → 当场修复。

### 10.1.2 执行流程

```
1. 启动 dev server（如果尚未启动）
   → npm run dev / pnpm dev（后台运行）

2. 使用 Playwright 截取全页面截图
   → viewport: 1920×1080
   → 等待 networkidle + 额外 2s（确保图片加载）
   → 保存为 /tmp/d2c-quick-diff-actual.png

3. 使用 MCP download_figma_images 导出设计稿整体为 PNG
   → 节点 ID = 根节点
   → pngScale: 1
   → 保存为项目临时目录

4. 逐区域目视对比（以下区域必检）：
   a. Hero/Banner 区域 — 背景图完整性、文字位置、按钮位置
   b. 内容区域 — 间距、字号、颜色
   c. 列表/卡片区域 — 卡片结构、行样式、按钮样式
   d. 底部区域 — 装饰图完整性

5. 记录每个区域的差异：
   - 差异率 ≤ 2%：✅ 通过
   - 差异率 2%~10%：⚠️ 可接受，记录差异
   - 差异率 > 10%：❌ 不通过，必须当场修复

6. 修复发现的问题后重新截图确认
```

### 10.1.3 常见可检出的问题（此步骤特别有效的场景）

| 问题类型 | 纯数据验证是否可发现 | 截图对比是否可发现 |
|---------|-------------------|-----------------|
| 按钮样式不对（outline vs 实色） | ❌ 数据层面 variant 匹配 | ✅ 视觉明显不同 |
| 元素位置偏移（分割线放错位置） | ⚠️ 需要精确比对坐标 | ✅ 一眼看出 |
| 字号不一致（18px vs 16px） | ⚠️ 需要逐节点回查 | ✅ 对比可见大小差异 |
| 背景图高度不对 | ❌ 图片文件存在即算通过 | ✅ 比例明显不对 |
| 间距丢失（模块间缺少 gap） | ⚠️ 需要坐标计算 | ✅ 模块贴在一起 |

### 10.1.4 产物输出格式

```
──── CP-10.1 QuickVisualDiff ────
📸 即时截图对比结果：

| 区域 | 差异描述 | 差异率 | 状态 | 修正 |
|------|---------|--------|------|------|
| Hero/Banner | 无明显差异 | ~1% | ✅ | — |
| 课程简介 | 分割线位置偏差 | ~15% | ❌ | 已修正：移到区域底部 |
| 课程列表 | 按钮样式不对 | ~12% | ❌ | 已修正：outline → 浅蓝底文字 |
| 底部装饰 | 无差异 | ~0% | ✅ | — |

修正记录：
  1. CourseIntro.tsx: 分割线从标题下方移到区域底部
  2. CourseList.tsx: Button variant="outline" → span bg-[#F2F3FF]

修正后重新截图确认：✅ 所有区域差异率 ≤ 5%
──── CP-10.1 END ────
```

### 10.1.5 门禁条件

```
CP-10.1 门禁：
1. 截图已生成（actual.png 存在）
2. 设计稿导出图已生成（expected.png 存在）
3. 所有区域差异率 ≤ 10%（或已修正后重新确认）
4. 修正记录中列出了所有修改的文件和内容

未通过门禁 → 禁止进入 CP-10.5，必须先修正差异
```

### 10.1.6 与 CP-11 回归验证的关系

```
CP-10.1（即时截图对比）和 CP-11（回归验证）的分工：

CP-10.1：轻量级冒烟测试
  - 目的：快速发现"一眼可见"的视觉偏差
  - 方法：截图 + 人眼对比
  - 时机：代码输出后立即执行
  - 修复：当场修复

CP-11：全面回归验证
  - 目的：逐维度精确验证还原度
  - 方法：数据对比 + 像素对比 + 代码质量检查
  - 时机：CP-10.1 通过后执行
  - 修复：最多 2 轮自动修复

两者不互相替代，CP-10.1 是"快速拦截"，CP-11 是"精确验证"。
```

---

## Step 10.5：背景图导出验证 `[CP-10.5]`

> **Checkpoint CP-10.5** | 必需输入：CP-10 `GeneratedFiles`（含资源下载清单） + CP-2.5 `PrecheckReport`（含背景图节点列表） | 产物：`BgImageVerification` | 门禁：所有背景图均验证通过或标注处理方案

在代码输出完成后、回归验证前，**必须对所有背景图执行导出验证**。此步骤解决 MCP 工具导出背景图时的常见陷阱。

### 10.5.1 验证范围

对以下类型的图片逐一验证：
- 所有 fills 含 IMAGE 类型的容器节点（Banner 背景、卡片背景、Hero 区域等）
- 所有通过 `download_figma_images` 下载的非图标/非封面类图片

### 10.5.2 验证检查项

| 检查项 | 验证方法 | 不通过时的处理 |
|--------|---------|-------------|
| **下载模式** | 确认使用的是节点渲染模式（模式 C：仅传 nodeId，不传 imageRef） | 如使用了 imageRef 模式，重新用模式 C 下载 |
| **cropTransform** | 检查下载参数中是否传递了 cropTransform | 如传递了 cropTransform，移除后重新下载 |
| **clipContent 检测** | 检查 Figma 节点是否有 `clipContent: true` | 如有，检查导出图片是否有边缘截断 |
| **图片宽高比** | 对比导出图片与设计稿节点的宽高比 | 宽高比误差 > 5% 则标记异常 |
| **视觉完整性** | 目视检查图片四边缘是否有非预期裁切（特别是波浪、花朵等装饰性边缘） | 有裁切则请求用户提供手动导出的原图 |
| **CSS 引用方式** | 背景图节点的代码是否使用 `background-image` + `background-size: cover` | 如使用 `<img>` 标签则修改为背景图方式 |

### 10.5.3 处理流程

```
对每张背景图：
1. 检查下载参数 → 确认使用模式 C
2. 检查导出文件尺寸 → 与设计稿节点尺寸对比
3. 如发现异常：
   a. cropTransform 裁剪 → 移除参数，重新下载
   b. clipContent 截断 → 尝试对父节点渲染导出，或请求用户手动导出
   c. imageRef 模式 → 改用模式 C（节点渲染）重新下载
4. 验证代码中的引用方式 → 确保 CSS background-image
5. 输出验证结果
```

### 10.5.4 验证结果输出

```
🖼️ 背景图导出验证：
  ✅ 节点 495:190 (Banner 背景): 模式 C 下载, 2560×400, 宽高比一致, CSS 背景图 ✅
  ✅ 节点 495:350 (卡片背景): 模式 C 下载, 800×200, 宽高比一致, CSS 背景图 ✅
  或
  ⚠️ 节点 495:190 (Banner 背景): 
    - 下载模式: imageRef (应改为模式 C) → 已重新下载
    - clipContent: true, 底部波浪被截断 → 已请求用户提供原图
```

**📋 CP-10.5 产物输出（必须）：**

```
──── CP-10.5 BgImageVerification ────
🖼️ 背景图导出验证：
  节点ID | 名称 | 下载模式 | 尺寸 | 宽高比 | CSS方式 | 状态
  ...    | ...  | 模式C   | WxH  | ✅/⚠️  | bg-image | ✅/⚠️ {处理方案}

如无背景图节点：
  🖼️ 背景图导出验证：无背景图节点，跳过
──── CP-10.5 END ────
```

---

## Step 11：回归验证 `[CP-11]`

> **Checkpoint CP-11** | 必需输入：CP-10 `GeneratedFiles` + CP-10.5 `BgImageVerification` | 产物：`RegressionReport` | 门禁：综合得分 ≥ 90%

代码输出完成后，**必须执行**回归验证流程，按照 `regression-check.md` 规范：

1. 重新获取设计稿基准数据
2. 逐维度比对生成的代码与设计稿（布局 / 间距 / 颜色 / 图片 / 组件 / 交互 / 代码质量 / 确定性）
3. **布局嵌套层级验证** — 特别检查：
   - 同行元素是否有对应的 `flex flex-row` 包裹容器（不被扁平化）
   - Auto Layout 嵌套层级是否保留（VERTICAL 内含 HORIZONTAL 不被合并）
4. **图片资源完整性验证** — 特别检查：
   - 多层 fill 中的 IMAGE 类型是否被遗漏
   - 背景图是否使用 CSS `background-image` 方式
   - MCP 导出的图片是否有裁剪/截断
5. 校验 `generation-manifest` 是否完整
6. 执行幂等性检查：相同输入重复生成时，结构与命名不得漂移
7. **执行视觉截图对比** — 包含：
   - 全页面截图对比
   - **分区域截图对比**（Banner、简介、列表等区域逐区对比，任一区域差异率 > 10% 即触发修复）
   - 背景图专项视觉验证
8. 生成定量验证报告（含各维度得分和加权综合得分，视觉截图对比纳入权重 0.08）
9. 自动修复不通过项（最多 2 轮循环修复）
10. 输出最终还原度报告

**此步骤不可跳过**。只有验证综合得分 ≥ 90%、Manifest 完整、确定性检查通过、且分区域视觉对比无严重偏差后，整个新建流程才算完成。

**📋 CP-11 产物输出（必须）：**

```
──── CP-11 RegressionReport ────
🔍 回归验证报告
  维度 | 通过项 | 总项 | 得分 | 权重 | 加权得分
  ...  | ...   | ... | ... | ... | ...
  综合 | —     | —   | —   | 1.00 | {总分}%

  结论：✅ 达标 / ⚠️ 需修复（列出不通过项）
──── CP-11 END ────
```

**📋 CP-M 产物输出（最终，在 CP-11 后输出）：**

```
──── CP-M GenerationManifest ────
已写入文件：{manifest文件路径}
摘要：
  - 请求：{action} {mode} {nodeId}
  - 配置：profile={版本} componentMap={规则数} tokenAliases={别名数}
  - 产物：{文件数}个文件 + {资源数}个资源
  - 检查点：CP-0 ✅ → CP-0.5 ✅ → CP-1 ✅ → CP-2 ✅ → CP-2.5 ✅ → CP-3 ✅ → CP-4.0 ✅ → CP-7.6 ✅ → CP-10 ✅ → CP-10.5 ✅ → CP-11 ✅
  - 验证：综合得分 {X}%
──── CP-M END ────
```
