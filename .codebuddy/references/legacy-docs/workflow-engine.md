# AI Team — 工作流引擎设计文档

> 版本：v0.1 | 更新日期：2026-03-24

---

## 一、设计目标

将 vibe-coding 项目中硬编码的 15 阶段状态机（SKILL.md + phase-transitions.json）升级为 YAML 配置驱动的通用工作流引擎。

## 二、YAML 配置规范

### 2.1 模板结构

```yaml
name: "工作流名称"
version: "1.0"
description: "工作流描述"

phases:
  - id: PHASE_ID                    # 阶段唯一标识
    name: "阶段显示名称"
    agent_role: "agent-role-name"   # 单 Agent 模式
    parallel_agents: [...]          # 并行 Agent 模式
    sequential_agents: [...]        # 串行 Agent 模式
    dynamic_dispatch: false         # 动态调度模式
    dispatch_strategy: "by_role"    # 调度策略
    three_step_mode: true           # 是否启用三步模式
    clarify_enabled: false          # 是否启用澄清循环
    outputs: [...]                  # 期望输出产物列表
    depends_on: [PHASE_ID]          # 前置依赖阶段
    rollback_target: PHASE_ID       # 回退目标阶段
    max_rollback: 2                 # 最大回退次数

transitions:
  PHASE_ID:
    next: NEXT_PHASE_ID             # 默认下一阶段
    can_skip_to: SKIP_PHASE_ID     # 可跳过到的阶段（澄清满足时）
```

### 2.2 来源映射

| vibe-coding 概念 | AI Team 通用化 |
|-----------------|---------------|
| phase-transitions.json | YAML transitions 节 |
| state.json.currentPhase | WorkflowRun.current_phase |
| state.json.phaseHistory | WorkflowRun.phase_history (JSONB) |
| state.json.platforms | WorkflowRun.platforms (JSONB) |
| state.json.rollbackLog | rollback_logs 表 |
| SKILL.md 三步模式 | PhaseRun.step (preview/execute/summary) |
| SKILL.md 质量门禁 | PhaseRun.quality_gate (pass/warn/fail) |

## 三、状态机执行逻辑

### 3.1 工作流生命周期

```
PENDING → RUNNING → COMPLETED
                  ↗ PAUSED（人工暂停）
                  ↗ BLOCKED（阻塞等待）
                  ↗ FAILED（不可恢复）
                  ↗ CANCELLED（手动取消）
```

### 3.2 阶段推进算法

```python
async def advance_phase(workflow_id, user_confirmation):
    workflow = load_workflow(workflow_id)
    template = parse_template(workflow.workflow_template)
    
    current = workflow.current_phase
    transition = template.transitions[current]
    
    # 1. 流转守卫校验
    if not validate_transition(current, transition.next):
        raise InvalidTransition()
    
    # 2. 质量门禁检查
    phase_run = get_current_phase_run(workflow_id)
    if phase_run.quality_gate == "fail":
        raise QualityGateFailed()
    
    # 3. 推进到下一阶段
    next_phase = transition.next
    
    # 4. 澄清跳过判断（来自 vibe-coding 的 canSkipTo 机制）
    if transition.can_skip_to and clarify_auto_satisfied(workflow_id):
        next_phase = transition.can_skip_to
    
    # 5. 更新状态
    workflow.current_phase = next_phase
    create_phase_run(workflow_id, next_phase)
```

### 3.3 三步模式生命周期

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│ PREVIEW │ → │ EXECUTE │ → │ SUMMARY │
│ 展示计划 │    │ 调度Agent│    │ 结果确认 │
└─────────┘    └─────────┘    └─────────┘
      ↑                             │
      └──── 用户拒绝 / 回退 ────────┘
```

每步的职责：

1. **PREVIEW**：加载模板配置 → 展示将要调度的 Agent 和输入产物 → 等待用户确认
2. **EXECUTE**：调度 Agent → 收集产物 → 记录 token 消耗 → 质量门禁检查
3. **SUMMARY**：展示执行结果 → 门禁结果 → 用户确认推进/回退

### 3.4 回退策略

来源于 vibe-coding 的 BUILD_VERIFY 精细化回退策略：

| 规则 | 说明 |
|------|------|
| 默认回退 | 回退到直接前驱阶段 |
| 指定回退 | 按 `rollback_target` 配置回退 |
| 最大次数 | 同一阶段回退不超过 `max_rollback` 次 |
| 精细回退 | 支持平台级回退（仅回退失败平台） |
| 修复模式 | 回退后注入错误上下文到 Agent |

回退时的状态变更：
```
1. rollback_logs 新增回退记录
2. 当前阶段 PhaseRun.status → rolled_back
3. workflow.current_phase → 回退目标阶段
4. 创建新的 PhaseRun（attempt_number + 1）
```

## 四、模板解析器

```python
@dataclass
class PhaseConfig:
    id: str
    name: str
    agent_role: str | None = None
    parallel_agents: list[str] = field(default_factory=list)
    sequential_agents: list[str] = field(default_factory=list)
    dynamic_dispatch: bool = False
    dispatch_strategy: str = "by_role"
    three_step_mode: bool = True
    clarify_enabled: bool = False
    outputs: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    rollback_target: str | None = None
    max_rollback: int = 2

@dataclass
class TransitionConfig:
    next: str | None = None
    can_skip_to: str | None = None

@dataclass
class WorkflowTemplate:
    name: str
    version: str
    phases: list[PhaseConfig]
    transitions: dict[str, TransitionConfig]
```

## 五、流转守卫校验

来源于 vibe-coding 的 phase-transitions.json rules：

1. **前向校验**：目标阶段必须是当前阶段的合法后继（next 或 can_skip_to）
2. **跳过条件**：can_skip_to 仅在澄清条件满足时可用
3. **回退限制**：仅允许回退到配置的回退目标
4. **终止校验**：只有最后一个阶段才能将状态设为 DONE
