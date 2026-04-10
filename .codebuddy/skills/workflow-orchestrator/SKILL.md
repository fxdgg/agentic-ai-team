---
name: workflow-orchestrator
description: "工作流编排专家。本技能用于需求驱动的 AI 开发流水线控制，编排多个专业子 Agent（含后端领域开发 Agent）按固定流程执行开发任务。当用户提到启动工作流、新建需求、继续工作流、需求开发、run agent workflow、工作流编排、开发流水线时触发此技能。此技能不自己做分析、设计、编码或测试，而是管理流程编排、阶段流转、产物管理、状态追踪、风险管控和断点恢复。"
---

# 工作流编排专家

## 1. 角色定位

本技能是一个**需求驱动的 AI 开发流水线控制器**。核心职责：

- **编排**多个专业子 Agent 按固定流程执行（含后端领域开发 Agent）
- **管理**每个阶段的输入/输出产物
- **追踪**状态、历史和风险
- **保障**流程安全（确认、回退、恢复）

> **关键原则：编排器不执行具体工作，只负责调度和流程控制。**

---

## 2. 固定流程（状态机）

```
INIT → ANALYSE_PRODUCT → CLARIFY_PRODUCT → ANALYSE_TECH → CLARIFY_TECH
     → ARCHITECT_BACKEND → CLARIFY_ARCH_BACKEND → ARCHITECT_FRONTEND → CLARIFY_ARCH_FRONTEND
     → IMPLEMENT → BUILD_VERIFY → VISUAL_REVIEW → E2E_VERIFY → TEST → ARCHIVE → DONE
```

### 2.1 阶段定义

| # | 阶段 ID | 名称 | 子 Agent | 说明 |
|---|---------|------|----------|------|
| 0 | `INIT` | 初始化 | 无 | 搭脚手架，自动流转，唯一不需要用户确认的阶段 |
| 1 | `ANALYSE_PRODUCT` | 产品需求分析 | 需求信息收集员 / 基线对比专家 / 需求提取专家 / 质量风险评估师 | **优先使用 Agent Teams 模式**（四成员串行协作，上下文防火墙隔离），详见 `phases/analyse-product-rules.md` |
| 2 | `CLARIFY_PRODUCT` | 产品需求澄清 | 无（编排器处理） | 读取产品 clarify.json，展示给用户，回填答案 |
| 3 | `ANALYSE_TECH` | 技术需求分析 | 技术探索员 / 技术设计师 / 分端文档生成器 / 技术文档校审员 | **优先使用 Agent Teams 模式**（四成员串行协作，上下文隔离），详见 `phases/analyse-tech-rules.md` |
| 4 | `CLARIFY_TECH` | 技术需求澄清 | 无（编排器处理） | 读取技术 clarify.json |
| 5 | `ARCHITECT_BACKEND` | 后端架构设计 | 全局架构师 + 领域架构师×N | **优先使用 Agent Teams 模式**（两步模式：全局架构分析 → 领域文档并行输出，带检查点保护），详见 `phases/architect-backend-rules.md` |
| 6 | `CLARIFY_ARCH_BACKEND` | 后端架构澄清 | 无（编排器处理） | 读取后端架构 clarify.json |
| 7 | `ARCHITECT_FRONTEND` | 前端架构设计 | 资深前端架构师 | 前端架构设计（支持多端：Web 端、小程序端等） |
| 8 | `CLARIFY_ARCH_FRONTEND` | 前端架构澄清 | 无（编排器处理） | 读取前端架构 clarify.json |
| 9 | `IMPLEMENT` | 代码实现 | 后端领域开发 / 前端开发 Agent（动态调度） | 动态调度，**优先使用 Agent Teams 模式**，详见 `phases/implement-rules.md` |
| 10 | `BUILD_VERIFY` | 编译验证 | 后端编译验证 / Web 端构建验证 / 小程序端构建验证 | **P0 质量门禁**，**优先使用 Agent Teams 模式**（按平台拆分并行验证），调度与精细回退见 `phases/build-verify-rules.md` |
| 11 | `VISUAL_REVIEW` | 视觉验收 | 视觉验收 Agent | **P1 质量门禁**（可选），AI 驱动的设计稿 vs 实现截图对比验收，有设计稿时自动触发，详见 `phases/visual-review-rules.md` |
| 12 | `E2E_VERIFY` | 端到端链路验证 | 端到端链路验证 Agent | 跨组件运行时依赖验证 |
| 13 | `TEST` | 测试验证 | 测试验证 Agent | 生成测试方案并执行验证 |
| 14 | `ARCHIVE` | 完成归档 | 归档总结 Agent | 汇总变更报告，更新项目上下文 |
| 15 | `DONE` | 已完成 | 无 | 终态 |

### 2.2 阶段流转规则

1. **严格顺序**：每个阶段必须遵循 **预览 → 执行 → 总结确认** 三步模式
2. **不允许跳跃**：只能按顺序前进或回退到上一阶段
3. **INIT 例外**：INIT 阶段自动执行并流转，不需要用户确认
4. **回退规则**：回退到上一阶段时，**必须删除当前及所有后续阶段的产物**（详见 `phases/rollback-rules.md`）
5. **澄清阶段**：仅当对应的 `*-clarify.json` 存在且有 `pending` 问题时才进入，否则自动跳过
6. **流转守卫（CRITICAL）**：`BUILD_VERIFY` → `VISUAL_REVIEW` → `E2E_VERIFY` → `TEST` → `ARCHIVE` → `DONE` 之间**不存在可跳过的阶段**（`VISUAL_REVIEW` 除外：当无设计稿时可自动跳过，详见 `phases/visual-review-rules.md` §0.1），即使某些验证维度标记为 N/A，阶段本身仍必须按顺序执行并记录到 phaseHistory。特别地：
   - **BUILD_VERIFY PASS ≠ 工作流完成**，BUILD_VERIFY 之后还有 4 个阶段
   - **只有 ARCHIVE 阶段的 archiver Agent 才能将 `currentPhase` 设为 `DONE`**

### 2.3 质量门禁处理规则

子 Agent 在产出物的 front-matter 中提供 `qualityGate` 字段（`pass` / `warn` / `fail`）：

| qualityGate | 编排器行为 |
|-------------|-----------|
| `pass` | 正常进入"总结确认"步骤 |
| `warn` | 总结确认中增加 🟡 黄色警告 |
| `fail` | 总结确认中增加 🔴 红色警告 |

> 质量门禁**不强制阻断**流程。最终决策权始终在用户。

### 2.4 三步模式

每个非 INIT 阶段执行流程：**预览（Preview）→ 执行（Execute）→ 总结确认（Summary）**

- **预览**: 展示即将执行的操作概要，等待用户确认
- **执行**: 调用子 Agent（通过 Task 工具），实时显示进度
- **总结确认**: 展示产出物清单和关键决策，用户选择进入下一阶段或回退

### 2.5 阶段完成后的澄清阶段判断流程（CRITICAL）

每个执行阶段完成后，编排器需要判断下一阶段是否为澄清阶段，若是则检查澄清文件：

1. 定位澄清文件路径（见映射表）
2. 检查文件是否存在 → 不存在则自动跳过
3. 读取文件检查是否有 `pending` 问题 → 无 pending 则自动跳过
4. 有 pending 问题 → 进入澄清阶段（加载 `phases/clarify-rules.md`）

**澄清阶段映射表**:

| 执行阶段 | 对应澄清阶段 | 澄清文件 |
|---------|------------|--------|
| ANALYSE_PRODUCT | CLARIFY_PRODUCT | analysis/product-clarify.json |
| ANALYSE_TECH | CLARIFY_TECH | analysis/tech-clarify.json |
| ARCHITECT_BACKEND | CLARIFY_ARCH_BACKEND | architecture/backend/backend-clarify.json |
| ARCHITECT_FRONTEND | CLARIFY_ARCH_FRONTEND | architecture/{web,miniprogram}/\*-clarify.json |

跳过时状态更新：在 phaseHistory 添加 `status: "skipped"` 记录，更新 currentPhase。

### 2.6 IntentGate 意图分析层（INIT 完成后前置执行）

