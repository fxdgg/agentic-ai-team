---
resource_id: 38
name: git-push-helper
description: "This skill should be used when the user says 'git push', 'push代码', '推送代码', '提交并推送', or any similar phrase indicating they want to save, commit, and push their current changes to a remote Git repository. The skill automatically stages all changes, generates a meaningful commit message by summarizing the current conversation session, and pushes to the remote branch."
---

# Git Push Helper

自动化完成完整的 Git 工作流：扫描 → 暂存 → 提交（AI 生成提交信息）→ 推送。

## 触发条件

当用户的消息匹配以下任一模式时激活此技能：

- `git push`
- `push 代码` / `推送代码`
- `提交并推送` / `提交推送`
- `push to remote` / `push to git`
- 任何表达"保存当前工作并推送到远端"意图的消息

## 工作流

按以下步骤**依次执行**，不得跳过任何步骤。

---

### Step 0: 工作区 Git 仓库扫描与确认

在执行任何 git 操作之前，先扫描当前工作区内存在多少个 Git 仓库，以确定推送目标。

#### 0-1. 扫描 Git 仓库

```bash
# 检查工作区根目录是否在某个 git 仓库内
git -C <workspace_root> rev-parse --show-toplevel 2>/dev/null

# 扫描工作区子目录中的独立 git 仓库（最多 3 层深度，排除 node_modules 等）
find <workspace_root> -maxdepth 3 -name ".git" -type d \
  ! -path "*/node_modules/*" \
  ! -path "*/.codebuddy/*" \
  2>/dev/null | head -20
```

对每个发现的仓库，收集基础信息：

```bash
# 获取仓库名称（目录名）
basename $(git -C <repo_path> rev-parse --show-toplevel)

# 获取当前分支
git -C <repo_path> branch --show-current

# 获取改动文件数量
git -C <repo_path> status --porcelain | wc -l

# 获取远程仓库 URL
git -C <repo_path> remote get-url origin 2>/dev/null
```

#### 0-2. 根据扫描结果分流

| 情况 | 处理方式 |
|------|---------|
| **仅发现 1 个 Git 仓库** | 直接使用该仓库作为推送目标，进入 Step 1（行为与原来一致，用户无感知） |
| **发现多个 Git 仓库** | 向用户展示仓库列表和改动概况，使用 `ask_followup_question` 让用户选择推送目标 |
| **发现 0 个 Git 仓库** | 提示用户"当前工作区未检测到 Git 仓库"，建议执行 `git init` 初始化，然后**停止** |

#### 0-3. 多仓库时的用户选择交互

当检测到多个仓库时，使用 `ask_followup_question` 工具展示选择器。

**选项生成规则**：
- 每个有改动的仓库显示为一个选项，格式：`{仓库名}（{分支名}，{改动数} 个改动）— {远程URL}`
- 没有改动的仓库也列出，标注"无改动"
- 额外提供 "🔄 全部推送 — 依次推送所有有改动的仓库" 选项
- 额外提供 "❌ 取消" 选项

示例：

```
标题: 📦 检测到多个 Git 仓库

问题: 当前工作区包含 3 个 Git 仓库，请选择要推送的目标：

选项:
  - "my-app-frontend（main，5 个改动）— git@github.com:user/frontend.git"
  - "my-app-backend（develop，3 个改动）— git@github.com:user/backend.git"
  - "shared-libs（main，无改动）"
  - "🔄 全部推送 — 依次推送所有有改动的仓库"
  - "❌ 取消 — 不执行推送"
```

**处理用户选择**：
- 选择单个仓库 → 以该仓库路径为目标，执行 Step 1 - Step 8
- 选择"全部推送" → 对每个有改动的仓库**依次**执行 Step 1 - Step 8，最后统一汇总（见 Step 8.2）
- 选择"取消" → 停止，不执行任何操作
- 选择了无改动的仓库 → 告知用户"该仓库当前没有需要提交的更改"，然后**停止**

---

### Step 1: 检查 Git 状态

在选定的仓库中运行 `git status`：

```bash
git -C <repo_path> status --porcelain
```

- 如果**没有改动**（工作区干净，无暂存内容），告知用户："当前没有需要提交的更改。"然后**停止**。
- 如果有改动，继续 Step 2。

---

### Step 2: 暂存所有更改

暂存所有修改、新增和删除的文件：

```bash
git -C <repo_path> add -A
```

**重要**：始终使用 `git add -A` 以确保捕获所有变更（包括新的未跟踪文件和删除操作）。

