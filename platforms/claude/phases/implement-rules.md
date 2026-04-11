# IMPLEMENT 阶段动态调度规则（按需加载）

> **加载时机**: 编排器进入 IMPLEMENT 阶段时加载本文件。

---

## 0. 调度模式选择

IMPLEMENT 阶段**锁定使用 Agent 工具并行调度模式**，即使仅 1 个 Agent 也使用独立 Agent 调用以保持上下文纯粹：

| 模式 | 触发条件 | 说明 |
|------|---------|------|
| **Agent 工具并行调度模式**（锁定） | 始终使用 | 使用 Agent 工具独立上下文窗口，即使仅 1 个 Agent 也发起独立调用 |
| **用户决策**（调用失败时） | Agent 调用失败 | 报错给用户决策，不自动降级 |

> **设计意图**：借鉴 agentic-mall 的生产经验——IMPLEMENT 阶段即使仅 1 个 Agent，也使用独立 Agent 调用以保持编排器上下文纯粹。开发 Agent 的代码搜索和写入操作会产生大量上下文，隔离在独立窗口中可避免编排器上下文膨胀，确保后续 BUILD_VERIFY 阶段的状态读取精度。调用失败时报错由用户决策，而非自动降级到上下文共享模式。

---

## 1. 平台调度策略

IMPLEMENT 阶段根据 `state.json` 中的 `platforms` 字段动态决定调用哪些开发 Agent：

```json
{
  "platforms": {
    "backend": { "enabled": true, "status": "pending" },
    "web": { "enabled": true, "status": "pending" },
    "miniprogram": { "enabled": false, "status": "skipped" }
  }
}
```

- 仅调用 `enabled: true` 的平台对应的开发 Agent
- 当需求涉及接口交互时，**后端 Agent 必须先执行（或先完成）**，前端 Agent 依赖后端 API 设计结果
- 无接口交互的纯前端需求可直接执行前端 Agent
- 每个平台 Agent 执行完毕后单独更新 `state.json` 中对应平台的 `status`

## 2. 后端领域调度规则（统一动态模式）

当 `backend.enabled: true` 时，编排器按以下规则调度后端领域开发 Agent：

1. **读取架构文档**: 从 `architecture/backend/priority-list.md` 获取开发优先级
2. **确定涉及领域**: 从 `architecture/backend/` 下各领域 `tech-requirements.md` 的存在性判断哪些领域需要开发
3. **读取领域注册表**: 从 `architecture/backend/domain-registry.json` 获取领域元信息
4. **按优先级调度**: 按 P0 -> P1 -> P2 -> P3 -> P4 顺序调度对应领域的开发 Agent
5. **同优先级可并行**: 同一优先级的多个领域 Agent 可在一条消息中并行发起调用
6. **公共模块优先**: `common` 领域始终最先执行（P0）
7. **领域 Agent 映射**: 统一使用动态生成模式，不区分项目类型

### 2.1 统一动态映射规则

> **设计意图**: 所有项目（Java / Node.js / Python / Go 等）统一使用 `domain-registry.json` 驱动的动态 Agent 调度，无需预先创建领域 Agent 文件。领域差异通过 Prompt 注入和 `domain-registry.json` 的 `extraRules` / `extraQualityChecks` 字段表达。

**映射流程**:

```
领域 Agent 动态映射流程：
1. 读取 architecture/backend/domain-registry.json
2. 遍历 domains[] 列表
3. 对每个领域：
   a) Agent 规范 -> 所有领域共享 agents/backend-developers/backend-dev-specification.md
   b) Agent 名 -> @{domain-id}-dev（如 @common-dev, @ad-service-dev）
   c) Prompt 中注入（见 3.2 Agent Prompt 模板）：
      - 领域 ID 和中文名（来自 domain-registry.json）
      - 领域包含的模块列表
      - 领域边界约束（仅允许操作指定目录）
      - 领域特有规则（来自 extraRules）
      - 领域特有检查项（来自 extraQualityChecks）
      - 技术需求文档路径
      - 全局架构文档路径
4. 优先级 -> 从 priority-list.md 读取，common 领域始终 P0
```

---

## 3. Agent 工具并行调度模式规则

