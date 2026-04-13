---
name: evolve-apply
description: 流水线进化落地。仅限流水线 Owner 使用。浏览 evolve-log 中的 pending 改进记录，逐条审阅后选择性地将改进建议落地到 Agent 定义文件和规则文件中。
---

# 流水线进化落地 (Evolve Apply)

## 指令概述

本指令用于**流水线 Owner** 审阅开发者通过 `/evolve` 沉淀的改进记录，选择性地将改进建议**实际落地到 Agent 定义文件和规则文件**中。

**核心原则：Owner 全程掌控，逐条审阅，择优落地。**

> 本指令默认进入**守卫模式**——每一步改动都需要 Owner 确认后执行。

---

## 适用场景

- 定期 review 开发团队沉淀的改进建议
- 挑选高价值改进落地到流水线
- 批量处理积压的 pending 记录

---

## 进化日志位置

```
docs/workflows/evolve-log/
├── pending/          ← 待处理（/evolve-apply 只扫描此目录）
├── applied/          ← 已落地
├── rejected/         ← 已拒绝
└── deferred/         ← 已暂缓
```

> **核心设计**：文件所在子目录即代表状态。`/evolve-apply` **只需扫描 `pending/` 目录**，无需全量遍历和解析 frontmatter。

---

## 执行流程

### Phase 1：浏览改进记录

**目标**：列出所有待处理的改进记录，给 Owner 一个全局视图。

1. **扫描 pending 目录**：只读取 `docs/workflows/evolve-log/pending/` 下的 `.md` 文件（这些就是所有待处理记录，无需解析 frontmatter 判断状态）

2. **统计其他目录**：用 `ls` 快速统计 `applied/`、`rejected/`、`deferred/` 下的文件数量，仅用于概览展示

3. **展示概览**：

   ```
   ## 🧬 进化日志概览

   ### 📋 待处理 (pending/) — N 条
   | # | 文件 | 标题 | 创建日期 | 关联 Agent |
   |---|------|------|---------|-----------|
   | 1 | 20260322-001-xxx.md | xxx | 2026-03-22 | agent-a, agent-b |
   | 2 | 20260323-001-xxx.md | xxx | 2026-03-23 | agent-c |

   ### 其他状态统计
   ✅ 已应用 (applied/): M 条 | ❌ 已拒绝 (rejected/): K 条 | ⏸️ 已暂缓 (deferred/): L 条
   ```

4. **无 pending 记录时**：

   ```
   ## 🧬 进化日志概览

   ✅ 当前没有待处理的改进记录。

   已应用: M 条 | 已拒绝: K 条 | 已暂缓: L 条

   → 开发者可通过 `/evolve` 指令提交新的改进建议。
   ```

   → 流程结束。

5. **有 pending 记录时**：询问 Owner 如何处理

   ```
   共有 N 条待处理记录，请选择处理方式：
   1. 逐条审阅（推荐）
   2. 选择特定记录审阅（输入序号，如 1,3）
   3. 查看全部详情后再决定
   ```

### Phase 2：逐条审阅

**目标**：展示每条改进记录的完整内容，Owner 逐条决策。

对每条 pending 记录：

1. **读取并展示完整内容**：

   ```
   ## 📄 审阅记录 [1/N]

   **文件**：20260322-001-运营端菜单路由缺失.md
   **标题**：运营端菜单路由缺失
   **创建日期**：2026-03-22
   **关联 Agent**：web-developer

   ### Bug 回顾
   {原文}

   ### 根因分析
   {原文}

   ### 改进建议（共 K 条）

   #### 建议 1：{类型} → {目标文件}
   - **当前行为**：{原文}
   - **期望行为**：{原文}
   - **具体修改**：
     ```
     {建议的修改内容}
     ```

   #### 建议 2：...
   ```

2. **请求 Owner 决策**：

   ```
   请对此记录做出决策：
   1. ✅ 接受 — 将改进建议落地到对应文件
   2. ✅ 部分接受 — 选择接受哪些建议（输入建议序号）
   3. ❌ 拒绝 — 标记为 rejected，不做任何修改
   4. ⏸️ 暂缓 — 标记为 deferred，后续再处理
   5. ✏️ 修改后接受 — Owner 提供修改意见，AI 调整后再确认
   ```

3. **记录决策**：不论哪种决策，都通过 `git mv` 将文件移到对应子目录，并同步更新 frontmatter 中的 `status` 字段。

   - **接受/部分接受** → 进入 Phase 3 落地后移到 `applied/`
   - **拒绝** → `git mv pending/{文件}.md rejected/`，更新 frontmatter `status: rejected`
   - **暂缓** → `git mv pending/{文件}.md deferred/`，更新 frontmatter `status: deferred`

### Phase 3：落地执行

**目标**：将 Owner 确认的改进建议实际写入 Agent/Rule 文件。

> ⚠️ **本阶段严格遵循守卫模式**：每个文件修改都先展示 diff 预览，等待 Owner 确认后再执行。

对每条被接受的改进建议：

1. **读取目标文件**：读取建议中指定的 Agent 或 Rule 文件

