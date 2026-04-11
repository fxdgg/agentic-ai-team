---
name: evolve
description: 流水线进化分析。基于刚修复的 Bug，自动追溯根因到流水线的哪个 Agent 环节，产出结构化改进建议并存入进化日志。任何开发者都可触发，改进记录仅做沉淀，不会直接修改流水线定义。
---

# 流水线进化分析 (Evolve)

## 指令概述

本指令用于在 Bug 修复后，**回溯根因到 AI 开发流水线的 Agent 环节**，产出结构化的改进建议并存入进化日志目录。

**核心原则：只分析、只记录，不修改任何 Agent 定义文件或流水线配置。**

> 改进记录的实际落地由流水线 Owner 通过 `/evolve-apply` 指令择优执行。

---

## 适用场景

- 刚修复了一个 Bug（通过 `/dev-bugfix` 或手动修复），想分析"为什么流水线没有避免这个问题"
- 发现流水线产出的代码有系统性缺陷模式，想记录下来供后续优化
- 多人协作中，开发者希望沉淀改进建议，由 Owner 统一 review 后落地

---

## 进化日志存储

### 目录结构（按状态子目录分流）

```
docs/workflows/evolve-log/
├── pending/          ← /evolve 产出直接写入这里
├── applied/          ← /evolve-apply 接受后移入
├── rejected/         ← /evolve-apply 拒绝后移入
└── deferred/         ← /evolve-apply 暂缓后移入
```

> **核心设计**：文件所在子目录即代表状态，无需解析 frontmatter 即可判断。`/evolve-apply` 只需扫描 `pending/` 目录即可获取待处理列表。

### 文件命名

```
{YYYYMMDD}-{序号}-{简短标题}.md
```

示例：`20260322-001-运营端菜单路由缺失.md`

### 文件格式

```markdown
---
id: evolve-{YYYYMMDD}-{序号}
title: {改进标题}
status: pending
created: {YYYY-MM-DD}
author: {提交人姓名，从 ~/.ai-team/preferences/profile.yaml 的 name 字段读取}
bug_source: {Bug 来源描述}
affected_agents:
  - {agent文件名1}
  - {agent文件名2}
context_health:
  compaction_count: {N}
  risk_level: {healthy/attention/warning/critical}
  is_contributing_factor: {true/false}
context_dashboard: {true/false}
applied_date:
applied_by:
---

## 1. Bug 回顾

...

## 2. 根因分析

...

### 2.1 上下文健康度分析

...

## 3. 关联 Agent 审查

...

## 4. 改进建议

...
```

## 5. 上下文复盘（当 contextHealth 数据可用时）

