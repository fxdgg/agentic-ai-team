# Agent Catalog — CodeBuddy 原生 Agent 注册表
# ====================================
#
# Agent Catalog 是 AI Team 的 Agent 参考定义库。
# 以 YAML 文件定义每个 Agent 的角色、能力标签、适用阶段、Prompt 模板等信息。
# 这些定义作为 workflow-orchestrator Skill 的参考资料，供编排器按需实例化 Agent。

## 定位

在 CodeBuddy IDE 原生架构中，Agent Catalog 是 **参考资料（references）**——
workflow-orchestrator 读取这些定义来了解每个 Agent 的能力和使用方式，
然后通过 Task 工具或 Agent Teams 成员方式来实际调度。

> ⚠️ 注意：实际的 Agent 执行定义（Prompt 模板、行为约束等）
> 位于 `.codebuddy/skills/workflow-orchestrator/agents/` 目录下的 Markdown 文件中。
> 本目录的 YAML 文件作为结构化元数据参考。

## 目录结构

```
agent-catalog/
├── README.md                          # 本文件 - Agent Catalog 说明
├── analysis/                          # 分析类 Agent
│   └── product-analyst.yaml           # 产品需求分析 Agent
├── architecture/                      # 架构类 Agent
│   ├── backend-architect.yaml         # 后端架构 Agent
│   └── frontend-architect.yaml        # 前端架构 Agent
├── implementation/                    # 实现类 Agent
│   └── domain-developer.yaml          # 领域开发 Agent（参数化模板）
├── verification/                      # 验证类 Agent
│   ├── build-verifier.yaml            # 编译验证 Agent
│   └── test-engineer.yaml             # 测试工程 Agent
└── operations/                        # 运维类 Agent
    ├── archiver.yaml                  # 归档 Agent
    └── tapd-sync.yaml                 # TAPD 需求同步 Agent
```

## 与 Agent Markdown 定义的关系

| YAML 元数据（本目录） | Markdown 执行定义（agents/） |
|---|---|
| 结构化的能力标签、阶段绑定 | 详细的 Prompt、行为约束、输出格式 |
| 适用于自动化调度匹配 | 适用于 Task 工具 / Agent Teams 注入 |
| 通用参数化模板 | 具体角色的完整指令 |

## Agent YAML 规范

每个 Agent 定义文件包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Agent 唯一名称 |
| `version` | string | ✅ | 语义版本号 |
| `role` | string | ✅ | 角色标识，与工作流模板中的 `agent_role` 对应 |
| `description` | string | ✅ | Agent 职责描述 |
| `capability_tags` | list | ✅ | 能力标签，用于调度匹配 |
| `phase_bindings` | list | ✅ | 适用的工作流阶段 ID |
| `prompt_template` | string | ✅ | Agent 执行时使用的 Prompt 模板 |
| `parameters` | object | ❌ | 可配置参数（支持模板实例化） |
| `input_artifacts` | list | ❌ | 期望的输入产物列表 |
| `output_artifacts` | list | ✅ | 必须产出的产物列表 |
| `evaluation` | object | ❌ | 评估标准 |
| `constraints` | object | ❌ | 执行约束（token limit, timeout 等）|

## 使用方式

### 在 workflow-orchestrator 中引用

workflow-orchestrator 的 SKILL.md 中的子 Agent 注册表会引用这些定义。
实际调度时，orchestrator 会：

1. 根据当前阶段查找 `phase_bindings` 匹配的 Agent
2. 根据 `capability_tags` 进行能力匹配
3. 使用 `agents/` 目录下对应的 Markdown 文件作为 Agent 的完整 Prompt
4. 通过 **Task 工具** 或 **Agent Teams 成员** 方式调度执行

### 新增 Agent

1. 在对应类别目录下创建 YAML 文件
2. 按照上述规范填写所有必填字段
3. 在 `.codebuddy/skills/workflow-orchestrator/agents/` 下创建对应的 Markdown 执行定义
4. 在 SKILL.md 的子 Agent 注册表中注册

## 评估标准

每个 Agent 的交付质量通过以下维度评估：

- **首次通过率 (First Pass Rate)**：无需返工的比例
- **平均执行时间**：从调度到完成的平均耗时
- **Token 效率**：每 token 的有效输出比
- **返工率 (Rework Rate)**：需要回退修复的比例
- **Owner 满意度**：人工审批时的评分
