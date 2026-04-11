---
name: flow-import
description: 历史项目知识导入。收集项目文档和代码信息，构建标准化知识基线，为后续的需求开发工作流提供项目上下文。
---

# 历史项目知识导入

## 指令概述

本指令用于已有代码但缺少知识库的历史项目。通过三步流程将项目的历史知识
转化为标准格式，接入 AI 工作流的知识传承体系。

**触发方式**：
1. `/flow-run` Step 0 自动检测后引导（推荐）
2. 用户手动执行 `/flow-import`

**核心原则**：导入流程不创建 PRD，不进入常规工作流阶段，仅构建知识基线。

## 执行流程

### Step 1：收集用户输入（输入优先，按需触发）

> **核心原则**：不预先检查任何外部系统的可用性，而是让用户先告诉我们有什么材料，再根据实际输入按需触发相应的能力。

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

### Step 1.5：根据用户选择，收集具体输入并智能分类

根据用户勾选的选项，**依次收集**具体输入内容：

| 用户选择 | 后续交互 | 收集结果 |
|---------|---------|---------|
| Git 代码仓库 | 请用户粘贴 git 仓库地址（HTTPS 或 SSH 均可，AI 自动转为 SSH） | `inputSources.gitRepos[]` |
| TAPD 需求链接 | 请用户粘贴 TAPD 链接（支持单条需求、需求列表页、迭代页，可提供多条） | `inputSources.tapdLinks[]` |
| iwiki 页面 | 请用户粘贴 iwiki 链接（单页面或目录页面，可提供多条） | `inputSources.iwikiLinks[]` |
| 本地文档 | 请用户通过 @ 引用文件（可多个） | `inputSources.localDocs[]` |
| 口述背景 | 请用户自由输入文字描述 | `inputSources.description` |
| 直接扫描当前代码 | 无需额外输入 | `inputSources.scanOnly = true` |

> **组合输入**：以上选项**不互斥**。用户可以同时提供 git 仓库 + TAPD 链接 + 本地文档 + 口述描述。

### Step 2：按需触发能力（输入驱动的延迟检测）

根据 Step 1.5 收集到的 `inputSources`，**按需**触发相应的前置处理。不在输入中的能力完全不触发、不检测。

#### 2a. Git 仓库克隆（仅当 `gitRepos` 非空时）

> **默认使用 SSH 协议**：SSH 是内网 Git 仓库的标准认证方式，避免 HTTPS 交互式认证问题。

```
对每个 git 仓库地址:
  1. 地址标准化（SSH 优先）:
     - 如果用户给的是 HTTPS 地址（如 https://git.woa.com/org/repo）
       → 自动转换为 SSH 地址: git@git.woa.com:org/repo.git
     - 如果用户给的已经是 SSH 地址（如 git@git.woa.com:org/repo.git）
       → 直接使用
     - 转换规则: https://{host}/{path} → git@{host}:{path}.git
       （如果 path 已以 .git 结尾则不重复添加）
  2. 确定克隆目标目录（默认: 当前工作区根目录下）
     - 克隆路径: {workspace}/{repo-name}
       如工作区为 /Users/xxx/Claude Code/ai-team，仓库名为 general-chatbot
       → 克隆到 /Users/xxx/Claude Code/ai-team/general-chatbot
     - ⚠️ 禁止克隆到工作区的上级目录或其他无关位置
     - 设计意图: 后续工作流 Agent（如 @codebase-profiler、@backend-architect）
       以"项目根目录路径"作为输入，直接扫描该目录下的代码结构。
       克隆到工作区根目录下可确保编排器传入的路径与 Agent 预期一致。
  3. 执行 git clone（浅克隆: --depth 1 --single-branch），使用 SSH 地址
  4. 克隆成功 → 记录本地路径到 inputSources.clonedPaths[]
  5.5. 仓库绑定（自动追加到 project.yaml）：
     - 检查 `.ai-team/project.yaml` 是否存在
       - 如不存在 → 提示用户先执行 `/team-init`
       - 如存在 → 继续
     - 对每个新 clone 的仓库：
       a) 检测类型和技术栈（pom.xml → Java, package.json → React 等）
       b) 推断编译命令
       c) 向用户确认：
          ```
          📁 新仓库已克隆: {repo-name}
          类型: {type} | 技术栈: {techStack} | 编译命令: {buildCommand}
          → 绑定到 project.yaml repos[]？[是/否]
          ```
       d) 用户确认后 → 追加到 `project.yaml` 的 `repos[]`
       e) 重新聚合 `tech_stack`
  5. 克隆失败 → 记录错误原因，提供选项:
     - "重试" / "跳过该仓库继续" / "我手动克隆后告诉你路径"
```

