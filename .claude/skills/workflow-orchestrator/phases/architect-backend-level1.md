# ARCHITECT_BACKEND — Level 1: Parallel Agent 模式调度规则

> **加载时机**: 编排器判定使用 Level 1 (Parallel Agent) 模式时按需加载。
> **前置**: 编排器已加载 `architect-backend-rules.md`（主文件）。

---

## 1. 团队创建

编排器作为 **调度中心（团队领导）** 创建 Agent Team，使用**委派模式（Delegate Mode）**。

**创建指令模板**:

```
创建一个名为 arch-backend-{需求ID} 的后端架构设计团队，使用委派模式。

团队任务：基于后端技术需求文档进行架构设计，产出全局架构文档和各领域技术需求文档。
团队采用两步模式：Step 1 全局架构分析（串行），Step 2 领域文档并行输出。

成员列表：
{见 §2 成员生成规则}

任务依赖关系：
1. [S1] 全局架构分析 — @global-architect — 无依赖
2. [S2-a] {领域1}领域文档 — @domain-architect-{service1} — 依赖 S1
3. [S2-b] {领域2}领域文档 — @domain-architect-{service2} — 依赖 S1
   ... （按涉及领域动态生成）
```

---

## 2. 成员生成规则

### 成员 1: @global-architect（必选，始终创建）

```
调用 Agent 工具，Prompt 如下：

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

完成后，请将产物写入指定路径并返回完成状态，包含：
- 涉及的领域/模块清单
- 是否存在循环依赖
- 是否有澄清问题
- 各全局产物文件路径确认"
```

### 成员 2~N: @domain-architect-{module}（按涉及领域/模块动态生成）

```
调用 Agent 工具，Prompt 如下：

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

完成后，请将产物写入指定路径并返回完成状态，包含：
- 输出文件路径确认
- 涉及的模板加载清单
- 文件级改动清单摘要
- 是否存在风险项"
```

> **关键**: 所有 Prompt 中的路径必须为**绝对路径**（通过 `scripts/resolve_agent_paths.py` 解析）。

---

## 3. 涉及领域/模块的动态识别

```
识别流程：
1. 读取 analysis/tech-requirements-backend.md
2. 定位「## 1. 改动范围」章节，提取涉及的后端模块列表
3. 统一使用动态识别策略（不区分架构师类型）：
   - 直接使用 tech-requirements-backend.md 中声明的模块列表
   - 根据模块划分原则将模块分组：
     * 公共基础模块（database/middleware/utils 等）→ 合并为 common 领域
     * 独立业务模块 → 各自作为独立领域
   - 为每个领域创建对应的 @domain-architect-{module} 成员
   - 如已有 domain-registry.json（历史需求产出），检查同名领域复用
4. 执行领域数量治理规则校验（§3.1）
5. 确认领域/模块数量，选择调度模式
```

### 3.1 领域数量治理规则（CRITICAL — 防膨胀防线）

| 约束 | 阈值 | 触发行为 |
|------|------|---------|
| 单需求领域上限 | **8** | 超过 8 个领域时 → 编排器**强制阻断**，要求全局架构师重新评估并合并，直到 ≤8 |
| 单领域最少模块数 | **2** | 低于 2 个模块的领域 → 标记为 ⚠️ 合并候选 |
| 公共模块合并规则 | — | database / middleware / utils / config / constants → 强制合并为 `common` 领域 |
| 同名领域复用规则 | — | `domain-registry.json` 中已存在同名领域 → 必须复用，禁止新建 |
| 单领域最大文件数 | **30** | 超过 30 个文件 → 标记为 ⚠️ 拆分候选 |

### 3.2 领域划分确认关卡（Step 1.5 — 人工确认点）

**确认时机**: Step 1 全局架构产物落盘 → **Step 1.5 领域划分确认** → Step 2 领域文档并行输出

```
Step 1.5 领域划分确认（CRITICAL — 不可跳过）：

1. 编排器从 @global-architect 的完成汇报和 architecture.md 中提取：
   - 领域列表（名称 + 中文描述）
   - 每个领域包含的模块
   - 每个领域的预期文件数
   - 领域间的依赖关系

2. 执行治理规则校验（§3.1），标记异常项

3. 向用户展示【领域划分确认单】（格式见 output-formats/architect-backend-formats.md §16.5）

4. 等待用户选择：
   a) 「确认」→ 按当前领域划分继续进入 Step 2
   b) 「调整」→ 用户指定合并/拆分/重命名操作，编排器更新领域列表后重新展示
   c) 「重做全局分析」→ 回到 Step 1 重新执行（罕见场景）

5. 用户确认后：
   - 将确认后的领域列表写入 domain-registry.json（§6）
   - 更新 state.json 的 architectBackendCheckpoint.step 为 "domains_confirmed"
   - 继续执行 Step 2
```

