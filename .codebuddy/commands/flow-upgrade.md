---
name: flow-upgrade
description: 工作流版本更新。从 ur-ai-team 远程仓库拉取最新版本，对比差异后选择性更新本地 .codebuddy/ 和 .claude/ 目录（双平台同步）。
---

# 工作流版本更新

## 指令概述

本指令用于将当前项目中的工作流引擎更新到最新版本。**同时更新 `.codebuddy/` 和 `.claude/` 两个目录**，确保用户可以随时在 CodeBuddy IDE 和 Claude Code 之间切换。

通过版本对比展示变更内容，支持全量更新或选择性更新。

**触发方式**：用户手动执行 `/flow-upgrade`

**核心原则**：先对比再更新，用户完全可控。不自动覆盖用户的本地自定义修改。双平台同步更新。

---

## 执行流程

### Step 1：检测当前版本

```
1. 读取 .codebuddy/.ai-team-version 文件（如存在）:
   {
     "commitHash": "abc1234",
     "installedAt": "2026-04-01T10:00:00+08:00",
     "updatedAt": "2026-04-01T10:00:00+08:00",
     "source": "git@git.woa.com:Agentic-CE-Infra/ur-ai-team.git"
   }

2. 如果 .ai-team-version 不存在:
   → 标记为 "未知版本（首次安装或早期版本）"
   → 后续按全量对比处理
```

### Step 2：拉取最新版本

```
1. 确定临时目录: {workspace}/.ai-team-upgrade/
2. 执行浅克隆:
   git clone --depth 1 git@git.woa.com:Agentic-CE-Infra/ur-ai-team.git .ai-team-upgrade/
3. 读取最新版本的 commit hash:
   cd .ai-team-upgrade && git rev-parse HEAD
4. 如果克隆失败:
   → 提示用户检查网络和 SSH 配置
   → 提供手动更新方案: "您也可以手动 git clone 后执行 cp -r 覆盖 .codebuddy/ 和 .claude/"
   → 终止流程
```

### Step 3：对比差异

```
分别对比两个平台目录：

对 .codebuddy/ 和 .claude/ 各执行一次对比：
  远程源: .ai-team-upgrade/.codebuddy/ → 本地目标: .codebuddy/
  远程源: .ai-team-upgrade/.claude/    → 本地目标: .claude/

对每个平台目录:
1. 遍历远程源下的所有文件
2. 按模块分组对比:
   - skills/{skill-name}/      → 每个 Skill 为一个模块
   - commands/                  → 命令集为一个模块
   - rules/{rule-name}/        → 每个 Rule 为一个模块
   - memory/                    → 跳过（不更新，保留用户本地记忆）

3. 对每个模块，标注变更状态:
   - 新增: 远程有、本地无
   - 已更新: 远程和本地都有，但内容不同
   - 无变化: 内容完全一致
   - 本地自定义: 本地有、远程无（用户自行添加的文件）

4. 统计变更文件数量

5. 特殊处理:
   - memory/ 目录始终跳过（组织记忆是项目特有的）
   - .ai-team-version 不计入对比（更新后自动重写）
   - 两个平台的变更合并展示，按模块去重（同一模块在两个平台都有变更只展示一条）
```

### Step 4：展示差异并让用户选择

```
向用户展示变更摘要:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 工作流更新检测
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前版本: {commitHash 前 7 位} ({installedAt})
最新版本: {newCommitHash 前 7 位}

变更摘要:
┌─────────────────────────────┬────────┬──────────────────────────┐
│ 模块                         │ 状态    │ 变更摘要                  │
├─────────────────────────────┼────────┼──────────────────────────┤
│ skills/workflow-orchestrator │ 已更新  │ 3 个文件变更              │
│ skills/knowledge-evolution  │ 已更新  │ 1 个文件变更              │
│ commands/                   │ 已更新  │ 新增 2 个命令             │
│ rules/java-backend          │ 无变化  │ —                        │
│ skills/figma-d2c            │ 无变化  │ —                        │
└─────────────────────────────┴────────┴──────────────────────────┘

新增文件: {N} 个 | 变更文件: {M} 个 | 无变化: {K} 个
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

使用 ask_followup_question 工具让用户选择:

选项:
  - "✅ 全部更新（推荐）— 更新所有变更和新增文件"
  - "🔧 选择性更新 — 选择要更新的模块"
  - "📋 查看详细变更 — 逐文件展示 diff"
  - "❌ 取消更新"
```

**选择性更新模式**：

```
如果用户选择"选择性更新":
  → 使用 ask_followup_question（multiSelect: true）列出所有变更模块
  → 用户勾选要更新的模块
  → 仅更新选中的模块
```

**查看详细变更模式**：

```
如果用户选择"查看详细变更":
  → 逐模块展示文件级 diff（仅展示已更新的文件）
  → 展示完成后回到选择界面
```

### Step 5：执行更新

```
按用户选择的范围，对 .codebuddy/ 和 .claude/ 同时执行文件复制:

1. 对每个选中的模块:
   a) 分别从远程 .codebuddy/ 和 .claude/ 复制到本地对应路径
   b) 新增文件: 直接复制
   c) 变更文件: 覆盖（本地旧版本不备份，可通过 git 恢复）
   d) 本地自定义文件: 保留不动

2. 分别更新两个目录的版本文件:
   更新 .codebuddy/.ai-team-version 和 .claude/.ai-team-version:
   {
     "commitHash": "{newCommitHash}",
     "installedAt": "{原 installedAt 或当前时间}",
     "updatedAt": "{当前 ISO-8601 时间}",
     "source": "git@git.woa.com:Agentic-CE-Infra/ur-ai-team.git"
   }

3. 清理临时目录:
   rm -rf .ai-team-upgrade/
```

### Step 6：验证与报告

```
更新完成后执行验证:

1. 检查关键文件完整性（两个平台都检查）:
   - .codebuddy/skills/workflow-orchestrator/SKILL.md 是否存在
   - .codebuddy/commands/flow-run.md 是否存在
   - .claude/skills/workflow-orchestrator/SKILL.md 是否存在
   - .claude/commands/flow-run.md 是否存在

2. 展示更新报告:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 工作流更新完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

版本: {commitHash 前 7 位} → {newCommitHash 前 7 位}
更新文件: {N} 个 | 新增文件: {M} 个 | 跳过: {K} 个

更新内容:
  ✅ {模块1}: {变更摘要}
  ✅ {模块2}: {变更摘要}
  ⏭️ {模块3}: 用户选择跳过

💡 提示: 更新后建议重新打开 CodeBuddy 以确保新 Skill/Command 被正确加载。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 注意事项

1. **memory/ 目录保护**：更新永远不会覆盖 `.codebuddy/memory/` 和 `.claude/memory/` 目录，组织记忆是项目特有的
2. **本地自定义保护**：用户自行添加的 Skill/Command/Rule 文件不会被删除
3. **版本追踪**：`.ai-team-version` 文件记录安装和更新信息，便于后续增量对比
4. **SSH 优先**：克隆使用 SSH 协议（与 `/flow-import` 的 Git 克隆策略一致）
5. **可回滚**：如果项目本身在 Git 管理下，更新前的文件可通过 `git checkout -- .codebuddy/ .claude/` 回滚
6. **幂等性**：多次执行 `/flow-upgrade` 是安全的，如果已是最新版本会提示无需更新
7. **双平台同步**：无论从哪个 CLI 工具执行，都会同时更新 `.codebuddy/` 和 `.claude/`，确保用户可随时切换工具
