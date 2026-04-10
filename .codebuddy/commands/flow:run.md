---
name: flow:run
description: 开启智慧工作流。支持直接启动或附带需求文档启动，自动解析文档内容、创建 PRD 并驱动 AI 开发流水线。
---

# 开启智慧工作流

## 指令概述

本指令用于启动 workflow-orchestrator（工作流编排专家）。支持三种使用方式：

1. **附带需求文档启动**：用户通过 `@` 引用或直接提供需求文档，系统自动解析文档内容，创建 PRD 后启动工作流
2. **附带文字描述启动**：用户提供简短的需求描述，系统引导创建 PRD 后启动工作流
3. **直接启动**：不提供任何输入，从 PRD 库选择已有文档或创建新 PRD 后启动工作流

**核心原则**：所有分支在启动工作流前都必须确保有 PRD 文档（已有或新建）。

## 执行流程

### Step 0：环境检查与首次运行判断

> **目的**：在工作流正式启动前，完成两项前置检查——① 确保用户拥有最佳的 Markdown 文档预览体验；② 检测当前项目是否曾运行过工作流或导入过知识，判断是否为首次运行。

#### 0-1. 检查 Markdown Preview Enhanced 插件

> Markdown 文件（`.md`）是本项目中最核心的交互文件——Skill 定义、PRD 文档、工作流产物等均以 Markdown 格式存储和呈现。为确保用户拥有最佳的阅读和预览体验，需先检查 IDE 是否已安装 **Markdown Preview Enhanced** 插件。

1. **检测插件安装状态**：

   使用终端命令检测 `Markdown Preview Enhanced` 插件是否已安装。由于不同 IDE（VS Code / CodeBuddy）的 CLI 命令名称和 PATH 配置可能不同，需按以下优先级尝试：

   ```bash
   # 优先级 1：直接使用 code 命令（VS Code 已配置 PATH 的场景）
   code --list-extensions 2>/dev/null | grep -i "shd101wyy.markdown-preview-enhanced"

   # 优先级 2：如果 code 命令不可用，尝试通过 CodeBuddy 应用内置路径
   # macOS CodeBuddy 路径示例（根据实际安装名称调整）：
   "/Applications/CodeBuddy CN.app/Contents/Resources/app/bin/code" --list-extensions 2>/dev/null | grep -i "shd101wyy.markdown-preview-enhanced"
   ```

   实际执行时，使用如下合并命令一次性检测：

   ```bash
   (code --list-extensions 2>/dev/null || "/Applications/CodeBuddy CN.app/Contents/Resources/app/bin/code" --list-extensions 2>/dev/null || "/Applications/CodeBuddy.app/Contents/Resources/app/bin/code" --list-extensions 2>/dev/null) | grep -i "shd101wyy.markdown-preview-enhanced"
   ```

   - 如果命令返回了扩展 ID（`shd101wyy.markdown-preview-enhanced`），说明插件已安装 → **跳转到 0-2**
   - 如果所有路径均无输出（未安装或无法检测），→ 继续步骤 2
   - 如果所有命令均失败（无法识别的 IDE 环境），→ 直接**跳转到 0-2**

2. **提示用户并安装插件**：

   使用 `ask_followup_question` 工具提示用户：

   ```
   标题: 📦 推荐安装 Markdown Preview Enhanced 插件
   问题: 检测到您尚未安装 Markdown Preview Enhanced 插件。Markdown 是本项目最核心的交互文件格式，安装该插件可以获得更好的文档预览体验。是否立即安装？

   选项:
     - "✅ 立即安装 — 自动安装 Markdown Preview Enhanced 插件后继续"
     - "⏭️ 跳过安装 — 不安装，直接继续工作流"
   ```

   - 用户选择"立即安装" → 执行安装命令：

     ```bash
     code --install-extension shd101wyy.markdown-preview-enhanced --force
     ```

     安装完成后，向用户确认安装成功，提示可通过 `Ctrl+Shift+V`（macOS 为 `Cmd+Shift+V`）或右键菜单打开 Markdown 预览 → **跳转到 0-2**

   - 用户选择"跳过安装" → **跳转到 0-2**
   - 安装失败 → 向用户报告错误信息，但不阻塞工作流 → **跳转到 0-2**