#### 2b. TAPD 需求拉取（仅当 `tapdLinks` 非空时）

> **默认使用 MCP 能力**：TAPD 需求拉取通过 TAPD MCP 服务完成，需先检查 MCP 配置是否就绪。
> 图片/附件操作使用 `tapd-toolkit` skill 中的本地脚本。

##### 2b-0. MCP 配置前置检查

在拉取 TAPD 需求前，**必须先检查 MCP 配置**：

```
检查步骤:
  1. 读取 项目 .claude/settings.json 或全局 ~/.claude/settings.json 的 mcpServers 配置 文件
  2. 检查 mcpServers 中是否存在 "tapd_mcp_http" 配置
  3. 检查 headers 中 X-Tapd-Access-Token 是否为真实 Token（非占位符 "YOUR_TAI_PAT_TOKEN"）

判断结果:
  - 文件不存在 / 缺少 tapd_mcp_http / Token 为占位符:
    → 调用 Skill 工具（skill: "mcp-setup-guide"） 引导用户完成 MCP 配置
    → 配置完成后继续 TAPD 拉取流程
  - 配置正常:
    → 继续执行 2b-1 的链接解析流程
```

##### 2b-1. TAPD MCP 调用方式

**重要**：TAPD MCP 服务基于 Streamable HTTP 协议，正确的调用方式如下（避免试错）：

| 配置项 | 值 |
|--------|-----|
| 服务 URL | `https://mcpgw.knot.woa.com/tapd/` |
| 传输协议 | `streamable-http` |
| HTTP 方法 | `POST` |
| Content-Type | `application/json` |
| Accept | `application/json, text/event-stream` |
| 认证头 | `X-Tapd-Access-Token: Bearer {tai_pat_token}` |
| 请求体格式 | JSON-RPC 2.0（`{"jsonrpc":"2.0","id":N,"method":"...","params":{...}}`） |

TAPD MCP 提供 3 个核心工具：
- **`lookup_tapd_tool`** — 语义搜索匹配 TAPD 工具（传入自然语言描述，返回最匹配的工具名）
- **`lookup_tool_param_schema`** — 查询指定工具的参数 schema
- **`proxy_execute_tool`** — 代理执行 TAPD 工具（传入工具名 + 参数，底层支持 60+ 种 TAPD 操作）

使用流程：先通过 `lookup_tapd_tool` 找到合适的工具名 → 通过 `lookup_tool_param_schema` 获取参数格式 → 通过 `proxy_execute_tool` 执行操作。

> 当 Claude Code 已加载 MCP 配置后，可直接使用 `mcp__tapd_mcp_http__lookup_tapd_tool`、`mcp__tapd_mcp_http__proxy_execute_tool` 等 MCP 原生工具调用，无需手动构造 HTTP 请求。

##### 2b-2. 链接解析与拉取

**支持两种链接形态**：

| 链接形态 | 示例 | 处理方式 |
|---------|------|---------|
| **单条需求链接** | `https://tapd.woa.com/tapd_fe/{workspace_id}/stories/view/{story_id}` | 直接拉取该需求详情 |
| **需求列表页链接** | `https://tapd.woa.com/tapd_fe/{workspace_id}/story/list?categoryId=...` | 先查询分类下所有需求，再逐条拉取 |

