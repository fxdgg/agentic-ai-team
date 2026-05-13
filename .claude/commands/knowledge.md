---
name: knowledge
description: 知识库维护命令。统一入口管理本地和团队知识库，支持状态查看、健康检查、同步、查询、手动添加和提升判定。
---

# 知识库维护

## 指令概述

本指令是知识库维护的**统一入口**，以子命令模式提供知识库的全生命周期管理能力。覆盖 `knowledge-evolution` SKILL 中定义的所有维护操作。

**触发方式**：`/knowledge {子命令}` 或 `/knowledge`（显示子命令列表）

**核心原则**：
- 所有写入操作严格遵循 knowledge-evolution 的结构规范（type/polarity/source/evidence），确保知识库数据质量
- **⚠️ 按需加载**：每个子命令仅加载对应的参考文件，不加载完整的 knowledge-evolution SKILL。参考文件路径为 `skills/knowledge-evolution/references/` 下的模块化文件

---

## 子命令总览

| 子命令 | 用途 | 读/写 | 按需加载的参考文件 |
|--------|------|-------|-------------------|
| `status` | 展示知识库健康状态 | 只读 | `references/architecture.md` |
| `lint` | 执行知识库健康检查（含模块活跃度抑制 + 事实漂移扫描） | 读+写（自动修复） | `references/evolution.md` |
| `sync` | 同步本地与团队知识仓库 | 读+写（Git） | `references/collaboration.md` |
| `query {关键词}` | 查询知识库 | 只读（可触发回流写入） | `references/evolution.md` + `references/consumption.md` |
| `add` | 手动添加知识条目 | 写入 | `references/extraction.md` |
| `fact-check` | 手动触发代码事实校对 | 读+写（front-matter + log.md） | `agents/fact-checker.md` |
| `promote` | 手动触发知识提升判定 | 读+写 | `references/extraction.md` |

> **路径前缀**: 参考文件的完整路径为 `{项目根目录}/.claude/skills/knowledge-evolution/references/{文件名}`。执行子命令前，先 Read 对应的参考文件获取详细规则。

---

## 无子命令时的行为

当用户仅输入 `/knowledge` 不带子命令时，展示子命令列表：

```
使用 AskUserQuestion 工具:

标题: 📚 知识库维护
问题: 请选择要执行的操作：

选项:
  - "📊 status — 查看知识库状态"
  - "🔍 lint — 健康检查与自动修复"
  - "🔄 sync — 同步团队知识仓库"
  - "🔎 query — 查询知识库"
```

第二轮选项：
```
选项:
  - "➕ add — 手动添加知识条目"
  - "🔬 fact-check — 手动触发代码事实校对"
  - "⬆️ promote — 触发知识提升判定"
```

---

## /knowledge status

展示知识库的全局健康状态。

### 执行流程

```
1. 读取团队知识仓库配置:
   - 从 .ai-team/project.yaml 获取 knowledge_repo.local_path
   - 如果未配置 → 提示用户先执行 /team-init

2. 扫描团队知识仓库:
   - tech-wiki/: 统计条目数、按类型分布
   - biz-wiki/{domain}/: 统计各领域条目数
   - team-conventions/: 检查文件存在性
   - 读取 knowledge-catalog.md 获取全景统计

3. 扫描本地项目知识:
   - docs/knowledge-base/: 统计条目数
   - docs/knowledge-import/: 检查导入产物

4. 检查 Git 同步状态:
   - cd {knowledgeRepoLocalPath}
   - git status → 是否有未提交的变更
   - git log origin/main..HEAD → 是否有未推送的提交
   - git log HEAD..origin/main → 是否有未拉取的更新

5. 输出状态报告
```

### 输出格式

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 知识库状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

团队知识仓库: {knowledgeRepoLocalPath}
最后同步: {git log -1 --format=%ci}
同步状态: ✅ 已同步 | ⚠️ 有 {N} 个未推送提交 | ⚠️ 有 {M} 个待拉取更新