#### 0-2. 判断工作流是否首次运行

1. **检测工作流运行痕迹**（使用 `list_dir`，**最多 2 次调用**）：

   并行检查以下两个目录：
   - `.codebuddy/memory/` —— 项目记忆目录，存放工作流运行过程中的知识沉淀
   - `docs/` —— 项目文档目录，存放知识库、PRD、工作流产物等

   只要**任一目录**存在且包含有效文件（非空目录、有实际文件内容），即视为项目曾进行过工作流相关操作。

2. **判定与分流**：

   ```
   has_memory = .codebuddy/memory/ 存在且目录下有任意文件
   has_docs   = docs/ 存在且目录树下有任意文件

   IF has_memory OR has_docs:
     → 项目曾运行过工作流或已导入知识 → 直接进入 Step 1
   ELSE:
     → 两个目录均不存在或均无有效文件 → 首次运行 → 询问用户意图
   ```

3. **首次运行 → 询问用户意图**：

   使用 `ask_followup_question` 工具展示选择器：

   ```
   标题: 👋 欢迎使用智慧工作流
   问题: 这是本项目首次启动工作流，请告诉我您的情况：

   选项:
     - "📥 这是一个已有的项目，我要先导入它 — 收集项目文档和代码信息，构建知识基线后再开始需求开发"
     - "🆕 这是一个全新项目，从零开始 — 直接进入需求创建流程"
     - "⏭️ 我已经有 PRD 了，直接开始 — 跳过检测，直接选择 PRD 启动工作流"
   ```

   - 用户选择"导入已有项目" → **调用 `/flow:import` 分支工作流**（知识导入工作流），完成后返回 Step 1
   - 用户选择"全新项目" → 记录 `projectType = "new"` → **跳转到 Step 1**
   - 用户选择"直接开始" → **跳转到 Step 1**

4. **🚨 CRITICAL 约束（Step 0 专用）**：
   - 0-1 **仅检测和安装插件**，不做任何项目结构扫描、文件读取或代码探索；`code` 命令不可用或安装失败时不阻塞工作流
   - 0-2 **仅检测 `.codebuddy/memory/` 和 `docs/` 两个目录是否存在且包含有效文件**，不做其他扫描
   - **禁止**读取任何文件内容（`read_file`、`codebase_search` 等），仅使用 `list_dir` 检测目录结构
   - 如果检测因权限等原因失败，视为"首次运行"，走询问流程

---

> Step 0 完成后，无论结果如何，后续流程与现有逻辑完全一致。

### Step 1：判断用户输入类型

根据用户的输入内容，分为以下三种情况：

| 情况 | 判断条件 | 跳转 |
|------|----------|------|
| **A. 附带需求文档/设计链接** | 用户通过 `@` 引用了文件、消息中包含文件路径，或包含 Figma 设计链接 | → Step 2A |
| **B. 附带文字描述** | 用户在指令后输入了需求描述文字（非文件引用） | → Step 2B |
| **C. 无任何输入** | 用户仅输入了 `/flow:run`，没有附带任何文档或文字 | → Step 2C |

**支持的文档类型**：
- **Word 文档**（`.docx`）
- **PDF 文档**（`.pdf`）
- **PowerPoint 文档**（`.pptx`）
- **Markdown 文件**（`.md`）
- **纯文本文件**（`.txt`）
- **图片文件**（`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`）—— 可能是需求截图
- **矢量设计稿**（`.svg`）—— Figma / Sketch 等工具导出的设计稿（需预处理，详见视觉分析协议 §0.2）
- **Figma 设计链接** —— `https://www.figma.com/design/...` 或 `https://www.figma.com/file/...` 格式的 URL（通过 MCP 获取结构化设计数据，用于辅助 PRD 创建。设计稿还原为代码的工作在后续工作流的前端设计方案阶段由 `figma-d2c` skill 完成）

---

### Step 2A：有需求文档/设计链接 → 解析文档并创建 PRD

当检测到用户提供了需求文档或 Figma 设计链接时，按以下步骤执行：

