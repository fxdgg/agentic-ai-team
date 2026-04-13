---
name: flow-import
description: 历史项目知识导入。收集项目文档和代码信息，构建标准化知识基线，为后续的需求开发工作流提供项目上下文。
---

# 历史项目知识导入

## 指令概述

本指令用于已有代码但缺少知识库的历史项目。通过阶段化流程将项目的历史知识
转化为标准格式，接入 AI 工作流的知识传承体系。

**触发方式**：
1. `/flow-run` Step 0 自动检测后引导（推荐）
2. 用户手动执行 `/flow-import`

**核心原则**：
- 导入流程不创建 PRD，不进入常规工作流阶段，仅构建知识基线
- **子 Agent 隔离拉取**：TAPD/iwiki 等 MCP 拉取操作**必须通过 Agent 工具派发子 Agent 执行**，MCP 的 tool_result 响应（每条 5-20KB）留在子 Agent 的独立上下文窗口中，主对话仅接收完成汇报，彻底避免上下文积累
- **拉取即落盘**：子 Agent 每拉取一条数据，立即写入文件系统
- **引用不内联**：下游步骤通过索引文件路径消费数据，不在 prompt 中内联文档正文
- **状态持久化**：通过 `import-state.json` 持久化进度，支持断点恢复

---

## Step 0：断点恢复检查

```
检查 docs/knowledge-import/import-state.json 是否存在:
  - 存在且 currentStep != "DONE":
    → 读取状态，展示已完成/进行中的步骤
    → 向用户确认: "检测到未完成的导入，从断点继续？"
      - "继续" → 跳转到 currentStep 对应的步骤
      - "重新开始" → 删除 import-state.json，从 Step 1 开始
  - 存在且 currentStep == "DONE":
    → 提示: "导入已完成。重新导入将增量更新。"
    → 从 Step 1 开始
  - 不存在 → 从 Step 1 开始
```

## Step 1：收集用户输入

使用 `AskUserQuestion` 工具引导用户提供信息（**多选**）：

```
标题: 📋 历史项目知识导入
问题: 为了让 AI 更好地理解这个项目，请选择您能提供的材料（可多选）：

选项（multiSelect: true）:
  - "📂 Git 代码仓库 —— 提供 git 仓库地址，AI 自动克隆并分析"
  - "🔗 TAPD 需求链接 —— 粘贴 TAPD 需求/迭代链接，AI 自动拉取内容"
  - "📖 iwiki 页面 —— 提供 iwiki 链接或空间 ID，AI 自动拉取文档内容"
  - "📄 本地文档 —— 通过 @ 引用文件（支持 .md/.txt/.pdf/.docx/.pptx）"
  - "💬 口述项目背景 —— 我会文字描述项目情况"
  - "🤖 直接扫描当前代码 —— 让 AI 自动分析当前项目结构（无额外输入）"
```

### Step 1.5：收集具体输入并创建状态文件

根据用户勾选的选项，**依次收集**具体输入内容（仅收集链接/路径/描述，不拉取正文）。

收集完毕后，**立即创建 `import-state.json`**：

```
1. 确保 docs/knowledge-import/ 目录存在
2. 创建 docs/knowledge-import/import-state.json:
{
  "version": "1.0",
  "currentStep": "FETCH_SOURCES",
  "startedAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "inputSelections": ["tapd", "iwiki", ...],  // 用户选择的来源类型
  "fetchProgress": {
    "tapd": {
      "status": "pending",
      "links": ["用户粘贴的链接"],
      "total": 0, "done": 0, "failed": 0,
      "failedIds": [],
      "indexPath": "docs/knowledge-import/tapd-stories/_story-index.json"
    },
    "iwiki": {
      "status": "pending",
      "links": ["用户粘贴的链接"],
      "total": 0, "done": 0, "failed": 0,
      "failedIds": [],
      "indexPath": "docs/knowledge-import/iwiki/_page-index.json"
    },
    "localDocs": {
      "status": "pending",
      "files": ["@引用的文件路径"],
      "total": 0, "done": 0,
      "indexPath": "docs/knowledge-import/local-docs/_doc-index.json"
    },
    "gitRepos": {
      "status": "pending",
      "urls": ["git 仓库地址"],
      "clonedPaths": []
    },
    "description": {
      "status": "pending",
      "filePath": "docs/knowledge-import/description.md"
    }
  },
  "orchestrateStatus": "pending"
}
```

