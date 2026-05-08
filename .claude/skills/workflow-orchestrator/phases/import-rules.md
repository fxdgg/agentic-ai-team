# 历史项目知识导入编排规则（按需加载）

> **加载时机**: 编排器在接收到 `knowledge-import` 模式标识时加载本文件。
> **注意**: 本规则描述的是独立于常规工作流（INIT → ... → ARCHIVE）的**导入专用流程**。

> **多仓模式路径说明**：本文件中所有 `docs/knowledge-import/` 路径，编排器在运行时基于 `state.json` 的 `projectConfig.docsRoot` 解析为绝对路径（`{workspaceRoot}/{docsRoot}/docs/knowledge-import/`）。Agent Prompt 中注入的路径已为绝对路径，Agent 无需感知单仓/多仓差异。

---

## 0. 导入工作流概述

导入工作流是一个**简化版编排**，不经过常规的 14 个阶段，而是执行 3 个导入步骤：

```
@doc-collector(s) + @doc-merger  ──→  @codebase-profiler  ──→  @knowledge-builder
  (文档收集，按文档数量自动并行)       (代码画像)               (知识基线构建)
```

**不修改 `phase-transitions.json`**。导入工作流有自己的状态管理，不占用常规阶段。

**关键设计：索引驱动**。所有文档内容已在 `/flow-import` Step 2 中拉取并落盘到 `docs/knowledge-import/` 子目录。编排器和 Agent 通过索引文件获取文档路径，按需读取文件内容，**不在 prompt 中内联文档正文**。

---

## 1. Agent 注册表

| Agent 文件 | 角色 | 说明 |
|------------|------|------|
| `agents/import-agents/doc-collector.md` | 项目文档收集与结构化专家 | 通过索引文件定位文档，按需读取，按 7 维度分类压缩。分批并行时每个 batch 实例独立执行 |
| `agents/import-agents/codebase-profiler.md` | 代码库架构分析与画像专家 | 全景扫描 + 深度画像（业务模块/数据模型/依赖关系） |
| `agents/import-agents/knowledge-builder.md` | 知识标准化与基线构建专家 | 转化为标准归档格式，对齐 archiver + knowledge-evolution |

---

## 2. 调度模式

### 2.0 索引驱动的分批并行架构

> **核心设计**：编排器通过读取索引文件（`_story-index.json`/`_page-index.json`/`_doc-index.json`）获取文档 ID 列表和文件路径，生成 batchPlan 并持久化。每个 batch Agent 接收索引路径 + 分配的 ID 列表，自行通过 Read 工具读取文件内容。

**索引文件位置**（由 `/flow-import` Step 2 生成）：

| 来源 | 索引文件 | 文档目录 |
|------|---------|---------|
| TAPD | `docs/knowledge-import/tapd-stories/_story-index.json` | `tapd-stories/` |
| iwiki | `docs/knowledge-import/iwiki/_page-index.json` | `iwiki/` |
| 本地文档 | `docs/knowledge-import/local-docs/_doc-index.json` | `local-docs/` |
| 口述 | 无索引，直接引用 `description.md` | — |
| Git 仓库 | 无索引，使用 `import-state.json` 中的 `clonedPaths` | — |

**分批策略**（编排器在发起 Agent 调度前执行）：