条目总数: {N}
┌──────────────┬────────┬──────────┬───────┬───────┐
│ 分类          │ 条目数  │ proven   │ verified │ draft │
├──────────────┼────────┼──────────┼───────┼───────┤
│ tech-wiki    │ {N}    │ {P}      │ {V}   │ {D}   │
│ biz-wiki     │ {N}    │ {P}      │ {V}   │ {D}   │
│ 项目知识库    │ {N}    │ —        │ —     │ —     │
└──────────────┴────────┴──────────┴───────┴───────┘

类型分布:
  model: {N} | decision: {N} | guideline: {N} | pitfall: {N} | process: {N}

贡献统计:
  总贡献者: {N} 人 | 本月新增: {M} 条 | 最近贡献: {name} ({date})

项目画像: {存在/不存在} | 最后更新: {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## /knowledge lint

执行知识库健康检查，调用 knowledge-evolution SKILL.md 6.3 定义的 Lint 规则。

> **⚠️ 上下文隔离**：Lint 需要扫描所有知识条目（可能 100+ 个文件），如果在主对话中逐个 Read 会导致上下文溢出。必须通过子 Agent 执行批量扫描，主对话仅接收检查报告。

### 执行流程

```
1. 加载 Lint 规则:
   → Read 参考文件: skills/knowledge-evolution/references/evolution.md §6.3

2. 收集待扫描目录路径:
   - {knowledgeRepoLocalPath}/tech-wiki/
   - {knowledgeRepoLocalPath}/biz-wiki/{domain}/（可能多个 domain）
   - docs/knowledge-base/

3. 派发子 Agent 执行 Lint 扫描:
   通过 Agent 工具启动子 Agent，prompt 包含:

   ---
   你是知识库 Lint 检查专员。

   任务: 扫描以下知识库目录，执行 9 项健康检查，产出 Lint 报告。

   Lint 规则参考文件: {绝对路径}/skills/knowledge-evolution/references/evolution.md §6.3
   
   待扫描目录:
   - {tech-wiki 绝对路径}
   - {biz-wiki 各 domain 绝对路径}
   - {docs/knowledge-base 绝对路径}
   
   团队配置文件（用于读取阈值）:
   - {knowledgeRepoLocalPath}/.knowledge-config.yaml 的 decay_rules 段
     缺失时默认: knowledge_inactive_months=12, module_active_threshold_months=6, module_dormancy_cap_months=24
   
   项目画像（用于模块活跃度判定）:
   - {knowledgeRepoLocalPath}/project-profiles/*.yaml 的 modules[].last_active_at

   检查项:
   a) 索引不一致: 对比各目录 index.json 与实际文件 → 自动修复
   b) 孤儿条目: related 字段为空且无 verified_in_projects → 标记待审核
   c) 矛盾检测: 同主题多条知识结论相反 → 创建 conflict 标记
   d) 过时检测: draft 且 6 月未引用 → 归档
   e) 导入未验证: imported- 前缀且 3 个工作流未引用 → 降级
   f) 重复/相似检测: 标题或摘要高度重合 → 标记合并候选
      ⚠️ 优化: 先对比 index.json 中的 title/one_line 字段做轻量筛选，仅对疑似重复的条目才 Read 全文对比
   g) 成熟度衰减（含模块活跃度抑制）:
      - proven 条目超过 knowledge_inactive_months 未引用 → 进入衰减判定
      - 派生关联模块（信号: tags 命中 module.name / source_references 路径前缀匹配 module.path / domain 关联）
      - 取关联模块中 last_active_at 最大值作为 most_active_at
      - 若 (now - most_active_at) ≤ module_active_threshold_months → 正常降级 verified
      - 若 module_active_threshold_months < (now - most_active_at) ≤ module_dormancy_cap_months → 抑制降级 + 打标 dormant-module-skipped-decay-at-{ISO}
      - 若 (now - most_active_at) > module_dormancy_cap_months → 强制降级 + 打标 auto-decay-long-dormant-module-at-{ISO}
      - 导入条目（source.trigger=="import"）不参与抑制，按原逻辑降级
      - verified 条目超过 6 月未引用 → 降级 draft（不参与活跃度抑制，直接降）
   h) 事实漂移待审（archiver §17.5 / /knowledge fact-check 已打标的条目）:
      - 扫描 evidence.contradiction_flags 含 "code-fact-drift" 的条目
      - 不自动修复，列入"待人工审核"清单
      - 标注: ID、title、distinct symbols 列表、首次打标日期
   i) 休眠抑制待复查（检查项 g 自动打标的延伸复查）:
      - 扫描 evidence.contradiction_flags 含 "dormant-module-skipped-decay" 的条目
      - 提取首次抑制日期，若距今 > 3 月 → 列入"待人工复查"清单
      - 提示 maintainer 检查关联模块是否仍在业务路线图内；若模块已废弃则手动归档知识

   执行后:
   - 直接修改文件（自动修复项 a/c/d/e + 检查项 g 的降级与打标）
   - 追加记录到 log.md（操作类型: lint / decay / decay-suppressed）
   - 更新各层 index.json 统计数据
   
   完成后汇报（按 evolution.md §6.3 报告格式输出）:
   - 各检查项的发现数量、自动修复数量
   - 💤 因模块休眠被抑制衰减: {S} 条 + 明细（ID/标题/关联模块/最后活跃日期）
   - ⚠️ 代码事实漂移待审: {F} 条 + 明细（ID/标题/缺失符号/打标日期）
   - 需人工处理的条目列表（含矛盾、合并候选、休眠抑制 > 3 月、事实漂移）
   ---

4. 接收子 Agent 报告，展示 Lint 结果给用户
```

---

## /knowledge sync

同步本地知识库与团队知识仓库。

### 执行流程

```
1. 获取知识仓库路径:
   - 从 .ai-team/project.yaml 获取 knowledge_repo.local_path

2. 拉取远程更新:
   cd {knowledgeRepoLocalPath}
   git fetch origin
   git status → 检查是否有本地未提交的变更

3. 处理本地变更（如有）:
   - 自动 commit 本地变更（commit message: "auto: knowledge sync from {project-name}"）
   - 包含 evidence.contributors 信息

4. 合并远程更新:
   git pull --rebase origin main

5. 冲突处理（按 knowledge-evolution §2.6.2 策略）:
   - 纯新增 → 自动合并
   - 证据追加 → 自动合并 evidence 数组
   - 内容矛盾 → 写入 contributions/conflicts/，通知 maintainer
   - 如果 rebase 失败 → 改用 merge，手动标记冲突文件

6. 推送本地变更:
   git push origin main

7. 更新 knowledge-catalog.md（如有变更）

8. 展示同步结果:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 知识库同步完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

拉取: {N} 个新条目 | {M} 个更新
推送: {P} 个本地变更
冲突: {C} 个（已写入 contributions/conflicts/）

新增条目:
  - {ID}: {title} (from {contributor})
  ...

更新条目:
  - {ID}: maturity {old} → {new}
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## /knowledge query {关键词}

查询知识库，遵循 knowledge-evolution SKILL.md 6.5 的 Query 流程。

> **⚠️ 上下文预算**：查询过程需严格控制读取的文件数量，避免沿引用链无限展开导致上下文溢出。

### 执行流程

```
1. 关键词提取:
   - 从用户输入中提取领域、模块、技术栈等关键词

2. 渐进式检索（三级索引，轻量优先）:
   a) 读 {knowledgeRepoLocalPath}/knowledge-catalog.md → 定位相关分类
      （~50 行，全景目录，上下文代价低）
   b) 读对应分类的 catalog.md → 扫描一行摘要，筛选相关条目
      （~100-300 行，按摘要过滤，不读全文）
   c) 读匹配的完整条目 → 获取知识内容
      ⚠️ 上限: 最多读取 **5 个**完整条目。如果匹配超过 5 个，按 maturity 降序取 Top 5，其余仅列出 ID+标题
   d) （可选）读归档产物 → 沿 source_references 获取原始上下文
      ⚠️ 上限: 最多展开 **3 个** SUMMARY.md，每个截取前 100 行
      ⚠️ 禁止递归展开: 不沿 SUMMARY 中的引用继续读取更多文件
   e) 读 docs/workflows/archived/index.md → 搜索历史需求
      ⚠️ 仅读 index.md 本身（摘要级），不逐个读取归档工作流目录