> 未选择的来源，status 设为 "skipped"。

---

## Step 2：拉取即落盘（各来源独立处理）

> **核心规则**：每拉取/解析一条数据，**立即写入文件**。对话上下文中**仅保留一行摘要**（如 `[✅ #12345] 用户注册优化 → 已保存`）。禁止在对话中累积文档正文。

各来源之间无依赖，可以任意顺序执行。每完成一个来源，更新 `import-state.json` 中对应的 `fetchProgress.{source}.status`。

### 2a. Git 仓库克隆（仅当 gitRepos 非空时）

```
对每个 git 仓库地址:
  1. 地址标准化（SSH 优先）:
     - HTTPS 地址 → 转换为 SSH: https://{host}/{path} → git@{host}:{path}.git
     - 已是 SSH → 直接使用
  2. 克隆到 {workspace}/{repo-name}（浅克隆: --depth 1 --single-branch）
  3. 仓库绑定: 检测技术栈 → 确认后追加到 .ai-team/project.yaml repos[]
  4. 更新 import-state.json: gitRepos.clonedPaths[] 追加路径, status → "done"
  5. 克隆失败 → 提供: "重试" / "跳过" / "我手动克隆后告诉你路径"
```

### 2b. TAPD 需求拉取（仅当 tapd 非空时）

> MCP 调用协议详见 `references/tapd-mcp-protocol.md`（此处不重复协议细节）。

**前置**：检查 MCP 配置（`tapd_mcp_http`），未配置则触发 `mcp-setup-guide` skill。

**⚠️ 子 Agent 隔离拉取模式**：

> **关键设计**：MCP 的 tool_result 响应体积很大（每条需求 5-20KB），即使主对话只输出一行摘要，tool_result 仍会累积在主对话上下文中。因此**必须通过 Agent 工具派发子 Agent 执行 MCP 拉取**，让 tool_result 留在子 Agent 的独立上下文窗口中，主对话仅接收子 Agent 的完成汇报。

```
1. 确保 docs/knowledge-import/tapd-stories/ 目录存在
2. 初始化 _story-index.json: { "stories": [], "totalCount": 0, "fetchedAt": "" }
3. 链接解析 → 获取需求 ID 列表（支持: 单条需求/列表页/迭代页链接）
   - 链接解析本身只是 URL 字符串处理，在主对话中完成即可
4. 更新 import-state.json: tapd.total = ID列表长度, tapd.status = "in_progress"

5. **分批派发子 Agent 拉取**:
   a) 将 ID 列表按 ≤10 条/批 分组（如 33 条 → 4 批: 10+10+10+3）
   b) 对每批，通过 Agent 工具（subagent_type: "general-purpose"）启动一个子 Agent:

   子 Agent Prompt 模板:
   ---
   你是 TAPD 需求拉取专员（批次 {batchIndex}/{totalBatches}）。
   
   任务: 通过 TAPD MCP 逐条拉取以下需求，每条拉取后立即写入文件。
   
   MCP 服务: tapd_mcp_http
   工作目录: {绝对路径}/docs/knowledge-import/tapd-stories/
   索引文件: {绝对路径}/docs/knowledge-import/tapd-stories/_story-index.json
   状态文件: {绝对路径}/docs/knowledge-import/import-state.json
   TAPD workspace_id: {workspace_id}
   
   本批次需求 ID 列表: [{id1}, {id2}, ..., {idN}]
   
   对每条需求执行:
   1. 通过 TAPD MCP 拉取需求详情（参考 MCP 调用协议）
   2. 立即写入文件:
      - tapd-stories/{story_id}.json  ← 原始 MCP 返回数据
      - tapd-stories/{story_id}.md   ← 清洗后 Markdown（≤3000 字，超出截断并标注 [TRUNCATED]）
   3. 读取当前 _story-index.json，追加索引条目:
      { "storyId": "xxx", "title": "需求标题", "status": "open", "priority": "high",
        "filePath": "tapd-stories/{story_id}.md", "rawPath": "tapd-stories/{story_id}.json", "charCount": N }
      然后写回 _story-index.json
   4. 读取 import-state.json，将 tapd.done++ 后写回
   5. 拉取失败的需求: 记录到 import-state.json 的 tapd.failedIds[]，tapd.failed++，继续下一条
   
   完成后汇报: 成功数、失败数、失败的 ID 列表（如有）
   ---

   c) 多批子 Agent **并行启动**（在同一条消息中发起多个 Agent 工具调用）
   d) 等待所有子 Agent 返回，主对话汇总结果:
      "[✅ TAPD] {done}/{total} 条需求已拉取（{failed} 条失败）"

6. 全部完成后: tapd.status → "done", 刷新 _story-index.json 的 totalCount 和 fetchedAt

降级策略:
  - MCP 未配置 → 触发 mcp-setup-guide skill
  - MCP 调用失败 → 提示: "重新配置 Token" / "我直接粘贴内容" / "跳过 TAPD"
  - 粘贴内容 → 写入 tapd-stories/pasted-{N}.md，追加索引
  - 子 Agent 全部失败 → 降级为主对话逐条拉取（仅当需求数 ≤5 时）
```