### 3.1 调度发起

编排器按优先级分批发起 Agent 调用，同优先级的 Agent 可在一条消息中并行发起。

**调度流程**:

```
按优先级分批发起 Agent 调用：

P0: Agent @common-dev（公共模块，独占执行）
  | 等待完成
P1: 在一条消息中并行发起 Agent @{domain-a}-dev + Agent @{domain-b}-dev
  | 等待全部完成
P2: Agent @{domain-c}-dev（依赖 P1 完成）
  | 等待完成
前端: Agent @web-dev / Agent @miniprogram-dev（依赖后端全部完成，如有接口交互）
```

### 3.2 Agent Prompt 规则

为每个涉及的领域生成一个独立 Agent 调用。Agent 的 Prompt 必须包含充分的上下文：

**统一 Agent Prompt 模板**（所有项目类型共用）:

```
使用 Agent 工具调度 @{domain-id}-dev（同步调用）：

Agent Prompt：
"你是一位资深后端开发工程师，负责 {领域名} 的代码实现。

## 文件所有权声明

你（@{domain-id}-dev）拥有以下目录的**独占写权限**：
- {领域对应的目录路径} — 你的领域代码目录

以下目录是**公共区域**，需要通过编排器协调后才能修改：
- {公共模块目录路径} — 公共模块（修改前必须在返回中标明申请）

**严禁修改**其他 Agent 的所有权目录：
{动态生成的其他领域目录列表}

如需跨领域修改，在返回中报告依赖关系，等待编排器协调。

## 工作职责

1. 读取后端开发通用规范：{agents/backend-developers/backend-dev-specification.md 的绝对路径}
2. 读取技术需求文档：{architecture/backend/{领域ID}/tech-requirements.md 的绝对路径}
3. 读取后端整体架构文档：{architecture/backend/architecture.md 的绝对路径}
4. 读取领域注册表确认边界：{architecture/backend/domain-registry.json 的绝对路径}
5. 严格按照技术需求文档中的文件级改动清单逐一实现代码
6. 生成实现报告到：{implementation/backend/{领域ID}-report.md 的绝对路径}

## 领域上下文

- 领域职责模块：{domain-registry.json 中该领域的 modules 数组}
- 领域依赖关系：{domain-registry.json 中该领域的 dependencies 数组}
- 领域特有规则：{domain-registry.json 中该领域的 extraRules 数组，逐条列出}
- 领域特有检查项：{domain-registry.json 中该领域的 extraQualityChecks 数组，逐条列出}

领域边界约束：
- 仅允许操作 {领域对应的目录路径} 下的代码
- 严禁修改其他领域目录的代码

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要，包含：
- 新增/修改的文件数量
- 关键变更摘要
- 是否存在风险项
- **验证证据**（编译结果、文件清单验证、边界验证）"

编排器收到返回后，检查产物文件是否存在且非空。
```

> **占位符说明**: `{领域对应的目录路径}` 在运行时由编排器根据 `state.json` 中 `projectConfig` 的路径配置解析为实际路径。如果 `projectConfig.repos[]` 存在，优先从 repos 中按 type 匹配路径。
>
> **多仓库模式（repos[] 适配）**:
> 当 `projectConfig.repos[]` 存在时，编排器按以下规则分配文件所有权：
> - 遍历 `repos[]`，对每个 `type=backend` 的 repo 分配一个后端开发 Agent，独占目录为 `repo.path`
> - 对每个 `type=frontend` 的 repo 分配 `@web-developer`，独占目录为 `repo.path`
> - 对每个 `type=miniprogram` 的 repo 分配 `@miniprogram-developer`
> - `type=common` 的 repo 作为公共模块区域
> - 各 Agent 的文件所有权声明直接使用 `repo.path` 替代领域目录路径
> - 跨仓库修改的协调规则与跨领域修改一致（向编排器报告，等待协调）
>
> **全新项目路径处理**（`projectConfig.projectType = "new"`）:
> - 路径字段已在 INIT 阶段由编排器根据 PRD 技术分析结果自动推导并经用户确认，Agent 在首次写入文件时自动创建目标目录
> - 编排器在生成 Agent Prompt 前**必须**用 Read 工具读取最新 `state.json`，确保使用 INIT 阶段已确认的路径值
> - 若某平台路径为 `null`（该平台未启用），编排器不为其生成 Agent 调用