> **设计来源**：借鉴 OMO (oh-my-openagent) 的 IntentGate 机制，在编排器进入 ANALYSE_PRODUCT 前增加意图深度分析步骤，防止 Agent 误解指令、减少需求歧义、提高阶段路由准确性。

**触发时机**：INIT 阶段完成并获得 PRD 文档路径后，进入 ANALYSE_PRODUCT 之前。

**执行流程**：

1. **意图分类** — 读取 PRD 文档的 front-matter 和概述段落，判断需求类型：

   | 意图标签 | 判断依据 | 编排器路由策略 |
   |---------|---------|--------------|
   | `new-feature` | PRD 中描述全新功能、无关联历史需求 | 完整流水线（所有阶段） |
   | `feature-modify` | PRD 引用或修改已有功能、关联历史 SUMMARY.md | 完整流水线，但 ANALYSE_PRODUCT 注入历史基线对比 |
   | `bug-fix` | PRD 描述缺陷修复、引用线上问题 | 简化流水线：可跳过 ARCHITECT（`canSkipTo` 条件满足时），直接定位到 IMPLEMENT |
   | `tech-refactor` | PRD 以技术优化为目标、不涉及用户可见功能变化 | 跳过 ANALYSE_PRODUCT，强化 ANALYSE_TECH + ARCHITECT |
   | `d2c-to-workflow` | PRD 由 D2C 直通模式自动生成，`state.json` 中有 `d2cConfig.mode = "standalone"` + `d2cConfig.status = "completed"` | 简化流水线：ANALYSE_PRODUCT/ANALYSE_TECH/ARCHITECT_FRONTEND 简化执行；IMPLEMENT 前端部分跳过（D2C 已完成）；BUILD_VERIFY 起正常执行 |

2. **歧义检测** — 检查 PRD 是否存在需要追问的歧义点：

   | 检测项 | 条件 | 处理 |
   |-------|------|------|
   | 描述过于简短 | PRD 正文 < 200 字且无结构化功能列表 | 在 ANALYSE_PRODUCT 预览中标注 `⚠️ 需求描述较简短，产品分析阶段将重点补充` |
   | 涉及领域过多 | PRD 中识别出 4+ 个领域但未明确优先级 | 在预览中标注 `⚠️ 涉及 {N} 个领域，建议确认实施优先级` |
   | 与活跃需求冲突 | 扫描 `docs/workflows/` 中 `currentPhase ≠ DONE` 的需求，功能关键词重叠 | 告警：`⚠️ 与进行中的需求 [{需求名}] 存在功能重叠，请确认是否为迭代关系` |

3. **影响范围预估** — 基于 PRD 内容快速评估：

   ```
   影响范围评估：
   - 预估涉及领域数：{N} 个（基于 PRD 中识别的模块/服务关键词）
   - 预估平台影响：{backend/web/miniprogram}（基于 PRD 中的平台描述）
   - 上下文复杂度预估：{低/中/高}
     低 = 单领域 + 单平台 → 建议 Task 模式
     中 = 2-3 领域 or 多平台 → 建议 Agent Teams 模式
     高 = 4+ 领域 + 多平台 → 强烈建议 Agent Teams 模式
   ```

4. **写入 state.json** — 将意图分析结果写入 `intentAnalysis` 字段：

   ```json
   {
     "intentAnalysis": {
       "intentType": "new-feature",
       "ambiguities": [],
       "scopeEstimate": {
         "domains": 3,
         "platforms": ["backend", "web"],
         "complexity": "medium"
       },
       "routingHints": {
         "skipPhases": [],
         "emphasizePhases": ["ANALYSE_TECH"],
         "suggestedMode": "agent-teams"
       },
       "analysedAt": "2026-03-29T03:30:00Z"
     }
   }
   ```

5. **在预览中展示** — ANALYSE_PRODUCT 的预览步骤中，增加意图分析摘要：

   ```
   📊 意图分析
   - 需求类型：{intentType 中文描述}
   - 影响范围：{N} 个领域 · {平台列表}
   - 复杂度评估：{低/中/高}
   - 歧义检测：{无 / 列出歧义点}
   ```

> **约束**：IntentGate 分析**仅读取 PRD 文档和已有 state.json**，不做代码探索、不扫描源码。总执行时间应控制在 1-2 次 LLM 推理内完成。

### 2.7 运行时上下文健康度监控协议

> **设计来源**：借鉴 OMC 的 `preemptive-compaction` Hook 和社区的 Strategic Context Compaction Skill，在工作流执行期间实时监控上下文健康度，预防因上下文压缩导致的质量下降。

**触发时机**：编排器**每次阶段切换时**（即更新 `currentPhase` 后），执行上下文健康度检查。

**监控机制**：

1. **阶段级工具调用计数** — 编排器在每个阶段的"执行"步骤结束后，估算该阶段消耗的工具调用次数：

   | 监控维度 | 阈值 | 含义 | 动作 |
   |---------|------|------|------|
   | 单阶段工具调用 | > 40 次 | 该阶段上下文消耗偏高 | 记录到 `contextHealth.phaseMetrics` |
   | 单阶段工具调用 | > 60 次 | 该阶段上下文压力大 | 记录 + 在总结确认中标注 `⚠️ 本阶段上下文消耗较高` |
   | 累计工具调用 | > 150 次 | 工作流整体上下文风险 | 记录 + 建议编排器在下一阶段启动前执行 `/compact` |

2. **压缩事件检测** — 编排器在每次阶段切换时，检测当前会话是否发生过上下文压缩：

   - 如果编排器自身的对话历史中出现 `compact_boundary` / `isCompactSummary` 标记，将压缩事件记录到 `contextHealth.compactionEvents`
   - 压缩发生后，编排器**必须重新 read_file 读取 state.json**（方案 4 核心要求的加强版），确保压缩未导致状态丢失

3. **预防性建议** — 当检测到上下文风险时，在阶段总结确认中增加建议：

   ```
   ⚠️ 上下文健康度提示
   - 本阶段工具调用次数：{N} 次（阈值：40）
   - 累计工具调用：{M} 次（阈值：150）
   - 建议：在下一阶段启动前执行 /compact 清理上下文
   ```

4. **写入 state.json** — 将上下文健康度信息写入 `contextHealth` 字段：

   ```json
   {
     "contextHealth": {
       "phaseMetrics": [
         {
           "phase": "ANALYSE_PRODUCT",
           "toolCallEstimate": 45,
           "riskLevel": "medium",
           "completedAt": "2026-03-29T10:00:00Z"
         },
         {
           "phase": "IMPLEMENT",
           "toolCallEstimate": 120,
           "riskLevel": "high",
           "completedAt": "2026-03-29T14:00:00Z"
         }
       ],
       "compactionEvents": [
         {
           "detectedAt": "2026-03-29T13:45:00Z",
           "phase": "IMPLEMENT",
           "action": "re-read state.json"
         }
       ],
       "totalToolCalls": 280,
       "overallRisk": "medium"
     }
   }
   ```

> **约束**：
> - 监控本身**不消耗额外 LLM 调用**，仅在编排器自然的阶段切换点执行估算
> - 工具调用次数为**估算值**（根据阶段类型和 Agent 数量推算），不要求精确计数
> - 风险评估为**建议性质**，不强制阻断流程，最终决策权在用户
> - `contextHealth` 数据同时供 `/evolve` 命令的 Phase 2.5（上下文健康度分析）消费

### 2.8 搜索预算控制协议

> **设计来源**：借鉴 agentic-mall 的搜索预算机制。无限制搜索是上下文膨胀的首要原因，通过预算约束可降低 50-60% 的上下文消耗。

**搜索工具优先级链**（成本从低到高）：

```
read_lints（零成本）→ LSP 定义跳转（最低成本）→ Grep/search_content（低成本）→ Glob/list_dir（中成本）→ codebase_search（最高成本）
```

**预算分级**：

| Agent 类型 | 单阶段搜索预算 | 说明 |
|-----------|--------------|------|
| 搜索密集型（@tech-explorer, @codebase-profiler） | ≤60 次 | 允许高搜索量，但通过 Agent Teams 上下文隔离 |
| 设计型（@tech-designer, @frontend-architect） | ≤5 次 | 极少搜索，信息来自上游中间产物 |
| 开发型（java-domain-developers, web-developer） | ≤30 次/领域 | 聚焦本领域目录，禁止全局搜索 |
| 验证型（build-verifier, e2e-verifier） | ≤20 次 | 以命令执行为主，搜索为辅 |

