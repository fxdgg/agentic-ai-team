---
name: skill-learner
description: "Skill 自学习引擎。当用户提到 Skill 优化、Skill 评分、Skill 效果分析、Agent 能力提升、prompt 优化、工作流效率提升时触发此技能。基于工作流历史数据持续分析各 Skill 和 Agent 的表现，自动提出优化建议并辅助 Skill 的迭代进化。"
---

# Skill 自学习引擎

## 1. 角色定位

本技能是 **Skills 系统的自我优化与进化引擎**。核心职责：

- **评估**各 Skill 和 Agent 在实际工作流中的表现质量
- **分析**识别 Skill 定义中可改进的模式和弱点
- **建议**生成具体可操作的 Skill 优化建议
- **验证**优化前后的效果对比

> **关键原则：Skill 学习是建议驱动的渐进优化，所有变更需人工确认。**

---

## 2. 评估体系

### 2.1 评估维度

| 维度 | 权重 | 评估来源 | 说明 |
|------|------|---------|------|
| 任务成功率 | 30% | state.json 阶段状态 | Agent 被调用后阶段是否顺利完成 |
| 产出物质量 | 25% | qualityGate 评分 | 产出物质量门禁通过率和评分 |
| 首次通过率 | 20% | 回退记录 | 无需回退即通过的比率 |
| 执行效率 | 15% | 阶段耗时统计 | 实际耗时 vs 预期耗时 |
| 用户满意度 | 10% | 用户确认/回退决策 | 用户在总结确认步骤的选择 |

### 2.2 评分模型

```
Skill 综合评分 = Σ (维度分数 × 维度权重)

每个维度分数计算:
- 任务成功率: 成功次数 / 总调用次数 × 100
- 产出物质量: 平均 qualityGate 分数
- 首次通过率: 首次通过次数 / 总调用次数 × 100
- 执行效率: min(预期耗时 / 实际耗时, 1.0) × 100
- 用户满意度: 确认次数 / (确认 + 回退次数) × 100
```

---

## 3. 数据采集

### 3.1 采集来源

| 数据点 | 来源 | 采集时机 |
|--------|------|---------|
| Agent 调用记录 | state.json → phaseHistory | 每次阶段转换时 |
| 质量评分 | state.json → qualityGate | 每个阶段完成时 |
| 回退记录 | state.json → rollbackLog | 回退发生时 |
| 阶段耗时 | state.json → timestamps | 阶段开始/结束时 |
| 用户决策 | 总结确认步骤的选择 | 用户确认/回退时 |
| 模型性能 | model-router 性能数据 | 每次 Agent 调用后 |

### 3.2 数据存储

```
docs/skill-analytics/
├── skill-scores.json           # 各 Skill 综合评分
├── agent-scores.json           # 各 Agent 表现评分
├── optimization-log.json       # 优化历史记录
└── experiments/                # A/B 测试记录（可选）
    └── EXP-001-{标题}.json
```

### 3.3 评分快照

```json
{
  "snapshotTime": "ISO-8601",
  "skills": {
    "workflow-orchestrator": {
      "overallScore": 85.2,
      "dimensions": {
        "successRate": 92.0,
        "qualityScore": 81.5,
        "firstPassRate": 78.0,
        "efficiency": 88.0,
        "satisfaction": 95.0
      },
      "agentBreakdown": {
        "product-analyst": { "score": 90.0, "callCount": 12 },
        "fullstack-analyst": { "score": 82.0, "callCount": 10 },
        "java-architect": { "score": 88.5, "callCount": 8 }
      },
      "trend": "improving",
      "sampleSize": 15
    }
  }
}
```

---

## 4. 优化分析

### 4.1 弱点识别

```
弱点检测规则:

1. 低成功率 Agent（< 80%）:
   → 分析失败案例，提取共同模式
   → 建议: 增强 Agent 的 system prompt

2. 高回退率阶段（回退率 > 30%）:
   → 分析回退原因分布
   → 建议: 加强前置阶段的输出约束

3. 低质量评分模式（连续 3 次 < 70）:
   → 对比高质量和低质量产出的差异
   → 建议: 调整 Agent 的评分标准或补充示例

4. 效率异常（耗时 > 2 × 中位数）:
   → 分析上下文大小和任务复杂度
   → 建议: 优化上下文注入策略或拆分任务

5. 用户频繁回退（特定阶段回退率 > 40%）:
   → 分析回退前的总结内容
   → 建议: 改进总结展示格式或增加预览信息
```

### 4.2 优化建议生成

```
每个优化建议的结构:

{
  "id": "OPT-{序号}",
  "target": "{skill-id}/{agent-file}",
  "type": "prompt-enhancement | context-optimization | flow-adjustment | template-update",
  "priority": "high | medium | low",
  "description": "建议描述",
  "rationale": "基于数据的理由",
  "expectedImpact": "预期改善效果",
  "suggestedChanges": ["具体变更建议列表"],
  "dataEvidence": {
    "sampleSize": 0,
    "currentScore": 0.0,
    "targetScore": 0.0
  }
}
```