```
前置: 调用 Skill 工具（skill: "tapd-toolkit"） 加载 TAPD 扩展技能（图片/附件操作需要）

对每个 TAPD 链接:
  1. 链接解析与分类:
     a) 单条需求链接（URL 含 /stories/view/{story_id} 或 /prong/stories/view/{story_id}）:
        → 提取 workspace_id + story_id
        → 通过 TAPD MCP 工具拉取需求详情
          * 先调用 lookup_tapd_tool 查找 "获取需求详情" 对应的工具
          * 再调用 proxy_execute_tool 执行拉取
     b) 需求列表页链接（URL 含 /story/list?categoryId=...）:
        → 提取 workspace_id（URL 路径中的数字段）
        → 提取 categoryId（query 参数）
        → 通过 TAPD MCP 工具按分类查询需求列表
           * 传入 filter: { category_id: categoryId }
           * 如果列表页还有其他筛选参数（status、iteration_id 等），一并作为 filter 传入
        → 获取需求 ID 列表后，逐条拉取完整详情
        → 向用户展示拉取到的需求清单（标题 + ID + 状态），确认是否全部导入
     c) 迭代链接（URL 含 /iterations/view/{iteration_id}）:
        → 提取 workspace_id + iteration_id
        → 通过 TAPD MCP 工具查询该迭代下的所有需求
        → 逐条拉取需求详情
     d) 无法识别的链接格式:
        → 尝试提取 workspace_id，通过 TAPD MCP 工具搜索相关需求
        → 如仍无法匹配 → 将链接作为文本记录，提示用户补充

  2. TAPD 能力不可用处理（统一降级策略）:
     - MCP 配置缺失（settings.json 中 mcpServers 未配置 tapd_mcp_http）:
       → 调用 Skill 工具（skill: "mcp-setup-guide"） 引导用户完成配置
       → 配置完成后重试
     - MCP 已配置但工具调用失败（Token 无效、网络问题等）:
       → 提示用户:
         "TAPD MCP 工具调用失败，请选择: "
         a) "重新配置 MCP Token"（触发 mcp-setup-guide）
         b) "我直接粘贴需求内容"
         c) "跳过 TAPD，继续其他导入"
     - 单条请求失败 → 记录失败的需求 ID，继续处理其他需求，最终汇总报告

  3. 拉取结果记录到 inputSources.tapdStories[]，每条包含:
     - storyId, title, description, status, priority
     - 关联的迭代、模块等元数据（如有）
```

#### 2b-iwiki. iwiki 文档拉取（仅当 `iwikiLinks` 非空时）

> **默认使用 MCP 能力**：iwiki 文档拉取通过 iwiki MCP 服务完成，需先检查 MCP 配置是否就绪。

##### 2b-iwiki-0. MCP 配置前置检查

```
检查步骤:
  1. 读取 项目 .claude/settings.json 或全局 ~/.claude/settings.json 的 mcpServers 配置 文件
  2. 检查 mcpServers 中是否存在 iwiki MCP 服务配置
  3. 检查认证 Token 是否为真实值（非占位符）

判断结果:
  - 文件不存在 / 缺少 iwiki MCP 配置 / Token 为占位符:
    → 调用 Skill 工具（skill: "mcp-setup-guide"） 引导用户完成 iwiki MCP 配置
    → 配置完成后继续 iwiki 拉取流程
  - 配置正常:
    → 继续执行 2b-iwiki-1 的链接解析流程
```

##### 2b-iwiki-1. 链接解析与拉取

**支持两种链接形态**：

| 链接形态 | 示例 | 处理方式 |
|---------|------|---------|
| **单页面链接** | `https://iwiki.woa.com/pages/viewpage.action?pageId=123456` | 直接拉取该页面内容 |
| **空间/目录链接** | `https://iwiki.woa.com/display/SPACENAME/...` 或空间 ID | 递归拉取子页面（默认深度 2，最大深度 3） |