### 2b-iwiki. iwiki 文档拉取（仅当 iwiki 非空时）

> MCP 配置检查同 TAPD（检查 iwiki MCP 服务）。

**⚠️ 子 Agent 隔离拉取模式**（原理同 TAPD，MCP tool_result 隔离在子 Agent 上下文中）：

```
1. 确保 docs/knowledge-import/iwiki/ 目录存在
2. 初始化 _page-index.json: { "pages": [], "totalCount": 0, "fetchedAt": "" }
3. 链接解析 → 获取页面 ID 列表（单页面/空间目录递归）
   - 空间/目录链接: 向用户展示页面树，确认拉取范围
   - 链接解析在主对话中完成
4. 更新 import-state.json: iwiki.total, iwiki.status = "in_progress"

5. **分批派发子 Agent 拉取**:
   a) 将页面 ID 列表按 ≤10 条/批 分组
   b) 对每批，通过 Agent 工具启动子 Agent:

   子 Agent Prompt 模板:
   ---
   你是 iwiki 页面拉取专员（批次 {batchIndex}/{totalBatches}）。
   
   任务: 通过 iwiki MCP 逐条拉取以下页面，每条拉取后立即写入文件。
   
   MCP 服务: iwiki MCP
   工作目录: {绝对路径}/docs/knowledge-import/iwiki/
   索引文件: {绝对路径}/docs/knowledge-import/iwiki/_page-index.json
   状态文件: {绝对路径}/docs/knowledge-import/import-state.json
   
   本批次页面 ID 列表: [{id1}, {id2}, ..., {idN}]
   
   对每个页面执行:
   1. 通过 iwiki MCP 拉取页面内容
   2. 转换为 Markdown，立即写入 iwiki/{pageId}.md
   3. 读取并追加 _page-index.json:
      { "pageId": "xxx", "title": "页面标题", "spaceKey": "...", "filePath": "iwiki/{pageId}.md", "charCount": N }
   4. 更新 import-state.json: iwiki.done++
   5. 失败的页面: 记录到 import-state.json 的 iwiki.failedIds[], iwiki.failed++
   
   完成后汇报: 成功数、失败数
   ---

   c) 多批子 Agent 并行启动
   d) 等待所有子 Agent 返回，主对话汇总:
      "[✅ iwiki] {done}/{total} 个页面已拉取（{failed} 个失败）"

6. 全部完成后: iwiki.status → "done"
```