> **关键**: Agent Prompt 中的所有路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析），因为 Agent **不会继承编排器的对话历史**。

### 3.3 任务列表与依赖关系

编排器根据 `priority-list.md` 中的优先级生成调度计划，并设置依赖关系：

```
调度计划（示例，实际由 domain-registry.json + priority-list.md 动态生成）：
1. [P0] 公共模块开发 — Agent @common-dev — 无依赖
2. [P1] 领域 A 开发 — Agent @{domain-a}-dev — 依赖 P0 完成
3. [P1] 领域 B 开发 — Agent @{domain-b}-dev — 依赖 P0 完成
4. [P2] 领域 C 开发 — Agent @{domain-c}-dev — 依赖 P1 全部完成
```

**依赖关系转化规则**:
- P0 任务无依赖，立即开始
- P(N) 任务依赖所有 P(N-1) 任务完成
- 同优先级的 Agent 可在一条消息中**并行发起调用**
- 编排器等待当前优先级全部返回后，再发起下一优先级

### 3.4 文件冲突管控（CRITICAL）

> **核心规则**: 两个 Agent 同时编辑同一个文件会导致互相覆盖。

| 管控措施 | 说明 |
|---------|------|
| **文件所有权显式声明** | 每个领域 Agent 的 Prompt 头部必须包含文件所有权声明段落，明确列出独占目录、公共目录和禁止目录 |
| **天然目录隔离** | 每个领域 Agent 只允许操作自己领域的目录，天然隔离 |
| **P0 独占期** | `@common-dev` 执行期间（P0），所有其他 Agent 尚未发起调用，不会并发修改公共模块 |
| **公共模块修改约束** | P1 及之后的 Agent 如果需要修改公共模块，必须在返回中标明申请，编排器在后续调度中协调串行执行 |

### 3.5 前端 Agent 调度

前端 Agent（web-developer / miniprogram-developer）的调度规则：

- **有接口交互时**: 前端 Agent 在所有后端 Agent 完成后再发起调用
- **无接口交互时**: 前端 Agent 无依赖，可与后端 Agent 并行发起调用
- 前端 Agent 使用同样的 Agent Prompt 注入规范

| 前端 Agent | Agent 名 |
|------------|---------|
| web-developer | `@web-dev` |
| miniprogram-developer | `@miniprogram-dev` |

### 3.6 编排器的行为约束

在 Agent 工具并行调度模式下，编排器：

| 必须做 | 禁止做 |
|--------|--------|
| 按优先级分批发起 Agent 调用 | 直接编写任何源代码 |
| Agent 同步返回后检查产物 | 在 Agent 工作时中断 |
| 汇总结果并更新 state.json | 替代 Agent 完成未完成的任务 |
| 处理公共模块修改冲突 | 忽略 Agent 的风险汇报 |

### 3.7 调度完成

所有 Agent 调用完成后，编排器执行：

```
1. 逐一确认每个 Agent 的返回结果和实现报告
2. 汇总所有 Agent 的风险项
3. 更新 state.json 中各平台的 status 为 "completed"
4. 在 state.json 的 implementMode 字段记录 "parallel-agent"
5. 准备进入 BUILD_VERIFY 阶段
```

---

## 4. 调用失败处理（替代原降级模式）

当 Agent 调用失败时，编排器**不自动降级**，而是：

1. 向用户展示错误信息
2. 提供选项：
   - **重试**：重新发起 Agent 调用
   - **手动处理**：用户自行在 IDE 中执行开发任务
   - **强制降级**：用户明确要求后，使用编排器直接执行模式（编排器加载 Agent 规范自行执行，上下文压力大，产出精度可能降低）

> **CRITICAL**：编排器**严禁自行决定降级**。即使检测到仅 1 个 Agent 需调度，也必须尝试发起独立 Agent 调用。

---

## 5. 编译修复模式（BUILD_VERIFY 回退后触发）