```
1. 读取各索引文件获取文档列表:
   - _story-index.json → stories[] 中的 storyId 列表
   - _page-index.json → pages[] 中的 pageId 列表
   - _doc-index.json → docs[] 中的 fileName 列表
   - description.md → 检查是否存在
   - import-state.json → gitRepos.clonedPaths

2. 按来源类型分组，每组为一个 batch:
   - batch-tapd:   TAPD stories（如索引存在且非空）
   - batch-iwiki:  iwiki pages（如索引存在且非空）
   - batch-docs:   本地文档（如索引存在且非空）
   - batch-desc:   口述描述（如 description.md 存在，与最小文档组合并，或独立成组）
   - batch-git:    Git 仓库 README/docs（如有克隆仓库）

3. 大组继续拆分（每 batch ≤ 15 个文档）:
   - 如 TAPD 需求有 30 条 → batch-tapd-1 (1-15), batch-tapd-2 (16-30)
   - 如 iwiki 有 20 页 → batch-iwiki-1 (1-15), batch-iwiki-2 (16-20)

4. 生成并持久化 batchPlan 到 docs/knowledge-import/_batch-plan.json:
   {
     "batches": [
       { "id": "batch-tapd-1", "source": "tapd", "docIds": ["id1","id2",...], "count": 15,
         "indexPath": "docs/knowledge-import/tapd-stories/_story-index.json",
         "docDir": "docs/knowledge-import/tapd-stories/" },
       { "id": "batch-tapd-2", "source": "tapd", "docIds": [...], "count": 15, ... },
       { "id": "batch-iwiki-1", "source": "iwiki", "docIds": [...], "count": 12, ... },
       { "id": "batch-docs-1", "source": "local", "docIds": [...], "count": 4, ... }
     ],
     "totalBatches": 4,
     "createdAt": "ISO-8601"
   }

   特殊情况: 只有 1 个来源且文档 ≤ 15 → batchPlan 只有 1 个 batch
```

### 2.1 优先模式：Parallel Agent 调度（分批并行 + 合并）

```
编排器发起 Agent 调度 →
  Phase 1 — 文档收集（并行）:
    T1-batch-1(@doc-collector) ──┐
    T1-batch-2(@doc-collector) ──┼─→ 各自产出 _batch-{id}.json（并行执行）
    T1-batch-N(@doc-collector) ──┘
         ↓ 全部完成后
  Phase 2 — 文档合并:
    T1-merger(@doc-merger) → 合并所有 _batch-{id}.json → 产出 _doc-collection.json
         ↓
  Phase 3 — 代码画像:
    T2(@codebase-profiler) → 消费 _doc-collection.json, 产出 codebase-profile.json
         ↓
  Phase 4 — 知识基线:
    T3(@knowledge-builder) → 消费前两步产物, 产出知识基线 + SUMMARY + 知识库条目
         ↓
（Agent 工具完成后自动释放）
```

> **单 batch 场景**：当 batchPlan 只有 1 个 batch 时，该 batch Agent 直接产出 `_doc-collection.json`（而非 `_batch-{id}.json`），跳过 merger 阶段。

**团队命名格式**: `import-{项目名}`

**batch 成员 Prompt 模板**（编排器注入）：

```
你是文档收集与结构化专家（批次 {batchId}），负责处理本批次分配的文档。

请读取你的 Agent 规范文件获取详细指令：
Agent 规范文件路径: {doc-collector.md 的绝对路径}

项目根目录: {项目根目录的绝对路径}
导入工作目录: {项目根目录}/docs/knowledge-import/

⚠️ 索引驱动模式：
- 你只负责处理下方分配的文档 ID，通过索引文件的 filePath 字段定位并 Read 文件内容
- 产出文件名: _batch-{batchId}.json（如果是唯一 batch 则直接产出 _doc-collection.json）
- 产出格式与 _doc-collection.json 完全一致
- 你的 7 维度评估仅基于本批次文档，某些维度为 missing 是正常的

本批次分配（共 {count} 个，来源: {source}）:
  索引文件: {索引文件的绝对路径}
  分配的 ID: [{id1}, {id2}, {id3}, ...]
  文档目录: {文档目录的绝对路径}

⚠️ 字符预算:
  - 单个文档 Read 上限: 5000 字符（超出部分截断，标注 [TRUNCATED]）
  - 本批次总 Read 上限: 100K 字符
  - 如文档有 .md 和 .json 两个版本，优先读取 .md（更精简）

完成后，请向领导发送消息汇报完成状态。
```

**merger 成员 Prompt 模板**（仅当 batch 数 > 1 时创建）：

