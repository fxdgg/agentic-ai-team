# 视觉分析协议

> **加载条件**: 当用户通过 `/flow-run` 提供的需求文档中包含图片文件（`.png`/`.jpg`/`.jpeg`/`.gif`/`.webp`/`.svg`）、设计稿截图、或 Figma 设计链接（`figma.com/design/...` / `figma.com/file/...`）时，加载本协议进行结构化视觉分析。
> **设计意图**: 图片/设计稿不再简单"降级为纯文本描述"，而是通过标准化流程提取**布局结构、组件树、交互行为、视觉风格**等设计意图，产出结构化 JSON 供 PRD 创建和后续架构设计消费。**当存在 Figma URL 时优先通过 MCP 获取精确数据，避免 SVG/PNG 中间转换的信息损失。**

> **多仓模式路径说明**：本文件中所有 `docs/prd/` 路径（如 `docs/prd/design-screenshots/`、`docs/prd/_visual-analysis.json`），编排器在运行时基于 `state.json` 的 `projectConfig.docsRoot` 解析为绝对路径（`{workspaceRoot}/{docsRoot}/docs/prd/...`）。Agent Prompt 中注入的路径已为绝对路径，Agent 无需感知单仓/多仓差异。

---

## 0. 前置检测与预处理（CRITICAL）

> **设计意图**: 不同来源和格式的设计稿文件差异巨大。在进入正式分析流程前，必须先检测文件格式和特征，对特殊格式进行预处理转换，确保后续分析能获得有效信息。

### 0.1 文件格式检测

对每个用户提供的图片/设计稿文件，执行以下检测：

```
1. 检测文件扩展名：
   - .png / .jpg / .jpeg / .gif / .webp → 标准位图格式 → 直接进入 §1 图片分类
   - .svg → 矢量格式 → 进入 §0.2 SVG 预处理流程

2. 检测文件大小：
   - ≤ 5MB → 正常处理
   - 5MB ~ 20MB → 标记 largeFile = true，正常处理但在分析时注意 Token 消耗
   - > 20MB → 标记 oversized = true，必须预处理后再分析（read_file 有 20MB 限制）
```

### 0.2 SVG 预处理流程

> **背景**: Figma / Sketch / Adobe XD 等设计工具导出的 SVG 文件有以下特征会导致 AI 视觉分析严重有损：
> - 所有文字转为 `<path>` 矢量曲线（0 个 `<text>` 元素），AI 无法识别文案内容
> - 文件体积极大（Figma 长页面导出可达 30MB+），超过 read_file 限制
> - 位图以 base64 内嵌在 `<image>` 和 `<pattern>` 中，进一步膨胀文件体积
> - 这类 SVG 虽然是"矢量格式"，但对 AI 分析而言**信息密度极低**——大量 path data 占据文件体积，却不包含任何可读语义

**检测 SVG 特征**：

```bash
# 快速特征检测（并行执行）
text_count=$(grep -c '<text' file.svg 2>/dev/null || echo 0)
path_count=$(grep -c '<path' file.svg 2>/dev/null || echo 0)
file_size=$(ls -l file.svg | awk '{print $5}')
viewbox=$(head -c 2000 file.svg | grep -o 'viewBox="[^"]*"')
```

根据检测结果分类处理：

| 特征 | 判定 | 处理策略 |
|------|------|---------|
| `<text>` 元素 > 0 且文件 < 5MB | 语义保留型 SVG | 可直接作为图片读取分析 |
| `<text>` = 0 且 `<path>` > 100 | 文字转曲线型 SVG（典型 Figma 导出） | **必须转换为 PNG 后分析** |
| 文件 > 20MB | 超大型 SVG | **必须转换 + 可能需要分段** |
| `<text>` = 0 且 `<path>` > 100 且文件 > 20MB | 重度有损型（如本案例） | **转换 + 分段 + 标记降级** |

**SVG → PNG 转换流程**：

