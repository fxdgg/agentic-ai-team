# ARCHITECT_BACKEND 阶段 Parallel Agent 输出格式

> **加载时机**: 仅在 ARCHITECT_BACKEND 阶段的预览/进度监控/总结确认时加载。
> **前置依赖**: 需同时加载 `output-formats/common.md`。

---

## 16. ARCHITECT_BACKEND 阶段 Parallel Agent 预览格式

```
** 📋 阶段预览: ARCHITECT_BACKEND（Parallel Agent 调度） **

📌 需求: [需求名称]
🔄 当前阶段: ARCHITECT_BACKEND (5/13)
🚀 调度模式: Parallel Agent 两步模式（全局架构 → 领域确认 → 领域文档并行输出）
🏷️ 团队名称: arch-backend-[需求ID]

👥 架构团队成员:
  ┌───────────┬────────────────────────────────┬──────────┬─────────────┐
  │ 步骤       │ 成员名                          │ 职责      │ 依赖         │
  ├───────────┼────────────────────────────────┼──────────┼─────────────┤
  │ S1        │ @global-architect              │ 全局架构分析 │ 无           │
  │ S1.5      │ 编排器（人工确认）                │ 领域划分确认 │ S1          │
  │ S2-a      │ @domain-architect-common       │ 公共模块文档 │ S1.5        │
  │ S2-b      │ @domain-architect-user-center  │ 用户中心文档 │ S1.5        │
  │ S2-c      │ @domain-architect-product-center│ 商品中心文档 │ S1.5        │
  │ ...       │ ...                            │ ...      │ ...         │
  └───────────┴────────────────────────────────┴──────────┴─────────────┘

🔄 执行策略:
  - Step 1: @global-architect 独占执行全局架构分析
  - 检查点 1: 全局产物落盘（architecture.md + dependency-graph.md + priority-list.md）
  - Step 1.5: 🆕 领域划分确认关卡（展示领域清单 + 治理指标，等待用户确认/调整）
  - 检查点 1.5: domain-registry.json 落盘
  - Step 2: 所有 @domain-architect-* 并行执行领域文档输出
  - 检查点 N: 每个领域文档完成即落盘（中断可恢复）

📥 输入:
  - analysis/tech-requirements.md（总纲）
  - analysis/tech-requirements-backend.md（后端技术需求）

📤 预期输出:
  - architecture/backend/architecture.md
  - architecture/backend/dependency-graph.md
  - architecture/backend/priority-list.md
  - architecture/backend/domain-registry.json（🆕 领域注册表）
  - architecture/backend/{service}/tech-requirements.md × [N]

🔒 检查点保护: 已启用（全局产物 Step 1 完成即落盘，领域确认 Step 1.5 落盘，领域文档逐个落盘）

⚠️ 已知风险: [N] 项

请确认是否执行？[执行 / 取消]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 16.5 ARCHITECT_BACKEND 领域划分确认单格式（Step 1.5）

> **展示时机**: Step 1 全局架构师完成后、Step 2 启动前。此格式专门聚焦领域划分合理性，是防止领域膨胀的核心人工确认点。

```
** 📋 后端领域划分确认（Step 1.5） **

📌 需求: [需求名称]
🏗️ 架构师: [backend-architect / java-architect]
📊 全局分析已完成: architecture.md + dependency-graph.md + priority-list.md ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 领域划分清单:

  ┌────┬──────────────┬────────────────┬──────────┬──────────────┬──────────┐
  │ #  │ 领域 ID       │ 领域名称        │ 包含模块数 │ 预估文件数    │ 治理状态  │
  ├────┼──────────────┼────────────────┼──────────┼──────────────┼──────────┤
  │ 1  │ common       │ 公共基础模块     │ 3        │ 9            │ ✅ 正常   │
  │ 2  │ user-service │ 用户认证服务     │ 2        │ 5            │ ✅ 正常   │
  │ 3  │ game-service │ 游戏房间服务     │ 2        │ 6            │ ✅ 正常   │
  │ 4  │ ai-engine    │ AI 对弈引擎     │ 1        │ 3            │ ⚠️ 合并候选 │
  │ 5  │ game-judge   │ 游戏裁判服务     │ 1        │ 2            │ ⚠️ 合并候选 │
  └────┴──────────────┴────────────────┴──────────┴──────────────┴──────────┘

📊 治理指标:
  - 领域总数: 5 / 8（上限）  ✅
  - 总模块数: 9
  - 总预估文件数: 25
  - 平均每领域模块数: 1.8
  - 平均每领域文件数: 5.0
  - 最小领域文件数: 2（game-judge）
  - 最大领域文件数: 9（common）

⚠️ 治理建议:
  1. ai-engine（1 个模块）和 game-judge（1 个模块）模块数不足 2，
     建议考虑合并为一个「游戏引擎」领域
  
  （若无建议则显示：✅ 所有领域通过治理规则校验，无需调整）

