---
name: knowledge
description: 知识库维护命令。统一入口管理本地和团队知识库，支持状态查看、健康检查、同步、查询、手动添加和提升判定。
---

# 知识库维护

## 指令概述

本指令是知识库维护的**统一入口**，以子命令模式提供知识库的全生命周期管理能力。覆盖 `knowledge-evolution` SKILL 中定义的所有维护操作。

**触发方式**：`/knowledge {子命令}` 或 `/knowledge`（显示子命令列表）

**核心原则**：所有写入操作严格遵循 knowledge-evolution 的结构规范（type/polarity/source/evidence），确保知识库数据质量。

---

## 子命令总览

| 子命令 | 用途 | 读/写 |
|--------|------|-------|
| `status` | 展示知识库健康状态 | 只读 |
| `lint` | 执行知识库健康检查 | 读+写（自动修复） |
| `sync` | 同步本地与团队知识仓库 | 读+写（Git） |
| `query {关键词}` | 查询知识库 | 只读（可触发回流写入） |
| `add` | 手动添加知识条目 | 写入 |
| `promote` | 手动触发知识提升判定 | 读+写 |

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

### 执行流程

```
1. 加载知识进化引擎:
   → Skill('knowledge-evolution')

2. 执行 Lint 检查项（按 SKILL.md §6.3）:
   a) 索引不一致检测:
      - 对比 tech-wiki/index.json 与实际文件
      - 对比 biz-wiki/{domain}/index.json 与实际文件
      - 对比 docs/knowledge-base/index.json 与实际文件
      → 自动修复: 补充缺失条目 / 移除悬空引用

   b) 孤儿条目检测:
      - 无交叉引用（related 字段为空）且无 evidence.verified_in_projects
      → 标记为待审核，建议补充关联

   c) 矛盾检测:
      - 同一主题的多条知识，结论相反
      → 创建 conflict 标记，降级 maturity

   d) 过时检测:
      - maturity 为 draft 且 6 个月未引用
      → 自动归档到 archive/ 目录

   e) 导入未验证检测:
      - imported- 前缀条目且连续 3 个工作流未引用
      → 降级 maturity，标记 unvalidated-import

   f) 重复/相似检测:
      - 标题或内容语义高度重合（含跨层重复检测）
      → 标记为合并候选

   g) 成熟度衰减执行:
      - proven 条目 12 月未引用 → 降级为 verified
      - verified 条目 6 月未引用 → 降级为 draft
      → 自动执行降级

3. 追加 Lint 记录到 log.md:
   ## [{日期}] lint | [system] | 定期健康检查 | {变更统计}
   - {修复详情}

4. 更新各层 index.json 统计数据

5. 输出 Lint 报告（格式遵循 SKILL.md §6.3 的报告格式）
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

### 执行流程

```
1. 关键词提取:
   - 从用户输入中提取领域、模块、技术栈等关键词

2. 渐进式检索（三级索引）:
   a) 读 {knowledgeRepoLocalPath}/knowledge-catalog.md → 定位相关分类
   b) 读对应分类的 catalog.md → 扫描一行摘要，筛选相关条目
   c) 读匹配的完整条目 → 获取知识内容
   d) （可选）读归档产物 → 沿 source_references 获取原始上下文
   e) 读 docs/workflows/archived/index.md → 搜索历史需求

3. 相关性排序:
   - 按 maturity 降序（proven > verified > draft）
   - 按关键词匹配度排序
   - 按 last_referenced 时间排序

4. 答案合成:
   - 读取匹配的完整条目
   - 合成结构化回答 + 引用来源

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

## /knowledge promote

手动触发知识提升判定，扫描 Layer 3 中未提升的条目。

### 执行流程

```
1. 扫描 Layer 3 条目:
   - 读取 docs/knowledge-base/ 下所有知识条目
   - 过滤出 layer=project 的条目

2. 对每条执行三问决策树（knowledge-evolution §4.5）:
   Q1: 是否包含项目特定代码实现细节？
     ├─ 否 → Q2
     └─ 是 → Q3
   Q2: 是否为跨项目通用的技术知识？
     ├─ 是 → 候选提升到 Layer 1 (tech-wiki)
     └─ 否 → Q3
   Q3: 是否为通用业务规则/实体/流程？
     ├─ 是 → 候选提升到 Layer 2 (biz-wiki)
     └─ 否 → 保留在 Layer 3

3. 展示提升建议:
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⬆️ 知识提升建议
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Layer 3 条目总数: {N} | 候选提升: {M}

   可提升到 Layer 1 (tech-wiki):
   ┌────────────┬──────────────────┬──────────┐
   │ ID          │ 标题              │ 目标目录  │
   ├────────────┼──────────────────┼──────────┤
   │ GL-003     │ 公共模块兼容检查   │ patterns │
   │ DEC-001    │ Spring Boot 3.x  │ frameworks │
   └────────────┴──────────────────┴──────────┘

   可提升到 Layer 2 (biz-wiki):
   ┌────────────┬──────────────────┬──────────┐
   │ ID          │ 标题              │ 目标领域  │
   ├────────────┼──────────────────┼──────────┤
   │ MOD-001    │ 广告计划实体定义   │ ad       │
   └────────────┴──────────────────┴──────────┘

   保留在 Layer 3:
     PIT-002: 本项目数据库连接池配置（含项目特定配置值）

4. 用户确认:
   使用 AskUserQuestion（multiSelect: true）:
   - 列出所有候选提升条目供勾选
   - 默认全选
   - 用户可取消不想提升的条目

5. 执行提升:
   对每个确认的条目:
   a) 检查目标层是否已有相似条目:
      - 已有 → 合并更新（追加 evidence）
      - 已有且来自不同项目 → maturity 提升为 verified
   b) 生成新 ID（TK-{领域}-{序号} 或 BK-{domain}-{类型}{序号}）
   c) 复制条目到目标层
   d) 更新目标层 index.json 和 catalog.md
   e) 更新 Layer 3 原条目（标注 "已提升到 {target-id}"）

6. 追加 promote 记录到 log.md:
   ## [{日期}] promote | [{用户}] | 知识提升 | +{N} TK, +{M} BK
   - 提升 {old-id} → {new-id} ({target-layer})
   ...

7. 提交并推送到团队知识仓库:
   - git add + commit + push
```

---

## 注意事项

1. **知识仓库前置**：除 `query` 和 `add` 外，所有子命令需要 `.ai-team/project.yaml` 中配置了 `knowledge_repo.local_path`，未配置时提示执行 `/team-init`
2. **来源追踪**：所有写入操作自动填充 `source` 元数据（phase/trigger/workflow/confidence），确保可溯源
3. **log.md 只追加**：遵循不可变追加日志原则，所有变更记录到 log.md
4. **Git 工作流**：团队知识仓库的写入通过 Git 分支 + 合并流程，不直接写 main 分支
5. **成熟度规则**：手动添加的条目初始 maturity 为 draft，需通过工作流引用自动提升
6. **类型规范**：严格使用 5 种知识类型（model/decision/guideline/pitfall/process），guideline 必须指定 polarity
7. **confidence 规则**：手动添加 0.7，导入 0.5，工作流提取 0.7-0.9