```
对每个 iwiki 链接:
  1. 链接解析与分类:
     a) 单页面链接（URL 含 pageId 参数或 /pages/viewpage.action）:
        → 提取 pageId
        → 通过 iwiki MCP 工具拉取页面内容
        → 将 HTML/wiki 格式内容转换为 Markdown 纯文本
     b) 空间/目录链接（URL 含 /display/{spaceKey}/... 或用户提供空间 ID）:
        → 提取 spaceKey 或空间 ID
        → 通过 iwiki MCP 工具获取空间/目录下的子页面列表
        → 向用户展示页面树结构，确认拉取范围:
          ```
          📖 iwiki 空间: {spaceName}
          找到 {N} 个页面（深度 2）:
            ├─ 项目概述 (pageId: 111)
            ├─ 技术方案/
            │   ├─ 后端架构 (pageId: 222)
            │   └─ 前端架构 (pageId: 333)
            └─ 接口文档/
                ├─ 用户模块 API (pageId: 444)
                └─ 订单模块 API (pageId: 555)
          全部拉取？ [是/选择性拉取/调整深度]
          ```
        → 用户确认后逐页拉取内容
     c) 无法识别的链接格式:
        → 提示用户: "无法解析此 iwiki 链接，请提供页面 ID 或标准 URL"

  2. iwiki MCP 不可用处理（统一降级策略）:
     - MCP 配置缺失:
       → 调用 Skill 工具（skill: "mcp-setup-guide"） 引导配置
       → 配置完成后重试
     - MCP 已配置但调用失败:
       → 提示用户:
         "iwiki MCP 调用失败，请选择: "
         a) "重新配置 MCP"（触发 mcp-setup-guide）
         b) "我直接粘贴页面内容"
         c) "跳过 iwiki，继续其他导入"
     - 单页面拉取失败 → 记录失败的页面 ID，继续处理其他页面，最终汇总报告

  3. 拉取结果:
     - 每个页面的内容转换为 Markdown 文本
     - 存入 docs/knowledge-import/iwiki/ 目录:
       - {pageId}.md（清洗后的 Markdown 内容）
     - 记录到 inputSources.iwikiPages[]，每条包含:
       - pageId, title, spaceKey, content（Markdown 文本）
       - parentPageId（用于保留文档层级关系）
```

#### 2c. 本地文档解析（仅当 `localDocs` 非空时）

```
按文件扩展名自动选择解析方式:
  - .md / .txt        → 直接 Read
  - .pdf              → 调用 pdf skill（Skill 工具（skill: "pdf"））解析提取文本
  - .docx             → 调用 docx skill（Skill 工具（skill: "docx"））解析提取文本
  - .pptx             → 调用 pptx skill（Skill 工具（skill: "pptx"））解析提取文本
  - 其他扩展名         → 尝试 Read，失败则跳过并提示用户
```

#### 2d. 汇总输入清单

完成上述前置处理后，向用户展示**输入汇总确认**：

```
📋 已收集的项目信息：

✅ Git 仓库: 2 个已克隆
   - repo-a → /path/to/repo-a
   - repo-b → /path/to/repo-b
✅ TAPD 需求: 3 条已拉取
   - [#12345] 用户注册优化
   - [#12346] 商品搜索重构
   - [#12347] 支付流程改造
✅ iwiki 页面: 5 个已拉取
   - 项目概述 (pageId: 111)
   - 后端架构 (pageId: 222)
   - 前端架构 (pageId: 333)
   - 用户模块 API (pageId: 444)
   - 订单模块 API (pageId: 555)
✅ 本地文档: 4 个已解析
   - 项目设计文档.pdf (128 页)
   - API接口规范.docx (45 页)
   - 架构说明.md
   - 部署手册.txt
✅ 口述描述: 已记录（约 200 字）

确认开始导入？
  - "✅ 确认，开始导入"
  - "📝 补充更多材料"
  - "❌ 取消"
```

### Step 3：启动导入工作流编排

调用 `Skill 工具（skill: "workflow-orchestrator"）` 并传入特殊模式标识：

