# ARCHITECT_BACKEND — Level 3: 编排器直接执行（兜底模式）

> **加载时机**: Level 2 也失败时，编排器加载此文件作为最终兜底。
> **前置**: 编排器已加载 `architect-backend-rules.md`（主文件）。

---

## 1. 执行策略

```
编排器直接执行流程：

1. 读取可用的中间产物（Level 1/2 可能已产出部分）：
 a) 如果 architecture.md 存在 → 读取作为输入（仅需补全领域文档）
 b) 如果 dependency-graph.md 存在 → 读取作为输入
 c) 如果 priority-list.md 存在 → 读取作为输入
 d) 如果以上均不存在 → 直接读取 tech-requirements.md + tech-requirements-backend.md + state.json

2. 参考 agents/{selected-architect}.md 的核心设计流程，在编排器上下文中执行：
 - 存量代码结构扫描 → 模块依赖分析 → 架构设计 → 领域文档输出
 ⚠️ 注意：编排器上下文有限，设计深度可能不及 Level 1/2，但保证流程不阻断

3. 直接写入最终产物：
 - architecture/backend/architecture.md（如尚不存在）
 - architecture/backend/dependency-graph.md（如尚不存在）
 - architecture/backend/priority-list.md（如尚不存在）
 - architecture/backend/{module}/tech-requirements.md（补全未完成的领域）

4. 更新 state.json: architectBackendMode = "fallback"

5. 进入"总结确认"步骤
```

---

## 2. 限制说明

| 限制 | 说明 |
|------|------|
| 上下文受限 | 编排器上下文已含 SKILL.md 等，留给架构设计的窗口有限 |
| 设计精度降低 | 多领域场景下可能无法完整深度分析，精度最低 |
| 产物质量标注 | 全局架构文档 front-matter 追加 `analysisMode: "fallback"` |
| 流程保障 | 即使精度下降，仍保证有结构化产物输出，不阻断工作流 |

> **注意**: 编排器应在总结确认中向用户明确说明"本次架构设计使用了兜底模式，设计精度可能有所下降，建议仔细审阅产物"。
