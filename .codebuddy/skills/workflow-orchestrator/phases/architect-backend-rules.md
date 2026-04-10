# ARCHITECT_BACKEND 阶段 Agent Teams 调度规则（按需加载）

> **加载时机**: 编排器进入 ARCHITECT_BACKEND 阶段时加载本文件。

---

## 0. Agent 选择与调度模式

### 0.1 架构师 Agent 自动选择（CRITICAL）

ARCHITECT_BACKEND 阶段支持两个架构师 Agent，编排器**必须先确定使用哪个**：

| Agent 文件 | 适用场景 | 技术栈 |
|-----------|---------|--------|
| `agents/backend-architect.md` | **通用版**（默认首选） | Node.js / Python / Go / Rust / 全新项目 / 未知技术栈 |
| `agents/java-architect.md` | **Java 专版** | Java / Spring Cloud / Spring Boot 项目 |

**选择流程**:
```
架构师 Agent 选择流程：
1. 读取 analysis/tech-requirements-backend.md，提取技术栈声明
2. 判断后端技术栈：
   a) 明确为 Java/Spring 系 → 使用 java-architect.md
   b) 明确为非 Java（Node.js/Python/Go 等） → 使用 backend-architect.md
   c) 未声明 / 无法判断 → 使用 backend-architect.md（通用版兜底）
3. 若项目有已有代码 → 扫描特征文件交叉验证：
   - pom.xml / build.gradle 存在 → Java
   - package.json 存在且非前端独占 → Node.js
   - requirements.txt / pyproject.toml 存在 → Python
   - go.mod 存在 → Go
4. 将选择结果记录到 state.json 的 architectBackendAgent 字段
```

> **设计意图**: `java-architect.md` 保留了 Java 生态的深度知识（Spring Cloud、分包规范、Feign 通信等），对 Java 项目提供更精准的架构设计。`backend-architect.md` 作为技术栈无关的通用版本，确保任何后端技术栈都能获得高质量的架构设计。

### 0.2 三级降级调度策略

ARCHITECT_BACKEND 阶段支持**三级降级调度**，编排器按优先级逐级尝试：

| 级别 | 模式 | 触发条件 | 说明 |
|------|------|---------|------|
| **Level 1** | Agent Teams 模式（默认） | 涉及的后端领域/模块 ≥2 个，始终优先尝试 | 使用 Agent Teams 两步模式：全局架构分析 → 领域/模块文档并行输出，上下文完全隔离 |
| **Level 2** | Task 串行流水线 | 涉及的后端领域/模块仅 1 个，或 Level 1 创建失败 / 超时无响应 | 2-3 个同步 Task 串行调用，复用架构师 Agent 规范，中间产物传递 |
| **Level 3** | 编排器直接执行 | Level 2 执行失败 | 编排器自身上下文内，参考 `agents/{selected-architect}.md` 规范直接生成产物 |

> **设计意图**:
> - **Level 1 (Agent Teams)** 的核心价值是**上下文防火墙**。ARCHITECT_BACKEND 阶段的核心瓶颈是**多领域/模块文档输出导致上下文膨胀**。通过 Agent Teams 将"全局架构分析"与"逐领域/模块文档输出"拆为两步，并在第二步为每个领域/模块分配独立上下文窗口，彻底消除上下文污染。同时引入检查点机制，确保全局产物在第一步完成后即刻落盘，即使第二步中断也不会丢失。
> - **Level 2 (Task 串行流水线)** 解决 Agent Teams 异步机制不可靠的问题。同步 Task 调用保证可靠性，同时通过拆分为 2-3 个 Task 并借助中间产物文件传递数据，避免单个 Task 上下文窗口被撑爆。每个 Task Agent 自行 `read_file` 读取架构师 Agent 规范文件（而非注入完整内容到 Prompt），控制 Prompt 大小。
> - **Level 3 (编排器直接执行)** 是最终兜底。编排器在自身上下文中参考 `agents/{selected-architect}.md` 的核心流程直接分析，产出精度最低但保证流程不阻断。

### 0.3 降级决策流程

```
编排器执行流程：

1. 读取 state.json，检查是否有断点恢复信息
2. 如果 architectBackendMode 已有值且非空：
   a) "agent-teams" → 进入 §3（Agent Teams 断点恢复）
   b) "task-pipeline" → 进入 §4（Task 流水线断点恢复）
   c) "fallback" → 进入 §4A（编排器直接执行恢复）
   d) "task"（兼容旧值）→ 进入 §4A（按 Level 3 处理）
3. 如果 architectBackendMode 为空或字段不存在：
   → 尝试 Level 1（§3），失败或超时则降级到 Level 2（§4），再失败降级到 Level 3（§4A）
```

---

## 1. 两步串行-并行混合协作模型

```
Step 1（串行，独占）:
  @global-architect  ──→  全局架构产物落盘（检查点 1）
                           ↓
Step 1.5（人工确认）:
  编排器展示领域划分确认单  ──→  用户确认/调整  ──→  domain-registry.json 落盘
                           ↓
Step 2（并行，多成员）:
  @domain-architect-common        ──→  {common-module}/tech-requirements.md
  @domain-architect-user-center   ──→  {user-center}/tech-requirements.md
  @domain-architect-product-center──→  {product-center}/tech-requirements.md
  ...（按需创建）                       ↓ 每完成一个即落盘（检查点 N）
```

### 1.1 成员注册表

| 成员名 | Agent 文件 | 职责 | 上下文特征 |
|--------|-----------|------|-----------|
| `@global-architect` | `agents/{selected-architect}.md`（§0.1 选择结果） | 全局架构分析：依赖图、优先级、模块边界、存量代码扫描 | **搜索密集**，上下文峰值较高（~100KB），但输出仅 3 个全局产物 |
| `@domain-architect-{module}` | `agents/{selected-architect}.md`（同一份 Agent 规范） | 单个领域/模块的技术需求文档输出 | **零搜索**，上下文极轻（~40KB），仅加载基础模板 + 本模块输入 + 全局产物引用 |