🔗 领域间依赖关系:
  user-service → common
  game-service → common, user-service
  ai-engine → common
  game-judge → common, game-service

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请确认领域划分是否合理？

  [✅ 确认] — 按当前划分继续
  [🔧 调整] — 指定合并/拆分/重命名操作（如：「将 ai-engine 和 game-judge 合并为 game-engine」）
  [🔄 重做] — 重新执行全局架构分析（回到 Step 1）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**调整操作后的重新展示格式**:

```
** 🔧 领域划分调整结果 **

📝 操作记录:
  1. [合并] ai-engine + game-judge → game-engine（游戏引擎）

📋 调整后的领域清单:

  ┌────┬──────────────┬────────────────┬──────────┬──────────────┬──────────┐
  │ #  │ 领域 ID       │ 领域名称        │ 包含模块数 │ 预估文件数    │ 治理状态  │
  ├────┼──────────────┼────────────────┼──────────┼──────────────┼──────────┤
  │ 1  │ common       │ 公共基础模块     │ 3        │ 9            │ ✅ 正常   │
  │ 2  │ user-service │ 用户认证服务     │ 2        │ 5            │ ✅ 正常   │
  │ 3  │ game-service │ 游戏房间服务     │ 2        │ 6            │ ✅ 正常   │
  │ 4  │ game-engine  │ 游戏引擎        │ 2        │ 5            │ ✅ 正常   │
  └────┴──────────────┴────────────────┴──────────┴──────────────┴──────────┘

📊 调整后治理指标:
  - 领域总数: 4 / 8（上限）  ✅（-1）
  - 平均每领域模块数: 2.3（↑0.5）
  - 所有领域通过治理规则校验 ✅

请确认调整后的领域划分？[✅ 确认 / 🔧 继续调整]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 17. ARCHITECT_BACKEND 阶段 Parallel Agent 进度监控格式

```
** 🔄 ARCHITECT_BACKEND 进度: Parallel Agent **

🏷️ 团队: arch-backend-[需求ID]
⏱️ 已运行: [时长]
🔒 检查点: [step 值] — 已落盘 [N] 个产物

📊 成员状态:
  ✅ @global-architect                  — 完成（Step 1）— 耗时 5m — 3 个全局产物已落盘
  ✅ 领域划分确认                        — 已确认（Step 1.5）— domain-registry.json 已落盘
  🔄 @domain-architect-common          — 执行中（Step 2）— 已运行 2m
  🔄 @domain-architect-user-center     — 执行中（Step 2）— 已运行 1m
  ⏳ @domain-architect-product-center  — 执行中（Step 2）— 已运行 1m

📈 总体进度: Step 1 ✅ | Step 1.5 ✅ | Step 2 [0/3] 领域完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 18. ARCHITECT_BACKEND 阶段 Parallel Agent 总结格式

```
** ✅ 阶段完成: ARCHITECT_BACKEND（Parallel Agent 调度） **

🏷️ 团队: arch-backend-[需求ID]
⏱️ 总耗时: [时长]
🚀 调度模式: Parallel Agent 两步模式（1 个全局成员 + [N] 个领域成员）
🔒 检查点: 全部 [N+4] 个产物已安全落盘（含 domain-registry.json）

📊 Step 1 — 全局架构分析:
  ┌────────────────────┬──────────┬──────────┬──────────────────────────┐
  │ 成员                │ 耗时     │ 状态      │ 摘要                      │
  ├────────────────────┼──────────┼──────────┼──────────────────────────┤
  │ @global-architect  │ 5m       │ ✅ 完成  │ 3 个全局产物，无循环依赖   │
  └────────────────────┴──────────┴──────────┴──────────────────────────┘

📊 Step 1.5 — 领域划分确认:
  - 确认方式: 用户确认
  - 领域数量: [N] 个
  - 调整操作: [N] 次（或"无调整"）
  - 治理状态: ✅ 全部通过

📊 Step 2 — 领域文档输出:
  ┌──────────────────────────────────┬──────────┬──────────┬──────────────────────────┐
  │ 成员                              │ 耗时     │ 状态      │ 摘要                      │
  ├──────────────────────────────────┼──────────┼──────────┼──────────────────────────┤
  │ @domain-architect-common         │ 3m       │ ✅ 完成  │ 2 个改动项，1 个新增类     │
  │ @domain-architect-user-center    │ 4m       │ ✅ 完成  │ 5 个改动项，3 个 API 细化  │
  │ @domain-architect-product-center │ 5m       │ ✅ 完成  │ 8 个改动项，4 个 DDL 细化  │
  └──────────────────────────────────┴──────────┴──────────┴──────────────────────────┘

📄 产出物:
  - architecture/backend/architecture.md（全局架构文档）
  - architecture/backend/dependency-graph.md（服务依赖图）
  - architecture/backend/priority-list.md（开发优先级清单）
  - architecture/backend/domain-registry.json（🆕 领域注册表）
  - architecture/backend/{common-module}/tech-requirements.md
  - architecture/backend/{user-center}/tech-requirements.md
  - architecture/backend/{product-center}/tech-requirements.md

🔑 关键决策:
  - [本阶段的关键决策点]

⚠️ 新增风险: [N] 项
📊 总体风险: [N] 项

下一阶段: CLARIFY_ARCH_BACKEND
请选择: [确认进入下一阶段 / 回退到上一阶段]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
