# BUILD_VERIFY 调度与精细化回退策略（按需加载）

> **加载时机**: 编排器进入 BUILD_VERIFY 阶段时加载本文件，包括调度模式选择、Agent 工具并行调度管理、编译失败回退等。

### repos[] 适配规则

当 `projectConfig.repos[]` 存在时，BUILD_VERIFY 的"平台"概念从固定的 backend/web/miniprogram 扩展为 **repos[] 中每个有改动的仓库**：

- 遍历 `repos[]`，对每个 repo 检查 `implementation/` 下是否有该 repo 相关的改动报告
- 有改动的 repo → 加入待验证列表
- 每个 repo 使用其自身的 `repo.buildCommand` 执行编译（`cd {repo.path} && {repo.buildCommand}`）
- 如果 `repo.buildCommand` 为 null → 跳过该 repo 的编译验证
- 编译结果按 repo 粒度记录到对应 report.md
- 回退时也按 repo 粒度精细回退（仅回退编译失败的 repo 对应的 Agent）

> 当 repos[] 不存在时（旧模式），仍按原有的 backend/web/miniprogram 平台逻辑执行。

---

## 0. 三级降级调度策略

BUILD_VERIFY 阶段支持**三级降级调度**，编排器按优先级逐级尝试：

| 级别 | 模式 | 触发条件 | 说明 |
|------|------|---------|------|
| **Level 1** | Agent 工具并行调度模式（默认） | 启用平台数量 ≥ 2 时优先尝试 | 各平台验证 Agent 独立上下文窗口，隔离 Maven/TypeScript/Taro 构建输出膨胀 |
| **Level 2** | Agent 串行流水线 | Level 1 创建失败 / 超时无响应 / 启用平台仅 1 个 | 1-N 个同步 Task 串行调用，复用子 Agent 规范，中间产物传递 |
| **Level 3** | 编排器直接执行 | Level 2 执行失败 | 编排器自身上下文内，参考 `agents/build-verifier.md` 规范直接执行编译验证 |

> **设计意图**:
> - **Level 1 (Agent 工具并行调度)** 的核心价值是**上下文防火墙**。后端 Maven 编译输出（数百行 stacktrace + 依赖树）与前端 TypeScript/Vite/Taro 构建输出各自在独立窗口中，彻底避免上下文溢出。多平台验证可真并行执行，效率最高。
> - **Level 2 (Agent 串行流水线)** 解决 Agent 工具并行调度 异步机制不可靠或仅单平台的问题。同步 Agent 调用保证可靠性，同时通过拆分 Task 并借助中间产物文件传递数据，避免单个 Task 上下文窗口被撑爆。每个 Agent 自行 Read 工具 读取子 Agent 规范文件（而非注入完整内容到 Prompt），控制 Prompt 大小。
> - **Level 3 (编排器直接执行)** 是最终兜底。编排器在自身上下文中参考 `agents/build-verifier.md` 的核心流程直接执行编译验证，产出精度最低但保证流程不阻断。

### 0.1 降级决策流程

```
编排器执行流程：

1. 读取 state.json，检查是否有断点恢复信息
2. 如果 buildVerifyMode 已有值且非空：
 a) "parallel-agent" → 进入 §4.7.4 断点恢复策略（Level 1 恢复分支）
 b) "task-pipeline" → 进入 §4.7.4 断点恢复策略（Level 2 恢复分支）
 c) "fallback" → 进入 §4.7.4 断点恢复策略（Level 3 恢复分支）
 d) "task"（兼容旧值）→ 进入 §4.7.4 断点恢复策略（按 Level 3 处理）
3. 如果 buildVerifyMode 为空或字段不存在：
 a) 计算启用平台数量：backend.enabled(1/0) + web.enabled(1/0) + miniprogram.enabled(1/0)
 b) 启用平台数量 ≥ 2 → 尝试 Level 1（§4.4），失败或超时则降级到 Level 2（§4.5），再失败降级到 Level 3（§4.6）
 c) 启用平台数量 = 1 → 直接使用 Level 2（§4.5），失败降级到 Level 3（§4.6）
```

---

## 1. 核心原则

BUILD_VERIFY 阶段的回退采用**平台级精细回退**，而非整体回退到 IMPLEMENT 重做所有端。

**仅回退编译失败的平台，已通过的平台保持原状。**