> **🚨 CRITICAL 约束（Step 2A 专用）**：
> - **本步骤仅做两件事：解析用户提供的文档/设计数据 + 调用 prd-creator**
> - **禁止在加载 prd-creator 之前做任何项目探索行为**——不读 README.md、不扫描项目结构、不探索源码

1. **识别输入类型并调用对应的解析工具**：
   - `.docx` 文件 → 调用 `docx` skill 读取并提取文档内容
   - `.pdf` 文件 → 调用 `pdf` skill 读取并提取文档内容
   - `.pptx` 文件 → 调用 `pptx` skill 读取并提取文档内容
   - `.md` / `.txt` 文件 → 直接使用 `read_file` 工具读取内容
   - 图片文件（`.png`/`.jpg`/`.jpeg`/`.gif`/`.webp`）→ 执行**视觉分析协议**（见下方 2a 子流程）
   - `.svg` 文件 → 执行**视觉分析协议**（见下方 2a 子流程，协议 §0.2 会自动进行 SVG 预处理）
   - **Figma 设计链接** → 执行**Figma 数据获取子流程**（见下方 2b 子流程）

2. **整理解析结果**：将文档内容整理为结构化的需求描述，提取以下关键信息（如文档中包含）：
   - 需求名称 / 项目名称
   - 功能描述与业务背景
   - 涉及的平台（后端 / Web 端 / 小程序端）
   - 用户角色与使用场景
   - 业务规则与约束条件
   - 非功能性需求（性能、安全等）

   **2a. 图片文件视觉分析子流程**：

   当用户提供的文件中包含图片（`.png`/`.jpg`/`.jpeg`/`.gif`/`.webp`）或矢量设计稿（`.svg`）时，不再简单使用 `read_file` 做纯文本降级，而是执行结构化视觉分析：

   1. **加载视觉分析协议**：读取 `.codebuddy/skills/workflow-orchestrator/rules/visual-analysis-protocol.md`
   2. **前置检测与预处理**（协议 §0）：
      - 检测文件格式和大小
      - **SVG 文件**：执行 §0.2 SVG 预处理流程（检测文字是否转路径 → 转换为 PNG → 长页面分段截图）
      - **超大文件**（>20MB）：必须先预处理转换
      - 标准位图格式：直接进入下一步
   3. **读取图片**：使用 `read_file` 工具读取图片文件（利用多模态图片识别能力）。对预处理后的文件，读取转换后的 PNG 而非原始 SVG
   4. **按协议规范执行分析**：
      - **图片分类**：判断图片类型（UI 设计稿 / 原型图 / 架构图 / 流程图 / 数据图表 / 截图 / 手绘草图）
      - **结构化分析**：根据图片类型执行对应的分析策略（组件树提取、交互推断、样式指南提取等）
      - **多图对比**（如有多张图片）：执行对比分析，生成差异清单
   5. **产出质量自检**（协议 §6.1）：检查不确定项数量、文案识别度、关键信息缺失情况，自动判定 `visualReviewReady` 值
   6. **保存分析结果**：将视觉分析产出保存为 JSON 中间产物文件：
      - 保存路径：`docs/prd/_visual-analysis.json`
      - 格式参见 `visual-analysis-protocol.md` §6 最终产出格式（v1.2）
   7. **生成视觉分析摘要**：提取关键信息作为 prd-creator 的补充输入（参见下方步骤 3 中的传递格式）

   > **💡 Token 优化**：视觉分析结果一经保存到 `_visual-analysis.json`，后续阶段（如 `frontend-architect`）直接读取 JSON 即可，**无需重复分析原始图片**。
   
   > **⚠️ SVG 注意事项**：Figma 等工具导出的 SVG 文件通常将所有文字转为 `<path>` 矢量曲线，且文件体积巨大（可达 30MB+）。必须先预处理转 PNG 再分析，否则 AI 无法识别文案内容，产出将严重有损。详见协议 §0.2。

   **2b. Figma 设计链接数据获取子流程**：

   当用户消息中包含 Figma 设计链接（`figma.com/design/...` 或 `figma.com/file/...`）时：

   1. **解析 Figma URL**：
      ```
      URL 格式: https://www.figma.com/(design|file)/<fileKey>/<fileName>?node-id=<nodeId>
      
      解析规则：
      - fileKey: URL 路径中 /design/ 或 /file/ 后的字母数字串
      - nodeId: 查询参数 node-id 的值，将 `-` 替换为 `:`
      ```

   2. **检查 MCP 可用性**：
      - 检查是否配置了 `FramelinkFigmaMCP` 服务
      - 如果 MCP 不可用 → 提示用户配置 MCP（参见 `mcp-setup-guide` skill），同时降级为视觉分析协议的兜底方案

   3. **通过 MCP 获取设计数据**：
      - 调用 `get_figma_data(fileKey, nodeId)` 获取完整节点树
      - 预期返回数据包含：节点树（id/name/type/layout/fills/text/textStyle/effects/children）、样式定义等

   4. **将 MCP 数据转化为视觉分析结果**：
      - 从节点树提取组件结构 → 生成 `componentTree`
      - 从 TEXT 节点提取所有文案内容（精确值，非 OCR 近似）
      - 从 layout 定义提取布局信息和坐标
      - 从 fills/textStyle/effects 提取样式指南（精确 rgba 值）
      - 产出 `_visual-analysis.json`（v1.2 格式），标注 `"sourceFormat": "figma-mcp"`

   5. **下载设计稿渲染图**：
      - 使用 `download_figma_images` 工具下载当前节点的完整渲染图到 `docs/prd/design-screenshots/`
      - 渲染图用于后续 `VISUAL_REVIEW` 阶段进行像素级对比
      - 在 `_visual-analysis.json` 中记录渲染图路径

   6. **记录 Figma URL 信息**：将 Figma URL、fileKey、nodeId 记录到 `_visual-analysis.json` 中，供后续工作流的前端实现阶段使用（`figma-d2c` skill 在前端设计方案阶段会读取此信息进行设计稿还原）

   > **💡 为什么不在此阶段直接进行 D2C？**
   > 设计稿还原为代码是前端实现的工作，属于工作流的 IMPLEMENT 阶段。在 PRD 创建阶段，Figma 数据的作用是帮助理解需求和确认设计方案，而非直接生成代码。D2C 能力会在 workflow-orchestrator 编排的前端设计方案阶段由 `figma-d2c` skill 自然调度执行。