### 2c. 本地文档解析（仅当 localDocs 非空时）

```
1. 确保 docs/knowledge-import/local-docs/ 目录存在
2. 初始化 _doc-index.json: { "docs": [], "totalCount": 0 }
3. 对每个本地文档:
   a) 按扩展名解析:
      - .md / .txt → 直接 Read 内容
      - .pdf → 调用 Skill(skill: "pdf") 解析
      - .docx → 调用 Skill(skill: "docx") 解析
      - .pptx → 调用 Skill(skill: "pptx") 解析
   b) **立即写入** local-docs/{filename}.md（提取的纯文本内容）
   c) **追加索引** _doc-index.json:
      { "filename": "xxx", "type": "pdf|docx|md|txt|pptx", "filePath": "local-docs/{filename}.md", "charCount": N }
   d) 更新 import-state.json: localDocs.done++
4. 全部完成后: localDocs.status → "done"
```

### 2d. 口述描述落盘（仅当 description 非空时）

```
将用户口述内容写入 docs/knowledge-import/description.md
更新 import-state.json: description.status → "done"
```

### 2e. 汇总输入清单（基于 import-state.json 生成）

读取 `import-state.json`，展示**输入汇总确认**：

```
📋 已收集的项目信息：

✅ Git 仓库: {gitRepos.clonedPaths.length} 个已克隆
   {列出路径}
✅ TAPD 需求: {tapd.done} 条已拉取（{tapd.failed} 条失败）
   {列出前 10 条标题，超出显示 "...及其他 N 条"}
✅ iwiki 页面: {iwiki.done} 个已拉取
   {列出标题}
✅ 本地文档: {localDocs.done} 个已解析
   {列出文件名}
✅ 口述描述: 已记录

确认开始导入？
  - "✅ 确认，开始导入"
  - "📝 补充更多材料"
  - "🔄 重新拉取失败的条目"（仅当有 failed 时显示）
  - "❌ 取消"
```

> 用户选择"重新拉取" → 仅重新拉取 `failedIds` 中的条目。

---

## Step 3：启动导入工作流编排（传引用不传内容）

> **⚠️ 关键改造**：传入编排器的是**索引文件路径**，不是文档正文。编排器和子 Agent 通过读取索引文件获知有哪些文档，再按需 `Read` 单个文件。

更新 `import-state.json`: `currentStep → "ORCHESTRATE"`, `orchestrateStatus → "in_progress"`

调用 `Skill 工具（skill: "workflow-orchestrator"）` 并传入：

```
历史项目知识导入模式，请加载 phases/import-rules.md 并执行导入流程：

---
【导入模式】：knowledge-import
【状态文件】：{绝对路径}/docs/knowledge-import/import-state.json
【输入来源索引】（编排器和 Agent 通过读取这些索引文件获取文档列表，再按需 Read 单个文件）：
  - tapdIndex: {绝对路径}/docs/knowledge-import/tapd-stories/_story-index.json（{N}条需求）
  - iwikiIndex: {绝对路径}/docs/knowledge-import/iwiki/_page-index.json（{N}个页面）
  - docIndex: {绝对路径}/docs/knowledge-import/local-docs/_doc-index.json（{N}个文档）
  - description: {绝对路径}/docs/knowledge-import/description.md
  - clonedPaths: [{克隆仓库的绝对路径列表}]
  - scanOnly: {true/false}
  - deepMode: {true/false}
---
```

> **统一知识仓库模式**：@knowledge-builder 知识产出写入 `{knowledgeRepoLocalPath}/` 对应目录（maturity: draft），通过 Git 分支工作流。写入后同步维护三级索引：更新 `catalog.md`（Layer B）、重新生成 `knowledge-catalog.md`（Layer A）、同步 `index.json`（详见 knowledge-builder.md Step 4）。

## Step 4：导入完成后的衔接

更新 `import-state.json`: `currentStep → "DONE"`, `orchestrateStatus → "done"`

询问用户：