## 2. 回退路由矩阵

```
BUILD_VERIFY 发现编译错误
 ↓
按平台分类错误
 ↓
┌──────────────────────────────────────────────────────────┐
│ 场景 A：仅后端编译失败（B1/B2 FAIL） │
│ → 仅重新调度失败相关的后端领域 Agent │
│ → Web 端和小程序端保持不变 │
├──────────────────────────────────────────────────────────┤
│ 场景 B：仅 Web 端编译失败（B3a FAIL） │
│ → 仅重新调度 Web 端开发 Agent │
│ → 后端和小程序端保持不变 │
├──────────────────────────────────────────────────────────┤
│ 场景 C：仅小程序端编译失败（B3b FAIL） │
│ → 仅重新调度小程序端开发 Agent │
│ → 后端和 Web 端保持不变 │
├──────────────────────────────────────────────────────────┤
│ 场景 D：多端同时失败 │
│ → 按 IMPLEMENT 原有调度顺序重新调度所有失败平台的 Agent │
│ → 各平台 Agent 仅接收自己平台的编译错误信息 │
│ → 已通过的平台保持不变 │
└──────────────────────────────────────────────────────────┘
```

## 3. 回退执行流程

```
1. BUILD_VERIFY 阶段总结确认 → 存在编译失败
2. 编排器按平台分组展示错误汇总及修复建议
3. 用户选择「回退修复」
4. 编排器执行回退：
 a) 在 state.json.rollbackLog 中记录回退信息（含 failedDimensions、
 failedPlatforms、passedPlatforms、errors 字段，详见 state-schema.json）
 b) 删除 implementation/ 下各 report 中的「编译验证」章节 + testing/ 目录
 c) 更新 state.json：
 - currentPhase → IMPLEMENT
 - 仅将失败平台的 platforms.{platform}.status 改回 "pending"
 - 已通过平台的 status 保持 "completed"
 d) phaseHistory 中 BUILD_VERIFY 记录状态改为 "rolled_back"
5. 重新进入 IMPLEMENT 阶段预览（编译修复模式，见 phases/implement-rules.md §3）
6. 仅调度失败平台的开发 Agent，注入编译错误上下文
7. IMPLEMENT 完成 → 重新进入 BUILD_VERIFY（二次验证）
```

## 4. 回退次数保护

为防止无限回退循环，设置最大回退次数保护：

| 规则 | 说明 |
|------|------|
| **最大回退次数**: 2 | 同一个 BUILD_VERIFY → IMPLEMENT 的回退循环**不超过 2 次** |
| **第 2 次回退时** | 编排器展示 🔴 强警告："已连续 2 次编译修复失败，建议人工介入排查。" |
| **超过 2 次** | 编排器**不阻断**，但记录为 HIGH 风险到 `risks.json`，并在总结中醒目展示 |

**回退次数计算规则**:
- 仅计算连续的 `BUILD_VERIFY → IMPLEMENT` 回退，中间不含其他回退
- 从 `rollbackLog` 中筛选 `fromPhase = "BUILD_VERIFY"` 且 `toPhase = "IMPLEMENT"` 的记录
- 若用户在回退后手动修复代码并重新进入 BUILD_VERIFY 成功通过，则计数重置

## 4.1 后端回退时的领域级精细调度

当后端编译失败时，不需要重新调度全部领域开发 Agent。编排器应从编译错误信息中提取涉及的模块，通过 `domain-registry.json` 映射到对应领域，只调度相关领域 Agent：

**映射规则**:
1. 从编译错误信息中提取失败的模块路径
2. 读取 `domain-registry.json`，遍历 `domains[].modules` 匹配失败模块
3. 确定涉及的领域 ID，仅调度这些领域的开发 Agent（Agent 名: `@{domain-id}-dev`）
4. 公共模块错误 → 调度 `@common-dev`

**上游依赖错误处理**: 如果错误涉及上游依赖（如公共模块的 optional 依赖问题导致下游模块编译失败），编排器应：
1. 根据 `dependency-graph.md` 分析错误根源
2. 如果根因在上游模块 → 调度上游 Agent 先修复
3. 如果根因在下游模块自身 → 只调度下游 Agent

## 4.2 编译修复模式的上下文注入