3. **调用 prd-creator skill 创建 PRD**：
   - 使用 `use_skill` 工具加载 `prd-creator` skill
   - 将解析后的文档内容作为初始输入传入，格式如下：

   ```
   用户提供了需求文档，以下是解析后的内容，请基于此创建 PRD：

   ---
   【文档来源】：{文件名}
   【文档类型】：{文档类型}

   【解析内容】：
   {解析后的完整文档内容}
   ---
   ```

   - **如果包含图片文件且已完成视觉分析**，在上述内容后追加视觉分析摘要：

   ```
   【视觉分析结果】（详见 docs/prd/_visual-analysis.json）：
   - 图片数量: {N} 张
   - 页面类型: {layout 类型，如 topnav-sidebar-main}
   - 核心组件: {top-5 组件摘要}
   - 关键交互: {top-3 交互推断}
   - 不确定项: {需要用户确认的点}
   ---

   请基于以上文档内容和视觉分析结果创建 PRD。
   对于视觉分析中标记为"不确定"的项，请在苏格拉底式提问中向用户确认。
   ```

   - **如果包含 Figma 设计链接且已获取 MCP 数据**，在上述内容后追加 Figma 数据摘要：

   ```
   【Figma 设计数据】（详见 docs/prd/_visual-analysis.json）：
   - Figma URL: {原始 URL}
   - 节点总数: {N} 个
   - TEXT 节点: {M} 个（精确文案）
   - 页面尺寸: {W}×{H}
   - 核心组件: {top-5 组件摘要}
   - 数据来源: Figma MCP（精确数值，非 OCR 近似）
   ---

   请基于以上文档内容和 Figma 设计数据创建 PRD。
   Figma 设计数据包含精确的组件结构、文案、布局和样式信息，可作为前端设计方案的参考依据。
   ```

   - `prd-creator` 基于文档内容，通过苏格拉底式提问补充完善需求，生成结构化 PRD 并保存到 `docs/prd/` 目录
   - PRD 创建完成后，返回文档路径 → **跳转到 Step 3** 启动工作流