> **注意**: `{selected-architect}` 根据 §0.1 的选择结果确定，可为 `backend-architect` 或 `java-architect`。

### 1.2 任务依赖关系

```
任务列表：
1. [S1] 全局架构分析 — 分配给 @global-architect — 无依赖
2. [S2-a] {common-module} 领域文档 — 分配给 @domain-architect-common — 依赖 S1
3. [S2-b] {user-center} 领域文档 — 分配给 @domain-architect-user-center — 依赖 S1
4. [S2-c] {product-center} 领域文档 — 分配给 @domain-architect-product-center — 依赖 S1
   ... （按实际涉及的领域动态生成）
```

**核心规则**:
- Step 1 完成后**必须先落盘全局产物并更新检查点**，才能启动 Step 2
- Step 2 的所有领域成员之间**无依赖关系**，可真并行执行
- 每个领域成员完成后**立即写入文件系统**，并向领导汇报

### 1.3 中间产物与检查点（上下文防火墙 + 落盘保护）

| 产物 | 写入方 | 读取方 | 落盘时机 |
|------|--------|--------|---------|
| `architecture/backend/architecture.md` | @global-architect | 所有 @domain-architect-* | Step 1 完成时（检查点 1） |
| `architecture/backend/dependency-graph.md` | @global-architect | 所有 @domain-architect-* | Step 1 完成时（检查点 1） |
| `architecture/backend/priority-list.md` | @global-architect | 所有 @domain-architect-* | Step 1 完成时（检查点 1） |
| `architecture/backend/backend-clarify.json` | @global-architect | 编排器（澄清阶段） | Step 1 完成时（检查点 1，可选） |
| `architecture/backend/domain-registry.json` | 编排器 | 编排器（IMPLEMENT 阶段）、所有 @domain-architect-* | 🆕 Step 1.5 用户确认后（检查点 1.5） |
| `architecture/backend/{service}/tech-requirements.md` | @domain-architect-{service} | 下游开发 Agent | 每个领域成员完成时（检查点 N） |

> **检查点 1 是"上下文防火墙"**: @global-architect 的存量代码扫描和依赖分析结果（~100KB 搜索上下文）被压缩为 3 个结构化文档（~20KB），领域成员的上下文因此保持干净。

---

## 2. 检查点机制（CRITICAL — 产物落盘保护）

### 2.1 检查点更新规则

编排器在以下时刻更新 `state.json` 的 `architectBackendCheckpoint` 字段：

| 时刻 | step 值 | completedArtifacts | 说明 |
|------|---------|-------------------|------|
| 阶段开始时 | `global_pending` | `[]` | 初始化检查点 |
| @global-architect 完成后 | `global_completed` | `[architecture.md, dependency-graph.md, priority-list.md]` | 全局产物已安全落盘 |
| 用户确认领域划分后（Step 1.5） | `domains_confirmed` | 同上 + `domain-registry.json` | 🆕 领域划分已经用户确认，domain-registry.json 已落盘 |
| 领域成员陆续完成时 | `domains_pending` | 追加 `{service}/tech-requirements.md` | 每完成一个领域即更新 |
| 所有领域成员完成后 | `domains_completed` | 所有产物 | 阶段完成 |

### 2.2 检查点更新流程

```
每个产物落盘后：
  1. 编排器 read_file 确认产物文件存在且非空
  2. 更新 architectBackendCheckpoint:
     - 将产物路径追加到 completedArtifacts
     - 将完成的领域从 pendingDomains 移至 completedDomains
     - 更新 updatedAt
  3. 写入 state.json
```

### 2.3 断点恢复策略

当 ARCHITECT_BACKEND 阶段中断后恢复时：

```
恢复策略：
1. read_file 读取 state.json
2. 检查 architectBackendCheckpoint.step：
   a) step = "global_pending"
      → @global-architect 未完成，需重新执行 Step 1
      → 创建新团队，从 @global-architect 开始
   b) step = "global_completed"
      → 全局产物已落盘，但领域划分尚未确认
      → 进入 Step 1.5 领域划分确认关卡
   c) step = "domains_confirmed"
      → 领域划分已确认，可直接进入 Step 2
      → 创建新团队，仅包含所有领域成员
   d) step = "domains_pending"
      → 部分领域已完成，部分未完成
      → 创建新团队，仅包含 pendingDomains 中的领域成员
      → completedDomains 中的领域不需要重新执行
   e) step = "domains_completed"
      → 所有产物已完成，直接进入"总结确认"
3. 恢复时，检查 completedArtifacts 中每个文件是否仍存在
   → 若文件被删除，从 completedArtifacts/completedDomains 中移除，加回 pendingDomains
```

---

## 3. Agent Teams 模式调度规则

### 3.1 团队创建

编排器作为 **team-lead（团队领导）** 创建 Agent Team，使用**委派模式（Delegate Mode）**。

**创建指令模板**:

```
创建一个名为 arch-backend-{需求ID} 的后端架构设计团队，使用委派模式。

团队任务：基于后端技术需求文档进行架构设计，产出全局架构文档和各领域技术需求文档。
团队采用两步模式：Step 1 全局架构分析（串行），Step 2 领域文档并行输出。

成员列表：
{见 §3.2 成员生成规则}

任务依赖关系：
1. [S1] 全局架构分析 — @global-architect — 无依赖
2. [S2-a] {领域1}领域文档 — @domain-architect-{service1} — 依赖 S1
3. [S2-b] {领域2}领域文档 — @domain-architect-{service2} — 依赖 S1
   ... （按涉及领域动态生成）
```

### 3.2 成员生成规则

#### 成员 1: @global-architect（必选，始终创建）

