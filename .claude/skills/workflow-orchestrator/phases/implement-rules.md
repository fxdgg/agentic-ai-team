# IMPLEMENT 阶段动态调度规则（按需加载）

> **加载时机**: 编排器进入 IMPLEMENT 阶段时加载本文件。

---

## 0. 调度模式选择

IMPLEMENT 阶段**锁定使用 Parallel Agent 调度**，即使仅 1 个 Agent 也使用 Parallel Agent 以保持上下文纯粹：

| 模式 | 触发条件 | 说明 |
|------|---------|------|
| **Parallel Agent 调度**（锁定） | 始终使用 | 使用 Parallel Agent 独立上下文窗口，即使仅 1 个 Agent 也创建单成员团队 |
| **用户决策**（创建失败时） | Agent 调用失败 | 报错给用户决策，不自动降级到 Agent 串行模式 |

> **设计意图**：借鉴 agentic-mall 的生产经验——IMPLEMENT 阶段即使仅 1 个 Agent，也使用 Parallel Agent 以保持编排器上下文纯粹。开发 Agent 的代码搜索和写入操作会产生大量上下文，隔离在独立窗口中可避免编排器上下文膨胀，确保后续 BUILD_VERIFY 阶段的状态读取精度。创建失败时报错由用户决策，而非自动降级到上下文共享的 Agent 串行模式。

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
4. **按优先级调度**: 按 P0 → P1 → P2 → P3 → P4 顺序调度对应领域的开发 Agent
5. **同优先级可并行**: 同一优先级的多个领域 Agent 可并行执行
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
   a) Agent 规范 → 所有领域共享 agents/backend-developers/backend-dev-specification.md
   b) 成员名 → @{domain-id}-dev（如 @common-dev, @ad-service-dev）
   c) Prompt 中注入（见 §3.2 成员 Prompt 模板）：
      - 领域 ID 和中文名（来自 domain-registry.json）
      - 领域包含的模块列表
      - 领域边界约束（仅允许操作指定目录）
      - 领域特有规则（来自 extraRules）
      - 领域特有检查项（来自 extraQualityChecks）
      - 技术需求文档路径
      - 全局架构文档路径
4. 优先级 → 从 priority-list.md 读取，common 领域始终 P0
```

---

## 3. Parallel Agent 模式调度规则（🚀 核心改造）

### 3.1 团队创建

编排器作为调度中心，通过 Agent 工具并行调度子 Agent。编排器只负责协调和任务管理，不直接编写代码。

**创建指令模板**:

```
创建一个名为 impl-{需求ID} 的开发团队，使用委派模式。

团队任务：根据技术架构文档实现后端代码。
团队成员按领域划分，每个成员负责独立的微服务模块，互不干扰。
所有成员使用 lite 模型以节省 Token。

成员列表：
{根据涉及的领域动态生成，见 §3.2}

任务依赖关系：
{根据优先级生成，见 §3.3}
```

### 3.2 成员生成规则

为每个涉及的领域生成一个独立成员。成员的初始 Prompt 必须包含充分的上下文：

**统一成员 Prompt 模板**（所有项目类型共用）:

```
生成一个 {领域中文名} 开发成员（{成员名}），Prompt 如下：

"你是一位资深后端开发工程师，负责 {领域名} 的代码实现。

## ⚠️ 文件所有权声明

你（{成员名}）拥有以下目录的**独占写权限**：
- ✅ {领域对应的目录路径} — 你的领域代码目录

以下目录是**公共区域**，需要通过编排器协调后才能修改：
- ⚠️ {公共模块目录路径} — 公共模块（修改前必须向领导申请）

**严禁修改**其他 Agent 的所有权目录：
{动态生成的其他领域目录列表，每行一个，格式: - ❌ {其他领域目录} — 归属 @{其他成员名}}

如需跨领域修改，向编排器报告依赖关系，等待协调指令。

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
- ✅ 仅允许操作 {领域对应的目录路径} 下的代码
- ❌ 严禁修改其他领域目录的代码

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}

完成后，请向领导发送消息汇报完成状态，包含：
- 新增/修改的文件数量
- 关键变更摘要
- 是否存在风险项
- **验证证据**（编译结果、文件清单验证、边界验证）"
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
> - 编排器在生成成员 Prompt 前**必须** `Read` 读取最新 `state.json`，确保使用 INIT 阶段已确认的路径值
> - 若某平台路径为 `null`（该平台未启用），编排器不为其生成 Agent 成员

> **关键**: 成员 Prompt 中的所有路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析），因为成员**不会继承领导的对话历史**。