**用户调整操作**: 合并领域 / 拆分领域 / 重命名领域 / 删除领域 / 新增领域

---

## 4. 领导（编排器）行为约束

| ✅ 必须做 | ❌ 禁止做 |
|-----------|----------|
| 发起 Agent 调度并分配任务 | 直接执行架构分析/文档输出 |
| 每个成员完成后立即更新检查点 | 跳过检查点更新 |
| 检测失败并执行自动降级（§5） | 失败时直接降级 |
| 处理澄清问题 | 向领域成员传递其他领域成员的对话 |

---

## 5. 失败检测与自动降级（Level 1 → Level 2）

Agent 工具为同步调用，无需超时计时器。降级触发条件：

1. **Agent 调用返回错误**：子 Agent 执行失败或返回空结果
2. **产物验证失败**：Agent 返回成功但产物文件不存在或内容为空

| 场景 | 处理 |
|------|------|
| @global-architect 失败且无全局产物 | 降级到 Level 2 |
| 领域 Agent 失败但前序产物已存在 | 从该领域 Task 开始 Level 2 |
| 领域 Agent 失败且无领域产物 | 降级到 Level 2 |

**降级执行**: 记录原因 → 更新 `architectBackendMode = "task-pipeline"` → 跳转到 Level 2 子文件

---

## 6. 领域注册表持久化（domain-registry.json）

### 6.1 存储路径

```
docs/workflows/{需求ID}/architecture/backend/domain-registry.json
```

### 6.2 Schema 定义

```json
{
  "registryVersion": "1.0",
  "createdAt": "ISO 8601",
  "confirmedBy": "user | auto",
  "confirmedAt": "ISO 8601",
  "projectType": "generic | java",
  "architectAgent": "backend-architect | java-architect",
  "domains": [
    {
      "id": "领域 ID（英文）",
      "name": "领域中文名",
      "modules": ["模块列表"],
      "estimatedFileCount": 0,
      "agentSpec": "backend-architect.md",
      "executionPhase": "阶段三",
      "dependencies": ["依赖的领域 ID"],
      "governanceFlags": {
        "mergeCandidateReason": "null | 原因",
        "splitCandidateReason": "null | 原因"
      }
    }
  ],
  "adjustmentHistory": [],
  "governanceMetrics": {
    "totalDomains": 0,
    "totalModules": 0,
    "totalEstimatedFiles": 0,
    "avgModulesPerDomain": 0,
    "avgFilesPerDomain": 0,
    "minFilesPerDomain": 0,
    "maxFilesPerDomain": 0
  }
}
```

### 6.3 写入流程

```
domain-registry.json 写入流程（Step 1.5 确认后）：

1. 编排器根据 @global-architect 的全局分析结果构建初始领域列表
2. 执行治理规则校验（§3.1），标记异常项
3. 展示领域划分确认单，等待用户确认/调整
4. 若用户调整 → 更新领域列表 + 记录 adjustmentHistory + 重算 metrics → 重新展示
5. 用户确认后 → 写入文件 + 追加到 checkpoint.completedArtifacts + 更新 checkpoint.step
```

### 6.4 下游消费方

| 消费方 | 消费场景 | 读取字段 |
|--------|---------|---------|
| 编排器（Step 2） | 创建领域架构师成员 | `domains[].id`, `domains[].modules` |
| 编排器（IMPLEMENT） | 动态映射领域开发 Agent | `domains[].id`, `domains[].agentSpec` |
| 编排器（复用检查） | 检查历史领域名称 | `domains[].id`, `domains[].name` |

---

## 7. 团队完成与清理

```
1. 确认 @global-architect 的完成消息和全局产物
2. 逐一确认每个 @domain-architect-{service} 的完成消息和领域产物
3. 执行产物完整性检查：
   - architecture/backend/architecture.md 存在
   - architecture/backend/dependency-graph.md 存在
   - architecture/backend/priority-list.md 存在
   - architecture/backend/domain-registry.json 存在
   - 每个涉及领域的 architecture/backend/{service}/tech-requirements.md 存在
4. 执行质量检查：
   - 接口签名引用总纲 API-xxx
   - 复用评级继承自 tech-requirements-backend.md
   - domain-registry.json 领域列表与实际产出目录一致
5. 汇总风险项
6. 更新 state.json（architectBackendMode = "agent-teams"，checkpoint = "domains_completed"）
7.  → 进入"总结确认"步骤
```