```
1. 优先方案：使用系统工具转换
   # macOS（使用内置 sips 工具或 rsvg-convert）
   sips -s format png input.svg --out output.png 2>/dev/null
   # 如果 sips 不支持 SVG，尝试 rsvg-convert
   rsvg-convert -f png -o output.png input.svg 2>/dev/null
   # 或使用 Playwright/Puppeteer 进行浏览器渲染转换
   # （适用于包含复杂 CSS/JS 的 SVG）

2. 备选方案：使用 npx 安装临时工具
   npx sharp-cli -i input.svg -o output.png 2>/dev/null
   npx svg2png input.svg output.png 2>/dev/null

3. 长页面分段策略（当 SVG 高度 > 4000px 时）：
   - 从 SVG 头部提取 viewBox 尺寸（如 "0 0 1920 11666"）
   - 按每段 ≤ 3000px 高度切分
   - 使用 Playwright 打开 SVG → 逐段 viewport 截图：
     a) 启动浏览器，创建页面
     b) 设置 viewport 为 SVG 宽度 × 3000px
     c) page.goto('file:///path/to/input.svg')
     d) 获取页面实际高度
     e) 循环截图：每次设置 clip { x:0, y: segmentIndex*3000, width, height:3000 }
     f) 保存为 {pageName}-segment-{N}.png

4. 兜底方案（所有转换工具均不可用时）：
   a) 提示用户："检测到您提供的 SVG 文件（{文件名}，{文件大小}）可能是从 Figma
      等设计工具导出的矢量文件。由于文字已转为路径曲线，AI 无法识别具体文案内容。
      建议您：
      ① 优先方案：从 Figma 导出为 PNG 格式（选择 2x 倍率以保证清晰度）
      ② 备选方案：从 Figma 导出 PDF 格式（保留文字可选中性）
      ③ 补充方案：在提供图片的同时，附带一份文字版的页面内容说明"
   b) 在 _visual-analysis.json 中标记：
      - sourceFormat: "svg-path-only"
      - preprocessFailed: true
      - 在 uncertainties 中追加关键缺失项
```

**转换后的处理**：

```
转换成功后：
1. 将 PNG 文件保存到 docs/prd/design-screenshots/ 目录
2. 在 _visual-analysis.json 中记录：
   - sourceFormat: "svg" 
   - originalFile: "首页.svg"
   - preprocessed: true
   - preprocessMethod: "svg-to-png" 或 "svg-to-png-segmented"
   - savedPath: 指向转换后的 PNG 文件（非原始 SVG）
3. 如果是分段截图，savedPath 为数组：
   ["docs/prd/design-screenshots/首页-segment-1.png",
    "docs/prd/design-screenshots/首页-segment-2.png", ...]
4. 后续分析流程基于转换后的 PNG 进行，走标准 §1~§4 流程
```

### 0.3 用户引导（设计稿最佳实践提示）

> 当检测到 SVG 文件属于"文字转曲线型"时，在分析结果的总结确认中向用户提示：

```
💡 设计稿格式建议：
检测到您提供的设计稿（{文件名}）为 Figma 导出的 SVG 格式，文字已被转为路径曲线。
为获得最佳的 AI 分析效果，建议后续提供设计稿时优先使用以下格式：

推荐优先级：
1. 🥇 Figma 设计链接（最佳）— 直接提供 Figma URL，AI 通过 MCP 获取精确设计数据
   示例：https://www.figma.com/design/xxx/MyApp?node-id=10-20
2. 🥈 PNG（2x 倍率导出）— AI 视觉理解效果好，文字可通过 OCR 识别
3. 🥉 PDF — 保留文字可选中性，兼顾清晰度和语义
4. ⚠️ JPG — 轻量但有压缩损失，适合快速预览场景
5. ⛔ SVG — 不推荐用于完整页面设计稿（文字转路径后 AI 无法识别）

如您使用 Figma：
- 最佳方式：直接复制设计稿链接提供给 AI
- 导出方式：File → Export → PNG → 2x 即可
```

### 0.4 Figma URL 数据源路由（当用户同时提供了 Figma 链接时）

> **设计意图**: Figma MCP 可直接从 Figma API 获取完整的结构化设计数据（节点树、精确文案、坐标、样式），数据质量远超任何导出文件方式。当用户提供了 Figma 设计链接时，应自动优先走 MCP 路径，避免无效的 SVG/PNG 中间转换。

**触发条件**：
- 用户消息中包含 `figma.com/design/` 或 `figma.com/file/` 格式的 URL
- 或用户在提供 SVG 文件的同时，SVG 文件名/路径暗示来自 Figma 导出（如用户主动说明"从 Figma 导出的"）

**数据源优先级**：