### 3.3 任务列表与依赖关系

编排器根据 `priority-list.md` 中的优先级生成共享任务列表，并设置依赖关系：

```
任务列表（示例，实际由 domain-registry.json + priority-list.md 动态生成）：
1. [P0] 公共模块开发 — 分配给 @common-dev — 无依赖
2. [P1] 领域 A 开发 — 分配给 @{domain-a}-dev — 依赖任务 1
3. [P1] 领域 B 开发 — 分配给 @{domain-b}-dev — 依赖任务 1
4. [P2] 领域 C 开发 — 分配给 @{domain-c}-dev — 依赖任务 2, 3
```

**依赖关系转化规则**:
- P0 任务无依赖，立即开始
- P(N) 任务依赖所有 P(N-1) 任务完成
- Parallel Agent 的任务依赖机制会自动阻塞下游任务，P(N-1) 完成后自动解除 P(N) 的阻塞
- 同优先级的任务可**真并行执行**

### 3.4 文件冲突管控（CRITICAL）

> **核心规则**: 两个成员同时编辑同一个文件会导致互相覆盖。

| 管控措施 | 说明 |
|---------|------|
| **文件所有权显式声明** | 每个领域 Agent 的启动 Prompt 头部必须包含 `## ⚠️ 文件所有权声明` 段落，明确列出独占目录、公共目录和禁止目录（见 §3.2 成员 Prompt 模板） |
| **天然目录隔离** | 每个领域 Agent 只允许操作自己领域的目录（如 `{user-center}/`），天然隔离 |
| **P0 独占期** | `@common-dev` 执行期间（P0），所有其他成员被任务依赖阻塞，不会并发修改 `{common-module}/` |
| **公共模块修改约束** | P1 及之后的成员如果需要修改 `{common-module}/`（领域 Agent 允许修改公共模块），必须先向领导发送消息申请，领导协调串行执行 |

### 3.5 前端 Agent 调度

前端 Agent（web-developer / miniprogram-developer）的调度规则：

- **有接口交互时**: 前端 Agent 作为独立任务加入任务列表，依赖**所有后端任务完成**
- **无接口交互时**: 前端 Agent 无依赖，可与后端 Agent 并行执行
- 前端 Agent 使用同样的成员 Prompt 注入规范

| 前端 Agent | Parallel Agent 成员名 |
|------------|-------------------|
| web-developer | `@web-dev` |
| miniprogram-developer | `@miniprogram-dev` |

### 3.6 领导（编排器）的行为约束

在 Parallel Agent 调度下，编排器作为调度中心：

| ✅ 必须做 | ❌ 禁止做 |
|-----------|----------|
| 发起 Agent 调用并收集结果 | 直接编写任何源代码 |
| 监控成员完成状态 | 在成员工作时中断它们 |
| 接收成员的完成消息 | 替代成员完成未完成的任务 |
| 汇总结果并更新 state.json | 向成员传递其他成员的完整对话 |
| 处理公共模块修改冲突 | 忽略成员的风险汇报 |

> **提示**: 使用委派模式（Shift+Tab）可自动限制领导只使用协调工具。

### 3.7 团队完成与清理

所有成员完成任务后，编排器执行：

```
1. 逐一确认每个成员的完成消息和实现报告
2. 汇总所有成员的风险项
3. 更新 state.json 中各平台的 status 为 "completed"
4. 关闭所有成员：让所有成员关闭
5. （Agent 工具为同步调用，无需清理）
6. 在 state.json 的 implementMode 字段记录 "agent-teams"
7. 恢复正常模式，准备进入 BUILD_VERIFY 阶段
```

> **重要**: Agent 工具为同步调用，每个 Agent 完成后自动释放，无需手动清理。

---

## 4. 创建失败处理（替代原降级模式）

当 Agent 调用失败时，编排器**不自动降级**，而是：

1. 向用户展示错误信息
2. 提供选项：
   - **重试**：重新尝试发起 Parallel Agent 调度
   - **手动处理**：用户自行在 IDE 中执行开发任务
   - **强制降级**：用户明确要求后，使用编排器直接执行模式（编排器加载 Agent 规范自行执行，上下文压力大，产出精度可能降低）

> **CRITICAL**：编排器**严禁自行决定降级**。即使检测到仅 1 个 Agent 需调度，也必须尝试发起 Parallel Agent 调度。

---

## 5. 编译修复模式（BUILD_VERIFY 回退后触发）

当 BUILD_VERIFY 阶段编译失败并回退到 IMPLEMENT 时，编排器进入**编译修复模式**。此模式下的调度规则与正常 IMPLEMENT 不同：

