# ARCHIVE 阶段规则（编排器视角）

> **加载时机**：编排器从 TEST 流转到 ARCHIVE 之前（按 SKILL.md §10 阶段规则按需加载映射表）。
>
> **本文件作用**：定义 ARCHIVE 阶段的进入条件、三步模式、严禁操作与漂移防御。具体的归档产物规范（SUMMARY.md 结构、关键词提炼、知识库写入等）由 `agents/archiver.md` 描述，本文件不重复。

---

## 0. 进入条件

ARCHIVE 是工作流的**唯一收尾阶段**。进入 ARCHIVE 的前提是：

1. `state.json.currentPhase == "TEST"`，且 TEST 阶段的"总结确认"已展示给用户
2. 用户在 TEST 总结确认后选择"继续"（无论 qualityGate 为 `pass` / `warn` / `fail`）
3. `references/phase-transitions.json` 中 `TEST.next == "ARCHIVE"`（流转守卫校验）

满足以上三点后，编排器**必须立即**：
- 加载本规则文件（`phases/archive-rules.md`）
- 更新 `state.json.currentPhase` → `ARCHIVE`
- 在 `phaseHistory` 追加 TEST 阶段完成记录
- 进入 ARCHIVE 三步模式的「预览」步骤

> ⚠️ 漂移防御：编排器**不得**在 TEST 总结确认后仅输出"提示进入 ARCHIVE 阶段"的文案就停止动作。文案展示与状态更新必须一并完成。详见 `agents/test-engineer.md` §「TEST 完成后的流转指令」。

---

## 1. 三步模式

ARCHIVE 阶段同样遵循 **预览 → 执行 → 总结确认** 三步模式。

### Step 1：预览（编排器执行）

展示即将执行的归档动作概要，等待用户确认：

```
即将执行 ARCHIVE 阶段（归档总结）：

📦 归档动作：
  1. 提炼功能关键词，生成 SUMMARY.md
  2. 移动需求目录 docs/workflows/{需求ID}/ → docs/workflows/archived/{需求ID}/
  3. 移动原始 PRD 文档 docs/prd/{prd}.md → docs/prd/archived/{prd}.md
  4. 追加项目经验到 docs/knowledge-base/pitfalls/
  5. 触发知识库 lint 校验（fact-checker 子 Agent）
  6. 更新 state.json.currentPhase → DONE
  7. 发送 workflow_done 归档通知（如启用）

📂 涉及文件：
  - prdSource: {state.json.prdSource}
  - 工作流目录: docs/workflows/{需求ID}/
  - 知识库目录: docs/knowledge-base/

⏱️  预计耗时：30 秒 ~ 2 分钟（取决于知识库 lint 范围）

请确认是否进入归档？(y/n)
```

> 用户输入 `n` / 「回退」 → 见 §2.2 回退行为。

### Step 2：执行（调用 archiver Agent）

调用 `agents/archiver.md` 中定义的归档总结专家 Agent，传入：

- `state.json` 路径
- 需求目录路径（`docs/workflows/{需求ID}/`）
- 原始 PRD 文件路径（`state.json.prdSource`）
- 知识库路径（`docs/knowledge-base/`）

archiver Agent 内部会自行调度：
- §16 自动 Lint 触发 → 派发 Lint 子 Agent
- §17 proven 时间衰减
- §17.5 代码事实校对 → 派发 fact-checker 子 Agent（独立上下文窗口）

详见 `agents/archiver.md`。

### Step 3：总结确认（编排器执行）

展示归档结果摘要：

```
✅ ARCHIVE 阶段完成

📄 归档产物：
  - SUMMARY.md：{N} 个功能关键词 / {M} 条经验 / {K} 条 pitfall
  - 需求目录已移动：docs/workflows/archived/{需求ID}/
  - PRD 已归档：docs/prd/archived/{prd}.md
  - 知识库写入：{X} 条新增 / {Y} 条更新

🧪 知识库 Lint：{通过 / 警告 N 项 / 失败 N 项}
🔍 代码事实校对：{通过 / 警告 N 项}

🎉 工作流已完成（state.json.currentPhase = DONE）
```

发送 `workflow_done` 通知（详见 SKILL.md §12.3.3）。

---

## 2. 状态机约束

### 2.1 currentPhase 终态写入

**只有 archiver Agent 才能将 `state.json.currentPhase` 设为 `DONE`**（详见 SKILL.md §2.2 流转守卫）。

- 编排器在 ARCHIVE 阶段**不得**自行将 `currentPhase` 设为 `DONE`
- archiver Agent 的写入时机：所有归档动作（含目录移动、知识库写入、lint）成功完成后
- 若归档过程中 archiver 因故失败 → `currentPhase` 保持 `ARCHIVE` 不变，进入 §2.2 回退或重试

### 2.2 回退行为

| 场景 | 处理 |
|------|------|
| 用户在 ARCHIVE 预览选择"回退" | 回退到 TEST 阶段；不删除 `testing/` 产物（与 TEST→E2E_VERIFY 回退不同，ARCHIVE→TEST 是"查看而不重做"，archiver 尚未执行任何写动作） |
| archiver 执行中失败（目录移动冲突 / 知识库写入失败 / lint 异常） | `currentPhase` 保持 `ARCHIVE`；展示失败摘要；用户可选"重试归档"或"回退到 TEST" |
| archiver 已完成目录移动但知识库写入失败 | 视为部分成功；保留 `currentPhase = ARCHIVE`；提示用户手动检查知识库后重试，**不得**自动回滚目录移动 |

---

## 3. 严禁操作（CRITICAL）

- ❌ 不得在编排器层将 `currentPhase` 直接设为 `DONE`（违反 SKILL.md §2.2）
- ❌ 不得跳过 ARCHIVE 阶段直接结束工作流
- ❌ 不得在 archiver 执行失败时强行将 `currentPhase` 写为 `DONE` 以"绕过失败"
- ❌ 不得修改任何源码文件、架构文档、分析文档（archiver 仅有 SUMMARY.md / 目录移动 / 知识库写入 三类写权限，详见 `agents/archiver.md` §「权限边界」）
- ❌ 不得在归档完成前发送 `workflow_done` 通知（必须在 archiver 完成 + currentPhase 已写为 DONE 之后）

---

## 4. 与其他规则的引用关系

| 引用对象 | 用途 |
|---------|------|
| `agents/archiver.md` | ARCHIVE 阶段执行体 Agent 定义 + 三步模式细节 + 权限边界 |
| `references/phase-transitions.json` | `TEST.next = ARCHIVE` / `ARCHIVE.next = DONE` 流转守卫校验 |
| `phases/rollback-rules.md` | ARCHIVE → TEST 回退时通用规则 |
| SKILL.md §2.2 | 流转守卫（ARCHIVE 是 DONE 写入的唯一入口） |
| SKILL.md §12.3.3 | `workflow_done` 通知触发协议 |

---

## 5. 完成检查清单

ARCHIVE 阶段视为完成的判定：

- [ ] `SUMMARY.md` 已在需求目录根下生成
- [ ] 需求目录已移动至 `docs/workflows/archived/`
- [ ] 原始 PRD 已移动至 `docs/prd/archived/`
- [ ] `docs/knowledge-base/pitfalls/` 已追加经验条目（如有）
- [ ] 知识库 Lint 已执行（pass / warn 均允许，fail 需用户确认）
- [ ] `state.json.currentPhase` 已由 archiver 写为 `DONE`
- [ ] phaseHistory 已追加 ARCHIVE 阶段完成记录
- [ ] `workflow_done` 通知已发送（如启用）