```
生成一个全局架构师成员（@global-architect），Prompt 如下：

"你是一位资深后台架构师，负责后端全局架构分析。

你的工作职责（仅限全局架构分析，不输出领域/模块技术需求文档）：
1. 读取 Agent 行为规范：{agents/{selected-architect}.md 的绝对路径}
   — 仅执行规范中的「阶段一：理解与分析」和「阶段二：架构设计」
   — 跳过「阶段三：领域/模块文档输出」（由领域/模块成员完成）
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
4. 读取后端技术需求文档：{analysis/tech-requirements-backend.md 的绝对路径}
5. 执行存量代码结构扫描（Agent 规范 §1.2）
6. 绘制模块依赖图并执行循环依赖检测
7. 确定开发优先级清单（拓扑排序）
8. 若有澄清问题，输出 backend-clarify.json

输出产物（全局级）：
- {architecture/backend/architecture.md 的绝对路径}
- {architecture/backend/dependency-graph.md 的绝对路径}
- {architecture/backend/priority-list.md 的绝对路径}
- {architecture/backend/backend-clarify.json 的绝对路径}（可选）

⚠️ 重要约束：
- 你只负责全局架构分析和全局产物输出
- 不要输出任何领域/模块的 tech-requirements.md（由领域/模块成员并行完成）
- 你需要在 architecture.md 中列出本次涉及的所有领域/模块及其职责边界，供领域/模块成员引用

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

完成后，请向领导发送消息汇报完成状态，包含：
- 涉及的领域/模块清单
- 是否存在循环依赖
- 是否有澄清问题
- 各全局产物文件路径确认"
```

#### 成员 2~N: @domain-architect-{module}（按涉及领域/模块动态生成）

```
生成一个 {领域/模块中文名} 架构成员（@domain-architect-{module}），Prompt 如下：

"你是一位资深后台架构师，负责 {领域/模块名} 的技术需求文档输出。

你的工作职责（仅限本领域/模块的技术需求文档输出）：
1. 读取 Agent 行为规范：{agents/{selected-architect}.md 的绝对路径}
   — 仅执行规范中的「阶段三：领域/模块文档输出」
   — 跳过「阶段一」和「阶段二」（已由全局架构师完成）
2. 读取全局架构文档：{architecture/backend/architecture.md 的绝对路径}
3. 读取模块依赖图：{architecture/backend/dependency-graph.md 的绝对路径}
4. 读取开发优先级清单：{architecture/backend/priority-list.md 的绝对路径}
5. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
6. 读取后端技术需求文档：{analysis/tech-requirements-backend.md 的绝对路径}
7. 按需加载领域/模块文档模板（Agent 规范 §3.2 渐进式模板加载策略）：
   - 基础模板：{templates/domain-tech-requirements-base.md 的绝对路径}
   - 领域模型模板：{templates/domain-model-template.md 的绝对路径}（如需要）
   - API 设计模板：{templates/api-design-template.md 的绝对路径}（如需要）
   - 数据模型模板：{templates/database-design-template.md 的绝对路径}（如需要）
   - 服务依赖模板：{templates/service-dependency-template.md 的绝对路径}（如需要）
8. 输出本领域/模块的技术需求文档

输出产物：
- {architecture/backend/{module}/tech-requirements.md 的绝对路径}

⚠️ 重要约束：
- 你只负责 {领域/模块名} 一个领域/模块的文档输出
- 不要修改全局架构产物（architecture.md、dependency-graph.md、priority-list.md）
- 接口签名必须引用总纲 API-xxx，禁止修改 API Path、字段名、字段类型
- 复用评级直接继承自 tech-requirements-backend.md
- 执行非传递性依赖声明检查（Agent 规范 §3.6，若适用）
- 目录结构/包结构必须与存量代码一致（引用全局架构文档中的扫描结论）

领域/模块边界约束：
- ✅ 仅输出 {module} 的 tech-requirements.md
- ❌ 严禁输出其他领域/模块的文档

需求 ID：{state.json 中的 id}
当前工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

完成后，请向领导发送消息汇报完成状态，包含：
- 输出文件路径确认
- 涉及的模板加载清单
- 文件级改动清单摘要
- 是否存在风险项"
```

> **关键**: 所有 Prompt 中的路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析）。

### 3.3 涉及领域/模块的动态识别

编排器通过以下方式确定本次需求涉及的后端领域/模块：

```
识别流程：
1. 读取 analysis/tech-requirements-backend.md
2. 定位「## 1. 改动范围」章节，提取涉及的后端模块列表
3. 根据 §0.1 选择的架构师 Agent 类型执行不同的匹配策略：

   a) 当 selected-architect = java-architect 时（Java 项目）：
      - 与项目已注册的领域列表交叉匹配
      - 领域列表来自 `agents/java-domain-developers/` 目录下的 Agent 文件名
      - 为每个匹配的领域创建对应的 @domain-architect-{service} 成员
   
   b) 当 selected-architect = backend-architect 时（通用项目）：
      - 直接使用 tech-requirements-backend.md 中声明的模块列表
      - 无需与预注册领域交叉匹配（通用版不依赖预注册的领域 Agent）
      - 根据模块划分原则将模块分组：
        * 公共基础模块（database/middleware/utils 等）→ 合并为 common 领域
        * 独立业务模块 → 各自作为独立领域
      - 为每个领域创建对应的 @domain-architect-{module} 成员

4. 执行领域数量治理规则校验（§3.6）
5. 确认领域/模块数量，选择调度模式（§0.2）
```

### 3.3.1 领域数量治理规则（CRITICAL — 防膨胀防线）

编排器在动态识别领域后、启动 Step 1 前，**必须**执行以下治理规则校验：

| 约束 | 阈值 | 触发行为 |
|------|------|---------|
| 单需求领域上限 | **8** | 超过 8 个领域时 → 编排器**强制阻断**，要求全局架构师重新评估并合并，直到 ≤8 |
| 单领域最少模块数 | **2** | 低于 2 个模块的领域 → 编排器标记为 ⚠️ 合并候选，在领域确认单（§3.3.2）中高亮提示用户 |
| 公共模块合并规则 | — | database / middleware / utils / config / constants 等基础设施模块 → 强制合并为 `common` 领域 |
| 同名领域复用规则 | — | 若 `domain-registry.json`（§3.7）中已存在同名领域 → 必须复用已有领域定义，禁止新建同名但不同边界的领域 |
| 单领域最大文件数 | **30** | 超过 30 个文件的领域 → 标记为 ⚠️ 拆分候选，在领域确认单中高亮提示用户 |