```
┌──────────────────────────────────────────────────────────┐
│                   数据源优先级路由                          │
├──────┬───────────────────────────┬─────────┬─────────────┤
│ 优先级 │ 数据源                     │ 数据质量 │ 适用场景     │
├──────┼───────────────────────────┼─────────┼─────────────┤
│ P0   │ Figma URL + MCP           │ ⭐⭐⭐⭐⭐ │ 有 Figma URL │
│      │ (get_figma_data)          │ 精确     │ + MCP 可用   │
├──────┼───────────────────────────┼─────────┼─────────────┤
│ P1   │ Figma URL + figma-d2c     │ ⭐⭐⭐⭐⭐ │ 需要直接     │
│      │ Skill                     │ 精确+代码│ 生成代码     │
├──────┼───────────────────────────┼─────────┼─────────────┤
│ P2   │ 设计稿截图 PNG/JPG        │ ⭐⭐⭐    │ 无 Figma URL │
│      │                           │ OCR近似  │ 仅有截图     │
├──────┼───────────────────────────┼─────────┼─────────────┤
│ P3   │ Figma 导出 SVG            │ ⭐       │ 仅作兜底     │
│      │                           │ 严重有损 │ 需预处理     │
└──────┴───────────────────────────┴─────────┴─────────────┘
```

**路由决策逻辑**：

```
IF 用户消息包含 Figma URL:
  1. 解析 URL:
     - fileKey: /design/ 或 /file/ 后的字母数字串
     - nodeId: 查询参数 node-id 的值，将 `-` 替换为 `:`
  
  2. 检查 MCP 可用性:
     - 读取 .codebuddy/mcp.json → 检查 FramelinkFigmaMCP 配置
     - IF MCP 可用:
       → 调用 get_figma_data(fileKey, nodeId)
       → 将返回的节点树/样式/文案转化为 _visual-analysis.json（v1.2 格式）
       → 标注 sourceFormat = "figma-mcp", colorAccuracy = "exact"
       → **下载节点渲染图**（CRITICAL — 视觉审查前置条件）:
         a) 使用 download_figma_images 下载当前节点的完整渲染图（PNG）
         b) 保存到 docs/prd/design-screenshots/{pageName}-design.png
         c) 在 _visual-analysis.json 中记录 savedPath 和 designScreenshotsDir
         d) 设置 visualReviewReady = true
         ⚠️ 没有渲染图，VISUAL_REVIEW 阶段将无法执行设计稿对比验收
       → 跳过 §0.2 SVG 预处理和 §1~§4 视觉分析流程
     - IF MCP 不可用:
       → 提示用户配置 MCP（推荐使用 mcp-setup-guide Skill）
       → 降级为 §0.2 SVG 预处理 + §1~§4 标准视觉分析流程

ELIF 用户提供了 .svg 文件（无 Figma URL）:
  → 执行 §0.2 SVG 预处理流程
  → 在 §0.3 用户引导中增加提示：
     "💡 如果您有此设计稿的 Figma 链接，推荐直接提供链接以获得
      更精确的分析结果（精确文案、坐标、样式等）。"

ELIF 用户提供了 .png/.jpg 等图片:
  → 执行标准 §1~§4 视觉分析流程
```

**MCP 数据 → _visual-analysis.json 映射规则**：

| MCP 返回数据 | 映射到 JSON 字段 | 说明 |
|-------------|-----------------|------|
| `nodes[].name/type/children` | `componentTree` | 生成精确的组件树（含节点名称和类型） |
| `nodes[].text` (TEXT 节点) | 组件树内的文案标注 | **精确文案**，非 OCR 近似 |
| `nodes[].layout` → `mode/gap/alignItems` | `layout` 类型判定 | 精确布局模式：row/column/none |
| `nodes[].layout` → `x/y/width/height` | `canvasSize` + 各区域坐标 | **精确到小数点的坐标和尺寸** |
| `fills` → 颜色/渐变定义 | `styleGuide.primaryColor` 等 | **精确 rgba 值**（标注 `colorAccuracy: "exact"`） |
| `textStyle` → `fontFamily/fontSize/lineHeight/fontWeight` | `styleGuide.fontSize` 等 | **精确字体规范** |
| `effects` → `boxShadow/filter` | `styleGuide.shadows` | 精确阴影/模糊值 |
| `fills[type=IMAGE]` → `imageRef` | `images[].analysis.imageRefs` | 图片资源引用，可通过 `download_figma_images` 下载 |

**MCP 数据源的 _visual-analysis.json 额外字段**：

