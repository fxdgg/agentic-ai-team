# AI Team — 人机映射设计文档

> 版本：v0.1 | 更新日期：2026-03-24

---

## 一、Capability Owner 模型

### 1.1 核心概念

从 vibe-coding 的"8 人分工表"升级为可配置的 Capability Owner 模型：

```
TeamMember（人）
  └── CapabilityDomain（能力域）
        └── AgentDefinition（Agent 定义）
              └── AgentRun（执行实例）
```

**关系说明**：
- **一人多域**：一个 TeamMember 可以拥有多个 CapabilityDomain
- **一域多 Agent**：一个 CapabilityDomain 下可以注册多个 Agent
- **Owner 责任**：域的 Owner 负责该域内所有 Agent 的审批和升级处理

### 1.2 映射示例

来源于 vibe-coding 的 8 人分工，通用化后：

| 团队成员 | 能力域 | 管辖 Agent |
|---------|--------|-----------|
| Alice (前端负责人) | frontend-platform | ui-architect, react-implementer, storybook-reviewer, frontend-tester, css-optimizer |
| Bob (交易域专家) | trade-domain | trade-analyst, trade-service, payment-safety, trade-e2e |
| Carol (基础设施) | infrastructure | docker-config, ci-pipeline, perf-monitor |
| Dave (质量保障) | quality-assurance | test-planner, regression-runner, security-scanner |

### 1.3 配置方式

通过 Dashboard 的"设置"页面配置人机映射：

1. 创建团队成员（姓名、邮箱、角色）
2. 创建能力域并指定 Owner
3. 将 Agent 定义挂载到对应能力域

## 二、审批流程

### 2.1 审批触发条件

| 触发源 | 创建的决策类型 | 审批人 |
|--------|--------------|--------|
| Agent 执行失败超过重试次数 | ESCALATION | 对应域 Owner |
| 质量门禁 FAIL | ESCALATION | 对应域 Owner |
| 需要人工确认的架构决策 | ADR | 技术负责人 |
| 风险被识别 | RISK_ACCEPT | 对应域 Owner |
| 工作流回退请求 | ROLLBACK | 触发回退的阶段 Owner |
| Agent 输出需要 Owner Override | OVERRIDE | 对应域 Owner |

### 2.2 审批状态机

```
PENDING → APPROVED → 工作流继续
        → REJECTED → 工作流阻塞/回退
```

### 2.3 审批队列

Owner 的审批队列在"决策中心"视图中展示，按紧急程度排序：

- 🔴 CRITICAL：阻塞其他工作流推进
- 🟡 HIGH：超过 2h 未处理
- 🔵 NORMAL：正常待处理
- ⚪ LOW：不紧急的建议类决策

## 三、升级策略

### 3.1 超时升级链

```
Agent 阻塞
  ↓ (立即)
域 Owner 收到通知
  ↓ (4h 无响应)
技术负责人收到升级通知
  ↓ (8h 无响应)
全团队广播通知
```

### 3.2 升级服务实现

```python
class EscalationService:
    async def escalate(self, agent_run: AgentRun, reason: str):
        # 1. 查找 Agent 所属能力域
        domain = agent_run.agent_definition.capability_domain
        
        # 2. 查找域 Owner
        owner = domain.owner
        
        # 3. 创建 Decision + Approval
        decision = create_decision(
            type=DecisionType.ESCALATION,
            title=f"Agent {agent_run.agent_definition.name} 需要人工介入",
            content=reason,
        )
        approval = create_approval(
            decision_id=decision.id,
            reviewer_id=owner.id,
        )
        
        # 4. 发送通知（WebSocket + 可选邮件）
        await notify_owner(owner, decision)
        
        # 5. 设置超时检查
        schedule_timeout_check(decision.id, hours=4)
    
    async def handle_timeout(self, decision_id: int):
        decision = get_decision(decision_id)
        if decision.approvals[0].status == "pending":
            # 升级到技术负责人
            tech_lead = get_tech_lead()
            create_approval(decision_id, tech_lead.id)
            await notify_owner(tech_lead, decision)
```

## 四、负载均衡

### 4.1 瓶颈检测算法

```python
def detect_bottleneck(owner: TeamMember) -> bool:
    pending = count_pending_approvals(owner.id)
    avg_response_hours = calc_avg_response_time(owner.id)
    active_agents = count_active_agents_under_owner(owner.id)
    
    # 瓶颈条件
    return (
        pending > 5 or
        avg_response_hours > 4.0 or
        active_agents > 20
    )
```

### 4.2 负载均衡建议

当检测到瓶颈时，Dashboard 会显示：
- 🔴 高亮过载 Owner
- 建议：将部分 Agent 重新分配到其他 Owner
- 建议：增加域内的辅助审批人
