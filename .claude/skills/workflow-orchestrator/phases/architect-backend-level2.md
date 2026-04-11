# ARCHITECT_BACKEND — Level 2: Task 串行流水线

> **加载时机**: 编排器判定使用 Level 2 (Task 流水线) 模式时按需加载，或从 Level 1 降级时加载。
> **前置**: 编排器已加载 `architect-backend-rules.md`（主文件）。

---

## 1. 核心设计原则

| 原则 | 说明 |
|------|------|
| **规范文件引用，非注入** | Task Prompt 中只给出 Agent 规范文件的**绝对路径**，由 Task Agent 自行 `Read` 加载，避免 Prompt 膨胀 |
| **中间产物传递** | 与 Level 1 完全相同的中间产物文件（全局架构产物），保证数据格式一致 |
| **断点恢复** | 每个 Task 完成后中间产物已落盘，降级或中断后可从已完成的 Task 之后继续 |
| **角色合并** | 涉及领域/模块仅 1 个时，全局分析 + 领域文档输出合并为单次 Task 调用 |

---

## 2. 流水线定义

### 单领域/模块（1 个 Task — 合并模式）

```
[Task-A] 全局架构分析 + 领域文档输出（合并模式）
  输入：state.json + tech-requirements.md + tech-requirements-backend.md + 存量代码
  产出：architecture/backend/architecture.md
        architecture/backend/dependency-graph.md
        architecture/backend/priority-list.md
        architecture/backend/{module}/tech-requirements.md
```

### 多领域/模块（2-3 个 Task — 从 Level 1 降级）

```
[Task-A] 全局架构分析
  产出：architecture.md + dependency-graph.md + priority-list.md
  ↓ 全局产物落盘（检查点 1）

[Task-B ~ Task-N] 各领域文档输出（每个领域一个 Task，串行）
  产出：architecture/backend/{module}/tech-requirements.md
  ↓ 每个领域产物落盘（检查点 N）
```

---

## 3. Task Prompt 模板

### Task-A: 全局架构分析

```
你是一位资深后台架构师。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read）：{agents/{selected-architect}.md 的绝对路径}
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
- 你必须先 Read 读取 Agent 规范文件，再按规范执行
- 你只负责全局架构分析，不输出领域/模块技术需求文档
- 完成后返回产物路径和关键摘要
```

### Task-B~N: 领域文档输出（每个领域一个 Task）

```
你是一位资深后台架构师，负责 {领域/模块名} 的技术需求文档输出。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read）：{agents/{selected-architect}.md 的绝对路径}
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
- 你必须先 Read 读取 Agent 规范文件，再按规范执行
- 你只负责 {领域/模块名} 一个领域/模块的文档输出
- 不要修改全局架构产物
- 完成后返回产物路径和关键摘要
```

### 合并模式 Task（单领域/模块）

```
你是一位资深后台架构师。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read）：{agents/{selected-architect}.md 的绝对路径}
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
- 你必须先 Read 读取 Agent 规范文件，再按规范执行
- 完成后返回产物路径和关键摘要
```

---

## 4. 执行流程

```
编排器执行流程：

1. 确定起始 Task（检查已存在的中间产物）：
   a) architecture.md 不存在 → 从 Task-A 开始
   b) architecture.md 存在但部分领域 tech-requirements.md 不存在 → 从对应领域 Task 开始
   c) 所有产物已存在 → 直接进入总结确认

2. 执行 Task-A（如需）：
   a) 使用 Task 工具，注入 §3 Task-A Prompt
   b) Task 返回后，检查全局产物是否成功写入
   c) 如果写入失败 → 降级到 Level 3
   d) 更新检查点 checkpoint.step = "global_completed"

3. 领域划分确认（Step 1.5，如适用）：
   a) 从 architecture.md 提取涉及领域列表
   b) 展示领域划分确认单，等待用户确认/调整
   c) 确认后写入 domain-registry.json → 更新检查点为 "domains_confirmed"

4. 串行执行领域 Task（Task-B ~ Task-N）：
   a) 对每个领域，使用 Task 工具注入 §3 领域 Task Prompt
   b) 每个 Task 返回后，检查领域产物是否成功写入
   c) 如果写入失败 → 降级到 Level 3（已完成的领域产物保留）
   d) 每个领域完成后更新检查点

5. 所有 Task 完成后：
   a) 执行产物完整性检查
   b) 更新 state.json: architectBackendMode = "task-pipeline"
   c) 进入"总结确认"步骤
```

---

## 5. 失败处理

| 失败场景 | 处理方式 |
|---------|---------|
| Task-A 返回空结果 / 无全局产物 | 降级到 Level 3 |
| 领域 Task 返回空结果 / 无领域产物 | 降级到 Level 3（已有产物可供参考） |
| Task 出错但有部分产物 | 产物完整视为成功；不完整则降级 |

> **注意**: Level 2 模式下 `architectBackendMode` 设为 `"task-pipeline"`，**仍使用检查点机制**。
