# ANALYSE_PRODUCT 阶段调度规则（按需加载）

> **加载时机**: 编排器进入 ANALYSE_PRODUCT 阶段时加载本文件。

---

## 0. 三级降级调度策略

ANALYSE_PRODUCT 阶段支持**三级降级调度**，编排器按优先级逐级尝试：

| 级别 | 模式 | 触发条件 | 说明 |
|------|------|---------|------|
| **Level 1** | Agent 工具并行调度模式（默认） | 始终优先尝试 | 四 Agent异步协作，独立上下文窗口隔离 PRD/基线产物膨胀 |
| **Level 2** | Task 串行流水线 | Level 1 创建失败 / 超时无响应 | 2-3 个同步 Task 串行调用，复用子 Agent 规范，中间产物传递 |
| **Level 3** | 编排器直接执行 | Level 2 执行失败 | 编排器自身上下文内，参考 `agents/product-analyst.md` 规范直接生成产物 |

> **设计意图**:
> - **Level 1 (Agent 工具并行调度)** 的核心价值是**上下文防火墙**。迭代需求需要同时管理"当前 PRD + 前一版 PRD + 前一版分析产物 + 分析数据"等多重上下文（2000-3000 行），单体窗口在后半段分析精度严重下降。通过将前一版产物阅读隔离在 @baseline-differ 的独立窗口中，后续 Agent只消费结构化摘要（~10-15KB），分析精度显著提升。
> - **Level 2 (Task 串行流水线)** 解决 Agent 工具并行调度 异步机制不可靠的问题。同步 Task 调用保证可靠性，同时通过拆分为 2-3 个 Task 并借助中间产物文件传递数据，避免单个 Task 上下文窗口被撑爆。每个 Task Agent 自行 `Read 工具` 读取子 Agent 规范文件（而非注入完整内容到 Prompt），控制 Prompt 大小。
> - **Level 3 (编排器直接执行)** 是最终兜底。编排器在自身上下文中参考 `agents/product-analyst.md` 的核心流程直接分析，产出精度最低但保证流程不阻断。

### 0.1 降级决策流程

```
编排器执行流程：

1. 读取 state.json，检查是否有断点恢复信息
2. 如果 analyseProductMode 已有值且非空：
  a) "parallel-agent" → 进入 §2（Agent 工具并行调度 断点恢复）
  b) "task-pipeline" → 进入 §3（Task 流水线断点恢复）
  c) "fallback" → 进入 §4（编排器直接执行恢复）
  d) "task"（兼容旧值）→ 进入 §4（按 Level 3 处理）
3. 如果 analyseProductMode 为空或字段不存在：
  → 尝试 Level 1（§2），失败或超时则降级到 Level 2（§3），再失败降级到 Level 3（§4）
```

---

## 1. 四 Agent 协作模型（Level 1 & Level 2 共享）

```
@product-collector ──→ @product-extractor ──→ @quality-assessor
    │ (并行)          ↑
@baseline-differ ────────────────┘ (仅迭代需求调度)
    │ (并行)          ↑
@visual-analyst  ────────────────┘ (仅含视觉附件时调度)
```

**流程说明**:
- @product-collector 和 @baseline-differ **可以并行执行**（differ 依赖 collector 的中间产物中的 `baseline` 路径信息，但 collector 先完成后两者可同步推进后续工作）
- @visual-analyst 与 @baseline-differ **并行执行**（analyst 依赖 collector 中间产物中的图片文件列表）
- 实际依赖关系：@baseline-differ 需要等待 @product-collector 完成后才能读取 `_product-collection.json` 中的基线路径
- @visual-analyst 需要等待 @product-collector 完成后才能读取 `_product-collection.json` 中的图片附件列表
- @product-extractor 需要等待 @product-collector 完成；如果是迭代需求，还需等待 @baseline-differ 完成；如果含视觉附件，还需等待 @visual-analyst 完成
- @quality-assessor 需要等待 @product-extractor 完成

### 1.1 Agent 注册表

| Agent 名 | Agent 文件 | 职责 | 上下文特征 | 调度条件 |
|--------|-----------|------|-----------|----------|
| `@product-collector` | `agents/product-analysts/product-collector.md` | 读取 PRD + 迭代判定 + 信息评估 + 条件追问 + PRD 摘要 | **轻量** ~30KB，仅读取 state.json 和 PRD | 始终调度 |
| `@baseline-differ` | `agents/product-analysts/baseline-differ.md` | 读取前一版产物 + 基线提取 + 增量对比 + 移除判定 | **中等** ~60KB，独立隔离前一版上下文 | **仅迭代需求** |
| `@visual-analyst` | 无独立 Agent 文件（内联规范） | 读取图片文件 + 结构化视觉分析 + 保存 JSON 产物 | **中等** ~50KB，图片分析消耗较高 | **仅 PRD 含视觉附件** |
| `@product-extractor` | `agents/product-analysts/product-extractor.md` | 结构化提取用户故事 + 规则 + 实体 + 验收标准 + clarify | **中等** ~50KB，消费中间产物 | 始终调度 |
| `@quality-assessor` | `agents/product-analysts/quality-assessor.md` | ISO/IEC 25010 评分 + 风险排查 + Kano 分类 + 报告整合 | **轻量** ~40KB，消费中间产物 | 始终调度 |

