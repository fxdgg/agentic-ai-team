# ANALYSE_TECH 阶段 Agent 工具并行调度 调度规则（按需加载）

> **加载时机**: 编排器进入 ANALYSE_TECH 阶段时加载本文件。

---

## 0. 调度模式选择

ANALYSE_TECH 阶段支持两种调度模式，编排器**优先使用 Agent 工具并行调度模式**：

| 模式 | 触发条件 | 说明 |
|------|---------|------|
| **Agent 工具并行调度模式**（默认） | 始终优先使用 | 使用 Agent 工具并行调度 四 Agent 串行调用，独立上下文窗口隔离搜索结果膨胀 |
| **Agent 工具串行模式**（降级） | Agent 工具并行调度 创建失败 | 回退到传统 Agent 工具调用单体 `fullstack-analyst.md` |

> **设计意图**: Agent 工具并行调度 的核心价值在 ANALYSE_TECH 阶段是**上下文隔离**而非并行执行。通过将代码搜索（上下文消耗最大的工作）隔离在独立窗口中，避免搜索结果膨胀导致上下文压缩，从而保障复杂规则（复用探索、证据链、接口契约、一致性校验）的执行精度。

---

## 1. 四 Agent 串行协作模型

```
@tech-explorer ──→ @tech-designer ──→ @tech-splitter ──→ @tech-reviewer
 (Phase 1+2) (Phase 3+总纲) (Phase 4 分端) (Phase 5 校审)
 搜索密集 零搜索 零搜索 零搜索
 上下文最重 上下文最轻 上下文适中 上下文轻
```

### 1.1 Agent 注册表

| Agent 名 | Agent 文件 | 职责 | 上下文特征 |
|--------|-----------|------|-----------|
| `@tech-explorer` | `agents/tech-analysts/tech-explorer.md` | 初始化 + 复用探索 + 证据收集 | **搜索密集**，上下文峰值最高（~140KB），但职责单一 |
| `@tech-designer` | `agents/tech-analysts/tech-designer.md` | 架构设计 + 接口契约定义 + 总纲输出 | **零搜索**，上下文极轻（~30KB），契约精度最高 |
| `@tech-splitter` | `agents/tech-analysts/tech-splitter.md` | 分端文档生成 + 一致性校验 | **零搜索**，上下文适中（~55KB），校验在同一窗口完成 |
| `@tech-reviewer` | `agents/tech-analysts/tech-reviewer.md` | 全链路反向验证 + 遗漏/矛盾检测 + 校审报告 | **零搜索**，上下文轻（~40KB），只读已有产物 |

### 1.2 任务依赖关系

```
任务列表：
1. [T1] 技术探索分析 — 分配给 @tech-explorer — 无依赖
2. [T2] 总纲设计与输出 — 分配给 @tech-designer — 依赖任务 1
3. [T3] 分端文档生成 — 分配给 @tech-splitter — 依赖任务 2
4. [T4] 技术文档校审 — 分配给 @tech-reviewer — 依赖任务 3
```

**依赖传递机制**: 通过**文件系统**（中间产物文件），而非对话历史。各 Agent通过读取前置 Agent 写入的文件获取上下文。

### 1.3 中间产物（上下文防火墙）

| 中间产物 | 写入方 | 读取方 | Schema |
|---------|--------|--------|--------|
| `analysis/tech-exploration-result.json` | @tech-explorer | @tech-designer, @tech-splitter, @tech-reviewer | `references/tech-exploration-schema.json` |
| `analysis/tech-requirements.md` | @tech-designer | @tech-splitter, @tech-reviewer | 总纲模板（内联于 tech-designer.md §8） |
| `analysis/tech-clarify.json` | @tech-designer | 编排器（澄清阶段） | `references/clarify-schema.json` |
| `analysis/tech-review-report.md` | @tech-reviewer | 编排器（总结确认） | 校审报告模板（内联于 tech-reviewer.md §8） |

> **核心设计**: `tech-exploration-result.json` 是 **"上下文防火墙"**——explorer 的 100+ 次搜索原始结果（~150KB）被压缩为结构化结论（~15KB），信息密度提升 10 倍，后续 Agent的上下文因此保持干净。

---

## 2. Agent 工具并行调度模式调度规则

