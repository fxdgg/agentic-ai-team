---
name: token-budget-manager
description: "Token 预算管理器。当用户提到 Token 用量、成本控制、预算管理、Token 限制、上下文优化、成本报告时触发此技能。实时追踪工作流中的 Token 消耗，提供预算预警、成本优化建议和消耗趋势分析。"
---

# Token 预算管理器

## 1. 角色定位

本技能是 **工作流 Token 消耗的全局监控与预算管理系统**。核心职责：

- **追踪**每个 Agent 调用的 Token 消耗（输入/输出）
- **预算**设定和管理单需求、日度、月度的 Token 预算
- **预警**在消耗接近预算时提前预警
- **优化**提供具体的 Token 节省策略和建议

> **关键原则：让 Token 消耗可见、可控、可优化，在成本和质量之间找到平衡。**

---

## 2. 消耗追踪体系

### 2.1 追踪粒度

```
追踪层级:
├── 全局层 (Global)
│   ├── 日度消耗
│   ├── 月度消耗
│   └── 累计消耗
│
├── 需求层 (Workflow)
│   ├── 单需求总消耗
│   ├── 各阶段消耗
│   └── 预算使用率
│
├── 阶段层 (Phase)
│   ├── 单阶段消耗
│   ├── Agent 调用次数
│   └── 回退额外消耗
│
└── Agent 层 (Agent)
    ├── 单次调用消耗
    ├── 输入 Token 数
    ├── 输出 Token 数
    └── 上下文注入占比
```

### 2.2 追踪数据结构

```json
{
  "workflow": "{需求ID}",
  "totalTokens": {
    "input": 0,
    "output": 0,
    "total": 0
  },
  "budget": {
    "limit": null,
    "used": 0,
    "remaining": null,
    "usagePercent": 0.0
  },
  "phases": {
    "{phase}": {
      "input": 0,
      "output": 0,
      "agentCalls": 0,
      "retries": 0,
      "retryCost": 0
    }
  },
  "agents": {
    "{agent-id}": {
      "totalCalls": 0,
      "totalInput": 0,
      "totalOutput": 0,
      "avgInputPerCall": 0,
      "avgOutputPerCall": 0,
      "contextInjectionRatio": 0.0
    }
  }
}
```

---

## 3. 预算管理

### 3.1 预算层级

| 层级 | 说明 | 默认值 | 可配置 |
|------|------|--------|--------|
| 单需求预算 | 单个工作流的 Token 上限 | 无限制 | ✅ |
| 日度预算 | 每日 Token 消耗上限 | 无限制 | ✅ |
| 月度预算 | 每月 Token 消耗上限 | 无限制 | ✅ |
| 单次调用上限 | 单次 Agent 调用的 Token 上限 | 模型窗口限制 | ✅ |

### 3.2 预算配置

```json
// docs/token-budget.json
{
  "budgets": {
    "perWorkflow": null,
    "daily": null,
    "monthly": null,
    "perCall": {
      "maxInputTokens": null,
      "maxOutputTokens": null
    }
  },
  "alerts": {
    "warningThreshold": 0.7,
    "criticalThreshold": 0.9,
    "notifyOnOverBudget": true
  },
  "optimization": {
    "autoContextTrim": false,
    "preferLowCostModel": false,
    "cacheRepeatedContext": true
  }
}
```

### 3.3 预警机制

```
预警级别:

🟡 警告 (消耗 ≥ 70% 预算):
  → 展示当前消耗和剩余预算
  → 提示优化建议

🟠 临界 (消耗 ≥ 90% 预算):
  → 强调预算即将耗尽
  → 建议降级模型或简化后续阶段
  → 通知 model-router 切换为成本优先策略

🔴 超预算 (消耗 > 100% 预算):
  → 展示超额数量
  → 如果配置了硬限制 → 暂停工作流等待用户决策
  → 如果配置了软限制 → 继续执行但持续提醒
```

---

## 4. 成本分析

### 4.1 消耗分布分析

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Token 消耗报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需求: {需求名称}
总消耗: {total} tokens (输入: {input} | 输出: {output})
预算使用率: ████████░░ {percent}%

阶段消耗分布:
┌─────────────────────────────────────────┐
│ ANALYSE_PRODUCT    ██░░░░░░░░  8.2%     │
│ ANALYSE_TECH       ████░░░░░░  18.5%    │
│ ARCHITECT_BACKEND  █████░░░░░  22.3%    │
│ ARCHITECT_FRONTEND ███░░░░░░░  12.1%    │
│ IMPLEMENT          ████████░░  35.4%    │  ← 最大消耗
│ BUILD_VERIFY       █░░░░░░░░░  2.1%     │
│ E2E_VERIFY         ░░░░░░░░░░  0.8%     │
│ TEST               ░░░░░░░░░░  0.6%     │
└─────────────────────────────────────────┘