---

### Step 3: 生成提交信息

根据**当前会话上下文**生成提交信息。提交信息必须：

1. **概述本次会话完成了什么** — 聚焦功能成果，而非实现细节。
2. **遵循 Conventional Commits 格式**：
   - `feat: ...` 新功能
   - `fix: ...` 修复缺陷
   - `refactor: ...` 重构
   - `chore: ...` 维护/配置变更
   - `docs: ...` 文档
   - `style: ...` 格式化
   - `perf: ...` 性能优化
   - `init: ...` 项目初始化
3. **使用中文**编写提交信息正文。
4. **第一行不超过 72 个字符**。
5. 如果有多个不同的变更点，使用多行提交信息：
   ```
   feat: 主要变更摘要

   - 变更点1
   - 变更点2
   - 变更点3
   ```

#### 提交信息生成规则

- 分析会话历史摘要和本次会话中完成的工作。
- 识别工作的**主要类型**（新功能、修复、重构等）。
- 写出其他开发者能理解的简洁摘要。
- 摘要行中**不要**包含文件路径或技术噪音。
- 提交信息中**不要**提及"AI 生成"或"CodeBuddy"。

---

### Step 4: 变更预览与确认

在执行 commit 之前，向用户展示变更预览和生成的提交信息，等待用户确认。

#### 4-1. 展示变更概览

```bash
# 获取变更统计
git -C <repo_path> diff --cached --stat
```

向用户展示：

```
📋 变更预览：

📦 仓库：{仓库名}（{分支名} → origin/{分支名}）
   新增：{N} 个文件
   修改：{M} 个文件
   删除：{D} 个文件

   主要变更文件：
   - src/pages/Register.tsx（新增）
   - src/api/auth.ts（修改）
   - ...

📝 生成的提交信息：
   feat: 新增用户注册页面组件和认证接口
```

#### 4-2. 使用 ask_followup_question 确认

```
问题: 请确认以上变更和提交信息：

选项:
  - "✅ 确认推送"
  - "✏️ 修改提交信息 — 请告诉我你想要的提交信息"
  - "❌ 取消推送"
```

**处理用户响应**：
- "确认推送" → 进入 Step 5
- "修改提交信息" → 等待用户提供新的提交信息，然后进入 Step 5
- "取消推送" → 执行 `git -C <repo_path> reset HEAD` 取消暂存，然后**停止**

> **注意**：当处于"全部推送"模式时（Step 0-3 选择了全部推送），为避免交互过于繁琐，仅展示变更概览，**跳过逐个确认**，直接进入 Step 5。

---

### Step 5: 提交

使用生成（或用户修改）的提交信息执行提交：

```bash
git -C <repo_path> commit -m "<提交信息>"
```

多行提交信息：

```bash
git -C <repo_path> commit -m "<摘要行>" -m "<正文内容>"
```

---

### Step 6: 确定远程分支

检查当前分支及其上游跟踪配置：

```bash
git -C <repo_path> branch --show-current
```

```bash
git -C <repo_path> rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

- 如果上游分支存在，推送到跟踪的远程分支。
- 如果未配置上游分支，使用 `--set-upstream origin <当前分支名>`。

---

### Step 7: 推送

**推送前**，记录当前远端 HEAD 用于后续变更检测（Step 8）：

```bash
git -C <repo_path> rev-parse origin/<当前分支名> 2>/dev/null
```

> 将此值保存为 `<push前远端HEAD>`。如果命令失败（如新分支无远程跟踪），设为空值 — Step 8 将对完整提交范围做 diff。

执行推送：

```bash
git -C <repo_path> push
```

如果无上游分支：

```bash
git -C <repo_path> push --set-upstream origin <当前分支名>
```

---

### Step 8: 检测技能/命令变更并通知

推送成功后，在报告结果**之前**，检查本次推送的提交是否包含**工作流编排技能**或**命令**的变更。

#### 8-1. 检测变更

获取本次 push 涉及的文件变更列表（对比远端分支推送前的 HEAD）：

```bash
git -C <repo_path> diff --name-only <push前远端HEAD> HEAD
```

> 提示：在 Step 7 push 之前，先通过 `git rev-parse origin/<branch>` 记录远端 HEAD，push 成功后用该值做 diff 基准。

检查 diff 文件列表中是否包含以下路径前缀的文件：

- `.codebuddy/skills/workflow-orchestrator/` — 工作流编排专家技能
- `.codebuddy/commands/` — 快捷指令

如果**没有匹配**，跳过通知，直接进入 Step 9。

#### 8-2. 生成变更通知消息

根据匹配到的变更文件，生成消息内容。消息模板如下：

```
🔔 AI 能力更新通知