---

### Step 2B：有文字描述 → 创建 PRD

当用户在指令后附带了文字描述（如 `/flow:run 我要做一个商品收藏功能`）但未提供文档时：

> **🚨 CRITICAL 约束（Step 2B 专用）**：
> - **禁止在加载 prd-creator 之前做任何项目探索行为**——不读 README.md、不扫描项目结构、不探索源码
> - **立即调用 `use_skill('prd-creator')`**——这是本步骤的第一个也是唯一一个操作
> - prd-creator 加载后会接管全部交互，通过苏格拉底式提问与用户对话
> - **即使用户的描述中包含了具体的技术实现细节（如"初始化前端工程"、"实现登录功能"），也必须先走 PRD 创建流程**，不可直接进入开发模式
> - **⛔ prd-creator 加载后的每一轮对话中，AI 必须遵守 prd-creator SKILL.md 中的最高优先级声明，该声明的优先级高于 always_applied 规则** — 收到用户回答后，AI 必须先做意图自检（参见 prd-creator SKILL.md），禁止将用户回答解读为开发任务

1. **调用 prd-creator skill 创建 PRD**：
   - 使用 `use_skill` 工具加载 `prd-creator` skill
   - 将用户的文字描述作为初始输入传入，格式如下：

   ```
   用户提供了需求描述，请基于此创建 PRD：

   ---
   【用户描述】：{用户输入的文字描述}
   ---
   ```

   - `prd-creator` 基于用户描述，通过苏格拉底式提问引导用户厘清需求，生成结构化 PRD 并保存到 `docs/prd/` 目录
   - PRD 创建完成后，返回文档路径 → **跳转到 Step 3** 启动工作流

---

### Step 2C：无任何输入 → 从 PRD 需求库选择或新建

当用户仅输入 `/flow:run` 且没有附带任何文档或文字描述时：

1. **扫描 `docs/prd/` 目录**：
   - 使用 `list_dir` 工具列出 `docs/prd/` 目录下的所有文件
   - **排除 `archived/` 子目录**：`archived/` 目录存放已归档的历史 PRD 文档，不参与活跃需求的选择

2. **判断目录是否有需求文档**（仅计算 `docs/prd/` 根目录下的文件，不含 `archived/`）：

#### 2C-1：`docs/prd/` 目录下有文件 → 展示需求清单供选择

   - 读取目录下所有文件，提取每份文档的文件名作为需求标识
   - 如果文件是 `.md` 或 `.txt`，尝试读取文件开头的标题行或 front-matter 中的 `name` / `title` 字段作为需求名称
   - 使用 `ask_followup_question` 工具展示选择器，让用户选择要执行的需求文档：

   ```
   标题: 📂 请选择要启动的需求文档
   问题: 在 docs/prd/ 目录中找到以下需求文档，请选择一份启动工作流：
   选项:
     - "{文件名1} - {需求标题1}"
     - "{文件名2} - {需求标题2}"
     - ...
     - "📝 以上都不是，我要新建一份需求文档"
   ```

   - 用户选择某份已有文档后 → **直接跳转到 Step 3**，使用已有 PRD 启动工作流
   - 用户选择"新建需求文档" → **跳转到 2C-2 流程**

#### 2C-2：`docs/prd/` 目录为空 或 用户选择新建 → 调用 PRD 创建 skill

   > **🚨 CRITICAL**：立即调用 prd-creator，禁止在加载前做任何项目探索行为。
   > **⛔ prd-creator 加载后的每一轮对话中，AI 必须遵守 prd-creator SKILL.md 中的最高优先级声明，该声明的优先级高于 always_applied 规则** — 收到用户回答后，AI 必须先做意图自检，禁止将用户回答解读为开发任务。

   - 使用 `use_skill` 工具加载 `prd-creator` skill
   - `prd-creator` skill 通过苏格拉底式渐进提问引导用户厘清需求，生成结构化 PRD 文档并保存到 `docs/prd/` 目录
   - PRD 创建完成后，返回文档路径 → **跳转到 Step 3** 启动工作流