Top 5 消耗 Agent:
1. java-architect        — {N} tokens (22.3%)
2. common-developer      — {N} tokens (12.1%)
3. user-center-developer — {N} tokens (10.5%)
4. fullstack-analyst     — {N} tokens (9.8%)
5. frontend-architect    — {N} tokens (8.4%)

回退额外消耗: {N} tokens ({percent}% 的总消耗)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.2 成本优化建议

```
优化建议引擎:

1. 上下文瘦身 (Context Trimming):
   → 识别 Agent 调用中冗余的上下文注入
   → 建议: "fullstack-analyst 的上下文中有 40% 是重复的规则文件"
   → 预估节省: {N} tokens/次

2. 回退减少 (Retry Reduction):
   → 分析回退导致的额外消耗
   → 建议: "加强 IMPLEMENT 阶段的前置检查可减少回退"
   → 预估节省: {N} tokens/需求

3. 模型降级 (Model Downgrade):
   → 识别可以使用更低层级模型的 Agent
   → 建议: "ARCHIVE 阶段可使用 mid-tier 模型"
   → 预估节省: {N} tokens/次（成本降低 X%）

4. 缓存利用 (Cache Usage):
   → 识别多次调用中的重复上下文
   → 建议: "规则文件可以在会话中复用"
   → 预估节省: {N} tokens/需求

5. 产物压缩 (Artifact Compression):
   → 识别过长的产物被重复注入
   → 建议: "architecture.md 可以只注入摘要版本"
   → 预估节省: {N} tokens/次
```

---

## 5. 趋势与对比

### 5.1 跨需求对比

```
消耗趋势 (最近 5 个需求):

需求 1: ████████░░ 150K tokens
需求 2: ██████████ 220K tokens  ← 含 3 次 BUILD_VERIFY 回退
需求 3: ███████░░░ 130K tokens
需求 4: ██████░░░░ 115K tokens  ← 优化上下文注入后
需求 5: █████░░░░░ 98K tokens   ← 最优

平均消耗: 142.6K tokens/需求
趋势: ↓ 下降 (持续优化中)
```

### 5.2 效率指标

```
Token 效率指标:
- Token/功能点: 平均 {N}K tokens 完成一个功能点
- Token/代码行: 平均消耗 {N} tokens 生成 1 行有效代码
- 回退消耗占比: {percent}%（目标 < 10%）
- 上下文利用率: {percent}%（实际用到的上下文 / 注入的总上下文）
```

### 5.3 数据存储

```
docs/token-metrics/
├── current.json                  # 当前活跃需求的实时消耗
├── history/
│   ├── {需求ID}.json            # 已完成需求的最终消耗快照
│   └── ...
├── daily-summary.json           # 日度汇总
└── monthly-summary.json         # 月度汇总
```

---

## 6. 使用方式

### 6.1 触发关键词

- "Token 消耗"、"Token 用量"、"Token 预算"
- "成本报告"、"成本分析"、"花了多少 Token"
- "优化成本"、"节省 Token"、"上下文优化"
- "预算设置"、"预算预警"

### 6.2 使用示例

```
用户: 当前需求消耗了多少 Token？
→ 展示实时消耗报告，按阶段和 Agent 分布

用户: 设置月度 Token 预算为 500 万
→ 更新 token-budget.json，启用预算追踪和预警

用户: 怎么减少 Token 消耗？
→ 基于历史数据生成优化建议列表

用户: 对比一下最近几个需求的消耗
→ 展示跨需求消耗趋势和效率指标

用户: 为什么这个需求消耗这么多？
→ 深入分析高消耗原因（回退、长上下文、复杂 Agent 等）
```

---

## 7. 与其他 Skill 的协作

| 协作 Skill | 协作方式 | 方向 |
|-----------|---------|------|
| model-router | 预算压力时通知 model-router 切换低成本模型 | → model-router |
| workflow-orchestrator | 从 Agent 调用中采集 Token 消耗数据 | ← 数据来源 |
| quality-guardian | 联合分析质量和成本的权衡关系 | ↔ 双向 |
| skill-learner | Token 效率作为 Skill 评估的一个维度 | → skill-learner |
| team-hub | 团队 Token 消耗作为看板指标 | → team-hub |

---

## 8. 行为约束

### 8.1 必须做的（DO）

- ✅ 实时更新消耗数据（每次 Agent 调用后）
- ✅ 预算预警必须及时且清晰
- ✅ 优化建议必须附带预估节省量
- ✅ 保留完整的消耗历史（支持回溯和分析）
- ✅ 尊重用户对预算策略的最终决策

### 8.2 禁止做的（DON'T）

- ❌ 禁止在未经用户确认的情况下强制停止工作流
- ❌ 禁止修改 Agent 的上下文注入内容（只提供建议）
- ❌ 禁止隐瞒消耗数据（完全透明）
- ❌ 禁止为了节省 Token 而跳过关键阶段
- ❌ 禁止在消耗报告中暴露其他需求的具体内容