```
历史项目知识导入模式，请加载 phases/import-rules.md 并执行导入流程：

---
【导入模式】：knowledge-import
【输入来源汇总】：
  - gitRepos: {克隆后的本地路径列表，或空}
  - tapdStories: {拉取到的需求数据，或空}
  - iwikiPages: {拉取到的 iwiki 页面数据，或空}
  - parsedDocs: {解析后的文档内容，含文件路径和类型}
  - userDescription: {用户口述的文字，或空}
  - scanOnly: {是否仅扫描当前代码}
---
```

> **关键变化**：传入编排器的是**已处理过的输入**（git 已克隆、PDF/DOCX 已解析、TAPD 已拉取），@doc-collector 无需再关心输入源的获取方式，只需消费已结构化的内容。

> **统一知识仓库模式**：@knowledge-builder 不再生成 `knowledge-baseline.json` 和 `codebase-profile.json`。改为：
> - 业务知识（用户故事/业务规则/数据实体）→ 直接写入 `{knowledgeRepoLocalPath}/biz-wiki/{domain}/`（maturity: draft）
> - UI 模式 → 写入 `{knowledgeRepoLocalPath}/tech-wiki/ui-patterns/`（maturity: draft）
> - 编码约定 → 写入 `{knowledgeRepoLocalPath}/tech-wiki/conventions/`（maturity: draft）
> - 技术决策(ADR) → 写入 `{knowledgeRepoLocalPath}/tech-wiki/` 对应目录（maturity: draft）
> - 项目画像 → 写入 `{knowledgeRepoLocalPath}/project-profiles/{project}.yaml`
> - 所有写入通过 Git 分支工作流（同 archiver 阶段七的 Git 操作流程）

### Step 4：导入完成后的衔接

知识导入完成后，询问用户：

```
标题: ✅ 知识基线已建立
问题: 项目知识导入已完成，接下来您想：

选项:
  - "🚀 开始新需求开发 — 启动 /flow-run 工作流"
  - "📊 查看导入结果 — 查看知识基线报告"
  - "⏸️ 暂时到这里 — 稍后再开始开发"
```

- 用户选择"开始新需求开发" → 调用 `/flow-run`（此时 Step 0 会检测到知识库存在，直接进入 Step 1）
- 用户选择"查看导入结果" → 展示 `docs/knowledge-import/SUMMARY.md` 内容
- 用户选择"暂时到这里" → 结束

---

## 使用示例

### 示例 1：从 /flow-run 自动引导
```
用户：/flow-run
→ Step 0 检测到历史项目 → 用户选择"导入历史知识"
→ 自动进入 /flow-import 流程
```

### 示例 2：手动执行
```
用户：/flow-import
→ 直接进入知识导入流程，展示输入选项（多选）
```

### 示例 3：附带本地文档执行
```
用户：/flow-import @项目设计文档.pdf @API接口规范.docx @架构说明.md
→ 自动识别文件类型 → PDF 用 pdf skill 解析 → DOCX 用 docx skill 解析 → MD 直接读取
→ 解析完成后进入知识导入流程
```

### 示例 4：提供 Git 仓库 + TAPD 链接
```
用户：/flow-import
→ 用户选择 "Git 代码仓库" + "TAPD 需求链接"
→ 粘贴 git 地址: https://git.woa.com/org/project（HTTPS 格式）
→ AI 自动转换为 SSH: git@git.woa.com:org/project.git → 克隆成功
→ 粘贴 TAPD 链接: https://tapd.woa.com/tapd_fe/20088921/story/list?categoryId=1020088921002732893
→ AI 检查 MCP 配置 → 配置就绪 → 通过 TAPD MCP 按分类查询所有需求 → 展示需求清单供确认
→ 汇总确认后启动导入
```

### 示例 5：混合输入
```
用户：/flow-import @设计文档.pdf
→ 用户额外选择 "口述项目背景"
→ 用户输入: "这是一个电商项目，后端用 Java Spring Boot..."
→ PDF 解析 + 口述记录 → 汇总确认 → 启动导入
```