3. 相关性排序:
   - 按 maturity 降序（proven > verified > draft）
   - 按关键词匹配度排序
   - 按 last_referenced 时间排序

4. 答案合成:
   - 基于已读取的 Top 5 条目合成结构化回答 + 引用来源
   - 如果有更多匹配条目未读取，附注: "还有 {N} 条相关知识未展开，可用 /knowledge query --expand 查看"

5. 回流判定（按 SKILL.md §6.5.4）:
   - 合成答案引用了 >= 3 个条目 → 候选回流
   - 用户对回答表示肯定 → 触发回流
   - 回流类型根据内容判定:
     排查类→pitfall，规范类→guideline，概念类→model，流程类→process

6. 输出查询结果（格式遵循 SKILL.md §6.5.3 的报告格式）
```

---

## /knowledge add

手动添加知识条目到知识库。

### 执行流程

```
Step 1: 选择知识类型
  使用 AskUserQuestion:
  标题: ➕ 添加知识条目
  问题: 请选择知识类型：
  选项:
    - "📐 model — 领域模型（实体定义、数据结构、关系图）"
    - "📋 decision — 决策记录（技术选型、架构决策、方案取舍及理由）"
    - "✅ guideline — 行为准则（推荐做法或禁止做法）"
    - "⚠️ pitfall — 已知陷阱（风险、故障模式、排查步骤）"

  第二轮（如果选了 guideline 之外的）:
    - "🔄 process — 流程定义（业务流程、状态机、操作步骤）"