当 BUILD_VERIFY 阶段编译失败并回退到 IMPLEMENT 时，编排器进入**编译修复模式**。此模式下的调度规则与正常 IMPLEMENT 不同：

### 5.1 模式选择

| 需修复的独立 Agent 数量 | 调度模式 |
|------------------------|---------|
| 1 个 Agent | 单次 Agent 工具调用 |
| 2+ 个 Agent | 在一条消息中并行发起多个 Agent 调用 |

### 5.2 共通规则（均适用）

1. **识别回退来源**: 编排器从 `rollbackLog` 中读取最近一条 `fromPhase = "BUILD_VERIFY"` 的记录
2. **仅调度失败平台**: 根据 `rollbackLog.failedPlatforms` 确定需要重新调度的平台，跳过 `passedPlatforms` 中的平台
3. **后端领域级调度**: 当后端失败时，根据 `rollbackLog.failedDimensions.B1.modules` 映射到具体领域 Agent（通过 `domain-registry.json` 查找），仅调度相关领域
4. **上游依赖分析**: 如果编译错误涉及上游依赖问题（如 optional 依赖未传递），编排器应根据 `dependency-graph.md` 分析错误根源，调度根因所在模块的 Agent
5. **注入修复上下文**: 调用开发 Agent 时注入以下额外上下文：

```
【编译修复模式】上次 BUILD_VERIFY 阶段发现以下编译错误，
请在本次实现中修复。仅需修复以下问题，不要修改其他代码：
{来自 rollbackLog.errors 的错误列表和修复建议}
```

6. **修复完成后**: 重新进入 BUILD_VERIFY 阶段进行二次验证

### 5.3 编译修复模式的特殊规则

在编译修复模式下：

- 仅为需修复的领域发起 Agent 调用，不调度已通过的领域
- Agent Prompt 中额外注入编译错误上下文（来自 rollbackLog.errors）
- 任务依赖关系根据失败模块的实际依赖关系重新计算

> **注意**: 编译修复模式下，已通过平台的 `platforms.{platform}.status` 保持为 `"completed"`，编排器根据此字段自动跳过这些平台的调度。

---

## 6. D2C 嵌入模式调度规则（Entry B）

> **触发条件**: IMPLEMENT 阶段开始时，编排器检测到当前需求关联了 Figma 设计稿，且前端架构文档中标注了 D2C 嵌入需求。

### 6.0 D2C 嵌入模式判定

编排器在 IMPLEMENT 阶段启动时，**先于常规平台调度**执行以下检测：

```
D2C 嵌入模式判定流程：

1. 检查 state.json：
   a) intentAnalysis.d2cConfig 是否存在
   b) 若存在且 d2cConfig.mode = "embedded" -> 直接进入 D2C 嵌入模式
   c) 若 d2cConfig.mode = "standalone" 且 status = "completed" -> D2C 已完成，
      检查 intentType 是否为 "d2c-to-workflow"：
      - 是 -> 跳过前端 IMPLEMENT（D2C 代码已生成），仅调度后端 Agent
      - 否 -> 异常 case，按防御性逻辑正常调度，并在日志中记录此异常状态组合

2. 若 d2cConfig 不存在，检查架构文档中是否有 Figma 关联：
   a) 读取 architecture/frontend/tech-requirements.md（如存在）
   b) 搜索关键标记：figmaUrl / figma.com/design / d2c-embedded
   c) 若找到 Figma 关联 -> 创建 d2cConfig（mode: "embedded"）并进入 D2C 嵌入模式
   d) 若未找到 -> 正常调度（跳过 D2C）

3. 状态更新：
   - 若进入 D2C 嵌入模式，在 state.json 中设置：
     intentAnalysis.d2cConfig = {
       mode: "embedded",
       figmaUrl: "{从架构文档中提取}",
       fileKey: "{解析出的 fileKey}",
       nodeId: "{解析出的 nodeId}",
       status: "pending",
       projectDir: "{projectConfig.webProject}"
     }
```

### 6.1 D2C 嵌入模式调度流程

当判定为 D2C 嵌入模式时，前端 Agent 的调度替换为 D2C 子流程。

### 6.2 D2C 嵌入模式与 Agent 调度的关系