```json
{
  "sourceFormat": "figma-mcp",
  "dataSource": "FramelinkFigmaMCP",
  "figmaUrl": "https://www.figma.com/design/xxx/xxx?node-id=xxx",
  "figmaFileKey": "xxx",
  "figmaNodeId": "xxx:xxx",
  "preprocessed": false,
  "analysisQuality": {
    "overallScore": "high",
    "textRecoverable": true,
    "uncertaintyCount": 0,
    "criticalGaps": [],
    "colorAccuracy": "exact",
    "layoutAccuracy": "exact"
  }
}
```

> **实测数据对比**（同一设计稿 `首页` 节点 `486:97715`）：
>
> | 维度 | SVG 解析（P3） | MCP 获取（P0） |
> |------|---------------|---------------|
> | TEXT 节点 | 0 个（全转 path） | **146 个**（精确文案） |
> | 总节点数 | ~10 泛化区域 | **636+ 精确节点** |
> | 颜色精度 | approximate | **exact rgba** |
> | 布局精度 | "Y: ~940\~2400" | **x/y/w/h 精确坐标** |
> | 文本样式 | 无 | **fontFamily/fontSize/lineHeight/fontWeight** |
> | 不确定项 | 9 项 | **0 项** |
> | 数据体积 | 30MB SVG → 预处理开销大 | 273KB YAML（高效轻量） |

---

## 1. 图片分类

首先判断图片类型，不同类型使用不同的分析策略：

| 类型 | 特征识别 | 分析策略 | 产出重点 |
|------|---------|---------|---------|
| **UI 设计稿** | 包含精细 UI 组件、色彩规范、排版细节 | 提取组件树 + 布局描述 + 交互流程 + 样式指南 | 组件粒度、视觉规范 |
| **原型图/线框图** | 灰度/低保真的页面布局草图、无色彩细节 | 提取页面结构 + 功能区域 + 导航流程 | 页面层级、功能分区 |
| **系统架构图** | 包含模块方块、箭头、连接关系、技术标签 | 提取模块列表 + 依赖关系 + 数据流向 | 系统边界、服务依赖 |
| **流程图** | 步骤框、判断菱形、分支箭头、泳道 | 提取步骤序列 + 分支条件 + 终态 | 业务流程、状态机 |
| **数据表/图表** | 表格、柱状图、折线图、饼图 | 提取数据点 + 趋势描述 + 关键指标 | 数据需求、统计维度 |
| **截图（现有系统）** | 真实系统界面截图、含浏览器边框等 | 提取当前状态 + 标记需修改区域 | 变更对比基准 |
| **手绘草图** | 手写文字、手绘线条、潦草布局 | 提取核心意图 + 粗粒度布局 | 用户核心诉求 |

> **分类失败兜底**: 如果无法判断图片类型，默认按"UI 设计稿"策略分析，并在产出中标注 `"typeConfidence": "low"`。

---

## 2. UI 设计稿 / 原型图结构化分析流程

### Step 1：全局布局分析

- 页面整体布局类型（常见模式识别）：
  - `sidebar-main` — 侧边栏 + 主内容区
  - `topnav-main` — 顶部导航 + 内容区
  - `topnav-sidebar-main` — 顶部导航 + 侧边栏 + 内容区
  - `card-grid` — 卡片网格布局
  - `single-column` — 单列布局（表单页、详情页）
  - `split-pane` — 左右分栏（主从页面）
  - `tab-panel` — Tab 切换面板
  - `other` — 其他（需文字描述）
- 页面尺寸线索（如设计稿标注了宽度或有响应式断点标记）
- 整体视觉风格（浅色/深色、扁平/拟物、企业风/消费风）

### Step 2：组件树提取

将页面拆解为**层级化的组件树**，使用缩进格式描述：

```
Page: {页面名称}
├── {区域组件}
│   ├── {子组件} ({组件类型}, {关键属性})
│   └── {子组件} ({组件类型}, {关键属性})
├── {区域组件}
│   ├── {子组件}
│   │   ├── {孙组件}
│   │   └── {孙组件}
│   └── {子组件}
└── {区域组件}
```