Step 2: 补充字段（根据类型）
  - type=guideline 时追问 polarity: recommend | avoid
  - 标题（title）
  - 一句话摘要（one_line）
  - 适用阶段（applicable_phases，多选）
  - 标签（tags）
  - 内容正文（背景 + 核心内容 + 适用场景）

Step 3: 自动填充元数据
  - id: 按类型缩写 + 序号自动生成（DEC-{seq}, GL-{seq} 等）
  - layer: 默认 project（Layer 3），后续可通过 promote 提升
  - maturity: draft
  - source:
      phase: "manual"
      trigger: "user-add"
      workflow: null
      confidence: 0.7（用户手动输入，比代码推导更可靠）
  - evidence:
      contributors:
        - name: "{从 project.yaml 获取当前用户名}"
          action: "create"
          date: "{当前 ISO-8601}"
          project: "{项目名}"
      verified_in_projects: []
      last_referenced: null

Step 4: 写入知识库
  - 生成条目文件（遵循 knowledge-evolution §4.3 模板）
  - 写入到 docs/knowledge-base/{类型目录}/
  - 更新 docs/knowledge-base/index.json
  - 追加到 log.md:
    ## [{日期}] manual-add | [{用户}] | 手动添加 | +1 {type}
    - 新增 {ID}: {title}

Step 5: 提升判定（自动执行）
  - 对新建条目执行 knowledge-evolution §4.5 的三问决策树
  - 如果符合提升条件:
    → 向用户确认: "此条目可提升到 {Layer 1/Layer 2}，是否提升？"
    → 用户确认后执行提升
    → 追加 promote 记录到 log.md

Step 6: 展示结果
  ✅ 知识条目已添加
  ID: {id} | 类型: {type} | 层级: {layer}
  路径: {文件路径}
  {如有提升: "已提升到 {target-layer}"}
```

---

## /knowledge fact-check

手动触发代码事实校对，调用 `agents/fact-checker.md` 定义的子 Agent，针对指定模块或最近变更的代码做符号级校对，识别因代码演进导致的过时知识。

> **设计来源**：归档时自动触发的 archiver §17.5 是绑定在 ARCHIVE 阶段的；本命令提供 **不依赖 ARCHIVE 的手动触发入口**，便于：
> - 在大规模重构后立即校对（不等到下一次需求归档）
> - 调试 fact-checker 行为（小批量观察）
> - 对特定模块做定向校对

> **⚠️ 上下文隔离**：本命令的实际工作完全在 fact-checker 子 Agent 的独立窗口内完成，主对话仅接收摘要结果（约 500-2K tokens）。

### 执行流程

```
Step 1: 前置检查
  - 从 .ai-team/project.yaml 获取 knowledge_repo.local_path
  - 未配置 → 提示先执行 /team-init 后再使用本命令
  - 读取 {knowledgeRepoLocalPath}/.knowledge-config.yaml 的 fact_check 段
    缺失则用默认: enabled=true, max_entries_per_archive=20, max_symbols_per_entry=5, skip_maturity=[draft]
  - 若 fact_check.enabled=false → 提示用户已禁用，询问是否本次强制执行