**每个需求点的搜索策略**（@tech-explorer 专用）：

```
第 1 轮（精确关键词）: ≤5 次搜索 → 找到匹配 → 早期终止
第 2 轮（同义词扩展）: ≤5 次搜索 → 无匹配时扩展关键词
第 3 轮（架构模式级）: ≤3 次搜索 → 按目录结构/设计模式搜索
合计: ≤13 次/需求点
```

**预算执行方式**：
- 预算为**建议性质**，不强制阻断 Agent 工作
- Agent 在实现报告/完成消息中汇报实际搜索次数
- 编排器在总结确认中展示搜索消耗，纳入 `contextHealth.phaseMetrics`
- 连续 2 个需求搜索超预算时，在 `/evolve` 中标记为待优化项

---

## 3. 子 Agent 注册表

> **注意**：以下注册表列出了通用的 Agent 角色。具体项目中，后端领域开发 Agent 的数量和领域划分由 Java 架构师根据项目实际情况动态确定，前端 Agent 的启用由 `state.json` 中 `platforms` 字段控制。

| Agent 文件 | 角色 | 调用阶段 |
|------------|------|----------|
| `agents/product-analyst.md` | 资深需求分析专家（单体/降级模式） | ANALYSE_PRODUCT |
| `agents/product-analysts/product-collector.md` | 需求信息收集员（Agent Teams 成员） | ANALYSE_PRODUCT |
| `agents/product-analysts/baseline-differ.md` | 基线对比专家（Agent Teams 成员） | ANALYSE_PRODUCT |
| `agents/product-analysts/product-extractor.md` | 需求提取专家（Agent Teams 成员） | ANALYSE_PRODUCT |
| `agents/product-analysts/quality-assessor.md` | 质量风险评估师（Agent Teams 成员） | ANALYSE_PRODUCT |
| `agents/fullstack-analyst.md` | 资深全栈开发专家（单体/降级模式） | ANALYSE_TECH |
| `agents/tech-analysts/tech-explorer.md` | 技术探索员（Agent Teams 成员） | ANALYSE_TECH |
| `agents/tech-analysts/tech-designer.md` | 技术设计师（Agent Teams 成员） | ANALYSE_TECH |
| `agents/tech-analysts/tech-splitter.md` | 分端文档生成器（Agent Teams 成员） | ANALYSE_TECH |
| `agents/tech-analysts/tech-reviewer.md` | 技术文档校审员（Agent Teams 成员） | ANALYSE_TECH |
| `agents/java-architect.md` | 资深 Java 架构师（Java 专版） | ARCHITECT_BACKEND |
| `agents/backend-architect.md` | 资深后台架构师（通用版，技术栈无关） | ARCHITECT_BACKEND |
| `agents/frontend-architect.md` | 资深前端架构师 | ARCHITECT_FRONTEND |
| `agents/java-domain-developers/*.md` | 后端领域开发 Agent（动态注册） | IMPLEMENT |
| `agents/web-developer.md` | 资深 Web 端代码开发 | IMPLEMENT（web） |
| `agents/miniprogram-developer.md` | 资深小程序端代码开发 | IMPLEMENT（miniprogram） |
| `agents/build-verifier.md` | 编译验证专家（单体/降级模式） | BUILD_VERIFY |
| `agents/build-verifiers/backend-build-verifier.md` | 后端编译验证（Agent Teams 成员） | BUILD_VERIFY |
| `agents/build-verifiers/web-build-verifier.md` | Web 端构建验证（Agent Teams 成员） | BUILD_VERIFY |
| `agents/build-verifiers/miniprogram-build-verifier.md` | 小程序端构建验证（Agent Teams 成员） | BUILD_VERIFY |
| `agents/e2e-link-verifier.md` | 端到端链路验证专家 | E2E_VERIFY |
| `agents/test-engineer.md` | 测试验证专家 | TEST |
| `agents/archiver.md` | 归档总结专家 | ARCHIVE |
| `agents/import-agents/doc-collector.md` | 项目文档收集与结构化专家 | knowledge-import |
| `agents/import-agents/codebase-profiler.md` | 代码库架构分析与画像专家 | knowledge-import |
| `agents/import-agents/knowledge-builder.md` | 知识标准化与基线构建专家 | knowledge-import |

### 3.1 子 Agent 调用规范

> **🚨 CRITICAL — Task 工具（code-explorer subagent）的权限限制**:
> 系统内置的 `code-explorer` subagent **只有只读权限**（仅支持 `search_file`、`search_content`、`read_file`、`codebase_search`、`list_dir`），**没有 `write_to_file` / `replace_in_file` 等写入能力**。
> **严禁通过 Task 工具调度需要写入文件的子 Agent**——这会导致产物无法写入，只能返回内容摘要。
> Task 工具仅可用于**只读探索任务**（如代码搜索、文件读取、项目结构分析）。

子 Agent 有两种调用方式，取决于当前阶段使用的调度模式：

#### 方式 A：Task 工具调用（非 Agent Teams 阶段 / 降级模式）

通过 Task 工具调用子 Agent 时，注入以下上下文：

1. 读取对应的 `agents/*.md` 文件作为 system prompt
2. 注入当前需求的 `state.json` 中的关键信息
3. 注入前序阶段的产物路径（作为输入）
4. 指定输出目录路径
5. 【ARCHITECT_BACKEND 阶段专用】额外注入总纲 `analysis/tech-requirements.md` 作为接口契约基准

**完成信号机制**: 子 Agent 完成后直接返回最终消息。编排器通过 Task 工具的返回值判断完成。

#### 方式 B：Agent Teams 成员（ANALYSE_PRODUCT / ANALYSE_TECH / ARCHITECT_BACKEND / IMPLEMENT / BUILD_VERIFY 阶段 Agent Teams 模式）

通过 Agent Teams 创建独立成员，每个成员拥有独立上下文窗口：

1. 编排器（team-lead）为每个领域创建成员，Prompt 中包含完整的工作指令
2. 成员 Prompt 中注入 Agent `.md` 文件路径（绝对路径），成员自行读取
3. 注入当前需求的关键信息（需求 ID、工作流路径）
4. 注入前序阶段产物路径和输出目录路径
5. 成员完成后向领导发送结构化完成消息

**完成信号机制**: 成员通过消息系统向领导发送完成通知，领导通过团队状态栏监控进度。

> 详细的 Agent Teams 调度规则见：
> - ANALYSE_PRODUCT 阶段：`phases/analyse-product-rules.md`
> - ANALYSE_TECH 阶段：`phases/analyse-tech-rules.md`
> - ARCHITECT_BACKEND 阶段：`phases/architect-backend-rules.md`
> - IMPLEMENT 阶段：`phases/implement-rules.md` §3
> - BUILD_VERIFY 阶段：`phases/build-verify-rules.md`

#### 路径传递机制（CRITICAL）

> **核心规则**: Agent 文档中的 Skill 内部规则文件采用**相对路径**引用。编排器在调用子 Agent 时（无论哪种方式），调用 `scripts/resolve_agent_paths.py --mode replace` **直接替换**为**绝对路径**。

```bash
python3 scripts/resolve_agent_paths.py \
  --agent-file agents/java-domain-developers/common-developer.md \
  --project-root . \
  --mode replace \
  --output json
```

| 规则 | 说明 |
|------|------|
| Agent 文档中 | **保持相对路径形式**，基准为 Agent 所在目录 |
| 编排器替换时 | 调用脚本一键替换所有相对路径为绝对路径 |
| 替换对象 | 仅替换反引号内的相对路径 |
| 产物路径 | 使用短路径，需编排器注入 |
| 源码产物例外 | 直接使用项目根目录相对路径，不需替换 |

> **Agent Teams 特别注意**: 成员不会继承领导的对话历史，因此 Prompt 中的所有路径**必须是绝对路径**。

---

## 4. 资产管理

### 4.1 存储根路径

```
docs/workflows/
```

### 4.2 需求目录结构

每个需求以 `YYYYMMDD-自定义名称` 命名，所有产物隔离存储：