**组件类型标注规范**：
- 输入类组件: `Input`, `Select`, `DatePicker`, `Upload`, `Checkbox`, `Radio`, `Switch`, `Slider`
- 展示类组件: `Table`, `List`, `Card`, `Tag`, `Badge`, `Avatar`, `Image`, `Statistic`
- 导航类组件: `Menu`, `Tabs`, `Breadcrumb`, `Pagination`, `Steps`
- 操作类组件: `Button`, `Dropdown`, `Modal`, `Drawer`, `Popover`
- 布局类组件: `Header`, `Sidebar`, `Footer`, `Content`, `Grid`, `Divider`

**关键属性标注**：
- 文本内容: `placeholder: "搜索商品"`, `label: "提交"`
- 数量/布局: `columns: 4`, `rows: 10`, `maxWidth: 1200px`
- 状态: `defaultValue: "全部"`, `disabled`, `loading`

### Step 3：交互行为推断

基于视觉元素推断用户交互行为。**只推断有明确视觉线索支撑的交互**，不做无根据的臆测：

| 视觉线索 | 推断交互 | 置信度 |
|---------|---------|--------|
| 带颜色/圆角的文字区域 | 按钮 → 点击动作 | 高 |
| 输入框/下拉箭头 | 表单输入 → 验证规则 | 高 |
| 表格 + 页码 | 分页列表 → 翻页/排序 | 高 |
| 带 `>` 箭头的列表项 | 列表点击 → 详情跳转 | 中 |
| 多个并排的标签页 | Tab 切换 → 内容切换 | 高 |
| 对话气泡/弹窗样式 | 模态交互 → 确认/取消 | 中 |
| 拖拽手柄/排序箭头 | 拖拽排序 | 中 |
| 无明确视觉线索 | **不推断，标记为待确认** | — |

### Step 4：样式指南提取

从设计稿中提取可识别的视觉规范：

```json
{
  "styleGuide": {
    "primaryColor": "#1890ff",
    "secondaryColor": "#f5222d",
    "backgroundColor": "#f0f2f5",
    "textColor": {
      "primary": "#333333",
      "secondary": "#666666",
      "disabled": "#999999"
    },
    "fontSize": {
      "title": "18px",
      "body": "14px",
      "caption": "12px"
    },
    "borderRadius": "4px",
    "spacing": "16px",
    "shadows": "有/无"
  }
}
```

> **注意**: 颜色值通过视觉近似估算，非精确值。在 JSON 中标注 `"colorAccuracy": "approximate"`。

---

## 3. 系统架构图 / 流程图分析流程

### 架构图分析

```json
{
  "architectureDiagram": {
    "modules": [
      {
        "name": "模块名称",
        "type": "service/database/gateway/queue/cache",
        "description": "识别到的职责描述"
      }
    ],
    "dependencies": [
      {
        "from": "模块A",
        "to": "模块B",
        "type": "sync/async/data-flow",
        "label": "箭头标签文字（如有）"
      }
    ],
    "layers": ["展示层", "业务层", "数据层"]
  }
}
```

### 流程图分析

```json
{
  "flowchart": {
    "steps": [
      {
        "id": "step-1",
        "type": "start/process/decision/end",
        "label": "步骤描述",
        "nextSteps": ["step-2"]
      },
      {
        "id": "step-2",
        "type": "decision",
        "label": "判断条件",
        "branches": {
          "yes": "step-3",
          "no": "step-4"
        }
      }
    ]
  }
}
```

---

## 4. 多图对比分析

当用户提供**多张图片**时（如"现状截图 + 设计稿"、"版本 A + 版本 B"），启用对比分析模式：

1. **识别图片对应关系**：判断哪些图片属于同一页面/功能的不同版本
2. **逐区域对比差异**：
   - 新增元素（设计稿中有但现状没有）
   - 删除元素（现状中有但设计稿没有）
   - 修改元素（位置/样式/内容变化）
   - 不变元素（两张图中完全一致的部分）
3. **产出差异清单**：

```json
{
  "comparison": {
    "source": "现状截图",
    "target": "设计稿",
    "changes": [
      {
        "type": "added",
        "element": "搜索筛选栏",
        "location": "页面顶部，表格上方",
        "description": "新增了按关键词+日期的组合搜索功能"
      },
      {
        "type": "modified",
        "element": "操作列按钮",
        "location": "表格最右列",
        "before": "编辑、删除 两个按钮",
        "after": "编辑、删除、详情 三个按钮",
        "description": "新增了详情按钮"
      },
      {
        "type": "removed",
        "element": "底部分页",
        "location": "页面底部",
        "description": "移除了传统分页，可能改为无限滚动"
      }
    ]
  }
}
```