Step 2: 选择校对范围
  使用 AskUserQuestion:
  标题: 🔬 代码事实校对
  问题: 请选择校对范围：
  选项:
    - "🆕 最近变更 — 校对最近 N 天内修改过的源码所属模块的关联知识（默认 N=14）"
    - "📁 指定模块 — 输入模块名或路径，仅校对该模块的关联知识"
    - "🔄 继续上次 — 从 .knowledge-lint-state.yaml 的 fact_check_cursor 继续扫描"
    - "🌐 全库轮扫 — 不限定模块，按 cursor 顺序扫描整个知识仓库（开销最大）"

Step 3: 准备 fact-checker 入参
  根据 Step 2 的选择计算 changedFiles[] 和 modules[]：

  分支 a) "最近变更":
    - 用 git log --since="N days ago" --name-only --pretty=format: 获取变更文件列表
    - 去重后作为 changedFiles[]
    - 读取 {knowledgeRepoLocalPath}/project-profiles/{project}.yaml 的 modules[]
    - 仅保留 path 命中 changedFiles[] 前缀的 modules（命中模块集合 M）

  分支 b) "指定模块":
    - 提示用户输入模块名（来自 project-profile.modules[].name）或路径前缀
    - 在该模块路径下执行 search_file 列出所有源码文件作为 changedFiles[]
    - modules[] 仅包含用户指定的模块

  分支 c) "继续上次":
    - 不传 changedFiles 和 modules（fact-checker 自动从 cursor 继续）
    - 注意: cursor 模式下候选范围由上次保存的"全集"决定

  分支 d) "全库轮扫":
    - changedFiles[]=null（特殊值，表示不限定）
    - modules[] = project-profile.modules[] 全部
    - fact-checker 进入"全库扫描模式"：候选集 C = 所有 maturity ∈ {verified, proven} 的条目
    - cursor 同样起作用（按 last_referenced 降序，按 max_entries_per_archive 分批）

Step 4: 派发 fact-checker 子 Agent
  通过 Agent 工具启动子 Agent，prompt 严格按 agents/fact-checker.md 的职责执行:

   ---
   你是代码事实校对专员。
   完整职责与执行规则见 {绝对路径}/skills/workflow-orchestrator/agents/fact-checker.md
   请严格按该文件的 Step A~E 执行。

   入参（手动触发模式）:
   {
     "stateJsonPath": null,                    // 手动触发，无关联工作流
     "workflowId": "manual-{ISO-8601}",        // 用占位符标识
     "knowledgeRepoLocalPath": "{...}",
     "changedFiles": [...],                    // 按 Step 3 计算
     "modules": [...],                         // 按 Step 3 计算
     "sessionHash": "{6 位随机哈希}",
     "config": { ... fact_check 段 ... },
     "triggerSource": "manual-fact-check"      // 区别于 archive 触发
   }

   特殊说明:
   - 由于是手动触发，本次产生的 front-matter 变更与 log.md 写入不会自动随 ARCHIVE 的贡献分支推送
   - 完成后请在返回摘要中标注 cursorUpdated 和 nextCursorPosition，由本命令负责后续 Git 提交
   - log.md 中操作类型使用 "fact-check-manual"（区别于 ARCHIVE 触发的 "fact-check"）

   完成后返回标准摘要结构。
   ---