| 场景 | 调度策略 |
|------|---------|
| D2C 嵌入 + 后端多领域 | Agent 工具并行调度：D2C 作为 `@d2c-frontend` Agent 调用，与后端领域 Agent 并行 |
| D2C 嵌入 + 仅前端 | 单次 Agent 调用：仅 1 个 Agent（D2C） |
| D2C 嵌入 + 后端单领域 | 并行发起 2 个 Agent 调用（@d2c-frontend + @{domain}-dev） |

### 6.3 D2C-to-Workflow 简化模式

当 `intentType = "d2c-to-workflow"`（D2C 直通模式完成后用户选择继续标准流水线）时：

```
D2C-to-Workflow IMPLEMENT 阶段简化规则：

1. 前端平台（web）：
   - 跳过前端 Agent 调度（D2C 代码已在直通模式中生成）
   - 直接将 platforms.web.status 设为 "completed"
   - 在 implementation/ 下创建 web-report.md，引用 D2C manifest

2. 后端平台（backend，如有）：
   - 正常调度后端领域 Agent（D2C 不影响后端）

3. 小程序平台（miniprogram，如有）：
   - 正常调度小程序 Agent

4. 状态标记：
   - state.json 中 implementMode 记录为 "d2c-to-workflow"
```

---

## 7. 异常处理与恢复

### 7.1 Agent 调用失败

| 场景 | 处理方式 |
|------|---------|
| Agent 调用返回空结果 | 重新发起 Agent 调用重试 |
| Agent 执行出错 | 检查已落盘的产物，决定重试或降级 |
| Agent 完成但报告缺失 | 重新发起 Agent 调用要求补充报告 |

### 7.2 断点恢复

```
恢复策略：
1. 读取 state.json，检查 implementMode 字段
2. 若 implementMode = "parallel-agent" 且 currentPhase = "IMPLEMENT"：
   a) 检查各平台 status，确定哪些领域已完成（status = "completed"）
   b) 对未完成的领域，发起新的 Agent 调用继续执行
   c) 仅调度未完成领域的 Agent
3. 若 implementMode = "task" 或字段不存在：
   a) 使用单次 Agent 调用模式恢复
```

### 7.3 公共模块冲突处理

当 P1+ 的 Agent 需要修改公共模块时：

```
冲突处理流程：
1. Agent 在返回中标明："需要在公共模块中添加 {具体内容}，请协调"
2. 编排器检查当前是否有其他 Agent 正在修改公共模块
3. 若无冲突 -> 编排器在后续调度中安排单独的公共模块修改 Agent 调用
4. 若有冲突 -> 编排器串行安排，等待前一个完成后再调度
5. 冲突解除后，编排器在后续 Agent 调用中注入公共模块已更新的信息
```

---

## 8. 确定性验证脚本（实验性）

> **设计来源**：借鉴 Karpathy LLM Wiki 社区的 "Deterministic Generation Engine"——"Run, don't Read" 原则。

### 8.1 适用场景

当 IMPLEMENT 阶段的开发 Agent 需要进行以下验证时，可调用确定性脚本替代手动搜索：

| 验证类型 | 脚本方式 | 替代的手动操作 | 上下文节省 |
|---------|---------|-------------|----------|
| Maven 依赖检查 | `mvn dependency:tree -Dincludes={groupId}` | Agent 手动搜索 pom.xml 解析依赖 | ~10KB -> ~0.5KB |
| import 一致性 | `grep -r "import {类名}" {目录} --include="*.java"` | Agent 用 Grep 工具搜索 | ~5KB -> ~0.3KB |
| 接口签名校验 | `grep -n "public.*{方法名}" {文件路径}` | Agent 用 Read 工具读取整个文件再解析 | ~20KB -> ~0.2KB |
| TypeScript 类型检查 | `tsc --noEmit 2>&1 | head -20` | Agent 人肉审查类型 | ~15KB -> ~0.5KB |

### 8.2 使用约束

- 确定性脚本为**可选优化**，不强制所有 Agent 使用
- Agent 可在"引用必读流程"中选择使用脚本替代全文件读取
- 脚本仅用于**验证和查询**，不用于代码生成
- 脚本执行结果必须记录在实现报告的验证证据中