回退到 IMPLEMENT 阶段时，`rollbackLog` 应包含以下结构（供编排器注入上下文使用）：

```json
{
 "fromPhase": "BUILD_VERIFY",
 "toPhase": "IMPLEMENT",
 "reason": "编译验证失败",
 "timestamp": "{ISO8601时间}",
 "deletedArtifacts": ["..."],
 "failedDimensions": {
 "B1": { "status": "FAIL", "modules": ["{user-center}-common"] },
 "B2": { "status": "FAIL", "modules": ["{user-center}-common"] },
 "B3a": { "status": "PASS" },
 "B3b": { "status": "N/A" }
 },
 "failedPlatforms": ["backend"],
 "passedPlatforms": ["web"],
 "errors": [
 {
 "platform": "backend",
 "module": "{user-center}-common",
 "file": "TemplateDetailVO.java",
 "line": 3,
 "error": "Cannot resolve symbol 'JsonSerialize'",
 "suggestion": "在 pom.xml 中添加 jackson-databind 依赖"
 }
 ]
}
```

**编排器注入上下文格式**:
```
【编译修复模式】上次 BUILD_VERIFY 阶段发现以下编译错误，
请在本次实现中修复。仅需修复以下问题，不要修改其他代码：
{错误列表 + 修复建议}
```

## 4.3 调度模式选择（参照 §0 三级降级策略）

BUILD_VERIFY 阶段的调度模式遵循 **§0 三级降级调度策略**，编排器按 Level 1 → Level 2 → Level 3 逐级尝试。

**启用平台计数规则**（决定初始调度级别的关键）：

```
启用平台总数 = backend.enabled(1/0) + web.enabled(1/0) + miniprogram.enabled(1/0)

示例：
- backend + web → 2 个平台 → Level 1 (Agent 工具并行调度) ✅
- backend + web + miniprogram → 3 个平台 → Level 1 (Agent 工具并行调度) ✅
- 仅 backend → 1 个平台 → 直接 Level 2 (Agent 串行流水线)
- 仅 web → 1 个平台 → 直接 Level 2 (Agent 串行流水线)
```

## 4.4 Agent 工具并行调度模式调度规则

### 4.4.1 调度发起

编排器按依赖关系发起 Agent 工具调用，使用****：

**创建指令模板**:

```
发起 Agent 调用组（调度标识: verify-{需求ID}）：

调度任务：对 IMPLEMENT 阶段产出的代码执行编译验证。
Agent 按平台划分，每个 Agent负责独立平台的构建验证，互不干扰。
所有 Agent使用 lite 模型以节省 Token。

Agent 列表：
{根据启用的平台动态生成，见 §4.4.2}

无任务依赖关系，所有 Agent可同时并行执行。
```

### 4.4.2 Agent Prompt 规则

为每个启用的平台生成一个独立 Agent 调用。Agent Prompt 必须包含充分的上下文：

**平台 → Agent 映射表**:

| 平台 | Agent 名 | Agent 文件 | 负责维度 |
|------|--------|-----------|----------|
| backend | `@backend-build-verifier` | `agents/build-verifiers/backend-build-verifier.md` | B1 + B2 + B2.5 |
| web | `@web-build-verifier` | `agents/build-verifiers/web-build-verifier.md` | B3a |
| miniprogram | `@miniprogram-build-verifier` | `agents/build-verifiers/miniprogram-build-verifier.md` | B3b |

**Agent Prompt 注入规范**:

```
使用 Agent 工具调度（同步调用）：

Agent Prompt：

"你是一位编译验证专家，负责 {平台名} 的构建验证。

你的工作职责：
1. 读取 Agent 行为规范：{agents/build-verifiers/{平台}-build-verifier.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取实现报告：{implementation/{平台}/*-report.md 的绝对路径}
4. **前置 LSP 扫描**：先调用 `read_lints` 扫描对应平台的项目目录，收集诊断信息
5. 严格按照 Agent 规范执行编译验证
6. 在对应 report.md 末尾追加编译验证章节（含 LSP 预扫描结果）

{后端额外注入}:
- 后端整体架构文档：{architecture/backend/architecture.md 的绝对路径}
- 服务依赖图：{architecture/backend/dependency-graph.md 的绝对路径}

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

完成后将产物写入指定路径，返回产物路径和关键摘要。"
```

