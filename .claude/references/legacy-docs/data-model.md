# AI Team — 数据模型文档

> 版本：v0.1 | 更新日期：2026-03-24

---

## 一、ER 关系概览

```
Project ──1:N── Requirement ──1:1── WorkflowRun ──1:N── PhaseRun ──1:N── AgentRun
   │                                    │                                    │
   └──1:N── CapabilityDomain            ├──1:N── Risk                       ├──1:N── Artifact
                 │                      ├──1:N── Blocker                    └──1:N── BudgetUsage
                 ├── owner → TeamMember ├──1:N── Decision ──1:N── Approval
                 └──1:N── AgentDef      └──1:N── RollbackLog
                              │
                              └──1:N── EvalResult

Rule ──1:N── EvolveRecord ── reviewer → TeamMember
```

## 二、核心实体定义

### 2.1 projects（项目）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| name | VARCHAR(255) NOT NULL | 项目名称 |
| description | TEXT | 项目描述 |
| repo_url | VARCHAR(512) | Git 仓库地址 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

### 2.2 team_members（团队成员）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| name | VARCHAR(255) NOT NULL | 姓名 |
| email | VARCHAR(255) UNIQUE NOT NULL | 邮箱（唯一） |
| role | VARCHAR(100) NOT NULL | 角色（tech_lead / developer / qa 等） |
| avatar_url | VARCHAR(512) | 头像 URL |
| is_active | BOOLEAN DEFAULT true | 是否在职 |
| created_at | TIMESTAMPTZ | 创建时间 |

### 2.3 capability_domains（能力域）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| project_id | INT FK→projects | 所属项目 |
| name | VARCHAR(255) NOT NULL | 能力域名称（如 frontend-platform） |
| description | TEXT | 描述 |
| owner_id | INT FK→team_members | 负责人 |
| created_at | TIMESTAMPTZ | 创建时间 |

### 2.4 requirements（需求）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| project_id | INT FK→projects | 所属项目 |
| name | VARCHAR(500) NOT NULL | 需求名称 |
| description | TEXT | 需求描述 |
| priority | VARCHAR(20) DEFAULT 'medium' | 优先级：critical/high/medium/low |
| sla_deadline | TIMESTAMPTZ | SLA 截止时间 |
| status | ENUM(RequirementStatus) | draft/ready/in_progress/blocked/completed/cancelled |
| prd_source | TEXT | PRD 来源内容 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

**索引**：project_id, status

### 2.5 workflow_runs（工作流运行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| requirement_id | INT FK→requirements UNIQUE | 一对一关联需求 |
| workflow_template | VARCHAR(255) NOT NULL | 使用的工作流模板名称 |
| current_phase | VARCHAR(100) | 当前阶段 ID |
| status | ENUM(WorkflowStatus) | pending/running/paused/blocked/completed/failed/cancelled |
| phase_history | JSONB | 阶段执行历史（兼容 vibe-coding 的 state.json 结构） |
| platforms | JSONB | 涉及的平台及各平台进度 |
| config_overrides | JSONB | 工作流配置覆盖项 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

**JSONB 字段 Schema**：

`phase_history` 示例：
```json
[
  {"phase": "ANALYSE_PRODUCT", "status": "completed", "startedAt": "...", "completedAt": "..."},
  {"phase": "ANALYSE_TECH", "status": "in_progress", "startedAt": "..."}
]
```

`platforms` 示例（来自 vibe-coding state-schema.json）：
```json
{
  "backend": {"enabled": true, "status": "completed"},
  "web": {"enabled": true, "status": "in_progress"},
  "miniprogram": {"enabled": false, "status": "skipped"}
}
```

### 2.6 phase_runs（阶段运行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| workflow_run_id | INT FK→workflow_runs | 所属工作流 |
| phase_id | VARCHAR(100) NOT NULL | 阶段 ID（如 ANALYSE_PRODUCT） |
| phase_name | VARCHAR(255) NOT NULL | 阶段显示名称 |
| status | ENUM(PhaseStatus) | pending/previewing/executing/summarizing/completed/failed/skipped/rolled_back |
| step | ENUM(PhaseStep) | 当前三步模式步骤：preview/execute/summary |
| quality_gate | ENUM(QualityGate) | 门禁结果：pass/warn/fail |
| gate_details | JSONB | 门禁详情 |
| attempt_number | INT DEFAULT 1 | 执行次数（回退后累加） |
| started_at | TIMESTAMPTZ | 开始时间 |
| completed_at | TIMESTAMPTZ | 完成时间 |
| created_at | TIMESTAMPTZ | 创建时间 |

### 2.7 agent_definitions（Agent 定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| name | VARCHAR(255) UNIQUE NOT NULL | Agent 名称 |
| role | VARCHAR(100) NOT NULL | 角色（如 product-analyst） |
| description | TEXT | 描述 |
| capability_tags | JSONB | 能力标签数组 |
| phase_bindings | JSONB | 绑定的阶段 ID 数组 |
| prompt_template | TEXT | Prompt 模板 |
| config | JSONB | 配置项 |
| version | VARCHAR(20) DEFAULT '1.0' | 版本号 |
| is_active | BOOLEAN DEFAULT true | 是否启用 |
| capability_domain_id | INT FK→capability_domains | 所属能力域 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

### 2.8 agent_runs（Agent 运行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增主键 |
| phase_run_id | INT FK→phase_runs | 所属阶段运行 |
| agent_definition_id | INT FK→agent_definitions | 使用的 Agent 定义 |
| status | ENUM(AgentRunStatus) | queued/running/completed/failed/cancelled/escalated |
| input_context | JSONB | 输入上下文 |
| output_summary | TEXT | 输出摘要 |
| token_input | INT DEFAULT 0 | 输入 token 数 |
| token_output | INT DEFAULT 0 | 输出 token 数 |
| error_message | TEXT | 错误信息 |
| started_at | TIMESTAMPTZ | 开始时间 |
| completed_at | TIMESTAMPTZ | 完成时间 |
| created_at | TIMESTAMPTZ | 创建时间 |

### 2.9 其他实体

- **artifacts**：Agent 产物，关联 agent_run_id
- **decisions**：决策记录，关联 workflow_run_id
- **approvals**：审批记录，关联 decision_id + reviewer_id
- **risks**：风险记录，关联 workflow_run_id
- **blockers**：阻塞项，关联 workflow_run_id
- **rollback_logs**：回退日志，关联 workflow_run_id
- **eval_results**：Agent 评估结果，关联 agent_definition_id
- **rules**：规则定义
- **evolve_records**：进化改进记录，关联 rule_id
- **budget_usages**：预算使用记录，关联 agent_run_id

## 三、索引策略

| 表 | 索引 | 类型 | 说明 |
|---|------|------|------|
| requirements | project_id | B-tree | 按项目查询需求 |
| requirements | status | B-tree | 按状态筛选 |
| workflow_runs | status | B-tree | Dashboard 统计 |
| phase_runs | workflow_run_id | B-tree | 查询工作流的阶段 |
| agent_runs | phase_run_id | B-tree | 查询阶段的 Agent 运行 |
| agent_runs | status | B-tree | 活跃 Agent 统计 |
| evolve_records | status | B-tree | 待审阅记录查询 |
