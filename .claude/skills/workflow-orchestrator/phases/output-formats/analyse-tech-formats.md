# ANALYSE_TECH 阶段 Parallel Agent 输出格式

> **加载时机**: 仅在 ANALYSE_TECH 阶段的预览/进度监控/总结确认时加载。
> **前置依赖**: 需同时加载 `output-formats/common.md`。

---

## 13. ANALYSE_TECH 阶段 Parallel Agent 预览格式

```
** 📋 阶段预览: ANALYSE_TECH（Parallel Agent 调度） **

📌 需求: [需求名称]
🔄 当前阶段: ANALYSE_TECH (3/15)
🚀 调度模式: Parallel Agent 三成员串行协作
🏷️ 团队名称: analyse-tech-[需求ID]

👥 分析团队成员:
  ┌───────────┬──────────────────┬──────────────┬──────────────────┐
  │ 顺序       │ 成员名            │ 职责          │ 依赖              │
  ├───────────┼──────────────────┼──────────────┼──────────────────┤
  │ T1        │ @tech-explorer   │ 技术探索分析   │ 无                │
  │ T2        │ @tech-designer   │ 总纲设计与输出 │ T1               │
  │ T3        │ @tech-splitter   │ 分端文档生成   │ T2               │
  └───────────┴──────────────────┴──────────────┴──────────────────┘

🔄 执行策略:
  - T1 独立执行代码搜索与复用探索（上下文隔离，搜索结果不传递）
  - T2 基于 T1 产出的结构化中间产物进行设计（零搜索，上下文最干净）
  - T3 基于 T2 产出的总纲拆分生成分端文档（零搜索，一致性校验在同一窗口完成）

📥 输入:
  - [产品需求文档路径]

📤 预期输出:
  - analysis/tech-exploration-result.json（中间产物）
  - analysis/tech-requirements.md（总纲）
  - analysis/tech-requirements-{platform}.md（分端文档）
  - analysis/tech-clarify.json（如有）

⚠️ 已知风险: [N] 项

请确认是否执行？[执行 / 取消]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 14. ANALYSE_TECH 阶段 Parallel Agent 进度监控格式

```
** 🔄 ANALYSE_TECH 进度: Parallel Agent **

🏷️ 团队: analyse-tech-[需求ID]
⏱️ 已运行: [时长]

📊 成员状态:
  ✅ @tech-explorer  — 完成 — 耗时 8m — 搜索 85/120 次，评级分布 🟢0 🟡3 🟠5 🔴2 ⚪0
  🔄 @tech-designer  — 执行中 — 已运行 3m — 接口契约定义中...
  ⏳ @tech-splitter  — 等待中 — 依赖 T2 完成

📈 总体进度: [1/3] 成员完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 15. ANALYSE_TECH 阶段 Parallel Agent 总结格式

```
** ✅ 阶段完成: ANALYSE_TECH（Parallel Agent 调度） **

🏷️ 团队: analyse-tech-[需求ID]
⏱️ 总耗时: [时长]
🚀 调度模式: Parallel Agent（3 个成员串行协作）

📊 各成员完成情况:
  ┌────────────────┬──────────┬──────────┬──────────────────────────┐
  │ 成员            │ 耗时     │ 状态      │ 摘要                      │
  ├────────────────┼──────────┼──────────┼──────────────────────────┤
  │ @tech-explorer │ 8m       │ ✅ 完成  │ 搜索 85 次，10 个需求点   │
  │ @tech-designer │ 5m       │ ✅ 完成  │ 6 个 API 契约，评分 4.2   │
  │ @tech-splitter │ 3m       │ ✅ 完成  │ 2 个分端文档，校验全通过   │
  └────────────────┴──────────┴──────────┴──────────────────────────┘

📄 产出物:
  - analysis/tech-exploration-result.json（中间产物）
  - analysis/tech-requirements.md（总纲）
  - analysis/tech-requirements-backend.md（后端）
  - analysis/tech-requirements-web.md（Web 端）
  - analysis/tech-clarify.json（{N} 个澄清问题）

📊 质量门禁: {qualityGate} (评分: {qualityScore}/5.0)
🔄 复用统计: 🟢{a} 🟡{b} 🟠{c} 🔴{d} ⚪{e}
🔗 接口契约: {N} 个 API 定义
📋 平台变更建议: {有/无}

⚠️ 新增风险: [N] 项
📊 总体风险: [N] 项

下一阶段: CLARIFY_TECH
请选择: [确认进入下一阶段 / 回退到上一阶段]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