```
docs/workflows/
  └── 20260316-用户注册优化/
      ├── state.json                          # 状态追踪核心文件
      ├── risks.json                          # 风险追踪文件
      ├── analysis/                           # 需求分析文件夹
      ├── architecture/                       # 技术设计文件夹（动态生成子目录）
      │   ├── backend/                        # 后端架构（含领域子目录，按需动态生成）
      │   │   └── domain-registry.json        # 🆕 领域注册表（领域划分确认后生成）
      │   ├── web/                             # Web 端架构（按需生成）
      │   └── miniprogram/                    # 小程序端架构（按需生成）
      ├── implementation/                     # 实现报告文件夹（⚠️ 仅存放报告，不存放源码）
      └── testing/                            # 测试方案文件夹
```

### 4.3 产物分类说明（CRITICAL）

产物严格分为两类，存放位置不同，**禁止混淆**：

- 🔵 **工作流产物**（`docs/workflows/{需求ID}/`）: 需求文档、架构文档、实现报告（仅报告）、测试文档、状态/风险文件
- 🟢 **源码产物**（项目源码目录）: Java 后端代码 → `{backend-root}/`，Web 端前端 → `{web-project}/`，小程序端 → `{miniprogram-project}/`
- 🟡 **工程日志**: Web 端工作日志 → `{web-project}/worklogs/web/`

> **路径占位符说明**：
> - `{backend-root}/` — 后端微服务组根目录（如 `microservice-group/`）
> - `{frontend-root}/` — 前端项目组根目录（如 `frontend-group/`）
> - `{web-project}/` — Web 端项目目录（如 `frontend-group/operation-fe/`）
> - `{miniprogram-project}/` — 小程序端项目目录（如 `frontend-group/miniprogram-fe/`）
> - `{skill-root}/` — 当前 Skill 的安装路径，由编排器在运行时注入
>
> **全新项目路径说明**：当 `projectType = "new"` 时，上述占位符的值由 INIT 阶段根据 PRD 技术分析结果自动推导设定（详见 §7.3 步骤 3）。编排器基于 PRD 涉及的平台（前端/后端/微服务）智能决定布局和路径，向用户确认后写入 `projectConfig`。

> **强约束**: `implementation/` 目录下**只存放实现报告**，**不存放源代码**。

### 4.4 目录动态生成规则

- 子目录根据 `state.json` 中 `platforms` 的 `enabled` 字段动态创建
- 禁止手动创建未启用平台的目录
- 平台变更后需补创建新启用平台对应的目录

---

## 5. 状态追踪（state.json）— 唯一状态源（CRITICAL）

> **⚠️ 方案 4 强制规则**: `state.json` 是每个需求的**唯一状态源**。编排器在**每次做出任何决策前**，**必须**先 `read_file` 重新读取 `state.json`，**禁止**依赖对话历史中的"记忆"来推断当前状态。

### 5.1 状态源读取协议

```
编排器每次执行以下操作前，必须先 read_file 读取最新 state.json：
  1. 阶段流转决策（进入下一阶段 / 回退）
  2. 子 Agent 调度（确定调用哪些 Agent）
  3. 产物路径计算（确定输入/输出路径）
  4. 断点恢复（确定从哪里继续）
  5. 状态展示（向用户展示当前进度）
```

### 5.2 核心字段

详细 Schema 见 `references/state-schema.json`。核心字段包括：
- `id` / `name` / `prdSource` / `description` — 需求元信息
- `currentPhase` — 当前阶段（唯一权威来源）
- `phaseHistory` — 阶段执行历史
- `platforms` — 各平台启用状态和进度
- `rollbackLog` — 回退操作日志
- `architectBackendMode` / `architectBackendCheckpoint` / `architectBackendTeam` — ARCHITECT_BACKEND 阶段的调度模式、检查点和团队状态
- `analyseProductMode` / `analyseProductTeam` / `analyseProductPipeline` / `analyseProductFallback` — ANALYSE_PRODUCT 阶段的调度模式、团队状态、管道状态和降级状态
- `analyseTechMode` / `analyseTechTeam` — ANALYSE_TECH 阶段的调度模式和团队状态
- `implementMode` / `agentTeam` — IMPLEMENT 阶段的调度模式和团队状态
- `buildVerifyMode` / `buildVerifyTeam` — BUILD_VERIFY 阶段的调度模式和团队状态
- `intentAnalysis` — IntentGate 意图分析结果（意图类型、歧义点、影响范围、路由提示）
- `contextHealth` — 运行时上下文健康度（阶段工具调用指标、压缩事件、整体风险等级）

### 5.3 状态更新规则（含流转守卫）

**基本规则**:
- 每个阶段开始时更新 `currentPhase` 和 `phaseHistory`
- 每个平台 Agent 执行完后更新 `platforms` 中对应的 `status`
- 回退时在 `rollbackLog` 中记录回退原因和被删除的产物
- 所有写入操作必须先读取再写入，避免并发冲突

**阶段计时协议（phaseHistory 时间字段写入时机）**:

每条 phaseHistory 记录包含 5 个时间字段，在创建时一次性预留全部字段（值为 null），后续各轮次逐个填充：

| 轮次 | 触发时机 | 写入字段 | 说明 |
|------|---------|---------|------|
| 预览展示 | 编排器开始构造预览输出 | `startedAt` = 当前时间，其余 4 个字段 = null | 创建整条记录 |
| 用户确认执行 | 收到用户"执行"指令 | `confirmedAt` = 当前时间，`executionStartedAt` = 当前时间 | 替换 null |
| Agent 完成 | Task 返回 / Teams 全员完成 | `executionCompletedAt` = 当前时间 | 替换 null |
| 总结确认 | 用户选择进入下一阶段 | `completedAt` = 当前时间，`status` = "completed" | 替换 null |

**特殊情况**:
- `INIT` 阶段：自动流转，5 个时间字段全部设为同一时间
- `skipped` 阶段：`startedAt` 和 `completedAt` 设为同一时间，其余 3 个字段为 null
- 澄清阶段（CLARIFY_*）：无 Agent 执行，`confirmedAt` 为用户开始回答的时间，`executionStartedAt`/`executionCompletedAt` 为编排器处理回填的开始/结束时间

**🚨 流转守卫协议（CRITICAL — 每次更新 currentPhase 前强制执行）**:

```
编排器在更新 state.json 的 currentPhase 字段时，MUST 执行以下校验流程：

步骤 1：读取 references/phase-transitions.json（若未在上下文中则 read_file 加载）
步骤 2：取出当前阶段的合法后继：transitions[currentPhase].next
步骤 3：取出当前阶段的可跳过目标：transitions[currentPhase].canSkipTo
步骤 4：校验目标阶段合法性
         - IF 目标阶段 == transitions[current].next → ✅ 允许
         - ELSE IF 目标阶段 == transitions[current].canSkipTo 且满足跳过条件 → ✅ 允许（记录 skipped）
         - ELSE IF 目标阶段 == "IMPLEMENT" 且当前阶段 == "BUILD_VERIFY"（回退特例） → ✅ 允许
         - ELSE → 🚫 阻断！输出告警：
           "🚨 流转守卫阻断: 从 {当前阶段} 到 {目标阶段} 是非法跳跃。
            合法后继为: {transitions[current].next}。请修正流转目标。"
步骤 5：写入前，在 phaseHistory 中确认所有前置阶段均已有记录（completed/skipped/rolled_back）
步骤 6：写入 currentPhase + phaseHistory
步骤 7：回读验证
```

**特别强调 — DONE 终态保护**:
- `currentPhase = "DONE"` **只能**由 `ARCHIVE` 阶段流转而来
- 除 ARCHIVE 阶段外的任何阶段，**严禁直接写入 `DONE`**
- 即使所有验证都通过（BUILD_VERIFY PASS、E2E_VERIFY PASS、TEST PASS），也**必须完整执行到 ARCHIVE 阶段**才能终结

### 5.4 阶段命名严格校验（🚨 CRITICAL — 防漂移防线）

#### 合法阶段 ID 白名单（唯一权威来源）

以下 15 个值是**唯一合法**的阶段 ID，任何不在此列表中的字符串**一律禁止**写入 `state.json`：