> **关键**: Agent Prompt 中的所有路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析），因为 Agent **不会继承编排器的对话历史**。

### 4.4.3 任务列表（无依赖关系 — 全并行）

与 IMPLEMENT 阶段不同，BUILD_VERIFY 的各平台验证之间**完全没有依赖关系**：

```
任务列表：
1. 后端编译验证 — 分配给 @backend-build-verifier — 无依赖
2. Web 端构建验证 — 分配给 @web-build-verifier — 无依赖
3. 小程序端构建验证 — 分配给 @miniprogram-build-verifier — 无依赖

→ 所有任务同时启动，真并行执行
```

### 4.4.4 编排器（编排器）的行为约束

在 Agent 工具并行调度模式下，编排器作为 编排器：

| ✅ 必须做 | ❌ 禁止做 |
|-----------|---------|
| 发起 Agent 调用并分配任务 | 直接执行任何编译命令 |
| Agent 同步返回后检查产物 | 在 Agent 工作时中断 |
| Agent 返回后检查产物 | 替代 Agent 完成未完成的任务 |
| 汇总各 Agent结果并生成统一总结 | 向 Agent 传递其他 Agent 的完整对话 |
| 根据汇总结果更新 state.json | 忽略 Agent 的风险汇报 |

### 4.4.5 调度完成

所有 Agent完成任务后，编排器执行：

```
1. 逐一接收每个 Agent的返回结果
2. 汇总所有 Agent的验证结果到统一的验证总结表格
3. 确认各端 report.md 已追加编译验证章节
4. 更新 state.json 中 buildVerifyMode 字段为 "parallel-agent"
5. 记录 buildVerifyTeam 信息（调度标识、Agent 列表、各 Agent状态）
6. 关闭所有 Agent → 汇总结果
7. 恢复正常模式，进入总结确认步骤
```

### 4.4.6 超时检测与自动降级（Level 1 → Level 2）

Agent 工具并行调度 异步消息机制存在不可靠性风险。编排器必须实施超时检测，防止无限等待：

#### 超时策略

```
超时检测流程（对每个 Agent执行）：

1. Agent 调用后
2. 等待 120 秒（2 分钟）后检查：
 a) 如果 Agent 已返回完成结果 → 正常继续
 b) 如果 Agent 未响应 → 发送催促消息：
 "请汇报当前进度。如果已完成，请返回完成结果。"
3. 催促后再等待 60 秒（1 分钟）：
 a) 如果收到响应 → 继续等待完成
 b) 如果仍无响应 → 判定为超时
4. 超时处理：
 a) 向该 Agent发送 无需（Agent 工具为同步调用）
 b) 检查该 Agent应产出的编译验证结果（对应 report.md 中的编译验证章节）是否已写入
 c) 如果产物已存在 → 跳过该 Agent，继续处理其他平台结果
 d) 如果产物不存在 → 触发降级
```

#### 降级触发条件

| 触发条件 | 降级目标 |
|---------|---------|
| Agent 调用失败 | Level 2 |
| 任一 Agent超时且无编译验证产物 | Level 2（从该 Agent对应的平台 Task 开始） |

#### 降级执行

```
降级执行流程：

1. 记录降级原因到控制台日志
2. 尝试清理已发起 Agent 调用（无需清理），忽略清理失败
3. 检查已完成的 Agent产出的编译验证结果，确定 Level 2 的起始平台
4. 更新 state.json: buildVerifyMode = "task-pipeline"
5. 跳转到 §4.5（Level 2 Agent 串行流水线），从断点继续
```

### 4.4.7 state.json 中的 Agent 工具并行调度 记录

使用 Agent 工具并行调度模式时，在 state.json 中记录以下信息：

```json
{
 "buildVerifyMode": "parallel-agent",
 "buildVerifyTeam": {
 "teamName": "verify-{需求ID}",
 "members": [
 {
 "name": "@backend-build-verifier",
 "platform": "backend",
 "dimensions": ["B1", "B2", "B2.5"],
 "status": "completed",
 "result": "PASS",
 "completedAt": "{ISO8601时间}"
 },
 {
 "name": "@web-build-verifier",
 "platform": "web",
 "dimensions": ["B3a"],
 "status": "completed",
 "result": "PASS",
 "completedAt": "{ISO8601时间}"
 }
 ],
 "createdAt": "{ISO8601时间}",
 "cleanedAt": "{ISO8601时间}"
 }
}
```