4. **将差异清单转化为需求条目**，供 PRD 创建阶段使用

---

## 5. 原始图片保存（CRITICAL — 视觉验收前置条件）

> **设计意图**: 原始设计稿图片必须持久化到项目目录，因为后续 `VISUAL_REVIEW` 阶段需要将实现截图与设计稿原图进行 AI 对比验收。仅保存 JSON 分析结果**不足以支撑视觉验收**。

### 5.1 保存规则

对每一张用户提供的图片（设计稿、原型图、截图等），执行以下操作：

1. **创建保存目录**：`docs/prd/design-screenshots/`（PRD 级别）或 `docs/workflows/{需求ID}/design-screenshots/`（需求级别）
2. **复制原始图片**到保存目录，文件名规则：
   - 保留原始文件名（如 `homepage-design.png`）
   - 如用户通过对话框粘贴图片（无原始文件名），使用 `design-{序号}-{页面名称推断}.png` 命名
   - 如用户提供多张同页面不同状态的图片，使用 `{页面名称}-{状态描述}.png` 命名
3. **在 `_visual-analysis.json` 中记录保存路径**：每个 `images[]` 条目增加 `savedPath` 字段

### 5.2 保存方式

```
执行流程：

1. 当用户通过 /flow-run 提供图片时：
   a) 读取图片内容
   b) 创建目标目录（如不存在）
   c) 将图片写入目标路径
   d) 在 _visual-analysis.json 的对应 images[] 条目中记录 savedPath

2. 当用户通过对话框直接粘贴图片时：
   a) 图片以临时路径存在于对话上下文中
   b) 使用 write_to_file 工具将图片内容保存到 design-screenshots/ 目录
   c) 如果无法直接保存二进制文件，提示用户手动将图片保存到指定路径
   d) 记录到 _visual-analysis.json

3. 兜底方案（无法自动保存时）：
   a) 在 _visual-analysis.json 中将 savedPath 设为 null
   b) 在 uncertainties 中追加："原始设计稿图片未保存，VISUAL_REVIEW 阶段将依赖文字描述进行验收"
   c) 在总结确认中提醒用户手动保存图片到 design-screenshots/ 目录
```

### 5.3 目录结构示例

```
docs/prd/design-screenshots/
├── homepage-design.png          # 首页设计稿
├── user-list-design.png         # 用户列表页设计稿
├── user-form-design.png         # 用户表单页设计稿
└── mobile-homepage-design.png   # 移动端首页设计稿
```

---

## 6. 最终产出格式

所有视觉分析结果统一输出为 JSON 结构，保存为中间产物文件：

**保存路径**: `docs/prd/_visual-analysis.json`（或 `docs/workflows/{需求ID}/analysis/_visual-analysis.json`）

```json
{
  "version": "1.2",
  "analysisDate": "2026-03-29",
  "designScreenshotsDir": "docs/prd/design-screenshots/",
  "images": [
    {
      "filename": "设计稿-首页.png",
      "originalFile": "设计稿-首页.png",
      "sourceFormat": "png",
      "preprocessed": false,
      "preprocessMethod": null,
      "savedPath": "docs/prd/design-screenshots/设计稿-首页.png",
      "imageType": "ui-design",
      "typeConfidence": "high",
      "pageName": "首页",
      "analysis": {
        "layout": "topnav-sidebar-main",
        "canvasSize": { "width": 1920, "height": 1080 },
        "componentTree": "...(组件树文本)",
        "interactions": ["..."],
        "styleGuide": {"...": "..."}
      }
    },
    {
      "filename": "首页-segment-1.png",
      "originalFile": "首页.svg",
      "sourceFormat": "svg-path-only",
      "preprocessed": true,
      "preprocessMethod": "svg-to-png-segmented",
      "savedPath": [
        "docs/prd/design-screenshots/首页-segment-1.png",
        "docs/prd/design-screenshots/首页-segment-2.png",
        "docs/prd/design-screenshots/首页-segment-3.png"
      ],
      "imageType": "ui-design",
      "typeConfidence": "high",
      "pageName": "首页",
      "textRecoveryNeeded": true,
      "analysis": {
        "layout": "topnav-main",
        "canvasSize": { "width": 1920, "height": 11666, "note": "长页面，已分段处理" },
        "componentTree": "...",
        "interactions": ["..."],
        "styleGuide": {"...": "..."}
      }
    }
  ],
  "comparison": null,
  "implementationNotes": [
    "商品卡片需要骨架屏加载效果",
    "分类筛选需要支持多选",
    "表格列宽总和超过容器宽度，需设置横向滚动"
  ],
  "uncertainties": [
    "底部是否为固定定位无法从静态图判断",
    "表格行点击行为不明确（跳转详情 or 展开行）"
  ],
  "analysisQuality": {
    "overallScore": "high",
    "textRecoverable": true,
    "uncertaintyCount": 2,
    "criticalGaps": []
  },
  "visualReviewReady": true
}
```