...
```

**状态流转**（通过 `git mv` 移动文件到对应子目录实现）：
- `pending/` — 新产出，等待 Owner review（`/evolve` 产出的默认状态）
- `applied/` — 已落地到流水线（由 `/evolve-apply` 移入）
- `rejected/` — Owner review 后决定不采纳（由 `/evolve-apply` 移入）
- `deferred/` — 暂缓，后续再处理（由 `/evolve-apply` 移入）

> frontmatter 中的 `status` 字段保留作为冗余记录，但**主判断依据是文件所在目录**。

---

## 执行流程

### Phase 1：Bug 回顾

**目标**：收集 Bug 的完整上下文。

1. **检查用户输入**：
   - 用户可能在指令后附带 Bug 描述（如 `/evolve 运营端菜单路由缺失导致页面 404`）
   - 用户也可能不带描述直接输入 `/evolve`

2. **信息收集**（如果用户未提供足够信息，主动询问）：
   - Bug 现象是什么？
   - 修复了哪些文件？（可通过 `git diff` 或用户描述获取）
   - 这个 Bug 是在哪个需求/工作流中引入的？（可选）
   - 是开发阶段引入还是架构设计遗漏？
   - **提交人**：从 `~/.ai-team/preferences/profile.yaml` 的 `name` 字段读取（由 `/team-init` 配置），如果不存在则提示用户执行 `/team-init`。填入 `author` 字段。**注意：`author` 是触发 `/evolve` 的人的姓名，不是 bug_source 或触发方式。**

3. **输出**：整理为结构化的 Bug 回顾，包含现象、影响范围、修复内容摘要。

### Phase 2：根因分析与 Agent 追溯

**目标**：判断 Bug 根因映射到流水线的哪个 Agent 环节。

1. **阅读 Agent 注册表**：
   - 读取 `.claude/skills/workflow-orchestrator/SKILL.md` 中的 §3 子 Agent 注册表
   - 理解每个 Agent 的职责边界

2. **根因分类**：根据 Bug 类型判断属于哪个层级的问题

   | Bug 类型 | 可能关联的 Agent | 说明 |
   |---------|-----------------|------|
   | 需求遗漏/理解偏差 | product-analyst | 需求分析阶段未识别 |
   | 技术方案缺陷 | fullstack-analyst | 技术可行性分析遗漏 |
   | 后端架构设计问题 | java-architect | 架构设计缺陷 |
   | 前端架构设计问题 | frontend-architect | 架构设计缺陷 |
   | 后端领域代码缺陷 | backend-developers/* | 具体领域开发 Agent |
   | Web 端代码缺陷 | web-developer | Web 端开发 Agent |
   | 小程序端代码缺陷 | miniprogram-developer | 小程序端开发 Agent |
   | 编译/构建问题 | build-verifier | 编译验证遗漏 |
   | 端到端联调问题 | e2e-link-verifier | 链路验证遗漏 |
   | 测试覆盖不足 | test-engineer | 测试方案不充分 |

3. **深入审查关联 Agent**：
   - 读取关联 Agent 的定义文件（`agents/*.md`）
   - 读取该 Agent 引用的规则文件（`rules/*.md`）
   - 分析：Agent 的提示词中是否缺少对此类问题的指导？规则文件是否有遗漏？

4. **输出**：明确列出根因链路和关联的 Agent 文件。

### Phase 2.5：上下文健康度分析

**目标**：检测 Bug 关联的工作流会话是否发生过上下文压缩，评估压缩是否为 Bug 的隐性根因。

> **设计意图**：Agent 在执行任务过程中触发上下文压缩（Context Compaction）后，关键信息可能丢失，导致后续输出质量下降。本步骤检测"上下文压缩"这一难以直接观察的隐性因素。

1. **定位会话日志**：
   - 在 `~/.claude/projects/` 下，按项目路径哈希查找对应的项目目录
   - 列出该目录下的 `.jsonl` 会话日志文件
   - 按修改时间筛选 Bug 引入时间窗口内的会话文件（如果能从 git log 确定 Bug 引入时间）
   - 如果无法定位会话文件（目录不存在、文件为空等），在输出中标注"上下文健康度：无法评估（会话日志不可用）"并跳过本步骤

2. **压缩事件扫描**：
   - 逐行扫描 JSONL 文件，检测以下标记：
     - `"type": "system"` 且 `content` 包含 `compact_boundary` → 压缩边界
     - `"isCompactSummary": true` → 压缩摘要
   - 统计指标：
     - 压缩总次数
     - 首次压缩在会话中的位置（前 1/3 / 中 1/3 / 后 1/3）
     - 压缩间隔（两次压缩之间的工具调用次数）
   - 提取每次压缩摘要的关键内容

3. **健康度评估**：

   | 指标 | 阈值 | 风险等级 | 含义 |
   |------|------|---------|------|
   | 压缩次数 | 0 次 | 🟢 健康 | 上下文未达到压力 |
   | 压缩次数 | 1 次且在后 1/3 | 🟡 注意 | 上下文在后期才触顶，影响有限 |
   | 压缩次数 | 1 次且在前 2/3 | 🟠 警告 | 上下文膨胀过早 |
   | 压缩次数 | ≥2 次 | 🔴 高风险 | 反复压缩，关键信息很可能丢失 |

4. **关联分析**：
   - 如果 Bug 关联的 Agent 输出发生在**某次压缩之后** → 标记 `context_compaction_risk: high`
   - 检查压缩摘要中是否包含与 Bug 相关的上下文信息（如涉及的文件名、功能名）
   - 如果压缩摘要中**缺失**了 Bug 相关的关键上下文 → 进一步确认压缩导致信息丢失

5. **输出**：在 evolve 日志的 `## 2. 根因分析` 之后新增子节：

   ```markdown
   ### 2.1 上下文健康度分析
   
   | 指标 | 值 |
   |------|-----|
   | 会话压缩次数 | {N} 次 |
   | 首次压缩位置 | {前/中/后 1/3} |
   | 压缩风险等级 | {🟢/🟡/🟠/🔴} |
   | 关联压缩事件 | {与 Bug 时间窗口重叠的压缩次数} |
   
   **评估结论**：{压缩是否为 Bug 的潜在诱因}
   
   **压缩摘要关键丢失**：{如有，列出被压缩遗漏的关键信息}
   ```

### Phase 3：产出改进建议

**目标**：将分析结果写入进化日志。

1. **生成改进建议**，每条建议需包含：
   - **改进类型**：`rule_enhancement`（规则补充）/ `agent_prompt_fix`（Agent 提示词修正）/ `new_rule`（新增规则）/ `workflow_adjustment`（流程调整）/ `context_optimization`（上下文优化）
   - **目标文件**：具体要修改的 Agent 或 Rule 文件路径
   - **当前行为**：Agent 当前在这类场景下会怎么做
   - **期望行为**：改进后应该怎么做
   - **具体修改建议**：尽量给出可直接采纳的文案/规则片段

   > **`context_optimization` 类型说明**：当 Phase 2.5 上下文健康度分析发现压缩风险为 🟠 或 🔴 时，应生成此类型的改进建议。常见方向包括：
   > - Agent 定义/规则文件过大 → 建议拆分或压缩
   > - 中间产物传递未压缩 → 建议增加摘要层
   > - 阶段规则加载冗余 → 建议增加条件加载
   > - Agent 输入上下文过重 → 建议增加上下文防火墙

2. **确保目录存在**：
   ```
   docs/workflows/evolve-log/pending/
   ```

3. **生成序号**：扫描 `docs/workflows/evolve-log/pending/` 目录下当天已有文件，确定序号（001、002...）

4. **写入文件**：在 `docs/workflows/evolve-log/pending/` 目录下写入 `.md` 文件，frontmatter 中 `status` 设为 `pending`

5. **输出总结**：向用户展示改进记录的摘要和文件路径

### Phase 3.5：上下文复盘仪表板

> **设计来源**：借鉴 `claude-compaction-viewer` 工具，结合 Plan B 运行时上下文健康度监控（SKILL.md §2.7）产出的 `contextHealth` 数据，提供会话级别的上下文使用回顾。

**目标**：基于 `state.json` 中的 `contextHealth` 数据和会话日志，生成直观的上下文使用复盘报告，帮助识别上下文压力热点。

1. **读取上下文健康度数据**：
   - 读取 Bug 关联的工作流 `state.json` 中的 `contextHealth` 字段
   - 如果 `contextHealth` 不存在（旧工作流未启用监控），在输出中标注"上下文复盘：不可用（工作流未启用运行时监控）"并跳过本步骤

2. **构建阶段级仪表板**：
   - 遍历 `contextHealth.phaseMetrics[]`，为每个阶段生成一行统计
   - 从 `contextHealth.compactionEvents[]` 中统计每阶段的压缩次数
   - 结合 Phase 2.5 的会话日志分析（如可用），估算峰值上下文占用

3. **生成改进建议**（针对 🟠 或 🔴 风险阶段）：
   - **工具调用过多**（>60）→ 建议检查 Agent 规范文件大小、是否可拆分工作
   - **压缩事件频繁**（≥2 次）→ 建议增加 Parallel Agent 并行度分散压力、中间产物进一步压缩
   - **单阶段压力集中** → 建议检查该阶段的 Rules 文件是否冗余加载

4. **输出格式**（嵌入进化日志的 `## 5. 上下文复盘` 章节）：

   ```markdown
   ## 5. 上下文复盘

   | 阶段 | 工具调用(估) | 压缩次数 | 风险等级 | 说明 |
   |------|------------|---------|---------|------|
   | ANALYSE_PRODUCT | 28 | 0 | 🟢 健康 | — |
   | ANALYSE_TECH | 52 | 1 | 🟡 注意 | 后期触发 1 次压缩 |
   | ARCHITECT | 35 | 0 | 🟢 健康 | — |
   | IMPLEMENT | 156 | 3 | 🔴 压力大 | 反复压缩，关键信息可能丢失 |
   | BUILD_VERIFY | 67 | 1 | 🟡 注意 | 验证轮次较多 |
   | **汇总** | **{totalToolCalls}** | **{总压缩次数}** | **{overallRisk}** | |

   ### 热点阶段改进建议
   - ⚠️ **IMPLEMENT**: 工具调用 156 次 + 压缩 3 次
     → 检查 backend-developers 的规范文件大小
     → 考虑增加 Parallel Agent 并行度（分散上下文压力）
     → 中间产物是否可进一步压缩后传递
   ```

5. **进化日志文件格式更新**：当 `contextHealth` 数据可用时，进化日志新增 `## 5. 上下文复盘` 章节（在 `## 4. 改进建议` 之后）。同时在 frontmatter 中增加 `context_dashboard: true` 标记。

### Phase 4：发送企微通知

**目标**：通知企微群有新的流水线改进方案产出，提醒审核员尽快审核。

1. **调用 send.py 脚本**（路径：`.claude/skills/send-flow-message/send.py`），发送审核提醒。

2. **消息内容模板**（5 行精简版，禁止逐条展开改进详情）：

   ```
   🧬 流水线改进 · 待审核

   📌 {一句话标题}
   🤖 {Agent1中文名}、{Agent2中文名} → {N}条建议
   👤 提交人：{author}
   🌿 分支：{branch}

   ▶ /evolve-apply 审核
   ```

   **字段说明**：
   - `{Agent中文名}` — 从 Agent 定义文件的标题中提取中文名称（如 `归档总结专家`），而非文件名
   - `{branch}` — 当前 Git 分支名，通过 `git branch --show-current` 获取

3. **发送方式**：

   ```bash
   echo '消息内容' | python3 .claude/skills/send-flow-message/send.py --tag evolve
   ```

4. **执行要求**：
   - 消息发送不需要额外确认，在进化日志写入成功后自动触发
   - 如果消息发送失败，向用户报告失败原因，但**不影响**进化日志的产出结果（日志已成功保存）

---

## 输出格式

### Phase 4 完成后的总结展示

```
## 🧬 进化分析完成

### Bug 回顾
- **现象**：{一句话描述}
- **修复文件**：{文件列表}

### 根因追溯
- **根因层级**：{需求分析 / 架构设计 / 代码实现 / 验证遗漏}
- **关联 Agent**：{Agent 名称列表}

### 上下文健康度
- **压缩次数**：{N} 次 | **风险等级**：{🟢/🟡/🟠/🔴}
- **压缩关联**：{压缩是否为潜在诱因}

### 上下文复盘仪表板
| 阶段 | 工具调用 | 压缩次数 | 风险等级 |
|------|---------|---------|---------|
| {各阶段统计行} |
| **汇总** | **{total}** | **{total}** | **{overall}** |
{如有热点阶段: → 改进建议摘要}

### 改进建议（共 N 条）
| # | 类型 | 目标文件 | 摘要 |
|---|------|---------|------|
| 1 | rule_enhancement | rules/xxx.md | ... |
| 2 | agent_prompt_fix | agents/xxx.md | ... |
| 3 | context_optimization | agents/xxx.md | ... |

### 📝 改进记录已保存
→ `docs/workflows/evolve-log/pending/{文件名}.md`
→ 状态：`pending`（等待 Owner 通过 `/evolve-apply` review）

### 📨 企微通知
→ {发送成功/发送失败：原因}
```

---

## 行为约束

1. **只读流水线文件**：可以读取 Agent 定义和 Rule 文件进行分析，但**禁止修改**
2. **只写进化日志**：产出物仅写入 `docs/workflows/evolve-log/` 目录
3. **不做假设**：如果信息不足以判断根因，向用户提问，不要猜测
4. **具体可操作**：改进建议要具体到文件和内容片段，不要泛泛而谈
5. **单次单 Bug**：每次 `/evolve` 只分析一个 Bug，避免混淆

---

## 使用示例

### 示例 1：带描述触发
```
用户：/evolve 运营端菜单路由缺失导致新增的营销管理页面 404
```
→ 收集 Bug 信息 → 追溯到 web-developer Agent → 分析路由规则遗漏 → 产出改进记录 → 发送企微通知

### 示例 2：不带描述触发
```
用户：/evolve
```
→ 询问 Bug 现象和修复内容 → 追溯根因 → 产出改进记录 → 发送企微通知

### 示例 3：结合 git diff 触发
```
用户：/evolve 刚修复了商品中心的库存扣减并发问题，改动见最近的 commit
```
→ 查看 git log/diff → 理解修复内容 → 追溯到 java-architect 和 product-center-developer → 产出改进记录 → 发送企微通知