## 4.5 Level 2: Agent 串行流水线

当 Level 1 失败/超时或启用平台仅 1 个时，编排器使用同步 Agent 工具调用，按平台串行执行编译验证。每个 Agent 调用 复用 `agents/build-verifiers/` 下的子 Agent 规范，通过中间产物文件传递上下文。

### 4.5.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **规范文件引用，非注入** | Agent Prompt 中只给出 Agent 规范文件的**绝对路径**，由 Agent 自行使用 Read 工具加载，避免 Prompt 膨胀 |
| **中间产物传递** | 各平台 Task 的编译验证结果写入对应 report.md 的编译验证章节，保证数据格式与 Level 1 一致 |
| **断点恢复** | 每个 Agent 调用 完成后产物已落盘，降级或中断后可从已完成的 Task 之后继续 |
| **上下文隔离** | 每个 Agent 调用 仅处理自己平台的编译输出，避免跨平台构建日志互相污染上下文 |

### 4.5.2 流水线定义

```
Agent 流水线（按启用的平台动态生成，顺序执行）：

[Agent-A] 后端编译验证（复用 @backend-build-verifier 规范）— 仅 backend.enabled 时调度
 输入：state.json + architecture/backend/* + implementation/backend/*-report.md
 产出：各 backend report.md 追加编译验证章节
 
 ↓ 编译验证结果落盘
 
[Agent-B] Web 端构建验证（复用 @web-build-verifier 规范）— 仅 web.enabled 时调度
 输入：state.json + implementation/web/*-report.md
 产出：web report.md 追加编译验证章节
 
 ↓ 编译验证结果落盘
 
[Agent-C] 小程序端构建验证（复用 @miniprogram-build-verifier 规范）— 仅 miniprogram.enabled 时调度
 输入：state.json + implementation/miniprogram/*-report.md
 产出：miniprogram report.md 追加编译验证章节
```

### 4.5.3 Agent Prompt 模板

#### 通用模板（按平台替换占位符）

```
你是一位编译验证专家，负责 {平台中文名} 的构建验证。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read 工具）：{agents/build-verifiers/{平台}-build-verifier.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取实现报告：{implementation/{平台}/*-report.md 的绝对路径}
{后端额外步骤}:
4. 读取后端整体架构文档：{architecture/backend/architecture.md 的绝对路径}
5. 读取服务依赖图：{architecture/backend/dependency-graph.md 的绝对路径}
{/后端额外步骤}
6. **前置 LSP 扫描**：调用 `read_lints` 扫描对应平台项目目录，收集诊断信息
7. 严格按照 Agent 规范执行编译验证
8. 在对应 report.md 末尾追加编译验证章节（含 LSP 预扫描结果）

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

⚠️ 重要：
- 你必须先使用 Read 工具读取 Agent 规范文件，再按规范执行
- 完成后返回各维度的 PASS/FAIL/WARN/N/A 状态和错误摘要
```

### 4.5.4 Agent 串行流水线执行流程

```
编排器执行流程：

1. 确定需要执行的平台 Task（检查已完成的验证结果）：
 a) 遍历启用的平台，检查对应 report.md 中是否已有编译验证章节
 b) 已有编译验证章节 → 跳过该平台
 c) 未有编译验证章节 → 加入待执行列表

2. 按顺序执行各平台 Task（如需）：
 a) 使用 Agent 工具，注入 §4.5.3 Prompt（替换平台占位符）
 b) Agent 返回后，检查对应 report.md 是否成功追加编译验证章节
 c) 如果写入失败 → 降级到 Level 3（§4.6）

3. 所有平台 Task 完成后：
 a) 汇总各平台验证结果
 b) 更新 state.json: buildVerifyMode = "task-pipeline"
 c) 记录 buildVerifyPipeline 信息
 d) 进入"总结确认"步骤
```

### 4.5.5 Level 2 失败处理

| 失败场景 | 处理方式 |
|---------|---------|
| 某平台 Agent 返回空结果 / 无编译验证产物 | 降级到 Level 3（已完成平台的结果保留） |
| Task 执行过程中出现错误但有部分产物 | 检查产物完整性，完整则视为成功；不完整则降级到 Level 3 |
| 所有平台 Task 均失败 | 降级到 Level 3（编排器直接执行全部平台的编译验证） |