### 1.2 任务依赖关系

#### 全新需求（三 Agent串行）

```
任务列表：
1. [T1] 需求信息收集 — 分配给 @product-collector — 无依赖
2. [T2] 需求结构化提取 — 分配给 @product-extractor — 依赖任务 1
3. [T3] 质量评估与报告输出 — 分配给 @quality-assessor — 依赖任务 2
```

#### 全新需求 + 含视觉附件（四 Agent，T1→T1.5 串行，T2 等待两者）

```
任务列表：
1. [T1] 需求信息收集 — 分配给 @product-collector — 无依赖
2. [T1.5] 视觉分析 — 分配给 @visual-analyst — 依赖任务 1（需读取 _product-collection.json 中的图片列表）
3. [T2] 需求结构化提取 — 分配给 @product-extractor — 依赖任务 1 和任务 1.5
4. [T3] 质量评估与报告输出 — 分配给 @quality-assessor — 依赖任务 2
```

#### 迭代需求（四 Agent，T1→T2 串行，T2 完成后 T3 和 T4 的调度取决于 T2 结果）

```
任务列表：
1. [T1] 需求信息收集 — 分配给 @product-collector — 无依赖
2. [T2] 基线对比分析 — 分配给 @baseline-differ — 依赖任务 1
3. [T3] 需求结构化提取 — 分配给 @product-extractor — 依赖任务 1 和任务 2
4. [T4] 质量评估与报告输出 — 分配给 @quality-assessor — 依赖任务 3
```

#### 迭代需求 + 含视觉附件（五 Agent，T2 和 T1.5 并行执行）

```
任务列表：
1. [T1] 需求信息收集 — 分配给 @product-collector — 无依赖
2. [T1.5] 视觉分析 — 分配给 @visual-analyst — 依赖任务 1（与 T2 并行）
3. [T2] 基线对比分析 — 分配给 @baseline-differ — 依赖任务 1（与 T1.5 并行）
4. [T3] 需求结构化提取 — 分配给 @product-extractor — 依赖任务 1、任务 1.5 和任务 2
5. [T4] 质量评估与报告输出 — 分配给 @quality-assessor — 依赖任务 3
```

> **注意**: @baseline-differ 的调度条件取决于 @product-collector 的 `_product-collection.json` 中的 `iterationType` 字段。@visual-analyst 的调度条件取决于 `_product-collection.json` 中是否包含图片附件信息（`visualAttachments` 字段非空）。编排器收到 @product-collector 的完成消息后，根据 `iterationType` 和 `visualAttachments` 动态决定调度组合。

**依赖传递机制**: 通过**文件系统**（中间产物文件），而非对话历史。各 Agent通过读取前置 Agent 写入的文件获取上下文。

### 1.3 中间产物（上下文防火墙）

| 中间产物 | 写入方 | 读取方 | 说明 |
|---------|--------|--------|------|
| `analysis/_product-collection.json` | @product-collector | @baseline-differ, @product-extractor, @quality-assessor | 需求信息摘要（含迭代判定、基线路径、PRD 章节摘要） |
| `analysis/_baseline-summary.json` | @baseline-differ | @product-extractor, @quality-assessor | 基线对比结构化结论（仅迭代需求） |
| `analysis/_extraction-result.json` | @product-extractor | @quality-assessor | 结构化分析数据（用户故事、规则、实体等） |
| `analysis/_visual-analysis.json` | @visual-analyst | @product-extractor, @quality-assessor | 结构化视觉分析产物（组件树+交互推断+样式指南，仅含视觉附件时产出） |

> **核心设计**: `_product-collection.json` 将 PRD 原文（通常 500-700 行）压缩为各章节结构化摘要（~100-150 行等效）；`_baseline-summary.json` 将前一版完整产物（~500 行×2 份）压缩为结构化对比结论（~10-15KB）。信息密度提升 5-10 倍，后续 Agent的上下文因此保持干净。

### 1.4 最终产物

| 产物 | 写入方 | 说明 |
|------|--------|------|
| `analysis/product-requirements.md` | @quality-assessor | 最终产品需求分析报告 |
| `analysis/product-clarify.json` | @quality-assessor | 待澄清问题（条件产出） |

---

## 2. Level 1: Agent 工具并行调度模式调度规则

### 知识基线注入协议（仅当 `knowledgeContext.baselineAvailable = true`）

> **加载条件**: 编排器在创建 Agent 工具并行调度 前，先读取 `state.json` 检查 `knowledgeContext.baselineAvailable` 字段。

当项目有历史知识导入记录时，编排器在`@product-collector` 的 Agent Prompt 中**额外注入**以下段落：

```
【历史知识基线参考】
本项目有历史知识导入记录，以下是功能域概要供参考：
- 功能关键词: {knowledgeContext.importedKeywords 用逗号分隔}
- 知识基线路径: {knowledgeContext.baselinePath 的绝对路径}
- TAPD 需求索引: {knowledgeContext.storyIndexPath 的绝对路径，如为 null 则输出 "不可用"}

请在执行迭代类型判定时，考虑以下额外信号：
- 知识基线中的 baselineUserStories 可作为基线版本参考
- 导入的功能关键词可辅助判断当前需求是否与已有功能重叠
- （如 TAPD 需求索引可用）读取 _story-index.json 中的 capabilitySummary，按业务能力域匹配当前需求涉及的能力域，获取历史需求迭代脉络
- ⚠️ 注意：导入知识的置信度为 0.5-0.6（TAPD 驱动为 0.65），仅供参考不作为确定依据
```