Step 5: 接收摘要并展示结果
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🔬 代码事实校对结果
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   触发方式: 手动 | 范围: {Step 2 选择}
   涉及模块: {M_names}
   候选条目: {scannedCount} 条（cursor: {start} → {next}）

   ❌ 降级（stale-source-reference）: {downgradedCount} 条
     {ID}: {title} — 缺失文件: {files}
     ...

   ⚠️ 打标待审（code-fact-drift）: {flaggedCount} 条
     {ID}: {title} — 缺失符号: {symbols}
     ...

   📋 弱信号观察（possibly-modified）: {observedCount} 条
   ⏭️  跳过（无可验证符号）: {skippedNoSymbolsCount} 条
   ⚠️ 错误: {errors.length} 条

   详情见: {knowledgeRepoLocalPath}/log.md（操作类型 fact-check-manual）
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 6: Git 提交与推送（手动触发场景的兜底）
  - 若 downgradedCount + flaggedCount > 0:
    询问用户: "本次校对产生了 {N} 条变更，是否立即提交并推送到团队仓库？"
    用户确认后:
      cd {knowledgeRepoLocalPath}
      git checkout -b fact-check/{contributor}/{timestamp}
      git add -A
      git commit -m "fact-check: manual scan from {project} ({downgradedCount} downgrade, {flaggedCount} flag)"
      git checkout main
      git merge fact-check/{contributor}/{timestamp}
      git push origin main
    用户拒绝 → 保留本地变更，提示用户后续可通过 /knowledge sync 推送
  - 若无变更 → 跳过 Git 操作
```

### 何时使用本命令

| 场景 | 推荐选项 |
|------|---------|
| 刚做完一次大规模重构（重命名、文件迁移）| 选 "最近变更"，N 设为重构窗口天数 |
| 怀疑某模块的知识陈旧 | 选 "指定模块" |
| 知识库长期未做事实校对（archiver 路径走得少）| 选 "继续上次" 或 "全库轮扫" |
| 排查 fact-checker 行为（少量样本观察）| 选 "指定模块" + 小模块路径 |

### 与 archiver §17.5 的关系

| 维度 | archiver §17.5（自动）| /knowledge fact-check（手动）|
|------|---------------------|---------------------------|
| 触发时机 | 每次 ARCHIVE 自动 | 用户主动触发 |
| 范围 | 本次工作流变更涉及的模块 | 由用户在 Step 2 选择 |
| Git 提交方式 | 随阶段七 Step 9 贡献分支统一推送 | 本命令 Step 6 单独提交（fact-check/* 分支）|
| log.md 操作类型 | `fact-check` | `fact-check-manual` |
| cursor 共享 | 是 | 是（共享 `.knowledge-lint-state.yaml`）|

两种触发方式**共享同一份 cursor 和扫描状态**，避免重复扫描。手动触发不会破坏 archiver 自动触发的进度。

---

## /knowledge promote

手动触发知识提升判定，扫描 Layer 3 中未提升的条目。

> **⚠️ 上下文隔离**：promote 需要读取所有 Layer 3 条目并逐条分析 + 对比目标层，条目多时会溢出上下文。扫描和分析阶段通过子 Agent 执行，主对话仅接收提升建议列表。

### 执行流程

```
1. 派发子 Agent 执行扫描与分析:
   通过 Agent 工具启动子 Agent，prompt 包含:

   ---
   你是知识提升分析专员。

   任务: 扫描 Layer 3 知识条目，执行三问决策树，生成提升建议报告。

   提升规则参考文件: {绝对路径}/skills/knowledge-evolution/references/extraction.md §4.5
   
   Layer 3 目录: {绝对路径}/docs/knowledge-base/
   Layer 1 目录: {knowledgeRepoLocalPath}/tech-wiki/
   Layer 2 目录: {knowledgeRepoLocalPath}/biz-wiki/

   执行步骤:
   1. 读取 docs/knowledge-base/ 下所有知识条目，过滤 layer=project
   2. 对每条执行三问决策树:
      Q1: 是否包含项目特定代码实现细节？→ 否→Q2, 是→Q3
      Q2: 是否为跨项目通用技术知识？→ 是→候选 Layer 1, 否→Q3
      Q3: 是否为通用业务规则/实体/流程？→ 是→候选 Layer 2, 否→保留 Layer 3
   3. 对候选提升的条目，读取目标层 index.json 检查是否已有相似条目
      ⚠️ 仅读 index.json 中的 title/one_line 字段做轻量对比，不读目标层全文
   
   产出 JSON 报告写入 docs/knowledge-base/_promote-report.json:
   {
     "scannedCount": N,
     "candidates": [
       { "id": "GL-003", "title": "...", "targetLayer": "tech-wiki", "targetDir": "patterns",
         "hasSimilar": false, "similarId": null },
       ...
     ],
     "retained": [
       { "id": "PIT-002", "title": "...", "reason": "含项目特定配置值" }
     ]
   }

   完成后汇报: 扫描条目数、候选提升数、保留数
   ---

