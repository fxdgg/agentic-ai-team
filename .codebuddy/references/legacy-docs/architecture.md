# AI Team — 架构设计文档

> 版本：v0.1 | 更新日期：2026-03-24

---

## 一、系统分层架构

AI Team 采用四层架构设计，每层职责明确、接口清晰：

```
┌──────────────────────────────────────────────────────────────────┐
│              可视化平面 — Dashboard (React 18)                     │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐        │
│  │ 交付总览  │ Agent看板 │ 决策中心  │ 人机映射  │ 质量中心  │        │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘        │
├──────────────────────────────────────────────────────────────────┤
│              API 网关层 — FastAPI + WebSocket                      │
│  REST API (CRUD + 业务操作) │ WebSocket (实时事件推送)              │
├──────────────────────────────────────────────────────────────────┤
│  控制平面          │  执行平面           │  知识平面 + 治理平面      │
│  ┌────────────┐    │  ┌──────────────┐  │  ┌──────────────────┐  │
│  │ 工作流引擎  │    │  │ 任务队列      │  │  │ 规则管理         │  │
│  │ Agent 调度  │    │  │ (Celery)      │  │  │ 产物管理         │  │
│  │ 策略引擎   │    │  │ Agent 执行器  │  │  │ 进化引擎         │  │
│  │ 人工升级器  │    │  │ 执行追踪器   │  │  │ 评估/审计/预算   │  │
│  └────────────┘    │  └──────────────┘  │  └──────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│              数据层 — PostgreSQL + Redis + File Storage            │
└──────────────────────────────────────────────────────────────────┘
```

## 二、控制平面

### 2.1 工作流引擎

**职责**：解析 YAML 工作流模板，驱动状态机推进，执行三步模式生命周期。

**关键设计**：
- 从 vibe-coding 的硬编码 15 阶段状态机升级为 YAML 配置驱动
- 保留三步模式（预览-执行-总结确认）作为通用协议
- 保留澄清循环和质量门禁机制
- 工作流状态变更采用乐观锁防止并发冲突

**核心接口**：
```python
class WorkflowEngine:
    async def load_template(self, template_path: str) -> WorkflowTemplate
    async def start_workflow(self, requirement_id: int, template: str) -> WorkflowRun
    async def advance_phase(self, workflow_id: int, confirmation: bool) -> PhaseRun
    async def rollback_phase(self, workflow_id: int, reason: str) -> RollbackLog
    async def validate_transition(self, current: str, target: str) -> bool
    async def preview_phase(self, workflow_id: int) -> dict
    async def execute_phase(self, workflow_id: int) -> AgentRun
    async def summarize_phase(self, workflow_id: int) -> dict
```

### 2.2 Agent 调度器

**职责**：根据阶段配置和调度策略，选择并分派 Agent 执行任务。

**调度策略**：
1. **角色匹配**：按阶段配置的 `agent_role` 匹配 Agent 注册表
2. **能力标签匹配**：按 `capability_tags` 精确匹配可用 Agent
3. **并行调度**：同一阶段配置 `parallel_agents` 时并行调度多个 Agent
4. **动态分派**：`dynamic_dispatch` 模式下按能力域自动分配
5. **预算检查**：调度前检查 token 预算余量

### 2.3 人工升级器

**职责**：当 Agent 遇到阻塞时，自动升级到对应的 Capability Owner。

**升级链路**：
```
Agent 阻塞 → 查找所属能力域 → 通知 Owner → 超时 → 升级到技术负责人
```

## 三、执行平面

### 3.1 任务队列

- 使用 Celery + Redis 实现异步任务队列
- Agent 执行任务不阻塞 API 响应
- 支持任务优先级、超时控制、重试策略

### 3.2 Agent 运行时

- 加载 Agent 定义（Prompt 模板 + 配置）
- 注入执行上下文（前序产物 + 编译修复信息等）
- 调用 LLM 执行任务
- 收集产物、记录 token 消耗

### 3.3 执行追踪器

- 每次 Agent 执行记录完整的输入/输出
- 追踪 token 使用量和执行时长
- 失败时记录错误信息用于诊断

## 四、知识平面

### 4.1 规则管理

- 编码规范、架构规则、审批规则的版本化管理
- 规则与 Agent 绑定，Agent 执行时自动加载适用规则

### 4.2 进化闭环

从 vibe-coding 的 `/evolve` 机制升级：
```
Bug 修复 → 回溯根因到 Agent → 生成改进建议 (pending)
                                    ↓
                        Owner 审阅 → applied / rejected / deferred
                                    ↓
                        applied → 更新 Agent 定义 + 规则
```

### 4.3 产物管理

- 所有 Agent 产物带版本号
- 支持 diff 和回溯
- 产物与 AgentRun 关联，可追溯来源

## 五、治理平面

### 5.1 评估体系

- Agent 可信度评分：基于首次通过率、回退率、返工率多维评估
- 定期评估并更新分数

### 5.2 审计日志

- 所有决策留痕（Decision 表记录 who/when/what/why）
- Agent 执行结果不可变（append-only）
- 回退操作需二次确认

### 5.3 预算管理

- Token 使用量按 Agent、阶段、工作流三级统计
- 成本计算精确到 USD
- 超预算自动告警

## 六、API 设计规范

### 6.1 RESTful 约定

| 方法 | 路径模式 | 说明 |
|------|---------|------|
| GET | /api/v1/{resource} | 列表查询 |
| GET | /api/v1/{resource}/{id} | 单个查询 |
| POST | /api/v1/{resource} | 创建 |
| PATCH | /api/v1/{resource}/{id} | 部分更新 |
| DELETE | /api/v1/{resource}/{id} | 删除 |
| POST | /api/v1/{resource}/{id}/{action} | 操作 |

### 6.2 WebSocket 事件

| 事件类型 | 触发时机 | 推送数据 |
|---------|---------|---------|
| workflow_updated | 工作流状态变更 | workflow_id, status, current_phase |
| phase_changed | 阶段推进/回退 | workflow_id, phase_id, step |
| agent_completed | Agent 执行完成 | agent_run_id, status, duration |
| decision_required | 需要人工决策 | decision_id, title, urgency |
| risk_identified | 发现新风险 | risk_id, severity, title |

## 七、部署架构

### 7.1 本地开发

```
Docker Compose:
  postgres:16  (port 5432)
  redis:7      (port 6379)
  backend      (port 8000)  — FastAPI + uvicorn
  celery-worker             — Celery worker × 4
  frontend     (port 5173)  — Vite dev server
```

### 7.2 生产环境（Phase 2）

- 后端：Kubernetes Deployment + HPA
- 数据库：托管 PostgreSQL
- 缓存：托管 Redis
- 前端：CDN + 静态托管
- 监控：Prometheus + Grafana