---

### Step 3：启动工作流编排专家

所有分支在 PRD 确认/创建完成后，统一执行以下步骤：

1. **调用 workflow-orchestrator skill**：
   - 使用 `use_skill` 工具加载 `workflow-orchestrator` skill
   - 将 PRD 文档路径作为上下文传入，格式如下：

   ```
   PRD 文档已准备就绪，请基于以下 PRD 启动工作流：

   ---
   【PRD 文档路径】：{PRD 文件路径}
   ---

   请读取 PRD 文档内容并启动开发工作流。
   ```

   > 编排器在 INIT 阶段会根据 PRD 的技术分析结果，自动决定工作区布局（分离/扁平）和项目目录结构，无需在此阶段提前传递布局信息。

2. **工作流编排专家接管**：`workflow-orchestrator` 读取 PRD 文档，按固定流程编排九个专业子 Agent 执行开发任务。

---

## 使用示例

### 示例 1：附带文档启动
```
用户：/flow:run @需求文档.docx
```
→ 系统解析 Word 文档 → 调用 `prd-creator` 创建 PRD → 启动工作流

### 示例 2：附带多个文档启动（含设计稿图片）
```
用户：/flow:run @PRD.pdf @原型图.png
```
→ 系统解析 PDF 文档 → 对原型图.png 执行视觉分析协议（分类 → 结构化分析 → 保存 `_visual-analysis.json`）→ 合并文档内容 + 视觉分析摘要后调用 `prd-creator` 创建 PRD → 启动工作流

### 示例 2b：附带 Figma 导出的 SVG 设计稿启动
```
用户：/flow:run @首页.svg
```
→ 加载视觉分析协议 → §0.2 检测到 SVG 文字转路径（30MB，2417 个 path，0 个 text）→ SVG→PNG 转换 + 长页面分段截图 → 基于 PNG 执行结构化分析 → §6.1 质量自检 → 保存 `_visual-analysis.json` → 调用 `prd-creator` → 启动工作流

### 示例 2c：附带 Figma 设计链接启动（推荐 ✅）
```
用户：/flow:run https://www.figma.com/design/dHIQ2vwvuFCVGYFk93gbTr/MyApp?node-id=486-97715
```
→ 解析 URL（fileKey=`dHIQ2vwvuFCVGYFk93gbTr`, nodeId=`486:97715`）→ 检查 MCP 可用 → 调用 `get_figma_data` 获取精确节点数据 → 生成 `_visual-analysis.json` + 下载设计稿渲染图 → 调用 `prd-creator` 创建 PRD → 启动工作流（后续前端设计方案阶段自动使用 `figma-d2c` skill 进行设计稿还原）

### 示例 2d：附带 Figma 链接 + 需求文档启动
```
用户：/flow:run @需求说明.docx https://www.figma.com/design/abc123/MyApp?node-id=10-20
```
→ 解析 Word 文档 → 通过 MCP 获取 Figma 设计数据 → 合并文档内容 + Figma 结构化数据后调用 `prd-creator` → 启动工作流

### 示例 3：附带简短描述启动
```
用户：/flow:run 我要做一个商品收藏功能
```
→ 调用 `prd-creator`（以描述为初始输入）→ 创建 PRD → 启动工作流

### 示例 4：直接运行（从 PRD 库选择已有文档）
```
用户：/flow:run
```
→ 扫描 `docs/prd/` 目录 → 展示需求清单 → 用户选择已有 PRD → 直接启动工作流

### 示例 5：直接运行（PRD 库为空或选择新建）
```
用户：/flow:run
```
→ 扫描 `docs/prd/` 目录 → 发现为空或用户选择新建 → 调用 `prd-creator` 创建 PRD → 启动工作流

---

## 流程总览图