### 5.1 模式选择

| 需修复的独立 Agent 数量 | 调度模式 |
|------------------------|---------|
| 1 个 Agent | Agent 串行模式（降级） |
| ≥2 个 Agent | Parallel Agent 调度 |

### 5.2 共通规则（两种模式均适用）

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

### 5.3 Parallel Agent 修复模式的特殊规则

在编译修复模式下使用 Parallel Agent 时：

- 团队名称为 `fix-{需求ID}-{回退次数}`（区别于正常的 `impl-{需求ID}`）
- 仅为需修复的领域创建成员，不创建已通过的领域
- 成员 Prompt 中额外注入编译错误上下文（来自 rollbackLog.errors）
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
   b) 若存在且 d2cConfig.mode = "embedded" → 直接进入 D2C 嵌入模式
   c) 若 d2cConfig.mode = "standalone" 且 status = "completed" → D2C 已完成，
      检查 intentType 是否为 "d2c-to-workflow"：
      - 是 → 跳过前端 IMPLEMENT（D2C 代码已生成），仅调度后端 Agent
      - 否 → ⚠️ 异常 case（standalone 完成后转入标准流水线时 intentType 应为 d2c-to-workflow），
             按防御性逻辑正常调度，并在日志中记录此异常状态组合

2. 若 d2cConfig 不存在，检查架构文档中是否有 Figma 关联：
   a) 读取 architecture/frontend/tech-requirements.md（如存在）
   b) 搜索关键标记：figmaUrl / figma.com/design / d2c-embedded
   c) 若找到 Figma 关联 → 创建 d2cConfig（mode: "embedded"）并进入 D2C 嵌入模式
   d) 若未找到 → 正常调度（跳过 D2C）

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

当判定为 D2C 嵌入模式时，前端 Agent 的调度替换为 D2C 子流程：

```
D2C 嵌入模式调度（替代常规前端 Agent）：

1. 前置条件检查：
   - FramelinkFigmaMCP 已配置且可用
   - Figma URL 已解析出 fileKey 和 nodeId
   - projectConfig.webProject 已设置

2. 加载 figma-d2c Skill：
   - 使用 Skill 工具（skill: "figma-d2c"） 加载 D2C Skill
   - 传入嵌入模式上下文：
     {
       mode: "d2c-embedded",
       figmaUrl: "{d2cConfig.figmaUrl}",
       fileKey: "{d2cConfig.fileKey}",
       nodeId: "{d2cConfig.nodeId}",
       projectDir: "{projectConfig.webProject}",
       architectureDocs: "{architecture/frontend/ 目录路径}"
     }

   > ⚠️ 执行模式由 figma-d2c Skill 自动判定：
   >   - 若当前在 Parallel Agent 环境中 → Multi-Agent 模式（Coordinator 调度 7 个 Agent）
   >   - 若当前在单一 AI 对话中 → 单 Agent 检查点协议（CP-0 ~ CP-M 顺序执行）
   > 两种模式产出相同的最终结果（代码 + manifest + 回归得分），调用方无需关心内部执行模式。

3. D2C 执行前端实现：
   - 使用 projectConfig.webProject 作为输出目录
   - 按 figma-d2c 检查点协议完整执行
   - 生成代码到 projectConfig.webProject 对应目录

4. D2C 完成后状态更新：
   - 更新 state.json：
     d2cConfig.status = "completed"
     d2cConfig.generatedFiles = [生成的文件列表]
     d2cConfig.regressionScore = {回归得分}
     d2cConfig.manifest = "{manifest 路径}"
     d2cConfig.completedAt = "{ISO 时间}"
   - 更新 platforms.web.status = "completed"

5. 继续正常流程：
   - D2C 完成后，编排器继续检查其他平台（后端等）
   - 所有平台完成后进入 BUILD_VERIFY 阶段
```

### 6.2 D2C 嵌入模式与 Parallel Agent 的关系

| 场景 | 调度策略 |
|------|---------|
| D2C 嵌入 + 后端多领域 | Parallel Agent 调度：D2C 作为 `@d2c-frontend` 成员加入团队，与后端领域 Agent 并行 |
| D2C 嵌入 + 仅前端 | Agent 串行模式（降级）：仅 1 个 Agent（D2C），直接用 Task 调用 |
| D2C 嵌入 + 后端单领域 | Parallel Agent 调度：2 个 Agent（@d2c-frontend + @{domain}-dev） |

**D2C 作为 Parallel Agent 成员时的 Prompt 模板**：

