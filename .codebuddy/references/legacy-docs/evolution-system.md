# AI Team — 知识进化系统设计文档

> 版本：v0.1 | 更新日期：2026-03-24

---

## 一、设计来源

直接继承 vibe-coding 项目的 `/evolve` 进化机制（03-总架构师审查工作流.md §六），将文件系统存储升级为数据库管理。

## 二、进化闭环流程

```
Bug 修复 / 缺陷发现
      ↓
回溯根因到 Agent 环节
      ↓
生成改进建议 → EvolveRecord (status: pending)
      ↓
Owner 审阅 (/evolve:apply)
      ↓
┌─────────────────────────────────────────────┐
│ APPLIED  → 更新 Rule + Agent 定义 + 版本号   │
│ REJECTED → 记录拒绝原因，不做修改             │
│ DEFERRED → 暂缓处理，后续再评估               │
└─────────────────────────────────────────────┘
```

## 三、改进记录生命周期

### 3.1 状态机

```
PENDING → APPLIED  (已应用)
        → REJECTED (已拒绝)
        → DEFERRED (已暂缓)
```

来源于 vibe-coding 的进化日志：
- `docs/workflows/evolve-log/{date}-{seq}-{title}.md`
- 现在升级为 `evolve_records` 数据库表

### 3.2 改进记录字段

| 字段 | 说明 | 示例 |
|------|------|------|
| rule_id | 关联的规则 | 编码规范 #3 |
| title | 改进标题 | "运营端菜单路由缺失" |
| bug_source | Bug 来源描述 | "E2E 测试发现菜单无法跳转" |
| affected_agents | 受影响的 Agent | ["frontend-architect", "react-implementer"] |
| improvement_type | 改进类型 | rule_update / agent_prompt / new_check |
| suggestion | 改进建议正文 | "在 frontend-architect 的 Prompt 中增加..." |

### 3.3 审阅操作

```python
async def review_evolve_record(record_id, review: EvolveRecordReview):
    record = get_evolve_record(record_id)
    
    record.status = review.status
    record.reviewer_id = review.reviewer_id
    record.review_comment = review.review_comment
    
    if review.status == "applied":
        record.applied_at = datetime.now()
        # 自动更新关联的 Rule 版本
        rule = get_rule(record.rule_id)
        rule.version = bump_version(rule.version)
        rule.content = apply_suggestion(rule.content, record.suggestion)
```

## 四、规则版本管理

### 4.1 规则分类

| 类别 | 说明 | 示例 |
|------|------|------|
| coding_standard | 编码规范 | "金额使用 BigDecimal，精度 2 位" |
| architecture_rule | 架构规则 | "跨服务调用必须有降级处理" |
| review_checklist | 审查清单 | "支付接口必须检查幂等" |
| agent_constraint | Agent 约束 | "Product-analyst 必须输出优先级列表" |
| quality_gate | 门禁规则 | "编译验证必须 0 error" |

### 4.2 版本策略

- 每次 APPLIED 改进自动 bump patch 版本
- 重大变更手动 bump minor 版本
- 规则内容变更前后保存 diff

## 五、质量评估体系

### 5.1 Agent 可信度评分

```python
def calculate_agent_trust_score(agent_def_id):
    runs = get_recent_runs(agent_def_id, limit=50)
    
    first_pass_rate = count(r for r in runs if r.status == "completed") / len(runs)
    retry_rate = count(r for r in runs if r.attempt > 1) / len(runs)
    avg_token = mean(r.token_input + r.token_output for r in runs)
    
    # 加权综合评分
    score = (
        first_pass_rate * 0.5 +
        (1 - retry_rate) * 0.3 +
        normalize_token_efficiency(avg_token) * 0.2
    )
    return round(score * 100, 1)
```

### 5.2 评估维度

| 指标 | 权重 | 计算方法 |
|------|------|---------|
| 首次通过率 | 50% | 一次执行成功的比例 |
| 无重试率 | 30% | 不需要重试的比例 |
| Token 效率 | 20% | 相同任务类型下的 token 消耗归一化 |

### 5.3 缺陷模式分析

从 Agent 运行历史中提取缺陷模式：
- 按 Agent 类型 × 缺陷类型 生成热力图
- 高频缺陷自动生成改进建议
- 跟踪规则改进后缺陷是否减少

## 六、组织记忆

### 6.1 自动沉淀

- 历史缺陷模式自动归档
- 最佳实践（高评分 Agent 的 Prompt 特征）自动提取
- 常见问题-解决方案对自动建库

### 6.2 知识检索

Agent 执行时可检索组织记忆：
- 相似需求的历史产物
- 同类型缺陷的修复方案
- 领域最佳实践