2. 读取 _promote-report.json，展示提升建议:
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⬆️ 知识提升建议
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Layer 3 条目总数: {N} | 候选提升: {M}

   可提升到 Layer 1 (tech-wiki):
   ┌────────────┬──────────────────┬──────────┐
   │ ID          │ 标题              │ 目标目录  │
   ...

   可提升到 Layer 2 (biz-wiki):
   ...

   保留在 Layer 3:
   ...

3. 用户确认:
   使用 AskUserQuestion（multiSelect: true）:
   - 列出所有候选提升条目供勾选
   - 默认全选
   - 用户可取消不想提升的条目

4. 派发子 Agent 执行提升写入:
   通过 Agent 工具启动子 Agent，prompt 包含:

   ---
   你是知识提升执行专员。

   任务: 将以下确认的知识条目从 Layer 3 提升到目标层。

   待提升条目: [{id, targetLayer, targetDir, hasSimilar, similarId}, ...]
   Layer 3 目录: {绝对路径}/docs/knowledge-base/
   Layer 1 目录: {knowledgeRepoLocalPath}/tech-wiki/
   Layer 2 目录: {knowledgeRepoLocalPath}/biz-wiki/

   对每个条目:
   a) 如果 hasSimilar=true → 读取目标层的 similarId 条目，合并 evidence
   b) 生成新 ID（TK-{领域}-{序号} 或 BK-{domain}-{类型}{序号}）
   c) 复制/合并条目到目标层
   d) 更新目标层 index.json 和 catalog.md
   e) 更新 Layer 3 原条目（标注 "已提升到 {target-id}"）

   执行后:
   - 追加 promote 记录到 log.md
   - 在 {knowledgeRepoLocalPath} 执行 git add + commit + push

   完成后汇报: 提升数量、各条目的新旧 ID 映射
   ---

5. 接收子 Agent 报告，展示最终结果给用户
```

---

## 注意事项

1. **知识仓库前置**：除 `query` 和 `add` 外，所有子命令需要 `.ai-team/project.yaml` 中配置了 `knowledge_repo.local_path`，未配置时提示执行 `/team-init`
2. **上下文隔离原则**：涉及批量文件扫描的操作（`lint`、`promote`、`fact-check`）**必须通过子 Agent 执行**，主对话仅接收结果报告。直接在主对话中逐个 Read 知识条目会导致上下文溢出
3. **查询预算控制**：`query` 操作严格限制读取文件数量（完整条目 ≤5 个，SUMMARY ≤3 个），禁止递归展开引用链
4. **来源追踪**：所有写入操作自动填充 `source` 元数据（phase/trigger/workflow/confidence），确保可溯源
5. **log.md 只追加**：遵循不可变追加日志原则，所有变更记录到 log.md
6. **Git 工作流**：团队知识仓库的写入通过 Git 分支 + 合并流程，不直接写 main 分支；`fact-check` 手动触发时使用独立 `fact-check/{contributor}/{timestamp}` 分支
7. **成熟度规则**：手动添加的条目初始 maturity 为 draft，需通过工作流引用自动提升
8. **类型规范**：严格使用 5 种知识类型（model/decision/guideline/pitfall/process），guideline 必须指定 polarity
9. **confidence 规则**：手动添加 0.7，导入 0.5，工作流提取 0.7-0.9
10. **衰减判定的双信号原则**：`lint` 和 `archiver §17` 共享时间衰减逻辑（含模块活跃度抑制）；`fact-check` 和 `archiver §17.5` 共享事实信号衰减逻辑。两类信号在 `evidence.contradiction_flags` 中独立留痕，可同时命中
11. **fact-check 与 lint 的分工**：`lint` 仅扫描已存在的 flag（消极扫描）；`fact-check` 主动产出新的 flag（积极扫描）。建议运行节奏: 月度 `lint` + 重构后立即 `fact-check`
12. **cursor 共享**：archiver §17.5 自动触发和 `/knowledge fact-check` 手动触发共享 `.knowledge-lint-state.yaml.fact_check_cursor`，避免重复扫描