---

## 4.6 Level 3: 编排器直接执行（兜底模式）

当 Level 2 也失败时，编排器在自身上下文中直接执行编译验证。

### 4.6.1 执行策略

```
编排器直接执行流程：

1. 检查已有的编译验证结果（Level 1/2 可能已完成部分平台）：
 a) 遍历启用的平台，检查 report.md 中是否已有编译验证章节
 b) 已有编译验证章节的平台 → 保持不动
 c) 未有编译验证章节的平台 → 加入待执行列表

2. 对待执行列表中的每个平台，参考 agents/build-verifier.md 的核心验证流程：
 a) 读取 state.json 和对应平台的实现报告
 b) 调用 `read_lints` 扫描对应平台的项目目录（前置 LSP 扫描）
 c) 执行编译命令（Maven/Vite/Taro）
 d) 解析编译输出，提取错误/警告
 e) 在对应 report.md 末尾追加编译验证章节（含 LSP 预扫描结果）
 ⚠️ 注意：编排器上下文有限，多平台验证日志可能导致上下文受压

3. 更新 state.json: buildVerifyMode = "fallback"

4. 进入"总结确认"步骤
```

### 4.6.2 Level 3 的限制说明

| 限制 | 说明 |
|------|------|
| 上下文受限 | 编排器的上下文已包含 SKILL.md、本规则文件等，留给编译验证的窗口有限 |
| 多平台日志冲突 | 多平台同时验证时，构建日志互相交织，可能导致错误归因不准确 |
| 产物质量标注 | 在编译验证章节中追加 `verifyMode: "fallback"` 标注，提示后续阶段注意 |
| 流程保障 | 即使精度下降，仍保证有编译验证产物输出，不阻断工作流 |

> **注意**: Level 3 产出时，编排器应在总结确认中向用户明确说明"本次编译验证使用了兜底模式，验证精度可能有所下降，建议仔细审阅结果"。

---

## 4.7 断点恢复与 state.json 记录

### 4.7.1 buildVerifyMode 字段

| 值 | 说明 |
|-----|------|
| `"parallel-agent"` | Level 1: Agent 工具并行调度模式成功完成 |
| `"task-pipeline"` | Level 2: Agent 串行流水线模式完成 |
| `"fallback"` | Level 3: 编排器直接执行模式完成 |
| `"task"` | 兼容旧值：等价于 Level 3（断点恢复时按 Level 3 处理） |

### 4.7.2 Agent 流水线记录（仅 Level 2）

```json
{
 "buildVerifyMode": "task-pipeline",
 "buildVerifyPipeline": {
 "completedPlatforms": ["backend", "web"],
 "pendingPlatforms": ["miniprogram"],
 "degradedFrom": "parallel-agent",
 "degradeReason": "Agent @web-build-verifier 调用失败",
 "completedAt": "{ISO8601时间}"
 }
}
```

### 4.7.3 兜底模式记录（仅 Level 3）

```json
{
 "buildVerifyMode": "fallback",
 "buildVerifyFallback": {
 "degradedFrom": "task-pipeline",
 "degradeReason": "Task 后端编译验证返回空结果",
 "completedPlatforms": ["web"],
 "fallbackPlatforms": ["backend"],
 "completedAt": "{ISO8601时间}"
 }
}
```

### 4.7.4 断点恢复策略

```
恢复策略：

1. 读取 state.json，检查 buildVerifyMode 字段
2. 根据 buildVerifyMode 值选择恢复策略：

 --- Level 1 恢复（buildVerifyMode = "parallel-agent"）---
 a) 检查各平台 report.md 中是否已有编译验证章节
 b) 根据已完成的平台，仅对未完成平台发起 Agent 调用
 c) 如果所有平台均已完成 → 直接进入总结确认

 --- Level 2 恢复（buildVerifyMode = "task-pipeline"）---
 a) 读取 buildVerifyPipeline.completedPlatforms 确定已完成的平台
 b) 检查 report.md 编译验证章节存在性进行交叉验证
 c) 从下一个未完成的平台 Task 继续执行

 --- Level 3 恢复（buildVerifyMode = "fallback" 或 "task"）---
 a) 检查各平台编译验证结果是否存在：
 - 全部存在 → 直接进入总结确认
 - 部分缺失 → 对缺失的平台重新执行 Level 3
 
3. 若 buildVerifyMode 字段不存在：
 a) 检查 report.md 编译验证章节存在性推断执行进度
 b) 从头开始，按 §0.1 降级决策流程执行
```