📦 更新内容：
{变更摘要，用一两句话总述本次更新了哪些能力，例如："工作流编排专家技能的实现阶段规则优化"、"新增 evolve 快捷指令" 等}

👤 提交人：{提交人姓名}
🌿 分支：{branch_name}
⏰ 时间：{当前时间}
```

**提交人获取规则**：
- **来源**：`~/.ai-team/preferences/profile.yaml` 的 `name` 字段（由 `/team-init` 配置）
- **获取方式**：直接读取 `~/.ai-team/preferences/profile.yaml` 文件
- **如果为 null 或文件不存在**：不发送企微通知，在推送报告中标注 "⚠️ 未配置个人信息，企微通知已跳过"
- **用户补救**：建议执行 `/team-init` 完成个人信息配置

**变更摘要生成规则**：
- 结合本次会话的对话上下文，用**简洁自然的中文**描述变更了什么能力
- 如果同时涉及技能和快捷指令的变更，分别描述
- 不要罗列具体文件名，聚焦于功能/能力层面的描述

#### 8-3. 发送企微通知

使用 `send-flow-message` 技能的 `send.py` 脚本发送消息：

```bash
echo '<消息内容>' | python3 skills/send-flow-message/send.py --tag flow-update
```

- **不需要**向用户确认，自动发送
- 如果发送**失败**，仅在最终报告中附加一行提示（如 "⚠️ 企微通知发送失败，不影响代码推送"），**不阻断**后续流程

---

### Step 9: 报告结果

#### 9-1. 单仓库推送报告

推送成功后，向用户展示摘要：

```
✅ 代码已成功推送！

📝 提交信息: <提交信息>
🌿 分支: <分支名>
📦 变更文件: <变更文件数> 个文件（+<新增行数> / -<删除行数>）
🔗 远程仓库: <远程URL>
📢 企微通知: 已发送 / 跳过（无技能/命令变更）
```

如果任何步骤失败，清晰报告错误并建议修复方案。

#### 9-2. 多仓库推送汇总报告

当 Step 0-3 选择了"全部推送"时，所有仓库推送完毕后展示汇总：

```
✅ 推送汇总

📦 my-app-frontend（main）:
   📝 feat: 新增用户注册页面
   📊 5 个文件（+120 / -15）

📦 my-app-backend（develop）:
   📝 feat: 新增用户注册接口
   📊 3 个文件（+80 / -5）

📦 shared-libs（main）:
   ⏭️ 跳过（无改动）

📊 总计: 2 个仓库推送成功，1 个跳过
```

#### 9-3. 附加 MR 创建链接

如果当前分支**不是 `master`**，则在报告末尾额外显示合并请求链接：

```
💡 如需创建合并请求，可访问：https://<remote_host>/<namespace>/<project>/-/merge_requests/new?merge_request[source_branch]=<branch_name>
```

**链接拼接规则**：
- 从远程仓库 URL 中解析出 `<remote_host>`、`<namespace>`、`<project>`（去掉 `.git` 后缀）
  - SSH 格式 `git@<host>:<namespace>/<project>.git` → `https://<host>/<namespace>/<project>`
  - HTTPS 格式 `https://<host>/<namespace>/<project>.git` → `https://<host>/<namespace>/<project>`
- `<branch_name>` 为当前分支名

**条件**：
- 当前分支是 `master` 时，**不显示**此行
- 当前分支是其他任何分支时，**必须显示**此行

---

## 错误处理

- **认证失败**：建议检查 SSH 密钥或凭据配置。
- **合并冲突 / 推送被拒绝**：建议先执行 `git pull --rebase`。
- **未配置远程仓库**：建议执行 `git remote add origin <url>`。
- **游离 HEAD 状态**：警告用户并建议先创建分支。

## 安全规则

- **禁止**使用 `--force` 或 `--force-with-lease`，除非用户明确要求。
- **禁止**在此工作流中修改 `.gitignore` 或其他配置文件。
- **禁止**使用 `--no-verify` 跳过 pre-commit 钩子。
- **必须**在推送前让用户看到生成的提交信息。如果用户反对，允许其修改。
- **必须**使用选定的仓库路径作为 git 命令的工作目录。