```
┌─────────────────────────────────────────────────────────────────┐
│                    /flow:run 指令入口                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Step 0             │
                    │  环境检查与         │
                    │  首次运行判断        │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  0-1: 检查 Markdown │
                    │  Preview Enhanced   │
                    │  插件是否已安装      │
                    └─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │ 已安装/跳过   │    │ 未安装        │
            │              │    │ 提示用户安装  │
            └──────────────┘    └──────────────┘
                    │                   │
                    │              ┌────┴────┐
                    │              ▼         ▼
                    │          立即安装   跳过安装
                    │              │         │
                    ▼              ▼         ▼
                    ┌─────────────────────┐
                    │  0-2: 检查          │
                    │  .codebuddy/memory/ │
                    │  和 docs/ 是否      │
                    │  存在且有有效文件    │
                    └─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │任一有文件     │    │ 均无有效文件  │
            │（曾运行/导入）│    │ （首次运行）  │
            │ 直接继续      │    │ 询问用户意图  │
            └──────────────┘    └──────────────┘
                    │              ┌────┼────┐
                    │              ▼    ▼    ▼
                    │          导入项目 新项目 直接开始
                    │          (/flow:  │     │
                    │           import) │     │
                    │              │    │     │
                    │              ▼    ▼     ▼
                    │          完成返回  │     │
                    │              │    │     │
                    ▼              ▼    ▼     ▼
                    ┌─────────────────┐
                    │  Step 1: 判断    │
                    │  用户输入类型     │
                    └─────────────────┘
                              │
       ┌──────────────────────┼───────────────────┐
       ▼                      ▼                   ▼
 ┌────────────┐         ┌───────────┐       ┌───────────┐
 │A. 有文档    │         │ B. 有文字  │       │ C. 无输入  │
 │ 或 Figma URL│         └───────────┘       └───────────┘
 └────────────┘               │                   │
       │                      │                   ▼
       │                      │             ┌───────────┐
       │                      │             │扫描PRD目录 │
       │                      │             └───────────┘
       │                      │                   │
       │                      │         ┌────────┴────────┐
       │                      │         ▼                 ▼
       │                      │   ┌──────────┐     ┌──────────┐
       │                      │   │ 有PRD文件 │     │ 无PRD文件 │
       │                      │   └──────────┘     └──────────┘
       │                      │         │                 │
       │                      │         ▼                 │
       │                      │   ┌──────────┐            │
       │                      │   │ 用户选择  │            │
       │                      │   └──────────┘            │
       │                      │         │                 │
       │                      │    ┌────┴────┐            │
       │                      │    ▼         ▼            │
       │                      │ 选择已有   选择新建 ───────┤
       │                      │    │                      │
       ▼                      ▼    │                      ▼
 ┌───────────────┐            │    │                      │
 │ Step 2A       │            │    │                      │
 │ 解析文档/     │            │    │                      │
 │ Figma数据     │            │    │                      │
 │               │            │    │                      │
 │ ┌───────────┐ │            │    │                      │
 │ │文件类型？  │ │            │    │                      │
 │ └───────────┘ │            │    │                      │
 │  │     │    │ │            │    │                      │
 │  ▼     ▼    ▼ │            │    │                      │
 │ 文档  图片 Figma            │    │                      │
 │ 解析  视觉  URL│            │    │                      │
 │       分析 MCP │            │    │                      │
 │  │     │  获取 │            │    │                      │
 │  │     ▼    │ │            │    │                      │
 │  │  _visual-│ │            │    │                      │
 │  │  analysis│ │            │    │                      │
 │  │     │    │ │            │    │                      │
 │  ▼     ▼    ▼ │            │    │                      │
 │ ┌───────────┐ │            │    │                      │
 │ │合并所有   │ │            │    │                      │
 │ │解析结果   │ │            │    │                      │
 │ └───────────┘ │            │    │                      │
 └───────────────┘            │    │                      │
       │                      │    │                      │
       ▼                      ▼    │                      ▼
 ┌─────────────────────────────────────────────────────────┐
 │              调用 prd-creator skill                      │
 │   (将文档内容/Figma数据/文字描述作为初始输入)          │
 │              生成 PRD 并保存到 docs/prd/              │
 └─────────────────────────────────────────────────────────┘
                    │                        │
                    ▼                        ▼
 ┌─────────────────────────────────────────────────────────┐
 │                      Step 3                              │
 │            调用 workflow-orchestrator                     │
 │              传入 PRD 文档路径启动工作流                │
 │                                                          │
 │  工作流各阶段（INIT → DESIGN → IMPLEMENT → ...）        │
 │  前端设计方案阶段自动调用 figma-d2c skill                │
 │  进行设计稿还原（如有 Figma 数据）                       │
 └─────────────────────────────────────────────────────────┘
```