**对 @product-collector 的影响**：
- 迭代类型判定新增第 4 层信号：`知识基线中存在同功能域记录`（置信度: 低，权重低于其他 3 层信号）
- `_product-collection.json` 新增可选字段 `knowledgeBaselineRef`（基线引用路径，供下游感知）
- 不改变现有的判定逻辑优先级，知识基线仅作为辅助参考

### 2.1 调度发起

编排器按以下规则发起 Agent 调用。

**创建指令模板**:

```
发起 Agent 调用，按以下规则调度：

调度任务：基于 PRD 文档进行产品需求分析，产出结构化的产品需求分析报告。
调度采用四 Agent协作模式（全新需求调度 3 个，迭代需求调度 4 个），通过文件系统传递中间产物。

Agent 调用列表：
{见 §2.2 Agent Prompt 规则}

任务依赖关系（由编排器根据迭代类型判定动态决定）：
1. [T1] 需求信息收集 — @product-collector — 无依赖
2. [T2] 基线对比分析 — @baseline-differ — 依赖 T1（仅迭代需求调度）
3. [T3] 需求结构化提取 — @product-extractor — 依赖 T1（全新）/ 依赖 T1+T2（迭代）
4. [T4] 质量评估与报告输出 — @quality-assessor — 依赖 T3
```

### 2.2 Agent Prompt 规则

为各 Agent生成独立的 Prompt。Agent Prompt 必须包含充分的上下文（因为 Agent **不会继承编排器的对话历史**）：

#### Agent 1: @product-collector（始终调度）

```
使用 Agent 工具调度 @product-collector（同步调用）：

Agent Prompt：

"你是一位资深需求信息收集专家，负责 PRD 文档的初始读取、迭代类型判定和信息评估。

你的工作职责：
1. 读取 Agent 行为规范：{agents/product-analysts/product-collector.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取 PRD 文档：{prdSource 指向的文件的绝对路径}
4. 读取澄清 Schema：{references/clarify-schema.json 的绝对路径}
5. 严格按照 Agent 规范执行迭代判定、信息评估和 PRD 摘要生成
6. 将收集结论写入：{analysis/_product-collection.json 的绝对路径}

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

#### Agent 2: @baseline-differ（仅迭代需求调度）

```
使用 Agent 工具调度 @baseline-differ（同步调用）：

Agent Prompt：

"你是一位资深需求变更分析专家，负责前一版产物的基线提取和增量对比。