> **字段说明（v1.2 新增/修改）**:
> - `version`: 版本号升级至 `"1.2"`
> - `images[].originalFile`: 用户提供的原始文件名（SVG 转 PNG 后追溯原始来源）
> - `images[].sourceFormat`: 原始文件格式（`"png"` / `"jpg"` / `"svg"` / `"svg-path-only"` / `"pdf"`）
> - `images[].preprocessed`: 是否经过预处理转换
> - `images[].preprocessMethod`: 预处理方法（`null` / `"svg-to-png"` / `"svg-to-png-segmented"` / `"pdf-to-png"`）
> - `images[].savedPath`: 位图格式为字符串，分段截图为字符串数组
> - `images[].textRecoveryNeeded`: 当源文件文字已转路径时为 `true`，提示后续需要用户补充文案
> - `designScreenshotsDir`: 设计稿保存目录路径
> - `images[].pageName`: 图片对应的页面名称（供 VISUAL_REVIEW 阶段匹配用）
> - `analysisQuality`: 产出质量自检结果（见 §6.1）
> - `visualReviewReady`: 是否具备视觉验收条件（见 §6.1 判定规则）

### 6.1 产出质量自检（CRITICAL）

> **设计意图**: 防止低质量的分析结果标记为 `visualReviewReady: true`，导致后续阶段基于不完整信息做出错误决策。

分析完成后，必须执行以下自检：

```
自检维度与评分：

1. 文案识别度（textRecovery）：
   - componentTree 中包含具体文案（按钮文字、标题内容等）→ "high"
   - componentTree 中部分组件有文案，部分用占位描述 → "medium"
   - componentTree 中几乎无具体文案（全是 Section1/2/3 等泛化描述）→ "low"

2. 不确定项数量（uncertaintyCount）：
   - 0~3 项 → 正常
   - 4~6 项 → 标记 overallScore = "medium"
   - ≥ 7 项 → 标记 overallScore = "low"

3. 关键信息缺失（criticalGaps）：
   检查以下关键信息是否被提取到，缺失的加入 criticalGaps 数组：
   - 导航栏菜单项文案
   - 主要按钮/CTA 文案
   - 各 section 的标题文案
   - 表单字段标签
   - 表格列头文案

综合判定：
- overallScore = "high" 且 criticalGaps 为空 → visualReviewReady = true
- overallScore = "medium" → visualReviewReady = true（但在摘要中提示信息可能不完整）
- overallScore = "low" 或 criticalGaps ≥ 3 项：
  → visualReviewReady = false
  → 在总结确认中明确告知用户："视觉分析结果信息不足，建议补充 PNG 格式设计稿或文字说明"
  → 后续仍可进入开发流程，但 VISUAL_REVIEW 阶段将自动跳过
```

---

## 7. 图片分析策略

> **核心原则**: 以最佳视觉理解效果为首要目标，不对图片做缩放或降质处理。对特殊格式（SVG）先预处理转换再分析。