```
你是文档合并专家，负责将多个批次的文档收集结果合并为最终的 _doc-collection.json。

项目根目录: {项目根目录的绝对路径}
导入工作目录: {项目根目录}/docs/knowledge-import/

需要合并的批次产物:
{batch 产物路径列表，如: _batch-tapd-1.json, _batch-tapd-2.json, _batch-iwiki-1.json}

合并规则:
1. 读取所有 _batch-{id}.json 文件
2. projectName: 取出现频率最高的，或从最大批次中提取
3. documentSources: 合并所有批次的 documentSources 数组（去重）
4. extractedInfo 的 7 个维度: 
   - 对每个维度，合并所有批次的 content（拼接后压缩到 500 字以内）
   - status 取最佳值: sufficient > partial > missing
   - 如果多个批次对同一维度有互补信息 → 合并后提升 status
5. informationCoverage: 重新统计合并后的结果
6. askTriggered: false（合并阶段不追问）

产出: docs/knowledge-import/_doc-collection.json

完成后，请向领导发送消息汇报完成状态，包含:
- 合并了几个批次
- 各维度的最终状态
- 是否发现批次间的矛盾信息
```

**后续阶段成员 Prompt 模板**（T2/T3，与文档收集阶段解耦）：

```
你是 {角色名}，负责历史项目知识导入的 {职责描述}。

请读取你的 Agent 规范文件获取详细指令：
Agent 规范文件路径: {Agent .md 文件的绝对路径}

项目根目录: {项目根目录的绝对路径}
导入工作目录: {项目根目录}/docs/knowledge-import/

前置产物路径:
- _doc-collection.json: {绝对路径}
- tapd-stories/_story-index.json: {绝对路径，如存在}

{仅 T3} 
- codebase-profile.json: {绝对路径}

{仅 T2(@codebase-profiler) 且有克隆仓库} 额外扫描路径:
- 克隆仓库路径: {clonedPaths 列表}

完成后，请向领导发送消息汇报完成状态，包含：
- 产出文件列表
- 关键发现摘要
- 是否存在问题
```

### 2.2 降级模式：Task 串行

当 Agent 调用失败时，降级为 Agent 工具串行调用：

```
Task 1: 调用 @doc-collector（如果有用户文档输入）
Task 2: 调用 @codebase-profiler
Task 3: 调用 @knowledge-builder
```

每个 Task 的 Prompt 中注入对应 Agent 文件路径 + 索引文件路径，由 Task 自行读取规范和文档。

### 2.3 特殊情况：跳过 @doc-collector

当用户在 `/flow-import` Step 1 选择"直接扫描当前代码"且无其他输入源时：

```
跳过 T1 → 直接创建空的 _doc-collection.json:
{
  "projectName": "（待代码画像识别）",
  "importedAt": "ISO-8601",
  "documentSources": [],
  "extractedInfo": {
    "projectBackground": { "status": "missing", "content": "" },
    "techStack": { "status": "missing", "content": "" },
    "moduleStructure": { "status": "missing", "content": "" },
    "businessDomain": { "status": "missing", "content": "" },
    "apiConventions": { "status": "missing", "content": "" },
    "deploymentInfo": { "status": "missing", "content": "" },
    "teamConventions": { "status": "missing", "content": "" },
    "tapdDeepCoverage": { "status": "skipped", "content": "", "storyIndexPath": null }
  },
  "informationCoverage": { "sufficient": 0, "partial": 0, "missing": 7 },
  "askTriggered": false,
  "askCount": 0
}

然后启动 T2(@codebase-profiler) → T3(@knowledge-builder)
```

---

## 3. 产物目录结构

