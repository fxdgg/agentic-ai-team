# AI Team — Agent 调度设计文档

> 版本：v0.1 | 更新日期：2026-03-24

---

## 一、调度概览

Agent 调度器负责在工作流引擎推进到某个阶段时，根据阶段配置和调度策略，选择并分派合适的 Agent 执行任务。

## 二、调度模式

### 2.1 单 Agent 模式

最简单的模式，按 `agent_role` 直接匹配唯一 Agent：

```yaml
phases:
  - id: ANALYSE_PRODUCT
    agent_role: "product-analyst"
```

### 2.2 并行 Agent 模式

多个 Agent 同时执行，全部完成后阶段才完成：

```yaml
phases:
  - id: ARCHITECT
    parallel_agents: ["backend-architect", "frontend-architect"]
```

### 2.3 串行 Agent 模式

多个 Agent 按顺序执行：

```yaml
phases:
  - id: VERIFY
    sequential_agents: ["build-verifier", "e2e-verifier", "test-engineer"]
```

### 2.4 动态分派模式

来源于 vibe-coding 的 IMPLEMENT 阶段调度规则。根据运行时上下文动态决定调度哪些 Agent：

```yaml
phases:
  - id: IMPLEMENT
    dynamic_dispatch: true
    dispatch_strategy: "by_capability_domain"
```

**调度策略**：

| 策略名称 | 说明 | 来源 |
|---------|------|------|
| by_role | 按 agent_role 精确匹配 | 默认 |
| by_capability_domain | 按能力域分配 | vibe-coding implement-rules §1-2 |
| by_priority | 按优先级排序调度 | vibe-coding implement-rules §2 |
| by_failed_platforms | 仅调度失败平台的 Agent | vibe-coding build-verify-rules §2-3 |

## 三、调度算法

### 3.1 匹配算法

```python
async def match_agents(phase_config, workflow_context):
    candidates = []
    
    if phase_config.agent_role:
        # 单 Agent 精确匹配
        agent = find_by_role(phase_config.agent_role)
        candidates = [agent]
    
    elif phase_config.parallel_agents:
        # 并行 Agent 列表匹配
        candidates = [find_by_role(r) for r in phase_config.parallel_agents]
    
    elif phase_config.dynamic_dispatch:
        # 动态分派
        candidates = dynamic_dispatch(phase_config, workflow_context)
    
    # 过滤：仅保留 is_active=True 的 Agent
    candidates = [a for a in candidates if a.is_active]
    
    return candidates
```

### 3.2 动态分派（来自 vibe-coding implement-rules.md）

```python
async def dynamic_dispatch(phase_config, context):
    strategy = phase_config.dispatch_strategy
    
    if strategy == "by_capability_domain":
        # 按能力域找出所有需要参与的 Agent
        domains = get_active_domains(context)
        agents = []
        for domain in domains:
            domain_agents = get_agents_by_domain(domain.id)
            agents.extend(domain_agents)
        return agents
    
    elif strategy == "by_failed_platforms":
        # 编译修复模式：仅调度失败平台的 Agent
        rollback = get_latest_rollback(context.workflow_id)
        failed_platforms = rollback.get("failedPlatforms", [])
        agents = []
        for platform in failed_platforms:
            platform_agents = get_agents_by_platform(platform)
            agents.extend(platform_agents)
        return agents
```

## 四、Token 预算控制

### 4.1 预算层级

```
组织级预算
  └── 项目级预算
        └── 工作流级预算
              └── Agent 级预算
```

### 4.2 检查逻辑

```python
async def check_budget(agent_def, workflow_id):
    # 获取当前工作流已用 token
    used = sum(budget_usages for workflow_id)
    limit = settings.default_token_budget_per_workflow
    
    # 估算本次 Agent 执行的 token 消耗
    estimated = estimate_token_usage(agent_def)
    
    if used + estimated > limit:
        return False, "Token budget exceeded"
    return True, None
```

## 五、失败处理

### 5.1 重试策略

| 失败类型 | 处理 |
|---------|------|
| LLM 超时 | 自动重试 1 次 |
| LLM 输出异常 | 自动重试 1 次（注入修正提示） |
| 质量门禁 WARN | 继续执行，记录警告 |
| 质量门禁 FAIL | 阻断，通知 Owner |
| 连续 2 次失败 | 升级到 Owner |

### 5.2 升级路径

```
Agent 失败 → 自动重试(1次) → 仍失败 → 查找能力域 Owner
                                           ↓
                                    通知 Owner 审批
                                           ↓
                                    Owner 4h 未响应
                                           ↓
                                    升级到技术负责人
```

## 六、编译修复模式

来源于 vibe-coding 的 build-verify-rules.md §3-4：

当 BUILD_VERIFY 阶段编译失败回退到 IMPLEMENT 时，调度器进入编译修复模式：

1. 从 rollback_logs 读取最近一条回退记录
2. 提取 failedPlatforms 和 errors
3. 仅调度失败平台对应的 Agent
4. 注入编译错误上下文到 Agent 的 input_context
5. 已通过平台的 Agent 不再调度

上下文注入格式：
```
【编译修复模式】上次 BUILD_VERIFY 阶段发现以下编译错误，
请在本次实现中修复。仅需修复以下问题，不要修改其他代码：
{错误列表 + 修复建议}
```