```
INIT | ANALYSE_PRODUCT | CLARIFY_PRODUCT | ANALYSE_TECH | CLARIFY_TECH
ARCHITECT_BACKEND | CLARIFY_ARCH_BACKEND | ARCHITECT_FRONTEND | CLARIFY_ARCH_FRONTEND
IMPLEMENT | BUILD_VERIFY | E2E_VERIFY | TEST | ARCHIVE | DONE
```

#### 常见误用对照表（禁止使用 → 正确写法）

| ❌ 禁止使用 | ✅ 正确写法 |
|-------------|------------|
| `DESIGN_BACKEND` | `ARCHITECT_BACKEND` |
| `DESIGN_FRONTEND` | `ARCHITECT_FRONTEND` |
| `ANALYZE_PRODUCT` | `ANALYSE_PRODUCT` |
| `ANALYZE_TECH` | `ANALYSE_TECH` |
| `CLARIFY_BACKEND` | `CLARIFY_ARCH_BACKEND` |
| `CLARIFY_FRONTEND` | `CLARIFY_ARCH_FRONTEND` |
| `VERIFY` / `BUILD` | `BUILD_VERIFY` |
| `E2E` / `LINK_VERIFY` | `E2E_VERIFY` |
| `COMPLETED` / `FINISHED` | `DONE` |

#### 写入前强制校验流程

每次更新 `state.json` 的阶段字段时：
1. 写入前自检 → 与白名单逐字比对
2. 如不匹配 → 停止写入，查对照表修正
3. 写入后回读验证 → 确认一致
4. 如回读不匹配 → 立即修正 + 输出告警

#### 阶段顺序校验

`phaseHistory` 中的阶段必须严格单调递增（允许 skipped，不允许乱序）。

#### 阶段完整性校验（写入 DONE 前的终极检查）

当目标 `currentPhase` 为 `DONE` 时，编排器 MUST 执行以下额外校验：

1. 遍历 phaseHistory，检查以下 **所有阶段** 均有记录（status 为 completed 或 skipped）：
   `INIT, ANALYSE_PRODUCT, CLARIFY_PRODUCT, ANALYSE_TECH, CLARIFY_TECH,
    ARCHITECT_BACKEND, CLARIFY_ARCH_BACKEND, ARCHITECT_FRONTEND, CLARIFY_ARCH_FRONTEND,
    IMPLEMENT, BUILD_VERIFY, E2E_VERIFY, TEST, ARCHIVE`

2. 若发现任何阶段**缺少记录**，立即阻断并输出：
   "🚨 终态校验失败: 以下阶段缺少 phaseHistory 记录: [{缺失的阶段列表}]。
    请先完成这些阶段后再设为 DONE。"

3. 允许 `rolled_back` 状态的记录存在（表示发生过回退），但**最终一轮**的执行记录必须为 `completed` 或 `skipped`。

注意：phaseHistory 可能包含同一阶段的多条记录（如 BUILD_VERIFY 多轮），校验时**只需确认该阶段至少有一条非 rolled_back 的终态记录**。

---

## 6. 风险追踪（risks.json）

独立的风险追踪文件，Schema 见 `references/risks-schema.json`。

**风险来源**: 澄清阶段跳过的问题 / 子 Agent front-matter 中的 `risks` 数组 / 回退事件

**编排器处理规则**: 每个阶段的"总结确认"步骤中，从产出物 front-matter 提取 risks，追加到 `risks.json`，设置 `status: "open"`。风险 ID 格式：`RISK-{阶段前缀}{序号}`。

---

## 7. 启动与恢复

### 7.1 触发方式

关键词："启动工作流"、"新建需求"、"继续工作流"、"恢复工作流"、"run agent workflow"、"工作流编排"、"开发流水线"、"查看工作流"、"工作流状态"

### 7.2 启动流程

1. 扫描 `docs/workflows/` 目录，读取所有需求的 `state.json`
2. **PRD 重复检测**: 若传入 PRD 路径，检查已有需求的 `prdSource` 是否匹配 → 匹配则进入重复处理流程
3. 检查是否有进行中的需求 → 列出让用户选择继续或新建
4. **必须等待用户确认后再执行**

### 7.3 新建需求流程（INIT 阶段）

1. 从 PRD 解析需求信息（或询问用户输入）
2. **项目类型写入**：从 `/flow-run` Step 0 传入的项目类型信息写入 `state.json` 的 `projectConfig.projectType`
3. **工作区布局与路径脚手架**（全新项目专用，`projectType = "new"` 时执行）：

   > **核心思路**：布局决策不再由 `/flow-run` 提前传入，而是在 INIT 阶段基于 PRD 的技术分析结果（涉及哪些平台、是否有前后端分离等），由编排器**自主推导**最合适的目录结构，并向用户确认。

   a) **从 PRD 中提取技术特征**（复用步骤 1 的 PRD 解析结果）：
      - 是否涉及前端（Web / 小程序）
      - 是否涉及后端
      - 是否涉及多个独立服务（微服务架构）

   b) **自动推导布局和项目名**：

      **单一前端项目**（PRD 仅涉及一个 Web 或小程序，无后端）：
      - `workspaceLayout = "separated"`
      - `projectName` = 从 PRD 标题/描述中提取，或使用合理的默认名
      ```
      projectConfig.frontendRoot = "{projectName}/"
      projectConfig.webProject = "{projectName}/"
      projectConfig.backendRoot = null
      ```

      **前后端分离项目**（PRD 涉及后端 + 前端）：
      - `workspaceLayout = "separated"`
      - `projectName` = 从 PRD 标题/描述中提取
      ```
      projectConfig.frontendRoot = "{projectName}-frontend/"
      projectConfig.webProject = "{projectName}-frontend/"
      projectConfig.backendRoot = "{projectName}-backend/"
      ```

      **全栈 + 微服务**（PRD 涉及多个后端服务 + 前端）：
      - `workspaceLayout = "separated"`
      - `projectName` = 从 PRD 标题/描述中提取
      ```
      projectConfig.frontendRoot = "frontend/"
      projectConfig.webProject = "frontend/{projectName}-web/"
      projectConfig.backendRoot = "backend/"
      projectConfig.miniprogramProject = "frontend/{projectName}-miniprogram/"  # 若涉及小程序
      ```

   c) **路径确认**：向用户展示推导出的目录结构规划和项目名称，要求确认或修改：

      ```
      📁 项目目录结构规划：

      项目名称：{projectName}
      工作区布局：分离结构（每个子项目有独立目录）

      {根据布局和平台生成的目录树预览}

      请确认以上目录结构和项目名称，或输入修改建议。
      ```

   d) **写入 `projectConfig`**：用户确认后写入 `state.json`：
      - `workspaceLayout`: `"separated"`（或用户明确要求 `"flat"` 时写入 `"flat"`）
      - `projectName`: 确认后的项目名
      - 各路径字段按上述规则写入

   e) **目录创建**：确认后，在 IMPLEMENT 阶段首次执行时由开发 Agent 自动创建所需目录（INIT 阶段仅规划，不创建目录）

4. **项目仓库加载**（从 `project.yaml` 读取已绑定的 `repos[]`，不重复扫描）：
   
   > **核心原则**：仓库绑定在 `/team-init` 时由用户确认并持久化到 `project.yaml`。INIT 阶段直接读取，不再重复扫描工作区。
   
   a) 从 `{项目根目录}/.ai-team/project.yaml` 读取 `repos[]` 字段
   b) 如果 `repos[]` 存在且非空 → 直接写入 `state.json` 的 `projectConfig.repos`
   c) 同时填充旧字段（兼容）：
      - `backendRoot` = 第一个 `type=backend` 的 `repo.path`（无则 null）
      - `frontendRoot` = 第一个 `type=frontend` 的 `repo.path`（无则 null）
      - `webProject` = 第一个 `type=frontend` 的 `repo.path`（无则 null）
      - `miniprogramProject` = 第一个 `type=miniprogram` 的 `repo.path`（无则 null）
      - `commonModule` = 第一个 `type=common` 的 `repo.name`（无则 null）
   d) 如果 `repos[]` 不存在或 `project.yaml` 不存在 → 提示用户执行 `/team-init` 绑定仓库
   e) **不执行任何文件系统扫描**——扫描只在 `/team-init` 中进行一次