**治理校验流程**:

```
治理校验：
1. 统计领域总数 → 若 > 8，阻断并要求合并
2. 统计每个领域的模块数 → 标记低于 2 个模块的领域为合并候选
3. 检查公共模块合并规则 → 确保基础设施模块已合并为 common
4. 读取已有 domain-registry.json（若存在）→ 检查同名领域复用
5. 估算每个领域预期文件数 → 标记超过 30 个文件的领域为拆分候选
6. 将治理校验结果注入到领域划分确认单（§3.3.2）中展示
```

### 3.3.2 领域划分确认关卡（Step 1.5 — 人工确认点）

> **设计意图**: 在全局架构师（Step 1）完成全局分析后、领域架构师（Step 2）启动前，增加一个**专门聚焦领域划分合理性**的人工确认关卡。这是防止领域膨胀的核心流程防线。

**确认时机**: Step 1 全局架构产物落盘 → **Step 1.5 领域划分确认** → Step 2 领域文档并行输出

**确认流程**:

```
Step 1.5 领域划分确认（CRITICAL — 不可跳过）：

1. 编排器从 @global-architect 的完成汇报和 architecture.md 中提取：
   - 领域列表（名称 + 中文描述）
   - 每个领域包含的模块
   - 每个领域的预期文件数
   - 领域间的依赖关系

2. 执行治理规则校验（§3.3.1），标记异常项

3. 向用户展示【领域划分确认单】（格式见 output-formats/architect-backend-formats.md §16.5）：
   - 领域清单表（含治理指标）
   - 治理规则校验结果
   - 合并/拆分建议（若有）
   - 领域间依赖关系摘要

4. 等待用户选择：
   a) 「确认」→ 按当前领域划分继续进入 Step 2
   b) 「调整」→ 用户指定合并/拆分/重命名操作，编排器更新领域列表后重新展示
   c) 「重做全局分析」→ 回到 Step 1 重新执行（罕见场景）

5. 用户确认后：
   - 将确认后的领域列表写入 domain-registry.json（§3.7）
   - 更新 state.json 的 architectBackendCheckpoint.step 为 "domains_confirmed"
   - 继续执行 Step 2
```

**用户调整操作支持**:

| 操作 | 编排器行为 |
|------|-----------|
| 合并领域 | 将指定领域的模块合并到目标领域，更新领域列表 |
| 拆分领域 | 将指定领域按用户指定的模块分组拆分为多个领域 |
| 重命名领域 | 修改领域 ID 和中文名 |
| 删除领域 | 移除领域（模块归入其他领域或标记为不涉及） |
| 新增领域 | 从已有领域中拆出模块组成新领域 |

### 3.4 领导（编排器）的行为约束

在 Agent Teams 模式下，编排器作为 team-lead：

| ✅ 必须做 | ❌ 禁止做 |
|-----------|----------|
| 创建团队并分配任务 | 直接执行任何架构分析/文档输出工作 |
| @global-architect 完成后立即更新检查点 | 在 Step 1 未完成时启动 Step 2 |
| 每个领域成员完成后立即更新检查点 | 跳过检查点更新直接流转 |
| 监控成员完成状态 | 替代成员完成未完成的任务 |
| 汇总结果并更新 state.json | 忽略成员的错误/风险汇报 |
| 处理 @global-architect 上报的澄清问题 | 向领域成员传递其他领域成员的对话 |
| 监控超时并执行自动降级（§3.5A） | 在超时降级前不发催促消息 |

### 3.5 团队完成与清理

所有成员完成任务后，编排器执行：

```
1. 确认 @global-architect 的完成消息和全局产物
2. 逐一确认每个 @domain-architect-{service} 的完成消息和领域产物
3. 执行产物完整性检查：
   - architecture/backend/architecture.md 存在
   - architecture/backend/dependency-graph.md 存在
   - architecture/backend/priority-list.md 存在
   - architecture/backend/domain-registry.json 存在（🆕 领域注册表）
   - 每个涉及领域的 architecture/backend/{service}/tech-requirements.md 存在
   - 若有澄清问题，backend-clarify.json 存在
4. 执行质量检查：
   - 所有领域文档中接口签名均引用了总纲 API-xxx
   - 复用评级直接继承自 tech-requirements-backend.md
   - 包结构一致性检查
   - 🆕 domain-registry.json 中的领域列表与实际产出的领域目录一致
5. 汇总所有成员的风险项
6. 更新 state.json:
   - architectBackendAgent 设为 §0.1 的选择结果（如 "backend-architect" 或 "java-architect"）
   - architectBackendMode 设为 "agent-teams"
   - architectBackendCheckpoint.step 设为 "domains_completed"
   - architectBackendTeam 记录团队信息
7. 关闭所有成员 → 清理团队
8. 恢复正常模式，进入"总结确认"步骤
```

### 3.5A 超时检测与自动降级（Level 1 → Level 2）

Agent Teams 异步消息机制存在不可靠性风险。编排器必须实施超时检测，防止无限等待：

#### 超时策略

```
超时检测流程（对每个成员执行）：

1. 成员创建后启动计时器
2. 等待 120 秒（2 分钟）后检查：
   a) 如果成员已发送完成消息 → 正常继续
   b) 如果成员未响应 → 发送催促消息：
      "请汇报当前进度。如果已完成，请发送完成消息。"
3. 催促后再等待 60 秒（1 分钟）：
   a) 如果收到响应 → 继续等待完成
   b) 如果仍无响应 → 判定为超时
4. 超时处理：
   a) 向该成员发送 shutdown_request
   b) 检查该成员应产出的产物文件是否已存在于文件系统
   c) 如果产物已存在 → 跳过该成员，继续调度下一成员
   d) 如果产物不存在 → 触发降级
```