## 4.8 编排器对接行为（BUILD_VERIFY 三步模式）

本阶段遵循标准三步模式（预览 → 执行 → 总结确认）：

**Step 1: 预览** — 展示即将执行的编译验证计划：
- 调度模式（Level 1 Agent 工具并行调度 / Level 2 Agent 串行流水线 / Level 3 编排器直接执行）
- 如为断点恢复，说明从哪个步骤继续
- 启用的平台列表（后端/Web 端/小程序端）
- Agent 工具并行调度模式下：调度标识、Agent 列表、各 Agent负责的维度
- Agent 流水线模式下：Agent 调用数量和各 Task 对应平台
- 后端：涉及的 Maven 模块列表和编译范围
- Web 端/小程序端：项目路径和构建命令
- 跳过的平台（未启用）和跳过原因

**Step 2: 执行** —
- **Level 1 (Agent 工具并行调度)**: 发起 Agent 调用 → 分配任务（全并行） → Agent 同步返回后检查产物 → 超时检测 → 汇总结果 → 汇总结果
- **Level 2 (Agent 串行流水线)**: 按平台串行调用 Task，检查编译验证产物
- **Level 3 (编排器直接执行)**: 编排器自身读取输入并执行编译验证

**Step 3: 总结确认** — 根据验证结果展示不同级别的提示：
- 实际使用的调度模式（含降级信息，如"Agent 工具并行调度 → Agent 串行流水线（@backend-build-verifier 超时降级）"）

| 验证结果 | 编排器行为 |
|----------|-----------|
| 全部 ✅ PASS | 正常展示总结，提示进入 VISUAL_REVIEW 阶段（或 E2E_VERIFY 如无设计稿）。展示编译耗时和模块覆盖率。 |
| 存在 ⚠️ WARN | 展示 🟡 黄色警告："编译验证发现 {N} 个警告项（依赖冲突/版本差异/包体积接近限制），建议关注但不阻塞。" 用户可选择继续或回退。 |
| 存在 ❌ FAIL | 展示 🔴 红色警告，按平台分组展示错误摘要。**强烈建议回退修复。** |
| Level 3 兜底模式 | 追加精度降低警告："本次编译验证使用了兜底模式，验证精度可能有所下降，建议仔细审阅结果。" |

## 5. BUILD_VERIFY PASS 后的流转指令（CRITICAL）

> **编排器必读**: BUILD_VERIFY PASS 仅表示"编译验证通过"，**不等于工作流完成**。

BUILD_VERIFY 阶段 PASS 后，编排器的下一步操作：

| 步骤 | 操作 |
|------|------|
| 1 | 在"总结确认"中展示编译通过的结果 |
| 2 | 查阅 `references/phase-transitions.json`，确认下一阶段为 **VISUAL_REVIEW** |
| 3 | 检查 VISUAL_REVIEW 触发条件（详见 `phases/visual-review-rules.md` §0.1）|
| 4a | 满足条件 → 更新 `state.json`: currentPhase → `VISUAL_REVIEW`，进入视觉验收阶段 |
| 4b | 不满足条件（无设计稿等）→ 跳过 VISUAL_REVIEW，更新 currentPhase → `E2E_VERIFY` |

**严禁操作**:
- ❌ 不得将 `currentPhase` 直接设为 `DONE`、`TEST`、`ARCHIVE` 或其他非 `VISUAL_REVIEW`/`E2E_VERIFY` 的阶段
- ❌ 不得在 BUILD_VERIFY PASS 后输出"需求完成总结"或"工作流完成"的消息
- ❌ 不得跳过 VISUAL_REVIEW（满足条件时）、E2E_VERIFY、TEST、ARCHIVE 中的任何一个阶段

BUILD_VERIFY PASS 后的完整剩余流程：
```
BUILD_VERIFY (PASS) → VISUAL_REVIEW → E2E_VERIFY → TEST → ARCHIVE → DONE
 ↑ ↑
 还有4个阶段（VISUAL_REVIEW 可跳过） 终态
```