```
标题: ✅ 知识基线已建立
问题: 项目知识导入已完成，接下来您想：

选项:
  - "🚀 开始新需求开发 — 启动 /flow-run 工作流"
  - "📊 查看导入结果 — 查看知识基线报告"
  - "⏸️ 暂时到这里 — 稍后再开始开发"
```

---

## 注意事项

1. 导入流程**不创建 PRD**，不进入常规工作流阶段
2. 导入产物存储在 `docs/knowledge-import/` 目录，与常规工作流隔离
3. 导入流程可多次执行（增量更新，不覆盖已有知识）
4. 导入产物的置信度初始为 0.5-0.6（标记为 imported）
5. **MCP 优先原则**：TAPD/iwiki 拉取通过 MCP 能力完成，未配置时触发 `mcp-setup-guide` skill
6. **直接执行原则**：Git 克隆使用 SSH 协议直接执行，不做冗余协议试探
7. **优雅降级**：外部能力不可用时提供替代方案，不阻断整个流程
8. **子 Agent 隔离原则**：所有 MCP 拉取操作（TAPD/iwiki）**禁止在主对话中直接执行**。MCP 的 tool_result 会累积在对话上下文中，即使输出只有一行摘要。必须通过 Agent 工具派发子 Agent，让 tool_result 留在子 Agent 的独立上下文窗口中。仅当文档数 ≤5 时可降级为主对话直接拉取。
8. **支持的 TAPD 链接格式**：
   - 单条需求：`https://tapd.woa.com/tapd_fe/{workspace_id}/stories/view/{story_id}`
   - 需求列表页：`https://tapd.woa.com/tapd_fe/{workspace_id}/story/list?categoryId={category_id}`
   - 迭代页面：`https://tapd.woa.com/tapd_fe/{workspace_id}/iterations/view/{iteration_id}`
   - 旧版链接：`https://www.tapd.cn/{workspace_id}/stories/view/{story_id}` 及 `https://www.tapd.cn/{workspace_id}/prong/stories/view/{story_id}`
9. **支持的 iwiki 链接格式**：
   - 单页面：`https://iwiki.woa.com/pages/viewpage.action?pageId={pageId}`
   - 空间/目录：`https://iwiki.woa.com/display/{spaceKey}/...` 或直接提供空间 ID
10. **支持的本地文档**：`.md`、`.txt`、`.pdf`、`.docx`、`.pptx`

---

## 产物目录结构

```
docs/knowledge-import/
├── import-state.json              # 状态持久化（断点恢复）
├── _batch-plan.json               # batch 调度计划（编排阶段生成）
├── _doc-collection.json           # @doc-collector 产出
├── codebase-profile.json          # @codebase-profiler 产出
├── knowledge-baseline.json        # @knowledge-builder 产出
├── SUMMARY.md                     # @knowledge-builder 产出
├── description.md                 # 口述内容落盘
├── tapd-stories/
│   ├── _story-index.json          # TAPD 需求轻量索引
│   ├── {story_id}.json            # 原始需求 JSON
│   └── {story_id}.md              # 清洗后 Markdown（≤3000 字）
├── iwiki/
│   ├── _page-index.json           # iwiki 页面索引
│   └── {pageId}.md                # 清洗后 Markdown
└── local-docs/
    ├── _doc-index.json            # 本地文档索引
    └── {filename}.md              # 解析后纯文本
```

---

## 深度导入模式（可选增强）

当用户选择"直接扫描当前代码"时，在 Step 2e 确认后追加深度导入选项。

选择"是"后，`@knowledge-builder` 在标准流程后追加生成目录级 `CONTEXT.md`：
- 为每个核心模块目录（含 `pom.xml`/`build.gradle`/`package.json`）生成独立上下文文档
- 就近保存在模块目录下（如 `{backend-root}/user-center/CONTEXT.md`）
- 后续领域 Agent 只需读取局部 CONTEXT.md，减少 15-25% 上下文消耗
- 置信度 0.5（imported），文件头部标注置信度提醒

> CONTEXT.md 内容结构和详细策略见 `references/deep-import-mode.md`