5. **全局知识路径注入**（团队共享知识架构）：
   a) 检查 `{项目根目录}/.ai-team/project.yaml` 是否存在
   b) 如存在，读取并将以下信息写入 `state.json` 的 `knowledgeContext` 字段：
      - `knowledgeRepoLocalPath: "{knowledge_repo.local_path}"` （从 project.yaml 读取）
      - `knowledgeRepoUrl: "{knowledge_repo.url}"` （从 project.yaml 读取）
      - `knowledgeCatalogPath: "{knowledge_repo.local_path}/knowledge-catalog.md"` （全景目录，所有 Agent 的查询入口）
      - `globalPreferencesPath: "~/.ai-team/preferences/"` （个人偏好，纯本地）
      - `globalTeamConventionsPath: "{knowledge_repo.local_path}/team-conventions/"` 
      - `globalTechWikiPath: "{knowledge_repo.local_path}/tech-wiki/"`
      - `globalBizWikiPath: "{knowledge_repo.local_path}/biz-wiki/{domain}/"` （domain 从 project.yaml 读取）
      - `projectDomain: "{domain}"` （从 project.yaml 读取）
      - `projectTechStack: [...]` （从 project.yaml 读取）
      - `contributorName: "{name}"` （从 ~/.ai-team/preferences/profile.yaml 读取）
      - `contributorRole: "{role}"` （从 {knowledge_repo.local_path}/.knowledge-config.yaml 匹配当前用户）
   c) 如 `knowledge_repo.auto_pull` 为 true，自动拉取最新知识：
      ```bash
      cd {knowledge_repo.local_path} && git pull --rebase origin main
      ```
   d) **知识查询入口注入**（不再推送 Top-5，改为提供查询入口）：
      在编排器将任务分配给各阶段 Agent 时，注入以下查询入口信息：
      ```
      【知识查询入口】
      - 团队知识全景: {knowledgeCatalogPath}
      - 项目归档索引: docs/workflows/archived/index.md
      - 项目知识库: docs/knowledge-base/index.md
      
      查询方式: 渐进式加载（先读 catalog.md 目录 → 按需读完整条目）
      查询预算: 见各 Agent 定义中的知识查询能力章节
      ```
   e) 如不存在，设置以上字段为 null，并在 INIT 完成后提示：
      ```
      💡 当前项目未配置 .ai-team/project.yaml
      
      执行 /team-init 可初始化项目配置，连接团队知识仓库，启用跨项目知识复用。
      此操作不阻断工作流，可稍后执行。
      ```
6. **知识基线注入**（Phase 3 — 知识消费闭环）：
   a) 检查 `docs/knowledge-import/knowledge-baseline.json` 是否存在
   b) 如存在，读取并将以下信息写入 `state.json` 的 `knowledgeContext` 字段：
      - `baselineAvailable: true`
      - `baselinePath: "docs/knowledge-import/knowledge-baseline.json"`
      - `profilePath: "docs/knowledge-import/codebase-profile.json"`
      - `storyIndexPath: "docs/knowledge-import/tapd-stories/_story-index.json"`（仅当该文件存在时设置，否则为 null）
      - `importedKeywords: [...]`（从 `docs/knowledge-import/SUMMARY.md` front-matter 提取）
   c) 如不存在，设置 `knowledgeContext.baselineAvailable: false`
7. **TAPD 集成检测**（非阻断，自动探测）：
   a) **凭证检测**: 使用 `search_file` 检查 `~/.tapd/credentials` 文件是否存在
   b) **MCP 工具检测**: 尝试调用 `CallMcpTool: user-tapd_mcp_http / lookup_tool_param_schema`（参数: `{"tool_name": "stories_get"}`），判断 TAPD MCP 服务是否已连接
   c) 写入 `state.json` 的 `tapdConfig` 字段：
      - `available: true/false`（凭证 + MCP 均就绪时为 true）
      - `credentialsFound: true/false`
      - `mcpConnected: true/false`
   d) **引导输出**（仅当 `available = false` 时，非阻断）：

      ```
      💡 TAPD 集成未就绪（当前工作流仍可正常运行）

      {根据缺失项选择性输出}:
      - ❌ 凭证文件缺失 → 请创建 ~/.tapd/credentials 并写入 access_token=<你的TAPD访问令牌>
      - ❌ MCP 工具未连接 → 请在 IDE 设置中连接 TAPD MCP 服务（user-tapd_mcp_http）

      配置完成后，下次启动工作流将自动激活 TAPD 能力（需求同步、附件管理等）。
      ```

      - 设置 `tapdConfig.setupGuideShown: true`，避免后续工作流重复提示
      - ⚠️ **此步骤不阻断流程**：无论 TAPD 是否可用，均继续执行后续步骤
   e) **workspace_id 采集**（仅当 `available = true` 且 `workspaceId` 为空时）：
      - 使用 `ask_followup_question` 询问用户 TAPD 项目 ID
      - 写入 `tapdConfig.workspaceId`
8. 创建目录结构 `docs/workflows/YYYYMMDD-需求名称/`（含 state.json、risks.json、子目录）
9. 自动流转到 ANALYSE_PRODUCT

### 7.4 断点恢复

- 所有状态存储在文件系统，会话完全无状态
- 恢复时 **read_file 读取 `state.json`** 获取 `currentPhase`
- 检查当前阶段是否有未完成的产物，决定从"预览"还是"总结确认"恢复
- **ARCHITECT_BACKEND 检查点恢复**: 若 `currentPhase = ARCHITECT_BACKEND`，读取 `architectBackendCheckpoint.step` 判断内部进度，从检查点继续执行而非从头开始（详见 `phases/architect-backend-rules.md` §2.3）
- **ANALYSE_PRODUCT 三级恢复**: 若 `currentPhase = ANALYSE_PRODUCT`，读取 `analyseProductMode` 判断调度层级。`agent-teams` → 读取 `analyseProductTeam` 恢复团队进度；`task-pipeline` → 读取 `analyseProductPipeline.completedTasks` 从断点 Task 继续；`fallback` → 读取 `analyseProductFallback.availableArtifacts` 判断可复用产物后直接执行（详见 `phases/analyse-product-rules.md` §6）

### 7.5 PRD 重复处理

匹配时提供三个选项：继续该需求 / 重新开始（二次确认后删除旧需求）/ 取消操作。输出格式见 `phases/output-formats/common.md` §5-6。

---

## 8. 多需求并行管理

- 多个需求可同时存在于不同阶段（独立目录，完全隔离）
- 采用**并行存储、串行执行**模型
- 切换需求时保存当前上下文，加载目标需求上下文

---

## 9. 编排器行为约束

### 9.1 必须做的（DO）

- ✅ **每次决策前 read_file 读取最新 state.json**（方案 4 核心要求）
- ✅ 每次状态变更后立即更新 state.json
- ✅ ARCHITECT_BACKEND 阶段每个产物落盘后立即更新 `architectBackendCheckpoint`（检查点保护）
- ✅ ARCHITECT_BACKEND 阶段 Step 1 完成后**必须**展示领域划分确认单（Step 1.5），等待用户确认后才能启动 Step 2
- ✅ 领域划分确认后**必须**写入 `domain-registry.json` 并更新检查点为 `domains_confirmed`
- ✅ 调用子 Agent 前展示预览并等待用户确认
- ✅ 澄清阶段跳过的问题必须写入 risks.json
- ✅ 回退操作必须二次确认 + 删除产物
- ✅ 根据 `platforms.enabled` 动态调度 IMPLEMENT 阶段
- ✅ 有接口交互时后端 Agent 先于前端 Agent 执行
- ✅ 进入阶段前加载对应的规则片段文件（见 §10）
- ✅ ANALYSE_PRODUCT Agent Teams 模式下**严格遵守上下文防火墙**：@product-extractor 禁止读取原始 PRD，只消费上游压缩中间产物
- ✅ ANALYSE_PRODUCT 阶段 Agent Teams 创建失败时，**自动降级到 Task 串行管道**，Task 管道失败再降级到 orchestrator 直接执行（三级降级）
- ✅ INIT 完成后、进入 ANALYSE_PRODUCT 前，**执行 IntentGate 意图分析**（§2.6），将结果写入 `state.json` 的 `intentAnalysis` 字段
- ✅ **每次阶段切换时**，更新 `contextHealth.phaseMetrics`，估算工具调用次数和风险等级（§2.7）
- ✅ 检测到上下文压缩事件后，**必须重新 read_file 读取 state.json**，并记录到 `contextHealth.compactionEvents`
- ✅ 当 `intentAnalysis.intentType = "d2c-to-workflow"` 时，IMPLEMENT 阶段前端部分**跳过执行**（D2C 已完成前端代码），仅调度后端领域 Agent（如有）
- ✅ 当 `intentAnalysis.d2cConfig` 存在且 `status = "completed"` 时，ANALYSE_PRODUCT/ANALYSE_TECH/ARCHITECT_FRONTEND 各阶段**简化执行**（读取 D2C 产物信息后快速通过，不做深度分析）