```
docs/knowledge-import/                    # 导入专用目录
├── import-state.json                    # 导入状态持久化（/flow-import 管理）
├── _batch-plan.json                     # 编排器 batch 调度计划（中间产物）
├── _doc-collection.json                 # @doc-collector 产出（中间产物）
├── codebase-profile.json                # @codebase-profiler 产出
├── knowledge-baseline.json              # @knowledge-builder 产出
├── SUMMARY.md                           # @knowledge-builder 产出
├── description.md                       # 口述内容落盘（/flow-import Step 2 生成）
├── tapd-stories/                        # TAPD 需求落盘目录（/flow-import Step 2 生成）
│   ├── _story-index.json               # 需求轻量索引
│   ├── {story_id}.json                 # 原始需求 JSON
│   └── {story_id}.md                   # 清洗后 Markdown（≤3000字）
├── iwiki/                               # iwiki 页面落盘目录（/flow-import Step 2 生成）
│   ├── _page-index.json                # 页面索引
│   └── {pageId}.md                     # 清洗后 Markdown（≤5000字）
└── local-docs/                          # 本地文档落盘目录（/flow-import Step 2 生成）
    ├── _doc-index.json                  # 文档索引
    └── {filename}.md                    # 解析后 Markdown

docs/knowledge-base/                      # 知识库（与 knowledge-evolution 共享）
├── index.json
├── decisions/
│   └── DEC-IMP-*.md
├── guidelines/
│   └── GL-IMP-*.md
└── pitfalls/
    └── PIT-IMP-*.md
```

---

## 4. 状态管理

导入工作流使用**双层状态管理**：

### 4.1 导入级状态：import-state.json

由 `/flow-import` 管理，追踪拉取进度和阶段流转。见 `/flow-import` 的状态持久化章节。

编排器在导入模式下：
- 读取 `import-state.json` 获取输入来源信息
- 更新 `orchestrateStatus` 字段标记编排进度
- 不覆盖 `fetchProgress` 中已有的拉取状态

### 4.2 编排级状态：产物文件存在性

| 检查点 | 判定方式 | 说明 |
|--------|---------|------|
| batchPlan 就绪 | `_batch-plan.json` 存在 | batch 调度计划已生成 |
| T1 完成 | `_doc-collection.json` 存在 | 文档收集完成 |
| T2 完成 | `codebase-profile.json` 存在 | 代码画像完成 |
| T3 完成 | `knowledge-baseline.json` 存在 | 知识基线构建完成 |
| 全流程完成 | T1+T2+T3 均完成 | 可以开始常规工作流 |

**断点恢复**：如果编排流程中断，重新执行时：
1. 检查 `_batch-plan.json` → 如存在，跳过 batchPlan 生成
2. 检查各产物文件 → 跳过已完成的步骤
3. 从断点 Agent 继续执行

---

## 5. 与常规工作流的衔接

导入完成后，常规工作流在 INIT 阶段会：
1. 检测 `docs/knowledge-import/knowledge-baseline.json` 是否存在
2. 如存在 → 将知识基线信息写入 `state.json` 的 `knowledgeContext` 字段
3. 后续阶段通过 `knowledgeContext` 消费导入的知识

---

## 6. 行为约束

### 编排器在导入模式下的必须做（DO）
- ✅ 通过索引文件获取文档列表，不在 prompt 中内联文档内容
- ✅ 持久化 batchPlan 到 `_batch-plan.json`
- ✅ 确保 `docs/knowledge-import/` 目录存在后再启动 Agent
- ✅ 每个 Agent 完成后验证产出文件是否存在
- ✅ Agent 调用失败时自动降级为 Task 模式
- ✅ 向用户展示每步的进度和关键发现
- ✅ 更新 import-state.json 的 orchestrateStatus

### 编排器在导入模式下的禁止做（DON'T）
- ❌ 禁止在 Agent prompt 中内联文档正文（必须通过索引路径让 Agent 自行读取）
- ❌ 禁止修改 `phase-transitions.json`
- ❌ 禁止创建 `docs/workflows/` 下的需求目录
- ❌ 禁止触发常规工作流的任何阶段
- ❌ 禁止在导入未完成时启动常规工作流