#### 降级触发条件

| 触发条件 | 降级目标 |
|---------|---------|
| 团队创建失败（team_create 报错） | Level 2 |
| @global-architect 超时且无全局产物 | Level 2 |
| 领域成员超时且无领域产物 | Level 2（从该领域对应的 Task 步骤开始） |

#### 降级执行

```
降级执行流程：

1. 记录降级原因到控制台日志
2. 尝试清理已创建的团队（team_delete），忽略清理失败
3. 检查已存在的产物文件，确定 Level 2 的起始步骤
4. 更新 state.json: architectBackendMode = "task-pipeline"
5. 跳转到 §4（Level 2 Task 串行流水线），从断点继续
```

---

## 4. Level 2: Task 串行流水线

当 Level 1 失败或超时后，或涉及的后端领域/模块仅 1 个时，编排器使用同步 Task 工具调用，将架构设计拆分为 2-3 个串行 Task。每个 Task 复用 §0.1 选择的架构师 Agent 规范，通过中间产物文件传递上下文。

### 4.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **规范文件引用，非注入** | Task Prompt 中只给出 Agent 规范文件的**绝对路径**，由 Task Agent 自行 `read_file` 加载，避免 Prompt 膨胀 |
| **中间产物传递** | 与 Level 1 完全相同的中间产物文件（全局架构产物），保证数据格式一致 |
| **断点恢复** | 每个 Task 完成后中间产物已落盘，降级或中断后可从已完成的 Task 之后继续 |
| **角色合并** | 涉及领域/模块仅 1 个时，全局分析 + 领域文档输出合并为单次 Task 调用 |

### 4.2 流水线定义

#### 单领域/模块（1 个 Task — 合并模式）

```
Task 流水线：

[Task-A] 全局架构分析 + 领域文档输出（合并模式）
  输入：state.json + tech-requirements.md + tech-requirements-backend.md + 存量代码
  产出：architecture/backend/architecture.md
        architecture/backend/dependency-graph.md
        architecture/backend/priority-list.md
        architecture/backend/{module}/tech-requirements.md
```

#### 多领域/模块（2-3 个 Task — 从 Level 1 降级）

```
Task 流水线：

[Task-A] 全局架构分析（复用 @global-architect 规范）
  输入：state.json + tech-requirements.md + tech-requirements-backend.md + 存量代码
  产出：architecture/backend/architecture.md
        architecture/backend/dependency-graph.md
        architecture/backend/priority-list.md

  ↓ 全局产物落盘（检查点 1）

[Task-B ~ Task-N] 各领域文档输出（每个领域一个 Task，串行执行）
  输入：全局架构产物 + tech-requirements.md + tech-requirements-backend.md
  产出：architecture/backend/{module}/tech-requirements.md

  ↓ 每个领域产物落盘（检查点 N）
```

### 4.3 Task Prompt 模板

#### Task-A: 全局架构分析

```
你是一位资深后台架构师。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（read_file）：{agents/{selected-architect}.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
4. 读取后端技术需求文档：{analysis/tech-requirements-backend.md 的绝对路径}
5. 仅执行规范中的「阶段一：理解与分析」和「阶段二：架构设计」
6. 跳过「阶段三：领域/模块文档输出」（由后续 Task 完成）
7. 执行存量代码结构扫描（Agent 规范 §1.2）
8. 绘制模块依赖图并执行循环依赖检测
9. 确定开发优先级清单（拓扑排序）

输出产物（全局级）：
- {architecture/backend/architecture.md 的绝对路径}
- {architecture/backend/dependency-graph.md 的绝对路径}
- {architecture/backend/priority-list.md 的绝对路径}
- {architecture/backend/backend-clarify.json 的绝对路径}（可选）

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

⚠️ 重要：
- 你必须先 read_file 读取 Agent 规范文件，再按规范执行
- 你只负责全局架构分析，不输出领域/模块技术需求文档
- 完成后返回产物路径和关键摘要
```

#### Task-B~N: 领域文档输出（每个领域一个 Task）

```
你是一位资深后台架构师，负责 {领域/模块名} 的技术需求文档输出。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（read_file）：{agents/{selected-architect}.md 的绝对路径}
   — 仅执行规范中的「阶段三：领域/模块文档输出」
2. 读取全局架构文档：{architecture/backend/architecture.md 的绝对路径}
3. 读取模块依赖图：{architecture/backend/dependency-graph.md 的绝对路径}
4. 读取开发优先级清单：{architecture/backend/priority-list.md 的绝对路径}
5. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
6. 读取后端技术需求文档：{analysis/tech-requirements-backend.md 的绝对路径}
7. 按需加载领域/模块文档模板（Agent 规范 §3.2 渐进式模板加载策略）
8. 输出本领域/模块的技术需求文档

输出产物：
- {architecture/backend/{module}/tech-requirements.md 的绝对路径}

⚠️ 重要：
- 你必须先 read_file 读取 Agent 规范文件，再按规范执行
- 你只负责 {领域/模块名} 一个领域/模块的文档输出
- 不要修改全局架构产物
- 完成后返回产物路径和关键摘要
```

#### 合并模式 Task（单领域/模块）

```
你是一位资深后台架构师。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（read_file）：{agents/{selected-architect}.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取技术需求总纲：{analysis/tech-requirements.md 的绝对路径}
4. 读取后端技术需求文档：{analysis/tech-requirements-backend.md 的绝对路径}
5. 严格按照 Agent 规范执行全部工作流程（阶段一至阶段四）

输出产物：
- {architecture/backend/architecture.md 的绝对路径}
- {architecture/backend/dependency-graph.md 的绝对路径}
- {architecture/backend/priority-list.md 的绝对路径}
- {architecture/backend/{module}/tech-requirements.md 的绝对路径}
- {architecture/backend/backend-clarify.json 的绝对路径}（可选）

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}

⚠️ 重要：
- 你必须先 read_file 读取 Agent 规范文件，再按规范执行
- 完成后返回产物路径和关键摘要
```