### 示例 6：TAPD MCP 未配置时的引导
```
用户：/flow-import
→ 用户选择 "TAPD 需求链接"
→ 粘贴 TAPD 链接
→ AI 检查 MCP 配置 → 发现 settings.json 中 mcpServers 未配置
→ 自动触发 mcp-setup-guide skill
→ 引导用户生成配置文件、申请 Token、回填 Token、验证连通性
→ 配置完成后继续 TAPD 需求拉取
```

---

## 注意事项

1. 导入流程**不创建 PRD**，不进入 ANALYSE_PRODUCT 等常规阶段
2. 导入产物存储在 `docs/knowledge-import/` 目录，与常规工作流隔离
3. 导入流程可多次执行（增量更新，不覆盖已有知识）
4. 导入产物的置信度初始为 0.5-0.6（标记为 imported，需通过后续工作流验证提升）
5. **支持的输入类型**：
   - **Git 代码仓库**：默认使用 SSH 协议克隆，自动将 HTTPS 地址转换为 SSH 格式（`https://{host}/{path}` → `git@{host}:{path}.git`），浅克隆（`--depth 1`）以节省时间和空间
   - **TAPD 需求链接**：默认通过 TAPD MCP 服务拉取（需先检查 MCP 配置），图片/附件操作通过 `tapd-toolkit` skill 的本地脚本完成。支持以下链接格式：
     - 单条需求：`https://tapd.woa.com/tapd_fe/{workspace_id}/stories/view/{story_id}`
     - 需求列表页：`https://tapd.woa.com/tapd_fe/{workspace_id}/story/list?categoryId={category_id}`
     - 迭代页面：`https://tapd.woa.com/tapd_fe/{workspace_id}/iterations/view/{iteration_id}`
     - 旧版链接：`https://www.tapd.cn/{workspace_id}/stories/view/{story_id}` 及 `https://www.tapd.cn/{workspace_id}/prong/stories/view/{story_id}`
   - **iwiki 页面**：默认通过 iwiki MCP 服务拉取（需先检查 MCP 配置）。支持以下链接格式：
     - 单页面：`https://iwiki.woa.com/pages/viewpage.action?pageId={pageId}`
     - 空间/目录：`https://iwiki.woa.com/display/{spaceKey}/...` 或直接提供空间 ID
     - 递归拉取子页面（默认深度 2，最大深度 3），拉取结果存入 `docs/knowledge-import/iwiki/`
   - **本地文档**：`.md`、`.txt`、`.pdf`（通过 pdf skill 解析）、`.docx`（通过 docx skill 解析）、`.pptx`（通过 pptx skill 解析）
   - **口述描述**：用户自由输入的文字
   - **当前代码扫描**：无需额外输入，直接分析当前项目
6. **MCP 优先原则**：TAPD 需求拉取默认使用 MCP 能力（`tapd_mcp_http`），iwiki 文档拉取默认使用 iwiki MCP 能力。使用前必须检查 `项目 .claude/settings.json 或全局 ~/.claude/settings.json 的 mcpServers 配置` 配置是否就绪。MCP 未配置时调用 `Skill 工具（skill: "mcp-setup-guide"）` 引导用户完成配置。`tapd-toolkit` skill 仅用于图片上传/附件操作等 MCP 不支持的本地文件操作场景
7. **直接执行原则**：Git 克隆默认 SSH 协议直接执行；TAPD MCP 调用使用 `POST` 方法 + `Accept: application/json, text/event-stream` 头 + JSON-RPC 2.0 格式，不做冗余的协议试探
8. **优雅降级**：任何外部能力不可用时（SSH 克隆失败、TAPD MCP 未配置或调用失败、PDF 解析异常），提供明确的替代方案（MCP 未配置→触发 mcp-setup-guide skill；MCP 调用失败→允许用户粘贴内容或跳过），不阻断整个导入流程

---

## 深度导入模式（可选增强）