### 代码画像注入协议（仅当 `knowledgeContext.profilePath` 存在）

> **加载条件**: 编排器在创建 Agent 工具并行调度 前，先读取 `state.json` 检查 `knowledgeContext.profilePath` 字段。

当项目有代码画像分析结果时，编排器在`@tech-explorer` 的 Agent Prompt 中**额外注入**以下段落：

```
【已有代码画像参考】
本项目已有代码画像分析结果（由知识导入流程生成），可加速全景扫描：
- 画像路径: {knowledgeContext.profilePath 的绝对路径}
- 建议: Step 1 初始化时优先读取此文件，可大幅减少全景扫描的工具调用次数

使用方式:
1. 在 Step 1 初始化时，先使用 Read 工具读取画像文件
2. 将画像中的 projectOverview（modules, techStack）作为扫描起点
3. 聚焦验证画像信息的准确性 + 补充画像缺失的部分
4. projectOverview 的最终输出以实际扫描为准，画像数据仅作为启动线索

⚠️ 注意: 画像数据置信度 0.5-0.6（导入时生成），关键信息需通过实际扫描验证。
```

**对 @tech-explorer 的影响**：
- Step 1 全景扫描可**跳过已画像的模块**，聚焦验证和补充
- `projectOverview` 输出以实际扫描为准，画像数据仅作为启动线索
- 搜索预算节省预估：约 20-30%（减少重复扫描）
- 不改变 Step 2 的搜索逻辑（需求点复用探索不受影响）

### 2.1 调度发起

编排器按依赖关系发起 Agent 工具调用，使用****。

**创建指令模板**:

```
发起 Agent 调用组（调度标识: analyse-tech-{需求ID}）：

调度任务：基于产品需求文档进行全局技术可行性分析，产出技术需求文档。
调度采用四 Agent 串行协作模式，每个 Agent负责独立的分析阶段，通过文件系统传递中间产物。

Agent 列表：
{见 §2.2 Agent Prompt 规则}

任务依赖关系：
1. [T1] 技术探索分析 — @tech-explorer — 无依赖
2. [T2] 总纲设计与输出 — @tech-designer — 依赖 T1
3. [T3] 分端文档生成 — @tech-splitter — 依赖 T2
4. [T4] 技术文档校审 — @tech-reviewer — 依赖 T3
```

### 2.2 Agent Prompt 规则

为四个 Agent 生成独立的 Prompt。Agent Prompt 必须包含充分的上下文（因为 Agent **不会继承编排器的对话历史**）：

#### Agent 1: @tech-explorer

```
生成一个技术探索员Agent（@tech-explorer），Prompt 如下：

"你是一位技术探索专家，负责代码库搜索和复用评估。

你的工作职责：
1. 读取 Agent 行为规范：{agents/tech-analysts/tech-explorer.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取产品需求文档：{analysis/product-requirements.md 的绝对路径}
4. 读取中间产物 Schema：{references/tech-exploration-schema.json 的绝对路径}
5. 严格按照 Agent 规范执行技术探索，对每个需求点进行 3 轮递进复用探索
6. 将探索结论写入：{analysis/tech-exploration-result.json 的绝对路径}

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

#### Agent 2: @tech-designer

```
生成一个技术设计师Agent（@tech-designer），Prompt 如下：

"你是一位资深全栈架构师，负责架构设计和接口契约定义。