### 4.4 Task 串行流水线执行流程

```
编排器执行流程：

1. 确定起始 Task（检查已存在的中间产物）：
   a) architecture.md 不存在 → 从 Task-A 开始
   b) architecture.md 存在但部分领域 tech-requirements.md 不存在 → 从对应领域 Task 开始
   c) 所有产物已存在 → 直接进入总结确认

2. 执行 Task-A（如需）：
   a) 使用 Task 工具，注入 §4.3 Task-A Prompt
   b) Task 返回后，检查全局产物是否成功写入
   c) 如果写入失败 → 降级到 Level 3
   d) 更新检查点 checkpoint.step = "global_completed"

3. 领域划分确认（Step 1.5，如适用）：
   a) 从 architecture.md 提取涉及领域列表
   b) 展示领域划分确认单（§3.3.2），等待用户确认/调整
   c) 确认后写入 domain-registry.json → 更新检查点为 "domains_confirmed"

4. 串行执行领域 Task（Task-B ~ Task-N）：
   a) 对每个领域，使用 Task 工具注入 §4.3 领域 Task Prompt
   b) 每个 Task 返回后，检查领域产物是否成功写入
   c) 如果写入失败 → 降级到 Level 3（已完成的领域产物保留）
   d) 每个领域完成后更新检查点

5. 所有 Task 完成后：
   a) 执行产物完整性检查
   b) 更新 state.json: architectBackendMode = "task-pipeline"
   c) 进入"总结确认"步骤
```

### 4.5 Level 2 失败处理

| 失败场景 | 处理方式 |
|---------|---------|
| Task-A 返回空结果 / 无全局产物 | 降级到 Level 3 |
| 领域 Task 返回空结果 / 无领域产物 | 降级到 Level 3（已有全局产物和已完成领域产物可供 Level 3 参考） |
| Task 执行过程中出现错误但有部分产物 | 检查产物完整性，完整则视为成功；不完整则降级到 Level 3 |

> **注意**: Level 2 模式下，`architectBackendMode` 设为 `"task-pipeline"`。**仍然使用检查点机制**——在每个 Task 返回后，编排器检查产物并更新 `architectBackendCheckpoint`。

---

## 4A. Level 3: 编排器直接执行（兜底模式）

当 Level 2 也失败时，编排器在自身上下文中直接执行后端架构设计。

### 4A.1 执行策略

```
编排器直接执行流程：

1. 读取可用的中间产物（Level 1/2 可能已产出部分）：
   a) 如果 architecture.md 存在 → 读取作为输入（全局分析已完成，仅需补全领域文档）
   b) 如果 dependency-graph.md 存在 → 读取作为输入
   c) 如果 priority-list.md 存在 → 读取作为输入
   d) 如果以上均不存在 → 直接读取 tech-requirements.md + tech-requirements-backend.md + state.json

2. 参考 agents/{selected-architect}.md 的核心设计流程，在编排器上下文中执行：
   - 存量代码结构扫描 → 模块依赖分析 → 架构设计 → 领域文档输出
   ⚠️ 注意：编排器上下文有限，设计深度可能不及 Level 1/2，但保证流程不阻断

3. 直接写入最终产物：
   - architecture/backend/architecture.md（如尚不存在）
   - architecture/backend/dependency-graph.md（如尚不存在）
   - architecture/backend/priority-list.md（如尚不存在）
   - architecture/backend/{module}/tech-requirements.md（补全未完成的领域）

4. 更新 state.json: architectBackendMode = "fallback"

5. 进入"总结确认"步骤
```

### 4A.2 Level 3 的限制说明

| 限制 | 说明 |
|------|------|
| 上下文受限 | 编排器的上下文已包含 SKILL.md、本规则文件等，留给架构设计的窗口有限 |
| 设计精度降低 | 多领域场景下，可能无法完整执行每个领域的深度分析，设计精度最低 |
| 产物质量标注 | 在全局架构文档 front-matter 中追加 `analysisMode: "fallback"`，提示后续阶段注意 |
| 流程保障 | 即使精度下降，仍保证有结构化产物输出，不阻断工作流 |

> **注意**: Level 3 产出时，编排器应在总结确认中向用户明确说明"本次架构设计使用了兜底模式，设计精度可能有所下降，建议仔细审阅产物"。

---

## 5. 检查点 + 状态记录示例

### 5.1 architectBackendMode 字段

| 值 | 说明 |
|-----|------|
| `"agent-teams"` | Level 1: Agent Teams 模式成功完成 |
| `"task-pipeline"` | Level 2: Task 串行流水线模式完成 |
| `"fallback"` | Level 3: 编排器直接执行模式完成 |
| `"task"` | 兼容旧值：等价于 Level 3（断点恢复时按 Level 3 处理） |

### 5.2 Level 1 Agent Teams 记录

#### Step 1 完成时的 state.json 片段

```json
{
  "currentPhase": "ARCHITECT_BACKEND",
  "architectBackendAgent": "backend-architect",
  "architectBackendMode": "agent-teams",
  "architectBackendCheckpoint": {
    "step": "global_completed",
    "completedArtifacts": [
      "architecture/backend/architecture.md",
      "architecture/backend/dependency-graph.md",
      "architecture/backend/priority-list.md"
    ],
    "pendingDomains": ["{common-module}", "{user-center}", "{product-center}"],
    "completedDomains": [],
    "updatedAt": "2026-03-25T12:30:00+08:00"
  },
  "architectBackendTeam": {
    "teamName": "arch-backend-20260325",
    "members": [
      {
        "name": "@global-architect",
        "role": "global",
        "domain": null,
        "status": "completed",
        "completedAt": "2026-03-25T12:30:00+08:00"
      },
      {
        "name": "@domain-architect-common",
        "role": "domain",
        "domain": "{common-module}",
        "status": "pending",
        "completedAt": null
      },
      {
        "name": "@domain-architect-user-center",
        "role": "domain",
        "domain": "{user-center}",
        "status": "pending",
        "completedAt": null
      },
      {
        "name": "@domain-architect-product-center",
        "role": "domain",
        "domain": "{product-center}",
        "status": "pending",
        "completedAt": null
      }
    ],
    "createdAt": "2026-03-25T12:00:00+08:00",
    "cleanedAt": null
  }
}
```

