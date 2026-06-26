# ANALYSE_PRODUCT 阶段 Agent Teams 输出格式

> **加载时机**: 仅在 ANALYSE_PRODUCT 阶段的预览/进度监控/总结确认时加载。
> **前置依赖**: 需同时加载 `output-formats/common.md`。

---

## 13. ANALYSE_PRODUCT 阶段 Agent Teams 预览格式

```
** 📋 阶段预览: ANALYSE_PRODUCT（Agent Teams 模式） **

📌 需求: [需求名称]
🔄 当前阶段: ANALYSE_PRODUCT (1/15)
🚀 调度模式: Agent Teams 四成员串行协作（三级降级）
🏷️ 团队名称: analyse-product-[需求ID]
📑 PRD 来源: [PRD 路径或用户输入]

👥 分析团队成员:
  ┌───────────┬───────────────────────┬──────────────────────┬──────────────────┐
  │ 顺序       │ 成员名                 │ 职责                  │ 依赖              │
  ├───────────┼───────────────────────┼──────────────────────┼──────────────────┤
  │ T1        │ @product-collector    │ PRD 阅读 & 信息收集    │ 无                │
  │ T2 (条件) │ @baseline-differ      │ 基线对比 & 移除判定    │ T1（仅迭代需求）   │
  │ T3        │ @product-extractor    │ 结构化需求提取         │ T1 / T2           │
  │ T4        │ @quality-assessor     │ 质量评估 & 风险分析    │ T3               │
  └───────────┴───────────────────────┴──────────────────────┴──────────────────┘

🔒 上下文防火墙:
  - T1 读取原始 PRD，压缩为 _product-collection.json（~100-150 行）
  - T3 禁止读取原始 PRD，仅消费 T1/T2 的压缩中间产物
  - 各成员拥有独立上下文窗口，历史不互传

🔄 降级策略:
  - L1: Agent Teams（当前） → L2: Task 串行管道 → L3: orchestrator 直接执行
  - 超时检测: 120s 无响应 + 60s 宽限期 → 自动降级

📥 输入:
  - [PRD 文档路径]

📤 预期输出:
  - analysis/_product-collection.json（中间产物 - T1）
  - analysis/_baseline-summary.json（中间产物 - T2，仅迭代需求）
  - analysis/_extraction-result.json（中间产物 - T3）
  - analysis/product-requirements.md（最终报告 - T4）
  - analysis/product-clarify.json（如有）

⚠️ 已知风险: [N] 项

请确认是否执行？[执行 / 取消]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 14. ANALYSE_PRODUCT 阶段 Agent Teams 进度监控格式

```
** 🔄 ANALYSE_PRODUCT 进度: Agent Teams **

🏷️ 团队: analyse-product-[需求ID]
⏱️ 已运行: [时长]
📋 需求类型: [全新需求 / 迭代增量需求]

📊 成员状态:
  ✅ @product-collector  — 完成 — 耗时 5m — 收集 {N} 个 PRD 章节，信息评级 🟢{a} 🟡{b}
  🔄 @baseline-differ   — 执行中 — 已运行 3m — 基线对比中（{M} 项变更已识别）
  ⏳ @product-extractor — 等待中 — 依赖 T2 完成
  ⏳ @quality-assessor  — 等待中 — 依赖 T3 完成

📈 总体进度: [1/4] 成员完成
🔒 上下文防火墙: 正常（T3 未接触原始 PRD）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**全新需求时（T2 跳过）**:

```
📊 成员状态:
  ✅ @product-collector  — 完成 — 耗时 4m — 收集 {N} 个 PRD 章节
  ⏭️ @baseline-differ   — 跳过（全新需求，无需基线对比）
  🔄 @product-extractor — 执行中 — 已运行 2m — 结构化提取中...
  ⏳ @quality-assessor  — 等待中 — 依赖 T3 完成

📈 总体进度: [1/3] 成员完成（T2 跳过）
```

## 15. ANALYSE_PRODUCT 阶段 Agent Teams 总结格式

```
** ✅ 阶段完成: ANALYSE_PRODUCT（Agent Teams 模式） **

🏷️ 团队: analyse-product-[需求ID]
⏱️ 总耗时: [时长]
🚀 调度模式: Agent Teams（{N} 个成员串行协作）
📋 需求类型: [全新需求 / 迭代增量需求]

📊 各成员完成情况:
  ┌─────────────────────┬──────────┬──────────┬───────────────────────────────┐
  │ 成员                 │ 耗时     │ 状态      │ 摘要                           │
  ├─────────────────────┼──────────┼──────────┼───────────────────────────────┤
  │ @product-collector  │ 5m       │ ✅ 完成  │ 收集 {N} 章节，追问 {M} 次     │
  │ @baseline-differ    │ 3m       │ ✅ 完成  │ {X} 项变更，{Y} 项移除         │
  │ @product-extractor  │ 4m       │ ✅ 完成  │ {P} 个功能点，{Q} 个业务规则   │
  │ @quality-assessor   │ 3m       │ ✅ 完成  │ 质量评分 {score}/5.0           │
  └─────────────────────┴──────────┴──────────┴───────────────────────────────┘

📄 产出物:
  - analysis/_product-collection.json（中间产物）
  - analysis/_baseline-summary.json（中间产物，仅迭代需求）
  - analysis/_extraction-result.json（中间产物）
  - analysis/product-requirements.md（最终报告）
  - analysis/product-clarify.json（{N} 个澄清问题）

📊 质量门禁: {qualityGate} (评分: {qualityScore}/5.0)
📐 质量维度:
  - 完整性: {completeness}/5.0 (权重 25%)
  - 一致性: {consistency}/5.0 (权重 20%)
  - 可测试性: {testability}/5.0 (权重 20%)
  - 可行性: {feasibility}/5.0 (权重 15%)
  - 明确性: {clarity}/5.0 (权重 10%)
  - 可追溯性: {traceability}/5.0 (权重 10%)

🏷️ Kano 分类:
  - 必备需求 (M): {count} 项
  - 期望需求 (O): {count} 项
  - 魅力需求 (A): {count} 项

⚠️ 新增风险: [N] 项
📊 总体风险: [N] 项

下一阶段: CLARIFY_PRODUCT
请选择: [确认进入下一阶段 / 回退到上一阶段]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 16. ANALYSE_PRODUCT 阶段降级通知格式

**L1 → L2 降级通知**:

```
** ⚠️ ANALYSE_PRODUCT 调度降级: L1 → L2 **

🔄 原模式: Agent Teams 四成员串行协作
🔄 新模式: Task 串行管道（{N} 个 Task）
📋 降级原因: {reason}

📦 可复用的中间产物:
  - {已产出的产物列表}

🔧 Task 管道计划:
  - Task 1: {描述}
  - Task 2: {描述}
  {- Task 3: {描述}（仅迭代需求）}

⏱️ 预计额外耗时: {估算}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**L2 → L3 降级通知**:

```
** 🚨 ANALYSE_PRODUCT 调度降级: L2 → L3 **

🔄 原模式: Task 串行管道
🔄 新模式: Orchestrator 直接执行（单体 Agent）
📋 降级原因: {reason}

📦 可复用的中间产物:
  - {已产出的产物列表}

⚠️ 注意: 降级到最低级模式，上下文防火墙将不再生效。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