你的工作职责：
1. 读取 Agent 行为规范：{agents/tech-analysts/tech-designer.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取探索结论中间产物：{analysis/tech-exploration-result.json 的绝对路径}
4. 读取产品需求文档：{analysis/product-requirements.md 的绝对路径}
5. 读取中间产物 Schema：{references/tech-exploration-schema.json 的绝对路径}
6. 读取澄清 Schema：{references/clarify-schema.json 的绝对路径}
7. 严格按照 Agent 规范制定架构方案、定义接口契约、计算质量评分
8. 将总纲写入：{analysis/tech-requirements.md 的绝对路径}
9. 如有澄清问题，写入：{analysis/tech-clarify.json 的绝对路径}

⚠️ 重要：你不执行任何代码搜索，所有信息来自探索结论中间产物。

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

#### Agent 3: @tech-splitter

```
生成一个分端文档生成器Agent（@tech-splitter），Prompt 如下：

"你是一位技术文档专家，负责将总纲拆分为各端技术需求文档。

你的工作职责：
1. 读取 Agent 行为规范：{agents/tech-analysts/tech-splitter.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
4. 读取探索结论中间产物：{analysis/tech-exploration-result.json 的绝对路径}
5. 按 platforms 启用情况，逐端读取模板并生成分端文档：
 - 后端模板：{templates/fullstack-analyst/tech-requirements-backend-template.md 的绝对路径}
 - Web 端模板：{templates/fullstack-analyst/tech-requirements-web-template.md 的绝对路径}
 - 小程序端模板：{templates/fullstack-analyst/tech-requirements-miniprogram-template.md 的绝对路径}
6. 执行总纲与分端文档的一致性校验，发现不一致时以总纲为准修正

⚠️ 重要：你不执行任何代码搜索，所有信息来自总纲和探索结论。

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
产出目录：{analysis/ 的绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

#### Agent 4: @tech-reviewer

```
生成一个技术文档校审员Agent（@tech-reviewer），Prompt 如下：

"你是一位技术文档校审专家，负责对全部前序产物执行反向验证和一致性检查。

你的工作职责：
1. 读取 Agent 行为规范：{agents/tech-analysts/tech-reviewer.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取探索结论中间产物：{analysis/tech-exploration-result.json 的绝对路径}
4. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
5. 按 platforms 启用情况，读取分端文档：
 - 后端：{analysis/tech-requirements-backend.md 的绝对路径}
 - Web 端：{analysis/tech-requirements-web.md 的绝对路径}
 - 小程序端：{analysis/tech-requirements-miniprogram.md 的绝对路径}
6. 读取产品需求文档：{analysis/product-requirements.md 的绝对路径}
7. 严格按照 Agent 规范执行 5 项反向验证检查（探索→总纲一致性、总纲→分端一致性、遗漏检测、矛盾检测、产品需求覆盖度）
8. 将校审报告写入：{analysis/tech-review-report.md 的绝对路径}

⚠️ 重要：你不执行任何代码搜索，不修改任何已有产物，只读取并校审。

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

> **关键**: 所有 Prompt 中的路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析）。

### 2.3 编排器（编排器）的行为约束

在 Agent 工具并行调度模式下，编排器作为 编排器：

| ✅ 必须做 | ❌ 禁止做 |
|-----------|----------|
| 发起 Agent 调用并分配任务 | 直接执行任何分析/设计工作 |
| Agent 同步返回后检查产物 | 在 Agent 工作时中断 |
| Agent 返回后检查产物 | 替代 Agent 完成未完成的任务 |
| 汇总结果并更新 state.json | 向 Agent 传递其他 Agent 的完整对话 |
| 处理 @tech-explorer 上报的阻断问题 | 忽略 Agent 的错误/风险汇报 |

### 2.4 阻断问题处理流程

当 @tech-explorer 在探索过程中发现阻断级技术问题时：

```
处理流程：
1. @tech-explorer 在中间产物的 blockingQuestions 中记录问题
2. @tech-explorer 返回结果标明有阻断问题
3. 编排器展示阻断问题给用户，请求回答
4. 编排器将用户回答注入到 @tech-explorer 的新一轮 Agent 调用中用户回答
5. @tech-explorer 根据回答更新中间产物中的相关分析
6. @tech-explorer 继续执行后续探索
```

### 2.5 调度完成与产物检查

所有 Agent完成任务后，编排器执行：

```
1. 逐一确认每个 Agent的返回结果
2. 检查所有产物文件是否存在：
 - analysis/tech-exploration-result.json（中间产物）
 - analysis/tech-requirements.md（总纲）
 - analysis/tech-requirements-{platform}.md（分端文档，按启用平台）
 - analysis/tech-review-report.md（校审报告）
 - analysis/tech-clarify.json（可选）
3. 读取总纲的 front-matter 获取 qualityGate 和 qualityScore
4. 读取校审报告的 front-matter 获取 reviewResult
5. 汇总所有 Agent的风险项
6. 更新 state.json:
 - analyseTechMode 字段设为 "parallel-agent"
 - analyseTechTeam 记录调度信息
7. 关闭所有 Agent → 汇总结果
8. 恢复正常模式，进入"总结确认"步骤
```

---

## 3. Agent 工具串行降级模式

当以下条件满足时，使用传统 Agent 工具串行模式（调用单体 `agents/fullstack-analyst.md`）：

| 降级条件 | 说明 |
|---------|------|
| Agent 工具并行调度 创建失败 | 功能异常时自动降级 |

降级模式下调用原 `agents/fullstack-analyst.md`（单体 Agent），行为与改造前完全一致：四阶段流程在单次 Agent 调用中完成。

> **注意**: 降级模式下，`analyseTechMode` 设为 `"task"`，不记录 `analyseTechTeam`。

---

## 4. state.json 中的 Agent 工具并行调度 记录

使用 Agent 工具并行调度模式时，在 state.json 中记录以下信息：

```json
{
 "analyseTechMode": "parallel-agent",
 "analyseTechTeam": {
 "teamName": "analyse-tech-{需求ID}",
 "members": [
 {
 "name": "@tech-explorer",
 "role": "技术探索员",
 "status": "completed",
 "completedAt": "{ISO8601时间}"
 },
 {
 "name": "@tech-designer",
 "role": "技术设计师",
 "status": "completed",
 "completedAt": "{ISO8601时间}"
 },
 {
 "name": "@tech-splitter",
 "role": "分端文档生成器",
 "status": "completed",
 "completedAt": "{ISO8601时间}"
 },
 {
 "name": "@tech-reviewer",
 "role": "技术文档校审员",
 "status": "completed",
 "completedAt": "{ISO8601时间}"
 }
 ],
 "createdAt": "{ISO8601时间}",
 "cleanedAt": "{ISO8601时间}"
 }
}
```

---

## 5. 异常处理与恢复

### 5.1 Agent 失败处理

| 场景 | 处理方式 |
|------|---------|
| @tech-explorer 失败 | 编排器重新发起 @tech-explorer Agent 调用并注入修复指令，或创建替代 Agent 调用 |
| @tech-designer 失败 | 同上；如果中间产物存在，可直接创建新 @tech-designer 重试 |
| @tech-splitter 失败 | 同上；如果总纲存在，可直接创建新 @tech-splitter 重试 |
| @tech-reviewer 失败 | 同上；如果分端文档存在，可直接创建新 @tech-reviewer 重试 |
| Agent 调用失败/返回空结果 | 重新发起 Agent 调用重试 |

### 5.2 断点恢复

Agent 工具并行调度模式下的断点恢复策略：

```
恢复策略：
1. 读取 state.json，检查 analyseTechMode 字段
2. 若 analyseTechMode = "parallel-agent" 且 currentPhase = "ANALYSE_TECH"：
 a) 检查哪些中间产物已存在：
 - tech-exploration-result.json 存在 → @tech-explorer 已完成
 - tech-requirements.md 存在 → @tech-designer 已完成
 - 分端文档存在 → @tech-splitter 已完成
 - tech-review-report.md 存在 → @tech-reviewer 已完成
 b) 根据已完成的 Agent，创建新的 Agent 调用 只包含未完成的 Agent
3. 若 analyseTechMode = "task" 或字段不存在：
 a) 使用传统 Agent 工具串行模式恢复
```

---

## 6. 编排器对接行为（三步模式）

本阶段遵循标准三步模式（预览 → 执行 → 总结确认）：

**Step 1: 预览** — 展示即将执行的技术分析计划：
- 调度模式（Agent 工具并行调度 / Agent 工具串行降级）
- Agent 工具并行调度模式下：调度标识、四个 Agent 的职责、依赖关系
- 启用的平台列表
- 产品需求文档概要

**Step 2: 执行** —
- **Agent 工具并行调度模式**: 发起 Agent 调用 → 分配任务（T1→T2→T3→T4 串行） → Agent 同步返回后检查产物 → 汇总结果 → 汇总结果
- **Agent 工具串行降级模式**: 调用单体 fullstack-analyst Agent

**Step 3: 总结确认** — 展示分析结果：
- 质量门禁（qualityGate + qualityScore）
- 校审结果（reviewResult + blockingCount + advisoryCount）
- 产物清单（总纲 + 分端文档 + 校审报告 + 中间产物 + 澄清问题）
- 复用评级统计
- 接口契约数量
- 风险项汇总
- 平台变更建议（如有）