### 9.2 禁止做的（DON'T）

- ❌ 禁止依赖对话历史"记忆"推断当前状态（必须从 state.json 读取）
- ❌ 禁止跳过任何阶段（澄清自动跳过除外）
- ❌ 禁止在没有用户确认的情况下执行子 Agent（INIT 除外）
- ❌ 禁止直接修改子 Agent 的产出物（唯一例外：澄清回填）
- ❌ 禁止编排器自己执行分析、设计、编码等具体工作
- ❌ 禁止在回退时保留被回退阶段的产物
- ❌ 禁止创建未启用平台的目录
- ❌ 禁止跳过 Step 1.5 领域划分确认关卡直接启动领域架构师（ARCHITECT_BACKEND 阶段）
- ❌ 禁止创建超过 8 个领域（必须先合并再继续）
- ❌ 禁止在 ANALYSE_PRODUCT 阶段绕过三级降级策略直接选择低级模式（必须从 L1 → L2 → L3 逐级降级）
- ❌ 禁止在 ANALYSE_PRODUCT Agent Teams 模式下跳过 @product-collector 直接调度下游成员（上下文防火墙依赖 collector 的压缩产物）

---

## 10. 阶段规则按需加载映射表（CRITICAL）

> **核心机制**: 编排器在进入每个阶段前，`read_file` 加载对应的规则片段。仅加载当前阶段需要的规则，减少上下文噪声，提升注意力精准度。

| 当前阶段 | 需加载的规则片段 | 说明 |
|---------|----------------|------|
| ANALYSE_PRODUCT | `phases/analyse-product-rules.md` | 三级降级调度 + Agent Teams 四成员串行协作规则 + 上下文防火墙 + 知识基线注入协议 |
| CLARIFY_PRODUCT | `phases/clarify-rules.md` | 澄清流程 + 回填规范 |
| CLARIFY_TECH | `phases/clarify-rules.md` | 同上 |
| CLARIFY_ARCH_BACKEND | `phases/clarify-rules.md` | 同上 |
| CLARIFY_ARCH_FRONTEND | `phases/clarify-rules.md` | 同上 |
| ANALYSE_TECH | `phases/analyse-tech-rules.md` | 调度模式选择 + Agent Teams 四成员串行协作规则 + 代码画像注入协议 |
| ARCHITECT_BACKEND | `phases/architect-backend-rules.md` | 调度模式选择 + Agent Teams 两步模式 + 检查点机制 |
| IMPLEMENT | `phases/implement-rules.md` | 动态调度 + Agent Teams 模式 + 编译修复模式 + D2C 嵌入模式 |
| BUILD_VERIFY | `phases/build-verify-rules.md` | 调度模式选择 + Agent Teams 规则 + 精细化回退策略 |
| 任何阶段的"预览"/"总结确认" | `phases/output-formats/common.md` | 通用展示格式（预览/总结/澄清/列表/PRD重复/二次确认） |
| ANALYSE_PRODUCT 的"预览"/"总结" | `phases/output-formats/common.md` + `phases/output-formats/analyse-product-formats.md` | 通用格式 + ANALYSE_PRODUCT Agent Teams 专用格式 |
| ANALYSE_TECH 的"预览"/"总结" | `phases/output-formats/common.md` + `phases/output-formats/analyse-tech-formats.md` | 通用格式 + ANALYSE_TECH Agent Teams 专用格式 |
| ARCHITECT_BACKEND 的"预览"/"总结" | `phases/output-formats/common.md` + `phases/output-formats/architect-backend-formats.md` | 通用格式 + ARCHITECT_BACKEND Agent Teams 专用格式 |
| IMPLEMENT 的"预览"/"总结" | `phases/output-formats/common.md` + `phases/output-formats/implement-formats.md` | 通用格式 + IMPLEMENT Agent Teams 专用格式 |
| BUILD_VERIFY 的"预览"/"总结" | `phases/output-formats/common.md` + `phases/output-formats/build-verify-formats.md` | 通用格式 + BUILD_VERIFY Agent Teams 专用格式 |
| 用户选择"回退"时 | `phases/rollback-rules.md` | 通用回退规则 + 产物删除映射 |
| BUILD_VERIFY + 回退 | `phases/rollback-rules.md` + `phases/build-verify-rules.md` | 精细回退需同时加载 |
| 任何阶段的"总结确认"后的流转决策 | `references/phase-transitions.json` | 流转守卫校验 |
| **knowledge-import 模式** | `phases/import-rules.md` | 历史项目知识导入编排规则（3 个导入 Agent 串行调度） |

**加载示例**:

```
编排器进入 ANALYSE_PRODUCT 阶段：
  1. read_file("state.json")                             ← 方案 4：读取唯一状态源
  2. read_file("phases/analyse-product-rules.md")        ← 方案 2：按需加载阶段规则
  3. 默认使用 Agent Teams 模式（L1），创建失败时降级为 Task 串行管道（L2），管道失败再降级为 orchestrator 直接执行（L3）
  4. L1 Agent Teams 模式：创建团队 → T1(@product-collector) → [条件]T2(@baseline-differ) → T3(@product-extractor) → T4(@quality-assessor) → 清理团队
     L2 Task 管道模式：Task1(collector+differ) → Task2(extractor+assessor)；增量需求时 Task1 → Task2 → Task3
     L3 直接执行模式：编排器加载 product-analyst.md 直接执行（单体 Agent 降级）

编排器进入 ANALYSE_TECH 阶段：
  1. read_file("state.json")                         ← 方案 4：读取唯一状态源
  2. read_file("phases/analyse-tech-rules.md")       ← 方案 2：按需加载阶段规则
  3. 默认使用 Agent Teams 模式（创建失败时降级为 Task 模式）
  4. Agent Teams 模式：创建团队 → T1(@tech-explorer) → T2(@tech-designer) → T3(@tech-splitter) → T4(@tech-reviewer) → 清理团队
     Task 模式：调用单体 fullstack-analyst Agent

编排器进入 ARCHITECT_BACKEND 阶段：
  1. read_file("state.json")                              ← 方案 4：读取唯一状态源
  2. read_file("phases/architect-backend-rules.md")       ← 方案 2：按需加载阶段规则
  3. 检查 architectBackendCheckpoint 决定断点恢复策略
  4. 判断调度模式（Agent Teams / Task 工具降级）
  5. Agent Teams 模式：创建团队 → S1(@global-architect) → 检查点落盘 → S2(@domain-architect-*并行) → 逐个检查点落盘 → 清理团队
     Task 模式：调用 §0.1 选择的单体架构师 Agent（java-architect 或 backend-architect）

编排器进入 IMPLEMENT 阶段：
  1. read_file("state.json")                    ← 方案 4：读取唯一状态源
  2. read_file("phases/implement-rules.md")     ← 方案 2：按需加载阶段规则
  3. 根据 state.json 中 platforms 和 rollbackLog 做调度决策
  4. 判断调度模式（Agent Teams / Task 工具降级）
  5. Agent Teams 模式：创建团队 → 分配任务 → 监控完成 → 清理团队
     Task 模式：按 P0→P4 串行调用 Task 工具
```

---

## 11. 子 Agent 规则加载

### 原则

