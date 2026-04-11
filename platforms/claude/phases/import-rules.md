# 历史项目知识导入编排规则（按需加载）

> **加载时机**: 编排器在接收到 `knowledge-import` 模式标识时加载本文件。
> **注意**: 本规则描述的是独立于常规工作流（INIT → ... → ARCHIVE）的**导入专用流程**。

---

## 0. 导入工作流概述

导入工作流是一个**简化版编排**，不经过常规的 14 个阶段，而是执行 3 个导入步骤：

```
@doc-collector(s) + @doc-merger ──→ @codebase-profiler ──→ @knowledge-builder
 (文档收集，按文档数量自动并行) (代码画像) (知识基线构建)
```

**不修改 `phase-transitions.json`**。导入工作流有自己的状态管理，不占用常规阶段。

---

## 1. Agent 注册表

| Agent 文件 | 角色 | 说明 |
|------------|------|------|
| `agents/import-agents/doc-collector.md` | 项目文档收集与结构化专家 | 收集用户文档、README，按 7 维度分类压缩。分批并行时每个 batch 实例独立执行 |
| `agents/import-agents/codebase-profiler.md` | 代码库架构分析与画像专家 | 全景扫描 + 深度画像（业务模块/数据模型/依赖关系） |
| `agents/import-agents/knowledge-builder.md` | 知识标准化与基线构建专家 | 转化为标准归档格式，对齐 archiver + knowledge-evolution |

---

## 2. 调度模式

### 2.0 统一分批并行架构

> **核心设计**：文档收集阶段统一采用"分批并行 + 合并"架构，无论文档数量多少。每个文档来源组（TAPD/iwiki/本地文档/口述）各自作为一个独立 batch，由独立的 @doc-collector Agent 在独立上下文中处理。这消除了单 Agent 上下文膨胀的问题，也让架构保持统一——1 个文档就是 1 个 batch、1 个 Agent。

**分批策略**（编排器在 Step 3 发起 Agent 调用前执行）：
```
1. 按来源类型分组，每组为一个 batch:
 - batch-tapd: tapdStories[]（如非空）
 - batch-iwiki: iwikiPages[]（如非空）
 - batch-docs: parsedDocs[]（如非空）
 - batch-desc: userDescription（如非空，与最小文档组合并，或独立成组）
 - batch-git: Git 仓库 README/docs（如有克隆仓库，独立成组）

2. 大组继续拆分（每 batch ≤ 15 个文档）:
 - 如 TAPD 需求有 30 条 → batch-tapd-1 (1-15), batch-tapd-2 (16-30)
 - 如 iwiki 有 20 页 → batch-iwiki-1 (1-15), batch-iwiki-2 (16-20)
 - 本地文档、口述通常不需拆分

3. 生成 batchPlan:
 {
 "batches": [
 { "id": "batch-tapd-1", "source": "tapd", "docs": [...], "count": 15 },
 { "id": "batch-tapd-2", "source": "tapd", "docs": [...], "count": 15 },
 { "id": "batch-iwiki-1", "source": "iwiki", "docs": [...], "count": 12 },
 { "id": "batch-docs-1", "source": "local", "docs": [...], "count": 4 }
 ],
 "totalBatches": 4
 }

 特殊情况: 只有 1 个来源且文档 ≤ 15 → batchPlan 只有 1 个 batch，流程不变
```

### 2.1 优先模式：Agent 工具并行调度（分批并行 + 合并）

```
编排器发起 Agent 调用 →
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
无需清理
```

> **单 batch 场景**：当 batchPlan 只有 1 个 batch 时，该 batch Agent 直接产出 `_doc-collection.json`（而非 `_batch-{id}.json`），跳过 merger 阶段。

**调度标识格式**: `import-{项目名}`

**batch Agent Prompt 模板**（编排器注入）：