> **设计来源**：借鉴 OMO (oh-my-openagent) 的分层 `AGENTS.md` 结构。IMPLEMENT 阶段的领域 Agent 通常需要加载全局文档（如 `_baseline-summary.json`、`knowledge-baseline.json`）才能理解项目上下文，这会消耗大量上下文窗口。目录级上下文文档可将全局信息**分布式预消化**，让每个 Agent 只读取当前工作目录的局部上下文。

### 触发条件

当用户在 Step 1 选择器中选择了 `🤖 直接扫描当前代码` 时，在 Step 2d（汇总输入清单确认）之后、Step 3（启动导入流程）之前，追加深度导入确认：

```
标题: 🔍 深度导入选项
问题: 是否生成目录级上下文文档？这将为每个核心模块目录生成独立的 CONTEXT.md，
让后续开发 Agent 只需读取局部上下文，减少上下文消耗。

选项:
  - "✅ 是，生成目录级上下文 — 适合大型项目（5+ 模块）"
  - "⏭️ 跳过 — 使用标准导入（适合中小型项目）"
```

- 用户选择"是" → 在 `inputSources` 中设置 `deepMode: true`，传入 Step 3
- 用户选择"跳过" → 标准导入流程

### 深度导入执行策略

当 `deepMode: true` 时，在 `@knowledge-builder` Agent 的标准知识基线构建完成后，追加以下步骤：

1. **扫描项目目录结构** — 识别核心模块目录：
   - 后端：扫描 `{backend-root}/` 下的子模块（含 `pom.xml` / `build.gradle` 的目录）
   - 前端：扫描 `{frontend-root}/` 下的子项目（含 `package.json` 的目录）
   - 每个核心目录生成一份 `CONTEXT.md`

2. **CONTEXT.md 内容结构**：

   ```markdown
   # {模块名称} 上下文

   > 本文件由 /flow-import 深度导入模式自动生成。
   > 生成时间：{ISO8601}
   > 置信度：0.5（imported，需通过后续工作流验证提升）

   ## 模块职责
   {一句话描述模块核心职责，基于代码画像推断}

   ## 核心类/文件
   | 文件 | 职责 | 说明 |
   |------|------|------|
   | {file1} | {description} | {notes} |
   | ... | ... | ... |

   ## 对外接口
   - {接口1}: {描述}
   - {接口2}: {描述}

   ## 依赖关系
   - 依赖: {上游模块列表}
   - 被依赖: {下游模块列表}

   ## 编码规范要点
   - {基于代码画像提取的规范，如命名风格、常用注解等}
   ```

3. **CONTEXT.md 保存路径** — 就近保存在对应模块目录下：
   ```
   {backend-root}/user-center/CONTEXT.md
   {backend-root}/product-center/CONTEXT.md
   {web-project}/CONTEXT.md
   {miniprogram-project}/CONTEXT.md
   ```

4. **IMPLEMENT 阶段集成** — 当 CONTEXT.md 存在时：
   - 领域 Agent 的 Prompt 注入提示：`优先读取当前领域目录下的 CONTEXT.md 获取局部上下文`
   - 仅在需要跨模块理解时才读取全局文档（`_baseline-summary.json`）
   - 预估可减少每个 Agent **15-25%** 的上下文窗口消耗

### 深度导入产物汇总

| 产物 | 位置 | 说明 |
|------|------|------|
| 标准产物 | `docs/knowledge-import/` | SUMMARY.md + knowledge-baseline.json + codebase-profile.json |
| 目录上下文 | `{module-dir}/CONTEXT.md` | 每个核心模块一份，就近存储 |

> **约束**：
> - CONTEXT.md 的置信度初始为 0.5（与其他导入知识一致），需通过后续工作流验证提升
> - CONTEXT.md 内容基于代码画像推断，非精确分析。在文件头部标注 `> 置信度：0.5（imported）` 提醒使用方
> - 不修改现有导入 Agent（@doc-collector、@codebase-profiler）的职责，CONTEXT.md 生成由 @knowledge-builder 在标准流程后追加