2. **展示修改预览**：

   ```
   ## ✏️ 修改预览

   **目标文件**：.claude/skills/workflow-orchestrator/agents/web-developer.md
   **改进来源**：evolve-20260322-001

   ### 修改内容：
   在 "## 行为约束" 章节末尾追加：

   + ### 路由注册检查
   + - 新增页面组件时，**必须**同步在路由配置中注册对应路由
   + - 检查父级菜单路由是否已存在，若不存在需一并创建
   + - 路由 path 命名规范：`/{模块名}/{功能名}`

   ---
   确认执行此修改？(y/n)
   ```

3. **执行修改**：Owner 确认后，使用 `replace_in_file` 工具执行修改

4. **更新改进记录状态**：通过 `git mv` 将文件从 `pending/` 移到 `applied/`，同时更新 frontmatter 中的状态字段作为冗余记录

   ```bash
   # 移动文件到 applied/ 目录（状态变更的主要方式）
   git mv docs/workflows/evolve-log/pending/{文件名}.md docs/workflows/evolve-log/applied/
   ```

   同时更新 frontmatter：
   ```yaml
   status: applied          # pending → applied
   applied_date: 2026-03-22
   applied_by: owner
   ```

5. **循环处理**：继续下一条被接受的建议，直到全部处理完毕

### Phase 4：总结报告 + 企微通知

**目标**：汇总本次 apply 的执行结果，并通知团队。

> ⚠️ **CRITICAL**：总结报告和企微通知是一个原子步骤，禁止输出总结后就结束。必须在同一个 Phase 内完成「输出报告 → 发送通知」。

#### 4.1 输出总结报告

```
## 🧬 进化落地总结

### 本次处理结果
| # | 记录 | 决策 | 修改文件 |
|---|------|------|---------|
| 1 | evolve-20260322-001 | ✅ 接受（2/3 条建议） | agents/web-developer.md |
| 2 | evolve-20260323-001 | ❌ 拒绝 | — |
| 3 | evolve-20260323-002 | ⏸️ 暂缓 | — |

### 被修改的流水线文件
- `.claude/skills/workflow-orchestrator/agents/web-developer.md`
  - [+] 新增路由注册检查规则

### 剩余待处理
- pending/: 0 条
- deferred/: 1 条

> 💡 建议：修改后可通过 `/flow-run` 在下一个需求中验证改进效果。
```

#### 4.2 发送企微通知

> 仅在本次**至少有 1 条建议被实际落地**时才发送。全部拒绝/暂缓则跳过此步骤并说明原因。

1. **消息内容模板**（精简版，禁止逐条展开修改详情）：

   ```
   🧬 流水线已更新 · 请同步

   ✅ {N}条改进已落地，涉及{M}个 Agent
   📂 {agent-1中文名}、{agent-2中文名}...
   🌿 分支：{branch}

   ▶ 请及时执行 /flow-upgrade 命令更新本地流水线
   ```

   **字段说明**：
   - `{N}` — 本次实际落地的建议条数
   - `{M}` — 被修改的 Agent/Rule 文件数量
   - `{agent-x中文名}` — 从 Agent 定义文件的标题中提取中文名称（如 `归档总结专家`），超过 3 个时用 `等{M}个文件` 缩略
   - `{branch}` — 当前 Git 分支名，通过 `git branch --show-current` 获取

2. **发送方式**（路径：`.claude/skills/send-flow-message/send.py`）：

   ```bash
   echo '消息内容' | python3 .claude/skills/send-flow-message/send.py --tag evolve-apply
   ```

3. **执行要求**：
   - 消息发送不需要额外确认，在总结报告输出后**立即**触发
   - 如果消息发送失败，向用户报告失败原因，但**不影响**已完成的落地结果

---

## 行为约束

1. **守卫模式全程生效**：每个文件修改必须先展示预览，等 Owner 确认后再执行
2. **只改流水线定义文件**：修改范围限定在 `.claude/skills/workflow-orchestrator/` 下的 Agent 和 Rule 文件
3. **精确修改**：使用 `replace_in_file` 做定向修改，不整体重写文件
4. **状态同步**：每条记录处理完毕立即通过 `git mv` 移到对应子目录，同时更新 frontmatter 中的 status 作为冗余记录
5. **回滚友好**：所有修改都应是可追溯的（git diff 可见），方便 Owner 必要时手动回退
6. **不自行扩展**：严格按照改进记录中的建议执行，不擅自扩展修改范围
7. **不修改进化日志内容**：对 evolve-log 文件只修改 frontmatter 状态字段，不改动正文内容

---

## 使用示例

### 示例 1：常规审阅
```
用户：/evolve-apply
```
→ 列出 pending 记录 → 逐条审阅 → 择优落地 → 汇总报告

### 示例 2：指定记录审阅
```
用户：/evolve-apply 只看今天的记录
```
→ 过滤 2026-03-22 的记录 → 逐条审阅 → 落地

### 示例 3：快速浏览
```
用户：/evolve-apply 有多少条待处理的？
```
→ 仅展示概览统计，不进入审阅流程