```
你是文档收集与结构化专家（批次 {batchId}），负责处理本批次分配的文档。

请读取你的 Agent 规范文件获取详细指令：
Agent 规范文件路径: {doc-collector.md 的绝对路径}

项目根目录: {项目根目录的绝对路径}
导入工作目录: {项目根目录}/docs/knowledge-import/

⚠️ 分批模式注意事项：
- 你只负责处理下方分配的文档，不要扫描项目目录或读取其他来源
- 产出文件名: _batch-{batchId}.json（如果是唯一 batch 则直接产出 _doc-collection.json）
- 产出格式与 _doc-collection.json 完全一致
- 你的 7 维度评估仅基于本批次文档，某些维度为 missing 是正常的

本批次分配的文档（共 {count} 个，来源: {source}）:
{文档列表，仅包含文件路径/ID 和类型，不内联文档内容}

完成后将产物写入指定路径，返回产物路径和关键摘要。"直接扫描当前代码"且无其他输入源时：

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
docs/knowledge-import/ # 导入专用目录
├── _doc-collection.json # @doc-collector 产出（中间产物）
├── codebase-profile.json # @codebase-profiler 产出
├── knowledge-baseline.json # @knowledge-builder 产出
├── SUMMARY.md # @knowledge-builder 产出
├── tapd-stories/ # @doc-collector 产出（Step 1.5，可选）
│ ├── _story-index.json # 需求-业务能力映射索引
│ ├── {story_id}.json # 原始需求 JSON（持久化留底）
│ └── {story_id}.md # 清洗后的可读 Markdown
└── iwiki/ # iwiki 页面拉取产出（可选）
 └── {pageId}.md # 清洗后的 Markdown 内容

docs/knowledge-base/ # 知识库（与 knowledge-evolution 共享）
├── index.json # @knowledge-builder 创建/更新
├── decisions/
│ └── DEC-IMP-*.md # @knowledge-builder 产出
├── guidelines/
│ └── GL-IMP-*.md # @knowledge-builder 产出
└── pitfalls/
 └── PIT-IMP-*.md # @knowledge-builder 产出

.claude/memory/{date}.md # @knowledge-builder 追加
```

---

## 4. 状态管理

导入工作流**不使用 `state.json`**（那是常规工作流的状态文件），而是通过产物文件的存在性来判断进度：

| 检查点 | 判定方式 | 说明 |
|--------|---------|------|
| T1 完成 | `docs/knowledge-import/_doc-collection.json` 存在 | 文档收集完成 |
| T2 完成 | `docs/knowledge-import/codebase-profile.json` 存在 | 代码画像完成 |
| T3 完成 | `docs/knowledge-import/knowledge-baseline.json` 存在 | 知识基线构建完成 |
| 全流程完成 | 以上三个文件均存在 | 可以开始常规工作流 |

**断点恢复**：如果导入流程中断，重新执行时：
1. 检查已有产物 → 跳过已完成的步骤
2. 从断点 Agent 继续执行
3. 不覆盖已有产物（增量模式）

---

## 5. 与常规工作流的衔接

导入完成后，常规工作流在 INIT 阶段会：
1. 检测 `docs/knowledge-import/knowledge-baseline.json` 是否存在
2. 如存在 → 将知识基线信息写入 `state.json` 的 `knowledgeContext` 字段
3. 后续 ANALYSE_PRODUCT、ANALYSE_TECH 等阶段通过 `knowledgeContext` 消费导入的知识

详见 `SKILL.md` §7.3 和 Phase 3 的知识消费协议。

---

## 6. 行为约束

### 编排器在导入模式下的必须做（DO）
- ✅ 确保 `docs/knowledge-import/` 目录存在后再启动 Agent
- ✅ 每个 Agent 完成后验证产出文件是否存在
- ✅ Agent 工具并行调度 创建失败时自动降级为 Task 模式
- ✅ 向用户展示每步的进度和关键发现

### 编排器在导入模式下的禁止做（DON'T）
- ❌ 禁止修改 `phase-transitions.json`
- ❌ 禁止创建 `docs/workflows/` 下的需求目录
- ❌ 禁止触发常规工作流的任何阶段
- ❌ 禁止在导入未完成时启动常规工作流