### 4.3 优化类型

| 类型 | 说明 | 典型改进 |
|------|------|---------|
| prompt-enhancement | Agent system prompt 增强 | 增加约束、补充示例、明确输出格式 |
| context-optimization | 上下文注入策略优化 | 减少冗余上下文、增加关键上下文 |
| flow-adjustment | 工作流程微调 | 调整阶段顺序、增加检查点 |
| template-update | 产物模板更新 | 优化模板结构、增加必填字段 |
| rule-refinement | 规则精化 | 加强编码规范、细化架构约束 |

---

## 5. 实验机制

### 5.1 A/B 测试框架

```
实验流程:
1. 基于优化建议创建实验:
   - 对照组: 当前 Skill/Agent 定义
   - 实验组: 优化后的定义
   
2. 运行实验:
   - 在接下来的 N 个工作流中交替使用
   - 记录两组的所有评估指标
   
3. 分析结果:
   - 对比各维度评分
   - 统计显著性检验
   - 生成实验报告
   
4. 决策:
   - 实验组显著优于对照组 → 推荐采纳
   - 无显著差异 → 保留当前版本
   - 实验组劣于对照组 → 回退到对照组
```

### 5.2 渐进式发布

```
大变更的渐进式发布:
1. 先在低风险阶段（如 ARCHIVE）测试
2. 观察 3 个工作流无异常
3. 推广到中风险阶段
4. 最后推广到高风险阶段（如 ARCHITECT_BACKEND）
```

---

## 6. 报告与展示

### 6.1 Skill 健康报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Skill 学习报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

统计周期: {开始} ~ {结束} | 工作流样本: {N} 个

Skill 综合评分: 85.2 / 100 (趋势: ↑ +3.5)

Agent 表现排行:
┌─────────────────────────────────────┐
│ 🥇 product-analyst       90.0 ↑    │
│ 🥈 java-architect        88.5 →    │
│ 🥉 test-engineer         86.0 ↑    │
│  4. fullstack-analyst     82.0 ↓    │
│  5. web-developer         80.5 →    │
│  ...                                │
└─────────────────────────────────────┘

⚠️ 关注项:
• fullstack-analyst 评分下降 5 分，主要原因: 技术分析深度不足
• BUILD_VERIFY 首次通过率从 85% 降至 72%

📋 优化建议 (Top 3):
1. [高] fullstack-analyst: 增强技术探索深度约束
2. [中] implement-rules: 优化编译修复上下文注入
3. [低] output-formats: 统一总结格式中的风险展示

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. 使用方式

### 7.1 触发关键词

- "Skill 评分"、"Skill 效果"、"Skill 分析"
- "Agent 表现"、"Agent 评估"、"谁表现最好"
- "优化建议"、"如何提升质量"
- "Skill 学习报告"、"效率分析"

### 7.2 使用示例

```
用户: 各个 Agent 表现怎么样？
→ 生成 Agent 表现排行和趋势分析

用户: 有什么优化建议？
→ 基于历史数据生成优先级排序的优化建议列表

用户: fullstack-analyst 为什么评分低？
→ 深入分析该 Agent 的表现数据，定位弱点

用户: 最近的优化效果怎么样？
→ 展示优化前后的对比数据
```

---

## 8. 与其他 Skill 的协作

| 协作 Skill | 协作方式 | 方向 |
|-----------|---------|------|
| workflow-orchestrator | 从工作流数据采集评估指标 | ← 数据来源 |
| quality-guardian | 质量评分作为 Skill 评估的核心输入 | ← 数据来源 |
| knowledge-evolution | 优化经验沉淀为知识库条目 | → 知识沉淀 |
| model-router | 模型选择影响 Skill 表现，联合优化 | ↔ 双向 |
| capability-router | 路由准确率影响用户满意度 | ← 数据来源 |
| skill-creator | 优化建议可直接驱动 Skill 更新流程 | → 驱动更新 |

---

## 9. 行为约束

### 9.1 必须做的（DO）

- ✅ 基于数据说话，所有建议必须有数据支撑
- ✅ 优化建议必须具体到文件和行级别
- ✅ 大变更必须通过实验验证再推广
- ✅ 保留完整的优化历史记录
- ✅ 尊重用户对优化建议的最终决策

### 9.2 禁止做的（DON'T）

- ❌ 禁止自动修改 Skill 或 Agent 定义文件（只提供建议）
- ❌ 禁止基于不充分样本（< 5 个工作流）给出强烈建议
- ❌ 禁止评分计算中使用未定义的指标
- ❌ 禁止泄露具体需求内容（只使用统计数据）
- ❌ 禁止在没有回退方案的情况下建议大范围变更