你的工作职责：
1. 读取 Agent 行为规范：{agents/product-analysts/baseline-differ.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 读取前一版分析产物：{baseline.analysisPath 的绝对路径}
4. 读取前一版 PRD：{baseline.prdPath 的绝对路径}
5. 读取当前 PRD：{prdSource 指向的文件的绝对路径}
6. 严格按照 Agent 规范执行基线数据提取、增量对比、移除判定三层策略
7. 将对比结论写入：{analysis/_baseline-summary.json 的绝对路径}

⚠️ 重要：前一版产物和 PRD 的完整内容仅在你的上下文中处理，后续 Agent只消费你的结构化摘要。

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

> **调度时机**: 编排器在收到 @product-collector 完成消息后，检查 `_product-collection.json` 中的 `iterationType`。如为 `incremental` 且 `iterationDetection.userConfirmed` 为 `true`，则调度本 Agent。如为 `new`，跳过本 Agent直接调度 @product-extractor。

#### Agent 2.5: @visual-analyst（仅含视觉附件时调度）

```
使用 Agent 工具调度 @visual-analyst（同步调用）：

Agent Prompt：

"你是一位资深视觉分析专家，负责对 PRD 中的图片附件（设计稿、原型图、截图等）进行结构化视觉分析。

你的工作职责：
1. 读取视觉分析协议规范：{rules/visual-analysis-protocol.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 从中间产物的 `visualAttachments` 字段获取图片文件列表
4. 逐张读取图片文件，严格按照视觉分析协议执行：
  a) 图片分类（UI 设计稿/原型图/架构图/流程图/数据表/截图/手绘草图）
  b) 结构化分析（组件树提取/交互行为推断/样式指南提取/架构关系提取）
  c) 多图对比分析（如存在现状截图 + 设计稿等对应关系）
5. 将视觉分析结论写入：{analysis/_visual-analysis.json 的绝对路径}

产出格式须遵循 visual-analysis-protocol.md §5 的 JSON 结构，包含：
- images[]: 每张图片的类型、置信度、分析结果
- comparison: 多图对比结论（如适用）
- implementationNotes: 实现注意事项
- uncertainties: 不确定项（需用户或后续阶段确认）

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

⚠️ 重要：
- 你严禁读取原始 PRD 文件全文，只通过中间产物获取图片文件列表
- 图片分析结果必须结构化，不做主观评价
- 不确定的推断必须在 uncertainties 中标注，不做无根据的臆测

完成后将产物写入指定路径，返回产物路径和关键摘要（含分析的图片数量和关键发现）。"
```

> **调度时机**: 编排器在收到 @product-collector 完成消息后，检查 `_product-collection.json` 中是否存在 `visualAttachments` 字段且非空数组。如果存在视觉附件，则调度本 Agent（与 @baseline-differ 并行）。如果无视觉附件，跳过本 Agent。

#### Agent 3: @product-extractor（始终调度）

```
使用 Agent 工具调度 @product-extractor（同步调用）：

Agent Prompt：

"你是一位资深需求结构化提取专家，负责将需求信息转化为标准化分析数据。

你的工作职责：
1. 读取 Agent 行为规范：{agents/product-analysts/product-extractor.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 条件读取基线对比中间产物：{analysis/_baseline-summary.json 的绝对路径}（仅迭代需求时存在）
4. 条件读取视觉分析中间产物：{analysis/_visual-analysis.json 的绝对路径}（仅含视觉附件时存在）
5. 读取澄清 Schema：{references/clarify-schema.json 的绝对路径}
6. 严格按照 Agent 规范提取用户故事、业务规则、数据实体、验收标准、不明确项
7. 迭代需求时，消费基线对比数据执行增量标注
8. 含视觉附件时，将视觉分析中的组件树和交互推断融入用户故事和验收标准
9. 将提取结论写入：{analysis/_extraction-result.json 的绝对路径}

⚠️ 重要：你严禁读取原始 PRD 文件和前一版产物文件。所有信息来自中间产物（上下文防火墙）。

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
迭代类型：{iterationType}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

#### Agent 4: @quality-assessor（始终调度）

```
使用 Agent 工具调度 @quality-assessor（同步调用）：

Agent Prompt：

"你是一位资深质量与风险评估专家，负责质量评分、风险评估和最终报告整合。

你的工作职责：
1. 读取 Agent 行为规范：{agents/product-analysts/quality-assessor.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 读取提取专家中间产物：{analysis/_extraction-result.json 的绝对路径}
4. 条件读取基线对比中间产物：{analysis/_baseline-summary.json 的绝对路径}（仅迭代需求时存在）
5. 读取澄清 Schema：{references/clarify-schema.json 的绝对路径}
6. 严格按照 Agent 规范执行 ISO/IEC 25010 评分、风险排查、Kano 分类
7. 整合所有数据，按报告模板输出最终报告
8. 将报告写入：{analysis/product-requirements.md 的绝对路径}
9. 如有待澄清问题，写入：{analysis/product-clarify.json 的绝对路径}

⚠️ 重要：你严禁读取原始 PRD 文件和前一版产物文件。所有信息来自中间产物。

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
迭代类型：{iterationType}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

> **关键**: 所有 Prompt 中的路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析）。

### 2.3 编排器的行为约束

在 Agent 工具并行调度模式下，编排器作为 编排器：

| ✅ 必须做 | ❌ 禁止做 |
|-----------|----------|
| 发起 Agent 调用并分配任务 | 直接执行任何分析/评估工作 |
| Agent 同步返回后检查产物 | 在 Agent 工作时中断 |
| Agent 返回后检查产物 | 替代 Agent 完成未完成的任务 |
| 根据 collector 的迭代判定结果决定是否调度 differ | 向 Agent 传递其他 Agent 的完整对话 |
| 汇总结果并更新 state.json | 忽略 Agent 的错误/风险汇报 |
| 处理 @product-collector 上报的追问需求 | 跳过迭代类型确认直接判定 |
| 监控超时并执行自动降级（§2.7） | 在超时降级前不发催促消息 |

### 2.4 动态调度流程（编排器视角）

```
编排器执行流程：

1. 发起 Agent 调用 → 发起 @product-collector Agent 调用 → → 等待完成
2. 接收 @product-collector 完成消息 → 读取 _product-collection.json
3. 检查 iterationType 和 visualAttachments，确定调度组合:
  a) 如果 iterationType = "incremental" 且 userConfirmed = true:
   → 发起 @baseline-differ Agent 调用 → → 等待完成
  b) 如果 iterationType = "new":
   → 跳过 @baseline-differ
  c) 如果 visualAttachments 非空:
   → 发起 @visual-analyst Agent 调用 → 
   → 与 @baseline-differ（如已调度）并行等待
  d) 如果 visualAttachments 为空或不存在:
   → 跳过 @visual-analyst
  e) 等待所有已调度的并行 Agent（@baseline-differ / @visual-analyst）完成
4. 发起 @product-extractor Agent 调用 → → 等待完成
5. 接收 @product-extractor 完成消息
6. 发起 @quality-assessor Agent 调用 → → 等待完成
7. 接收 @quality-assessor 完成消息 → 进入产物检查流程（§2.6）
```

### 2.5 阻断问题处理流程

#### @product-collector 的追问处理

@product-collector 可能通过 AskUserQuestion 工具直接与用户交互（迭代确认、信息补充），无需编排器中转。Agent 自行管理追问配额（上限 10 个问题）。

#### @baseline-differ 的异常处理

当 @baseline-differ 遇到前一版产物不存在时，不阻断流程——在中间产物中标记 `baselineAvailable: false`，后续 Agent以全新需求模式处理。

### 2.6 调度完成与产物检查

所有 Agent完成任务后，编排器执行：

```
1. 逐一确认每个Agent 的返回结果
2. 检查所有产物文件是否存在：
  - analysis/_product-collection.json（中间产物）
  - analysis/_baseline-summary.json（中间产物，仅迭代需求）
  - analysis/_visual-analysis.json（中间产物，仅含视觉附件时）
  - analysis/_extraction-result.json（中间产物）
  - analysis/product-requirements.md（最终报告）
  - analysis/product-clarify.json（可选）
3. 读取最终报告的 front-matter 获取 qualityGate 和 qualityScore
4. 汇总所有 Agent的风险项
5. 更新 state.json:
  - analyseProductMode 字段设为 "parallel-agent"
  - analyseProductTeam 记录调度信息
6. （Agent 工具调用完成即自动释放资源）
7. 恢复正常模式，进入"总结确认"步骤
```

### 2.7 超时与降级

**超时与降级**:
Agent 工具为同步调用，无需手动超时检测。
- 调用成功 → 检查产物完整性 → 继续下一步
- 调用失败/返回空结果 → 检查已落盘的中间产物 → 决定降级策略

#### 降级触发条件

| 触发条件 | 降级目标 |
|---------|---------|
| Agent 调用失败 | Level 2 |
| 第一个 Agent（@product-collector）返回空结果且无中间产物 | Level 2 |
| 任一后续 Agent 返回空结果且无中间产物 | Level 2（从该 Agent 对应的 Task 步骤开始） |

#### 降级执行

```
降级执行流程：

1. 记录降级原因到控制台日志
2. 检查已存在的中间产物文件，确定 Level 2 的起始步骤
3. 更新 state.json: analyseProductMode = "task-pipeline"
4. 跳转到 §3（Level 2 Task 串行流水线），从断点继续
```


---

## 3. Level 2: Task 串行流水线

当 Level 1 失败或超时后，编排器使用同步 Agent 工具调用，将分析拆分为 2-3 个串行 Task。每个 Task 复用 `agents/product-analysts/` 下的子 Agent 规范，通过中间产物文件传递上下文。

### 3.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **规范文件引用，非注入** | Task Prompt 中只给出 Agent 规范文件的**绝对路径**，由 Task Agent 自行 `Read 工具` 加载，避免 Prompt 膨胀 |
| **中间产物传递** | 与 Level 1 完全相同的中间产物文件（`_product-collection.json`、`_baseline-summary.json`、`_extraction-result.json`），保证数据格式一致 |
| **断点恢复** | 每个 Task 完成后中间产物已落盘，降级或中断后可从已完成的 Task 之后继续 |
| **角色合并** | 最后一个 Task 合并 extractor + assessor 两个角色，减少 Task 调用次数 |

### 3.2 流水线定义

#### 全新需求（2 个 Task）

```
Task 流水线：

[Task-A] 需求收集（复用 @product-collector 规范）
 输入：state.json + PRD
 产出：analysis/_product-collection.json
 
 ↓ _product-collection.json 落盘
 
[Task-B] 需求提取 + 质量评估（合并 @product-extractor + @quality-assessor 规范）
 输入：analysis/_product-collection.json
 产出：analysis/_extraction-result.json + analysis/product-requirements.md + analysis/product-clarify.json（条件）
```

#### 全新需求 + 含视觉附件（3 个 Task）

```
Task 流水线：

[Task-A] 需求收集（复用 @product-collector 规范）
 输入：state.json + PRD
 产出：analysis/_product-collection.json
 
 ↓ _product-collection.json 落盘
 
[Task-A2] 视觉分析（内联 @visual-analyst 规范）
 输入：analysis/_product-collection.json + 图片文件列表
 产出：analysis/_visual-analysis.json
 
 ↓ _visual-analysis.json 落盘
 
[Task-B] 需求提取 + 质量评估（合并 @product-extractor + @quality-assessor 规范）
 输入：analysis/_product-collection.json + analysis/_visual-analysis.json
 产出：analysis/_extraction-result.json + analysis/product-requirements.md + analysis/product-clarify.json（条件）
```

#### 迭代需求（3 个 Task）

```
Task 流水线：

[Task-A] 需求收集（复用 @product-collector 规范）
 输入：state.json + PRD
 产出：analysis/_product-collection.json
 
 ↓ _product-collection.json 落盘
 
[Task-B] 基线对比（复用 @baseline-differ 规范）
 输入：analysis/_product-collection.json + 前一版产物 + 前一版 PRD + 当前 PRD
 产出：analysis/_baseline-summary.json
 
 ↓ _baseline-summary.json 落盘
 
[Task-C] 需求提取 + 质量评估（合并 @product-extractor + @quality-assessor 规范）
 输入：analysis/_product-collection.json + analysis/_baseline-summary.json
 产出：analysis/_extraction-result.json + analysis/product-requirements.md + analysis/product-clarify.json（条件）
```

#### 迭代需求 + 含视觉附件（4 个 Task）

```
Task 流水线：

[Task-A] 需求收集（复用 @product-collector 规范）
 输入：state.json + PRD
 产出：analysis/_product-collection.json
 
 ↓ _product-collection.json 落盘
 
[Task-A2] 视觉分析（内联 @visual-analyst 规范）
 输入：analysis/_product-collection.json + 图片文件列表
 产出：analysis/_visual-analysis.json

[Task-B] 基线对比（复用 @baseline-differ 规范）
 输入：analysis/_product-collection.json + 前一版产物 + 前一版 PRD + 当前 PRD
 产出：analysis/_baseline-summary.json
 
 ↓ Task-A2 和 Task-B 可串行执行（Level 2 不支持并行），顺序无关
 
[Task-C] 需求提取 + 质量评估（合并 @product-extractor + @quality-assessor 规范）
 输入：analysis/_product-collection.json + analysis/_baseline-summary.json + analysis/_visual-analysis.json
 产出：analysis/_extraction-result.json + analysis/product-requirements.md + analysis/product-clarify.json（条件）
```

### 3.3 Task Prompt 模板

#### Task-A: 需求收集

```
你是一位资深需求信息收集专家。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read 工具）：{agents/product-analysts/product-collector.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取 PRD 文档：{prdSource 指向的文件的绝对路径}
4. 读取澄清 Schema：{references/clarify-schema.json 的绝对路径}
5. 严格按照 Agent 规范执行全部工作流程
6. 将收集结论写入：{analysis/_product-collection.json 的绝对路径}

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

⚠️ 重要：
- 你必须先 用 Read 工具读取 Agent 规范文件，再按规范执行
- 完成后返回产物路径和关键摘要
```

#### Task-A2: 视觉分析（仅含视觉附件时）

```
你是一位资深视觉分析专家。请按以下步骤执行：

1. 读取视觉分析协议规范文件（Read 工具）：{rules/visual-analysis-protocol.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 从中间产物的 `visualAttachments` 字段获取图片文件列表
4. 逐张读取图片文件，严格按照视觉分析协议执行：
  a) 图片分类（§1）
  b) 结构化分析（§2/§3）
  c) 多图对比分析（§4，如适用）
5. 将视觉分析结论写入：{analysis/_visual-analysis.json 的绝对路径}

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

⚠️ 重要：
- 你必须先 用 Read 工具读取视觉分析协议文件，再按协议执行
- 产出格式须遵循协议 §5 的 JSON 结构
- 不确定的推断必须在 uncertainties 中标注
- 完成后返回产物路径和关键发现摘要
```

#### Task-B: 基线对比（仅迭代需求）

```
你是一位资深需求变更分析专家。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read 工具）：{agents/product-analysts/baseline-differ.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 读取前一版分析产物：{baseline.analysisPath 的绝对路径}
4. 读取前一版 PRD：{baseline.prdPath 的绝对路径}
5. 读取当前 PRD：{prdSource 指向的文件的绝对路径}
6. 严格按照 Agent 规范执行基线数据提取、增量对比、移除判定
7. 将对比结论写入：{analysis/_baseline-summary.json 的绝对路径}

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

⚠️ 重要：
- 你必须先 用 Read 工具读取 Agent 规范文件，再按规范执行
- 前一版产物和 PRD 的完整内容仅在你的上下文中处理
- 完成后返回产物路径和关键摘要
```

#### Task-B/C（最终 Task）: 需求提取 + 质量评估（合并角色）

```
你是一位资深需求分析与质量评估专家，负责结构化提取和最终报告整合。请按以下步骤执行：

**Phase 1: 需求结构化提取**
1. 读取需求提取专家的 Agent 行为规范（Read 工具）：{agents/product-analysts/product-extractor.md 的绝对路径}
2. 读取收集员中间产物：{analysis/_product-collection.json 的绝对路径}
3. 条件读取基线对比中间产物：{analysis/_baseline-summary.json 的绝对路径}（仅迭代需求时存在）
4. 读取澄清 Schema：{references/clarify-schema.json 的绝对路径}
5. 按照 Agent 规范提取用户故事、业务规则、数据实体、验收标准、不明确项
6. 迭代需求时，消费基线对比数据执行增量标注
7. 将提取结论写入：{analysis/_extraction-result.json 的绝对路径}

**Phase 2: 质量评估与报告输出**
8. 读取质量评估师的 Agent 行为规范（Read 工具）：{agents/product-analysts/quality-assessor.md 的绝对路径}
9. 基于已提取的数据（Phase 1 已在上下文中）和 Agent 规范执行：
  - ISO/IEC 25010 六维度评分
  - 风险排查（六维度）
  - Kano 模型分类
  - 报告整合（按报告模板组织）
10. 将最终报告写入：{analysis/product-requirements.md 的绝对路径}
11. 如有待澄清问题，写入：{analysis/product-clarify.json 的绝对路径}

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
迭代类型：{iterationType}

⚠️ 重要：
- 你必须先 用 Read 工具读取各 Agent 规范文件，再按规范执行
- 你严禁读取原始 PRD 文件和前一版产物文件，所有信息来自中间产物（上下文防火墙）
- Phase 1 和 Phase 2 在同一个上下文窗口中连续执行，Phase 1 的提取数据直接供 Phase 2 使用
- 完成后返回产物路径和关键摘要
```

### 3.4 Task 串行流水线执行流程

```
编排器执行流程：

1. 确定起始 Task（检查已存在的中间产物）：
  a) _product-collection.json 不存在 → 从 Task-A 开始
  b) _product-collection.json 存在，含视觉附件但 _visual-analysis.json 不存在 → 从 Task-A2 开始
  c) _product-collection.json 存在但 _baseline-summary.json 不存在（迭代需求）→ 从 Task-B 开始
  d) _product-collection.json 存在且非迭代 / _baseline-summary.json 已存在 → 从最终 Task 开始

2. 执行 Task-A（如需）：
  a) 使用 Agent 工具，注入 §3.3 Task-A Prompt
  b) Task 返回后，检查 _product-collection.json 是否成功写入
  c) 如果写入失败 → 降级到 Level 3
  d) 读取 _product-collection.json 中的 iterationType 和 visualAttachments 判断后续流程

2.5. 执行 Task-A2（仅含视觉附件时，如需）：
  a) 使用 Agent 工具，注入 §3.3 Task-A2 Prompt
  b) Task 返回后，检查 _visual-analysis.json 是否成功写入
  c) 如果写入失败 → 跳过视觉分析，继续后续流程（非阻断）

3. 执行 Task-B（仅迭代需求，如需）：
  a) 从 _product-collection.json 中提取 baseline 路径信息
  b) 使用 Agent 工具，注入 §3.3 Task-B Prompt（替换路径占位符）
  c) Task 返回后，检查 _baseline-summary.json 是否成功写入
  d) 如果写入失败 → 降级到 Level 3

4. 执行最终 Task（Task-B 或 Task-C）：
  a) 使用 Agent 工具，注入 §3.3 合并 Task Prompt
  b) Task 返回后，检查最终产物：
   - analysis/_extraction-result.json 是否存在
   - analysis/product-requirements.md 是否存在
  c) 如果最终产物缺失 → 降级到 Level 3

5. 所有 Task 完成后：
  a) 读取最终报告 front-matter
  b) 更新 state.json: analyseProductMode = "task-pipeline"
  c) 进入"总结确认"步骤
```

### 3.5 Level 2 失败处理

| 失败场景 | 处理方式 |
|---------|---------|
| Task-A 返回空结果 / 无中间产物 | 降级到 Level 3 |
| Task-B 返回空结果 / 无中间产物 | 降级到 Level 3（已有 _product-collection.json 可供 Level 3 参考） |
| 最终 Task 返回空结果 / 无最终产物 | 降级到 Level 3（已有中间产物可供 Level 3 参考） |
| Task 执行过程中出现错误但有部分产物 | 检查产物完整性，完整则视为成功；不完整则降级到 Level 3 |

---

## 4. Level 3: 编排器直接执行（兜底模式）

当 Level 2 也失败时，编排器在自身上下文中直接执行产品需求分析。

### 4.1 执行策略

```
编排器直接执行流程：

1. 读取可用的中间产物（Level 1/2 可能已产出部分）：
  a) 如果 _product-collection.json 存在 → 读取作为输入（避免重复读取 PRD 原文）
  b) 如果 _baseline-summary.json 存在 → 读取作为输入
  c) 如果 _extraction-result.json 存在 → 读取作为输入
  d) 如果以上均不存在 → 直接读取 PRD 原文 + state.json

2. 参考 agents/product-analyst.md 的核心分析流程（六步流程），在编排器上下文中执行：
  - 需求信息收集 → 迭代判定 → 深度分析 → 质量评估 → 风险评估 → 报告生成
  ⚠️ 注意：编排器上下文有限，分析深度可能不及 Level 1/2，但保证流程不阻断

3. 直接写入最终产物：
  - analysis/product-requirements.md
  - analysis/product-clarify.json（如有）

4. 更新 state.json: analyseProductMode = "fallback"

5. 进入"总结确认"步骤
```

### 4.2 Level 3 的限制说明

| 限制 | 说明 |
|------|------|
| 上下文受限 | 编排器的上下文已包含 SKILL.md、本规则文件等，留给分析的窗口有限 |
| 分析精度降低 | 迭代需求场景下，可能无法完整对比前一版产物，分析精度最低 |
| 产物质量标注 | 在最终报告 front-matter 中追加 `analysisMode: "fallback"`，提示后续阶段注意 |
| 流程保障 | 即使精度下降，仍保证有结构化产物输出，不阻断工作流 |

> **注意**: Level 3 产出时，编排器应在总结确认中向用户明确说明"本次分析使用了兜底模式，分析精度可能有所下降，建议仔细审阅报告"。

---

## 5. state.json 记录

### 5.1 analyseProductMode 字段

| 值 | 说明 |
|-----|------|
| `"parallel-agent"` | Level 1: Agent 工具并行调度模式成功完成 |
| `"task-pipeline"` | Level 2: Task 串行流水线模式完成 |
| `"fallback"` | Level 3: 编排器直接执行模式完成 |
| `"task"` | 兼容旧值：等价于 Level 3（断点恢复时按 Level 3 处理） |

### 5.2 Agent 工具并行调度 记录（仅 Level 1）

使用 Agent 工具并行调度模式时，在 state.json 中记录以下信息：

```json
{
 "analyseProductMode": "parallel-agent",
 "analyseProductTeam": {
  "teamName": "analyse-product-{需求ID}",
  "members": [
   {
    "name": "@product-collector",
    "role": "需求信息收集员",
    "status": "completed",
    "completedAt": "{ISO8601时间}"
   },
   {
    "name": "@baseline-differ",
    "role": "基线对比专家",
    "status": "completed",
    "completedAt": "{ISO8601时间}",
    "note": "仅迭代需求时存在"
   },
   {
    "name": "@product-extractor",
    "role": "需求提取专家",
    "status": "completed",
    "completedAt": "{ISO8601时间}"
   },
   {
    "name": "@quality-assessor",
    "role": "质量风险评估师",
    "status": "completed",
    "completedAt": "{ISO8601时间}"
   }
  ],
  "iterationType": "incremental",
  "createdAt": "{ISO8601时间}",
  "cleanedAt": "{ISO8601时间}"
 }
}
```

### 5.3 Task 流水线记录（仅 Level 2）

```json
{
 "analyseProductMode": "task-pipeline",
 "analyseProductPipeline": {
  "completedTasks": ["Task-A", "Task-B", "Task-C"],
  "iterationType": "incremental",
  "degradedFrom": "parallel-agent",
  "degradeReason": "Agent @product-collector 返回空结果",
  "completedAt": "{ISO8601时间}"
 }
}
```

### 5.4 兜底模式记录（仅 Level 3）

```json
{
 "analyseProductMode": "fallback",
 "analyseProductFallback": {
  "degradedFrom": "task-pipeline",
  "degradeReason": "Task-A 返回空结果",
  "availableArtifacts": ["_product-collection.json"],
  "completedAt": "{ISO8601时间}"
 }
}
```

---

## 6. 异常处理与断点恢复

### 6.1 Agent 失败处理（Level 1）

| 场景 | 处理方式 |
|------|---------|
| @product-collector 失败 | 编排器通过 `@product-collector` 发送修复指令，或重新发起 Agent 调用 |
| @baseline-differ 失败 | 同上；如果 `_product-collection.json` 存在，可直接创建新 @baseline-differ 重试 |
| @product-extractor 失败 | 同上；如果前置中间产物存在，可直接创建新 @product-extractor 重试 |
| @quality-assessor 失败 | 同上；如果 `_extraction-result.json` 存在，可直接创建新 @quality-assessor 重试 |
| Agent 调用失败/返回空结果 | 检查已落盘的中间产物 → 决定降级策略 |

### 6.2 断点恢复

```
恢复策略：

1. 读取 state.json，检查 analyseProductMode 字段
2. 根据 analyseProductMode 值选择恢复策略：

  --- Level 1 恢复（analyseProductMode = "parallel-agent"）---
  a) 检查哪些中间产物已存在：
   - _product-collection.json 存在 → @product-collector 已完成
   - _baseline-summary.json 存在 → @baseline-differ 已完成（迭代需求）
   - _extraction-result.json 存在 → @product-extractor 已完成
   - product-requirements.md 存在 → @quality-assessor 已完成
  b) 根据已完成的 Agent，创建新的 Agent Team 只包含未完成的 Agent
  c) 特殊情况：若 _product-collection.json 中 iterationType = "incremental"
   但 _baseline-summary.json 不存在 → 需要调度 @baseline-differ

  --- Level 2 恢复（analyseProductMode = "task-pipeline"）---
  a) 读取 analyseProductPipeline.completedTasks 确定已完成的 Task
  b) 检查中间产物文件存在性进行交叉验证
  c) 从下一个未完成的 Task 继续执行

  --- Level 3 恢复（analyseProductMode = "fallback" 或 "task"）---
  a) 检查最终产物是否存在：
   - product-requirements.md 存在 → 直接进入总结确认
   - 不存在 → 读取可用中间产物，重新执行 Level 3

3. 若 analyseProductMode 字段不存在：
  a) 检查中间产物存在性推断执行进度
  b) 从头开始，尝试 Level 1
```

---

## 7. 编排器对接行为（三步模式）

本阶段遵循标准三步模式（预览 → 执行 → 总结确认）：

**Step 1: 预览** — 展示即将执行的产品需求分析计划：
- 调度模式（Level 1 Agent 工具并行调度 / Level 2 Task 流水线 / Level 3 编排器直接执行）
- 如为断点恢复，说明从哪个步骤继续
- Agent 工具并行调度模式下：调度标识、Agent 列表（3 或 4 个）、依赖关系
- Task 流水线模式下：Task 数量（2 或 3 个）、各 Task 职责
- PRD 文档来源
- 涉及平台列表
- 需求描述概要

**Step 2: 执行** —
- **Level 1 (Agent 工具并行调度)**: 发起 Agent 调用 → 分配任务（T1→判定→T2 条件→T3→T4） → 监控完成 → 超时检测 → 汇总结果 → 
- **Level 2 (Task 流水线)**: 串行调用 Task-A → [Task-B] → Task-B/C，检查中间产物
- **Level 3 (编排器直接执行)**: 编排器自身读取输入并生成产物

**Step 3: 总结确认** — 展示分析结果：
- 实际使用的调度模式（含降级信息，如"Agent 工具并行调度 → Task 流水线（@product-collector 超时降级）"）
- 质量门禁（qualityGate + qualityScore）
- 产物清单（最终报告 + 中间产物 + 澄清问题）
- 迭代类型（new / incremental）
- 迭代变更统计（仅迭代需求：added/modified/removed/unchanged）
- 用户故事数量和优先级分布
- 业务规则数量和确认状态分布
- 风险项汇总
- 待澄清问题数量和优先级分布
- Level 3 兜底模式时，追加精度降低警告