#### 部分领域完成时的 state.json 片段

```json
{
  "architectBackendCheckpoint": {
    "step": "domains_pending",
    "completedArtifacts": [
      "architecture/backend/architecture.md",
      "architecture/backend/dependency-graph.md",
      "architecture/backend/priority-list.md",
      "architecture/backend/{common-module}/tech-requirements.md",
      "architecture/backend/{user-center}/tech-requirements.md"
    ],
    "pendingDomains": ["{product-center}"],
    "completedDomains": ["{common-module}", "{user-center}"],
    "updatedAt": "2026-03-25T13:00:00+08:00"
  }
}
```

### 5.3 Level 2 Task 流水线记录

```json
{
  "currentPhase": "ARCHITECT_BACKEND",
  "architectBackendAgent": "backend-architect",
  "architectBackendMode": "task-pipeline",
  "architectBackendCheckpoint": {
    "step": "domains_completed",
    "completedArtifacts": [
      "architecture/backend/architecture.md",
      "architecture/backend/dependency-graph.md",
      "architecture/backend/priority-list.md",
      "architecture/backend/domain-registry.json",
      "architecture/backend/{common-module}/tech-requirements.md",
      "architecture/backend/{user-center}/tech-requirements.md",
      "architecture/backend/{product-center}/tech-requirements.md"
    ],
    "pendingDomains": [],
    "completedDomains": ["{common-module}", "{user-center}", "{product-center}"],
    "updatedAt": "2026-03-25T14:00:00+08:00"
  },
  "architectBackendPipeline": {
    "completedTasks": ["Task-A", "Task-B-common", "Task-B-user-center", "Task-B-product-center"],
    "degradedFrom": "agent-teams",
    "degradeReason": "成员 @global-architect 超时无响应",
    "completedAt": "2026-03-25T14:00:00+08:00"
  }
}
```

### 5.4 Level 3 兜底模式记录

```json
{
  "currentPhase": "ARCHITECT_BACKEND",
  "architectBackendAgent": "backend-architect",
  "architectBackendMode": "fallback",
  "architectBackendCheckpoint": {
    "step": "domains_completed",
    "completedArtifacts": [
      "architecture/backend/architecture.md",
      "architecture/backend/dependency-graph.md",
      "architecture/backend/priority-list.md",
      "architecture/backend/{common-module}/tech-requirements.md"
    ],
    "pendingDomains": [],
    "completedDomains": ["{common-module}"],
    "updatedAt": "2026-03-25T15:00:00+08:00"
  },
  "architectBackendFallback": {
    "degradedFrom": "task-pipeline",
    "degradeReason": "Task-A 返回空结果",
    "availableArtifacts": [],
    "completedAt": "2026-03-25T15:00:00+08:00"
  }
}
```

---

## 6. 异常处理与恢复

### 6.1 成员失败处理（Level 1）

| 场景 | 处理方式 |
|------|---------|
| @global-architect 失败 | 领导通过 @global-architect 发送修复指令，或创建替代成员 |
| @domain-architect-{service} 失败 | 同上；全局产物已存在，可直接创建新的领域成员重试 |
| 成员长时间无响应 | 执行 §3.5A 超时检测流程，必要时降级到 Level 2 |
| 部分领域成员失败但其他已完成 | 已完成的领域产物保留（检查点保护），仅重试失败的领域 |

### 6.2 全局产物落盘验证

@global-architect 完成后，编排器**必须**执行以下验证才能更新检查点：

```
验证流程：
1. read_file(architecture/backend/architecture.md) → 确认非空
2. read_file(architecture/backend/dependency-graph.md) → 确认包含 Mermaid 图
3. read_file(architecture/backend/priority-list.md) → 确认包含优先级表
4. 以上全部通过 → 更新 checkpoint.step = "global_completed"
5. 任一失败 → 保持 checkpoint.step = "global_pending"，要求 @global-architect 补充
```

### 6.3 断点恢复（三级降级）

```
恢复策略：

1. 读取 state.json，检查 architectBackendMode 字段
2. 根据 architectBackendMode 值选择恢复策略：

   --- Level 1 恢复（architectBackendMode = "agent-teams"）---
   a) 检查 architectBackendCheckpoint.step：
      - "global_pending" → @global-architect 未完成，需重新执行 Step 1
      - "global_completed" → 全局产物已落盘，进入 Step 1.5 领域划分确认
      - "domains_confirmed" → 领域划分已确认，直接进入 Step 2
      - "domains_pending" → 部分领域已完成
        → 创建新团队，仅包含 pendingDomains 中的领域成员
      - "domains_completed" → 所有产物已完成，直接进入总结确认
   b) 恢复时，检查 completedArtifacts 中每个文件是否仍存在
      → 若文件被删除，从 completedArtifacts/completedDomains 中移除，加回 pendingDomains

   --- Level 2 恢复（architectBackendMode = "task-pipeline"）---
   a) 读取 architectBackendPipeline.completedTasks 确定已完成的 Task
   b) 检查产物文件存在性进行交叉验证
   c) 从下一个未完成的 Task 继续执行

   --- Level 3 恢复（architectBackendMode = "fallback" 或 "task"）---
   a) 检查最终产物是否存在：
      - 所有产物已存在 → 直接进入总结确认
      - 部分产物缺失 → 读取可用产物，重新执行 Level 3 补全缺失部分

3. 若 architectBackendMode 字段不存在：
   a) 检查产物存在性推断执行进度
   b) 从头开始，尝试 Level 1
```

---

## 7. 编排器对接行为（三步模式）

本阶段遵循标准三步模式（预览 → 执行 → 总结确认）：