---

## 注意事项

1. **PRD 优先原则**：分支 A、B 必须先创建 PRD 再启动工作流；分支 C 选择已有 PRD 时可直接启动
2. **多文档合并**：当用户提供多个文档时，按顺序解析并合并内容，作为 `prd-creator` 的初始输入
3. **解析失败处理**：如果文档解析失败，向用户报告错误并建议手动输入需求描述，然后跳转到 Step 2B 流程
4. **大文档处理**：对于超长文档，提取核心需求信息进行摘要，避免上下文溢出
5. **格式兼容**：优先保留文档中的表格、列表等结构化信息，便于 PRD 创建阶段使用
6. **PRD 目录约定**：`docs/prd/` 是需求文档的统一存放目录，支持任意格式的文件（`.md`、`.docx`、`.pdf` 等）。其中 `docs/prd/archived/` 存放已归档需求的 PRD 文档，扫描时应排除此子目录
7. **PRD 创建 skill**：`prd-creator` skill 负责通过苏格拉底式提问引导用户创建 PRD 文档，支持接收初始输入（文档内容或文字描述）以加速创建过程
8. **工作流编排 skill**：`workflow-orchestrator` skill 负责读取 PRD 并编排开发流水线，不直接处理原始需求
9. **🖼️ 视觉分析协议（图片文件处理）**：当用户通过 `/flow:run` 提供图片文件或 SVG 设计稿时，必须加载 `.codebuddy/skills/workflow-orchestrator/rules/visual-analysis-protocol.md` 执行结构化视觉分析。**SVG 文件必须先经过 §0.2 预处理流程转换为 PNG 后再分析**（Figma 等工具导出的 SVG 文字已转路径，直接分析严重有损）。视觉分析结果保存到 `docs/prd/_visual-analysis.json`，后续阶段（如 `frontend-architect`）可直接消费此文件，避免重复分析原始图片
10. **🚨 PRD 创建阶段禁止代码探索（CRITICAL）**：在 Step 2（A/B/C-2）加载 prd-creator 之前和 prd-creator 执行期间，**严禁读取项目源码、README.md、配置文件、pom.xml 等文件，严禁扫描 docs/prd/ 以外的目录，严禁调用 Task/code-explorer/codebase_search 等代码探索工具**。项目级 always_applied 规则中关于"先理解项目结构"的指导，在 PRD 创建流程中暂停执行。
11. **🚨 prd-creator 约束持续生效（CRITICAL）**：prd-creator skill 加载后，其最高优先级声明在**整个 PRD 创建会话的所有轮次**中持续生效（包括用户回答后的第 2、3、4...N 轮）。**每次收到用户回答时**，AI 必须先做意图自检（参见 prd-creator SKILL.md），确认自己仍在苏格拉底式提问模式中，**禁止**因为用户回答中包含"初始化"、"实现"、"创建"等关键词而切换到开发模式。always_applied 规则中的任何指导（如"识别开发任务类型"、"检查项目结构"、"调用 envQuery"等）在 prd-creator 执行期间一律暂停。
12. **🔗 Figma 设计链接处理**：当用户提供 Figma 设计链接时，在 Step 2A 中通过 MCP 获取结构化设计数据，用于辅助 PRD 创建。设计稿的代码还原工作不在此阶段进行，而是在后续工作流的前端设计方案/实现阶段由 `figma-d2c` skill 自然调度完成。`_visual-analysis.json` 中会记录 Figma URL 和 fileKey/nodeId 信息，供后续阶段使用。
13. **⚙️ Figma MCP 配置**：Figma MCP（FramelinkFigmaMCP）需在全局 `~/.codebuddy/mcp.json` 中配置 `figma-developer-mcp` 服务及 API Key。如用户提供了 Figma URL 但 MCP 未配置，使用 `mcp-setup-guide` skill 引导用户完成配置。