| 策略 | 说明 |
|------|------|
| **Figma MCP 优先** | 当用户提供了 Figma 设计链接时，**必须优先通过 MCP（`get_figma_data`）获取结构化数据**，跳过 SVG/PNG 的中间转换。MCP 数据包含精确的文案、坐标、样式和节点树，数据质量远超任何视觉分析方式。详见 §0.4 |
| **SVG 降级自动提示** | 当用户仅提供了 SVG 文件（无 Figma URL）且检测到文字转曲线特征时，在分析结果中自动追加提示："如有 Figma 链接，推荐直接提供链接以获取更精确的分析结果"。详见 §0.3 |
| **原始分辨率分析** | **始终使用原始分辨率**进行图片分析，不做任何缩放或压缩。高分辨率设计稿中的细节（字号、间距、图标、阴影、圆角等）对后续视觉验收至关重要，缩放会丢失关键信息 |
| **SVG 预处理优先** | SVG 文件**必须先经过 §0.2 预处理流程**转换为 PNG 后再进入分析。直接对 Figma 导出的大型 SVG 做 `read_file` 会因文字转路径而严重有损 |
| **长页面分段分析** | 当设计稿高度 > 4000px 时（如本案例 11666px），按每段 ≤ 3000px 切分为多张截图，逐段分析后合并组件树。确保每个 section 的细节不会因上下文过长而被忽略 |
| **完整逐区域分析** | 对每张设计稿同时进行全局布局分析和逐区域精细分析，确保不遗漏任何视觉细节。不做"粗粒度优先"的渐进策略 |
| **分析缓存** | 视觉分析结果保存到 `_visual-analysis.json`，后续阶段（如 frontend-architect）直接读取 JSON，不重复分析原始图片 |
| **多维度并行提取** | 对每张图片一次性提取所有维度信息（布局、组件、色彩、字体、间距、交互、动效线索），避免多次读取同一张图片 |
| **产出质量门禁** | 分析完成后必须执行 §6.1 自检。当 `uncertainties ≥ 7` 或关键文案大面积缺失时，不得标记 `visualReviewReady = true` |

---

## 8. 与 PRD 创建流程的集成

视觉分析产出作为 `prd-creator` 的**补充输入**（而非替代）：

```
传递给 prd-creator 的格式：

---
【视觉分析结果】：
- 页面类型: {layout}
- 核心组件: {top-5 组件摘要}
- 关键交互: {top-3 交互推断}
- 不确定项: {需要用户确认的点}
---

请基于以上视觉分析结果和文档内容创建 PRD。
对于视觉分析中标记为"不确定"的项，请在苏格拉底式提问中向用户确认。
```

---

## 9. 与前端架构设计的集成

当 `_visual-analysis.json` 存在时，`frontend-architect` 可直接消费（详见 `agents/frontend-architect.md` §1.2.5）：

- **组件树 → 组件目录结构**：视觉分析的组件树可作为前端架构设计的起点
- **交互推断 → 状态管理方案**：推断的交互行为辅助判断是否需要引入状态机
- **样式指南 → 全局样式变量**：提取的色彩/字号/间距可直接转化为 CSS 变量定义
- **差异清单 → 精确改动范围**：comparison.changes 直接对应文件级改动
- **设计稿覆盖度标注**：前端架构文档 front-matter 中追加 `designCoverage` 字段，标注哪些页面有设计稿支撑，哪些是架构师推断
- **不确定项 → 澄清问题**：uncertainties 转化为前端架构阶段的澄清问题

---

## 10. 与视觉验收（VISUAL_REVIEW）阶段的集成

当 `_visual-analysis.json` 存在且 `visualReviewReady = true` 时，`VISUAL_REVIEW` 阶段的 `visual-reviewer` Agent 会消费以下数据：

- **`designScreenshotsDir`** → 定位设计稿原图目录
- **`images[].savedPath`** → 逐页获取设计稿原图，与实现截图进行 AI 对比
- **`images[].pageName`** → 将设计稿与对应页面的实现截图配对
- **`images[].analysis.componentTree`** → 验证组件是否完整实现
- **`images[].analysis.styleGuide`** → 验证色彩、字号、间距等视觉规范的还原度
- **`images[].analysis.interactions`** → 交互行为的验证检查清单
- **`implementationNotes`** → 特殊实现注意事项的验收检查

> **关键依赖链**:
> - **路径 A（Figma MCP，最优）**: `Figma URL` → `MCP get_figma_data`（§0.4） → `_visual-analysis.json`（精确数据） + `download_figma_images`（节点渲染图 → `design-screenshots/`）→ `frontend-architect` → `web-developer` → `visual-reviewer`（基于渲染图对比验收）
> - **路径 B（图片分析）**: `visual-analysis-protocol`（§0 预处理 + §1~§4 图片分析 + 保存） → `_visual-analysis.json` → `frontend-architect` → `web-developer` → `visual-reviewer`（设计还原度验收）
> - **路径 C（SVG 兜底）**: `SVG 文件` → §0.2 预处理（SVG→PNG） → §1~§4 分析 → `_visual-analysis.json`（近似数据） → 后续流程同路径 B
