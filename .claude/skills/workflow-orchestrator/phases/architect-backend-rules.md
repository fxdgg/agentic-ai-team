# ARCHITECT_BACKEND 阶段调度规则（按需加载）

> **加载时机**: 编排器进入 ARCHITECT_BACKEND 阶段时加载本文件。
> **设计意图**: 本文件仅包含编排器在进入阶段时**立刻需要**的决策逻辑（~280行）。三级降级路径的详细规则（Prompt 模板、治理规则、Schema 等）拆分到子文件中，编排器根据实际走的路径**按需加载**对应子文件，避免上下文膨胀。

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

### 0.2 三级降级调度策略

| 级别 | 模式 | 触发条件 | 子文件 |
|------|------|---------|--------|
| **Level 1** | Parallel Agent | 涉及领域/模块 ≥2 个，始终优先尝试 | `phases/architect-backend-level1.md` |
| **Level 2** | Task 串行流水线 | 领域/模块仅 1 个，或 Level 1 创建失败/超时 | `phases/architect-backend-level2.md` |
| **Level 3** | 编排器直接执行 | Level 2 执行失败 | `phases/architect-backend-level3.md` |

### 0.3 降级决策流程

```
编排器执行流程：

1. 读取 state.json，检查是否有断点恢复信息
2. 如果 architectBackendMode 已有值且非空：
   a) "agent-teams" → Read("phases/architect-backend-level1.md")，进入 Level 1 断点恢复
   b) "task-pipeline" → Read("phases/architect-backend-level2.md")，进入 Level 2 断点恢复
   c) "fallback" 或 "task" → Read("phases/architect-backend-level3.md")，进入 Level 3 恢复
3. 如果 architectBackendMode 为空或字段不存在：
   → 尝试 Level 1:
     a) Read("phases/architect-backend-level1.md")
     b) 按 Level 1 规则执行
     c) 失败或超时 → Read("phases/architect-backend-level2.md")，降级到 Level 2
     d) Level 2 也失败 → Read("phases/architect-backend-level3.md")，降级到 Level 3
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
| `@global-architect` | `agents/{selected-architect}.md` | 全局架构分析 | **搜索密集**，峰值 ~100KB，输出 3 个全局产物 |
| `@domain-architect-{module}` | 同上 | 单领域/模块文档输出 | **零搜索**，~40KB，仅加载模板 + 本模块输入 |

### 1.2 中间产物与检查点

| 产物 | 写入方 | 读取方 | 落盘时机 |
|------|--------|--------|---------|
| `architecture/backend/architecture.md` | @global-architect | 所有 @domain-architect-* | 检查点 1 |
| `architecture/backend/dependency-graph.md` | @global-architect | 所有 @domain-architect-* | 检查点 1 |
| `architecture/backend/priority-list.md` | @global-architect | 所有 @domain-architect-* | 检查点 1 |
| `architecture/backend/backend-clarify.json` | @global-architect | 编排器 | 检查点 1（可选） |
| `architecture/backend/domain-registry.json` | 编排器 | IMPLEMENT 阶段 | Step 1.5 确认后 |
| `architecture/backend/{service}/tech-requirements.md` | @domain-architect-{service} | 下游开发 Agent | 检查点 N |

> **检查点 1 是"上下文防火墙"**: @global-architect 的搜索上下文（~100KB）被压缩为 3 个结构化文档（~20KB），领域成员的上下文因此保持干净。

---

## 2. 检查点机制（CRITICAL — 产物落盘保护）

### 2.1 检查点更新规则

| 时刻 | step 值 | 说明 |
|------|---------|------|
| 阶段开始时 | `global_pending` | 初始化 |
| @global-architect 完成后 | `global_completed` | 全局产物已安全落盘 |
| 用户确认领域划分后 | `domains_confirmed` | domain-registry.json 已落盘 |
| 领域成员陆续完成时 | `domains_pending` | 每完成一个即更新 |
| 所有领域成员完成后 | `domains_completed` | 阶段完成 |

### 2.2 检查点更新流程

```
每个产物落盘后：
  1. 编排器 Read 确认产物文件存在且非空
  2. 更新 architectBackendCheckpoint（追加 completedArtifacts，移动 pendingDomains→completedDomains）
  3. 写入 state.json
```

### 2.3 断点恢复策略

```
恢复策略：
1. 读取 state.json，检查 architectBackendMode 和 architectBackendCheckpoint.step
2. 根据 step 值确定恢复点：
   - "global_pending" → 重新执行 Step 1
   - "global_completed" → 进入 Step 1.5 领域划分确认
   - "domains_confirmed" → 直接进入 Step 2
   - "domains_pending" → 仅创建 pendingDomains 中未完成的领域成员
   - "domains_completed" → 直接进入总结确认
3. 恢复时，检查 completedArtifacts 中每个文件是否仍存在
   → 若文件被删除，从 completedArtifacts/completedDomains 中移除，加回 pendingDomains
```

---

## 3. 异常处理概要

| 场景 | 处理方式 |
|------|---------|
| @global-architect 失败 | 发送修复指令，或创建替代成员 |
| @domain-architect-{service} 失败 | 全局产物已存在，可创建新成员重试 |
| 成员长时间无响应 | Level 1 子文件 §5 的超时检测流程 |
| 部分领域失败但其他已完成 | 检查点保护，仅重试失败的领域 |
| 全局产物落盘验证失败 | 保持 `global_pending`，要求补充 |

### 全局产物落盘验证

```
验证流程：
1. Read(architecture.md) → 确认非空
2. Read(dependency-graph.md) → 确认包含 Mermaid 图
3. Read(priority-list.md) → 确认包含优先级表
4. 全部通过 → 更新 checkpoint.step = "global_completed"
5. 任一失败 → 保持 "global_pending"，要求补充
```

---

## 4. 编排器对接行为（三步模式）

**Step 1: 预览** — 展示即将执行的后端架构设计计划：
- 调度模式（Level 1/2/3）
- 如为断点恢复，说明从哪个步骤继续
- 涉及领域数量、团队/Task 列表
- 检查点机制说明

**Step 2: 执行** —
- **Level 1**: 创建团队 → S1 全局分析 → 检查点 → Step 1.5 领域确认 → S2 并行领域文档 → 逐个检查点 → 清理
- **Level 2**: Task-A 全局分析 → [领域确认] → Task-B~N 串行领域文档 → 检查产物
- **Level 3**: 编排器自身读取输入并生成产物

**Step 3: 总结确认** — 展示架构设计结果：
- 实际调度模式（含降级信息）
- 全局产物清单 + 领域注册表 + 各领域文档清单
- 循环依赖检测结果、澄清问题、风险项汇总
- Level 3 时追加精度降低警告

---

## 5. 子文件索引

| 子文件 | 行数 | 加载条件 | 包含内容 |
|--------|------|---------|---------|
| `phases/architect-backend-level1.md` | ~340 | 走 Level 1 路径时 | Parallel Agent 完整规则：Prompt 模板、领域治理、确认关卡、超时降级、domain-registry Schema |
| `phases/architect-backend-level2.md` | ~180 | 走 Level 2 路径时 | Task 流水线定义 + Prompt 模板 + 执行流程 + 失败处理 |
| `phases/architect-backend-level3.md` | ~45 | 走 Level 3 路径时 | 编排器直接执行策略 + 限制说明 |
| `references/architect-backend-state-examples.json` | — | 仅调试参考 | state.json 各阶段状态示例（不加载到上下文） |