**Step 1: 预览** — 展示即将执行的后端架构设计计划：
- 调度模式（Level 1 Agent Teams / Level 2 Task 流水线 / Level 3 编排器直接执行）
- 如为断点恢复，说明从哪个步骤继续
- Agent Teams 模式下：团队名称、全局成员 + 领域成员列表、涉及领域数量
- Task 流水线模式下：Task 数量、各 Task 职责
- 两步执行策略说明
- 检查点机制说明

**Step 2: 执行** —
- **Level 1 (Agent Teams)**:
  1. 创建架构团队
  2. 分配 @global-architect 任务（S1）
  3. S1 完成 → 验证全局产物 → 更新检查点
  4. **Step 1.5 领域划分确认**：展示领域划分确认单（§3.3.2），等待用户确认/调整 → 确认后写入 domain-registry.json（§3.7）→ 更新检查点为 `domains_confirmed`
  5. 动态创建 @domain-architect-{service} 成员（S2-a, S2-b, ...）并行执行
  6. 每个领域成员完成 → 验证产物 → 更新检查点
  7. 全部完成 → 汇总结果 → 清理团队
  8. 超时 → 自动降级到 Level 2（§3.5A）
- **Level 2 (Task 流水线)**: 串行调用 Task-A → [领域划分确认] → Task-B~N，检查产物
- **Level 3 (编排器直接执行)**: 编排器自身读取输入并生成产物

**Step 3: 总结确认** — 展示架构设计结果：
- 实际使用的调度模式（含降级信息，如"Agent Teams → Task 流水线（@global-architect 超时降级）"）
- 全局产物清单（architecture.md、dependency-graph.md、priority-list.md）
- 领域注册表（domain-registry.json）及治理指标摘要
- 各领域技术需求文档清单
- 涉及领域数量和各领域改动概要
- 循环依赖检测结果
- 澄清问题（如有）
- 风险项汇总
- Level 3 兜底模式时，追加精度降低警告

---

## 8. 领域注册表持久化（§3.7 — 数据层治理）

### 8.1 设计意图

领域注册表（`domain-registry.json`）是领域治理三层体系的**数据层**，解决以下问题：

| 问题 | 解决方式 |
|------|---------|
| 领域划分决策不可追溯 | 完整记录领域清单、确认方式、治理指标 |
| 跨需求领域名称不一致 | 同名领域复用规则（§3.3.1）基于此表检查 |
| IMPLEMENT 阶段找不到通用项目领域开发 Agent | 编排器读取此表动态映射 Agent |
| 复盘时无法还原当时的领域边界 | 每个领域的模块列表、文件数、Agent 规范完整记录 |

### 8.2 存储路径

```
docs/workflows/{需求ID}/architecture/backend/domain-registry.json
```

### 8.3 Schema 定义

```json
{
  "registryVersion": "1.0",
  "createdAt": "ISO 8601 时间戳",
  "confirmedBy": "user | auto",
  "confirmedAt": "ISO 8601 时间戳（用户确认时间）",
  "projectType": "generic | java",
  "architectAgent": "backend-architect | java-architect",
  "domains": [
    {
      "id": "领域唯一标识（英文，如 common / user-service）",
      "name": "领域中文名（如 公共基础模块）",
      "modules": ["该领域包含的模块列表"],
      "estimatedFileCount": "预估文件数（整数）",
      "agentSpec": "使用的 Agent 规范文件名（如 backend-architect.md）",
      "executionPhase": "该领域 Agent 执行的阶段（如 阶段三）",
      "dependencies": ["该领域依赖的其他领域 ID 列表"],
      "governanceFlags": {
        "mergeCandidateReason": "合并候选原因（如模块数不足）| null",
        "splitCandidateReason": "拆分候选原因（如文件数过多）| null"
      }
    }
  ],
  "adjustmentHistory": [
    {
      "action": "merge | split | rename | delete | add",
      "timestamp": "ISO 8601 时间戳",
      "details": "具体操作描述（如：将 utils 合并到 common）",
      "before": "操作前领域列表快照（领域 ID 数组）",
      "after": "操作后领域列表快照（领域 ID 数组）"
    }
  ],
  "governanceMetrics": {
    "totalDomains": "领域总数（整数）",
    "totalModules": "模块总数（整数）",
    "totalEstimatedFiles": "预估总文件数（整数）",
    "avgModulesPerDomain": "平均每领域模块数（浮点数）",
    "avgFilesPerDomain": "平均每领域文件数（浮点数）",
    "minFilesPerDomain": "最小领域文件数（整数）",
    "maxFilesPerDomain": "最大领域文件数（整数）"
  }
}
```

### 8.4 写入时机与流程

```
domain-registry.json 写入流程（Step 1.5 确认后）：

1. 编排器根据 @global-architect 的全局分析结果构建初始领域列表
2. 执行治理规则校验（§3.3.1），标记异常项
3. 展示领域划分确认单，等待用户确认/调整
4. 若用户调整：
   a) 更新领域列表
   b) 将调整操作记录到 adjustmentHistory
   c) 重新计算 governanceMetrics
   d) 重新展示确认单
5. 用户确认后：
   a) 设置 confirmedBy = "user"，confirmedAt = 当前时间
   b) 写入 domain-registry.json 到 architecture/backend/ 目录
   c) 将文件路径追加到 checkpoint.completedArtifacts
   d) 更新 checkpoint.step = "domains_confirmed"
```

### 8.5 下游消费方

| 消费方 | 消费场景 | 读取字段 |
|--------|---------|---------|
| 编排器（ARCHITECT_BACKEND Step 2） | 创建领域架构师成员 | `domains[].id`, `domains[].modules` |
| 编排器（IMPLEMENT 阶段） | 动态映射领域开发 Agent | `domains[].id`, `domains[].agentSpec`, `architectAgent` |
| 编排器（同名领域复用检查） | 检查历史领域名称 | `domains[].id`, `domains[].name` |
| 用户（复盘） | 回顾领域划分决策 | 全部字段 |