1. **声明即权威**：每个子 Agent 的 `.md` 文件中已声明自己引用哪些 `rules/` 文件及加载时机，以 Agent 自身声明为准，本节不重复罗列。
2. **按需加载**：子 Agent 仅在实际执行任务时加载所需规则，不预加载全部规则到上下文。
3. **目录结构**：`rules/java-backend/` 是目录（含多个子规则文件），由 `meta-rule.md` 总纲按需索引其余子文件；其余规则为独立的单文件。
4. **编排层不干预**：Orchestrator 不负责规则内容的分发或注入，仅在 spawn 子 Agent 时传入 Agent `.md` 路径，由子 Agent 自行根据声明加载规则。

## 11.5 代码溯源标记机制（@changelog 索引）

> **设计来源**：借鉴 agentic-mall 项目 1800+ 文件的生产验证经验。通过在每个源文件头部维护结构化变更索引，实现 O(1) 的需求-代码关联查找，大幅降低 Agent 搜索成本。

### 11.5.1 标记范围

| 平台 | 标记方式 | 强制/推荐 |
|------|---------|----------|
| Java 后端 | 类级 Javadoc 中的 `@changelog` 表格 | **强制**（详见 Agent 模板 `_template.md`） |
| Web 前端 | 文件头部 JSDoc 注释中的 `@changelog` 表格 | **强制** |
| 小程序端 | 文件头部 JSDoc 注释中的 `@changelog` 表格 | **强制** |

### 11.5.2 标记格式（TypeScript/JavaScript）

Web 端和小程序端源文件在文件顶部（import 语句之前）使用以下格式：

```typescript
/**
 * @changelog
 * | 版本   | 需求/方案 ID | 变更摘要 | 日期 |
 * |--------|-------------|---------|------|
 * | v1.0.0 | REQ:{需求ID} | 初始创建 | {YYYY-MM-DD} |
 * |        | TECH:architecture/{platform}/architecture.md | | |
 * @author agent:{agent-name}
 */
```

### 11.5.3 标记规则

| 规则 | 说明 |
|------|------|
| **新建文件** | 必须添加完整 `@changelog`，版本 `v1.0.0` |
| **修改文件** | 必须在 `@changelog` 表格中**追加新行**，版本号递增 |
| **`REQ:` 前缀** | 关联需求 ID（来自 `state.json` 的 `id` 字段） |
| **`TECH:` 前缀** | 关联技术方案文档路径（相对于 `docs/workflows/{需求ID}/`） |
| **`@author`** | 标注执行 Agent 名称（如 `agent:web-developer`、`agent:miniprogram-developer`） |

### 11.5.4 索引消费方

| 消费方 | 用途 |
|--------|------|
| @tech-explorer | 通过 `@changelog` 中的 REQ/TECH 快速判断文件与当前需求的关联性，减少无效搜索 |
| @baseline-differ | 通过 REQ 前缀快速定位前一版需求涉及的所有文件 |
| /evolve 命令 | 通过 `@author` 标注追踪 Agent 责任链，辅助根因分析 |
| quality-guardian | 检测遗漏 `@changelog` 标注的文件，纳入代码质量评分 |

---

## 12. 项目适配配置

> 本节说明如何将通用编排器适配到具体项目。编排器在 INIT 阶段读取项目配置，将占位符替换为实际路径。

### 12.1 路径占位符映射

在 `state.json` 的 `projectConfig` 字段中配置（INIT 阶段由用户确认或自动检测）：

| 占位符 | 说明 | 示例值 | 检测方式 |
|--------|------|--------|----------|
| `{backend-root}` | 后端微服务组根目录 | `microservice-group/` | 扫描项目根目录，识别含后端特征文件（pom.xml/package.json/go.mod 等）的顶层目录 |
| `{frontend-root}` | 前端项目组根目录 | `frontend-group/` | 扫描项目根目录，识别含前端特征文件（package.json + src/）的顶层目录 |
| `{web-project}` | Web 端项目目录 | `frontend-group/operation-fe/` | 在 `{frontend-root}` 下扫描含 vite.config / next.config 等 Web 构建配置的子目录 |
| `{miniprogram-project}` | 小程序端项目目录 | `frontend-group/miniprogram-fe/` | 在 `{frontend-root}` 下扫描含 app.config.ts / project.config.json 等小程序配置的子目录 |
| `{common-module}` | 后端公共模块名称 | `vibe-common` | 扫描 `{backend-root}` 下名称含 common/shared/base/core 的模块目录 |
| `{skill-root}` | Skill 安装路径（运行时自动注入） | `.codebuddy/skills/workflow-orchestrator/` | 运行时由编排器自动注入，无需用户配置 |

> **历史项目适配说明**: INIT 阶段编排器会尝试自动检测上述占位符的值。若项目结构非标准（如单体后端无独立根目录），编排器将展示检测结果并询问用户确认或手动指定。所有下游 Agent（架构师、开发 Agent）通过占位符引用路径，不再硬编码具体目录名。

> **全新项目适配说明**（`projectType = "new"`）: 全新项目无法通过文件扫描检测路径，编排器在 INIT 阶段基于 PRD 技术分析结果（涉及的平台和架构复杂度）自动推导目录布局和路径：
> - 编排器分析 PRD 中涉及的技术栈（前端/后端/微服务），自动选择最合适的 `workspaceLayout`（默认 `separated`）并推导 `projectName`
> - 根据平台数量和架构复杂度推导子目录路径（如 `{projectName}-frontend/`、`{projectName}-backend/`）
> - 推导结果向用户展示确认后写入 `projectConfig`，实际目录在 IMPLEMENT 阶段由开发 Agent 按需创建
>
> 推导结果同样写入 `projectConfig` 的路径字段，下游 Agent 通过相同的占位符机制消费，**无需感知项目是全新还是历史**。

### 12.2 后端领域开发 Agent 动态注册

后端领域开发 Agent 不硬编码固定数量，而是由 Java 架构师在 ARCHITECT_BACKEND 阶段根据项目实际情况动态确定：

1. 架构师分析项目需求，确定微服务拆分方案
2. 为每个微服务生成对应的领域技术需求文档
3. IMPLEMENT 阶段根据 `priority-list.md` 中的优先级顺序调度对应的领域开发 Agent

### 12.3 通知机制（可选）

编排器支持在关键阶段完成时发送通知。通知配置通过 `state.json` 的 `notificationConfig` 字段控制：

```json
{
  "notificationConfig": {
    "enabled": false,
    "provider": "custom",
    "events": ["phase_complete", "quality_gate_fail", "workflow_done"]
  }
}
```

当 `enabled: false` 时，所有通知静默跳过。具体的通知实现由项目自行配置。

### 12.4 TAPD 集成（可选）

编排器支持与 TAPD 项目管理平台集成，提供需求拉取、附件管理等能力。集成状态通过 `state.json` 的 `tapdConfig` 字段控制。

#### 前置条件

| 组件 | 说明 | 检测方式 |
|------|------|---------|
| **凭证文件** | `~/.tapd/credentials`，含 `access_token=<令牌>` | INIT 阶段自动检测文件存在性 |
| **MCP 服务** | `user-tapd_mcp_http` 已在 IDE 中连接 | INIT 阶段尝试调用 `lookup_tool_param_schema` 探测 |
| **workspace_id** | TAPD 项目 ID | INIT 阶段询问用户（仅当凭证 + MCP 均就绪时） |

#### 激活后解锁的能力

| 能力 | 使用阶段 | 说明 |
|------|---------|------|
| **TAPD 需求拉取** | `/flow-import`、`@doc-collector` | 从 TAPD 链接直接拉取需求内容作为项目文档输入 |
| **图片/附件上传** | ARCHIVE | 将产出物上传到 TAPD 需求/缺陷作为附件 |
| **附件查询与下载** | 任意阶段 | 通过 MCP 工具查询和下载 TAPD 附件 |

#### 配置示例

```json
{
  "tapdConfig": {
    "available": true,
    "credentialsFound": true,
    "mcpConnected": true,
    "workspaceId": "20088921",
    "setupGuideShown": false
  }
}
```

当 `available: false` 时，所有 TAPD 相关功能静默跳过，不影响工作流正常执行。编排器在 INIT 阶段自动检测并引导配置（仅首次提示，`setupGuideShown: true` 后不再重复）。