```
生成一个 D2C 前端开发成员（@d2c-frontend），Prompt 如下：

"你是 D2C Multi-Agent 协调器，负责将 Figma 设计稿转换为前端代码。

## 工作职责

1. 加载 figma-d2c Skill
2. 以嵌入模式（d2c-embedded）执行完整 D2C 流程
3. 遵循 figma-d2c SKILL.md 的检查点协议
4. 输出目录：{projectConfig.webProject}

## 上下文

- Figma URL: {d2cConfig.figmaUrl}
- fileKey: {d2cConfig.fileKey}
- nodeId: {d2cConfig.nodeId}
- 项目目录: {projectConfig.webProject 的绝对路径}
- 前端架构文档: {architecture/frontend/tech-requirements.md 的绝对路径}

## 依赖关系

{若需要后端 API → 依赖所有后端 Agent 完成}
{若无接口交互 → 无依赖，可并行}

完成后，请向领导发送消息汇报完成状态，包含：
- D2C 回归验证得分
- 生成的文件数量
- generation-manifest.json 路径
- 是否存在风险项"
```

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
   - 后端 Agent 可参考 D2C 生成的前端代码理解接口需求

3. 小程序平台（miniprogram，如有）：
   - 正常调度小程序 Agent

4. 状态标记：
   - state.json 中 implementMode 记录为 "d2c-to-workflow"
```

---

## 7. 异常处理与恢复

### 7.1 成员卡死/失败

| 场景 | 处理方式 |
|------|---------|
| 成员长时间无响应 | 通过 `@成员名` 发送消息唤醒，或让领导生成替代成员 |
| 成员执行出错 | 领导通过 `@成员名` 发送修复指令 |
| 成员完成但报告缺失 | 领导通过 `@成员名` 要求补充报告 |

### 7.2 断点恢复

Parallel Agent 调度下的断点恢复有特殊限制（Parallel Agent 不支持 /resume 恢复成员）：

```
恢复策略：
1. 读取 state.json，检查 implementMode 字段
2. 若 implementMode = "agent-teams" 且 currentPhase = "IMPLEMENT"：
   a) 检查各平台 status，确定哪些领域已完成（status = "completed"）
   b) 对未完成的领域，创建新的 Agent Team 继续执行
   c) 新团队只包含未完成领域的成员
3. 若 implementMode = "task" 或字段不存在：
   a) 使用 Agent 工具串行模式恢复
```

### 7.3 成员间公共模块冲突处理

当 P1+ 的成员需要修改公共模块（如 `{common-module}/`）时（例如需要添加一个公共枚举类）：

```
冲突处理流程：
1. 成员向领导发送消息："我需要在公共模块中添加 {具体内容}，请协调"
2. 领导检查当前是否有其他成员正在修改公共模块
3. 若无冲突 → 领导回复该成员："已授权，请执行修改"
4. 若有冲突 → 领导回复："请等待 @{另一成员} 完成公共模块修改后再执行"
5. 冲突解除后，领导通知等待的成员可以继续
```

---

## 8. 确定性验证脚本（实验性）

> **设计来源**：借鉴 Karpathy LLM Wiki 社区的 "Deterministic Generation Engine"——"Run, don't Read" 原则。脚本执行输出结果，Agent 只消费输出（~1KB），而非自行搜索分析（~50KB 上下文）。

### 8.1 适用场景

当 IMPLEMENT 阶段的开发 Agent 需要进行以下验证时，可调用确定性脚本替代手动搜索：

| 验证类型 | 脚本方式 | 替代的手动操作 | 上下文节省 |
|---------|---------|-------------|----------|
| Maven 依赖检查 | `mvn dependency:tree -Dincludes={groupId}` | Agent 手动搜索 pom.xml 解析依赖 | ~10KB → ~0.5KB |
| import 一致性 | `grep -r "import {类名}" {目录} --include="*.java"` | Agent 用 Grep 搜索 | ~5KB → ~0.3KB |
| 接口签名校验 | `grep -n "public.*{方法名}" {文件路径}` | Agent Read 整个文件再解析 | ~20KB → ~0.2KB |
| TypeScript 类型检查 | `tsc --noEmit 2>&1 | head -20` | Agent 人肉审查类型 | ~15KB → ~0.5KB |

### 8.2 使用约束

- 确定性脚本为**可选优化**，不强制所有 Agent 使用
- Agent 可在"引用必读流程"中选择使用脚本替代全文件读取
- 脚本仅用于**验证和查询**，不用于代码生成
- 脚本执行结果必须记录在实现报告的验证证据中