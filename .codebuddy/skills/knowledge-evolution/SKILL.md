---
name: knowledge-evolution
description: "知识进化引擎。当用户提到项目知识沉淀、经验总结、最佳实践提取、历史复盘、模式学习、知识图谱、技术决策记录、团队知识库时触发此技能。自动从已完成的工作流中提取可复用的知识模式，持续进化项目团队的集体智慧。"
---

# 知识进化引擎

## 1. 角色定位

本技能是 **团队知识的自动提炼与持续进化系统**。核心职责：

- **提取**从已完成工作流中自动提取可复用的知识模式
- **沉淀**将零散的项目经验结构化为团队共享知识库条目
- **进化**基于新的工作流成果持续更新和修正已有知识
- **推送**在合适的时机向相关 Agent 推荐已沉淀的知识
- **协作**支持团队成员共建知识库，自动处理并发贡献冲突

> **关键原则：知识进化是被动提取 + 主动推送，不干预工作流执行本身。知识库为团队共建共享，通过独立 Git 仓库管理。**

---

## 2. 知识体系架构

```
知识进化引擎
├── 知识提取层 (Extraction)
│   ├── 工作流产物分析器
│   ├── 代码模式识别器
│   └── 决策链路追踪器
│
├── 知识存储层 (Storage)
│   ├── Layer 0-P — 个人偏好 (~/.ai-team/preferences/)（纯本地，不共享）
│   ├── Layer 0-T — 团队约定 ({knowledge-repo}/team-conventions/)
│   ├── Layer 1 — 技术知识 ({knowledge-repo}/tech-wiki/)
│   ├── Layer 2 — 业务知识 ({knowledge-repo}/biz-wiki/{domain}/)
│   └── Layer 3 — 项目上下文 ({project}/.ai-team/)
│
└── 知识推送层 (Delivery)
    ├── 多层合并查询推荐
    ├── 新 Agent 启动注入
    └── 回顾报告生成
```

### 2.5 团队共享知识架构

> **核心理念**：知识库为团队共建共享，存储在独立 Git 仓库中。所有使用 ai-team 工作流的团队成员都能贡献和消费知识。个人偏好保留在本地，不共享。

知识按作用范围分为五层，存储在不同位置：

| 层级 | 位置 | 内容 | 作用域 | 共享方式 |
|------|------|------|--------|---------|
| Layer 0-P | `~/.ai-team/preferences/` | 个人偏好（编码风格、工具偏好） | 个人专属 | 不共享，纯本地 |
| Layer 0-T | `{knowledge-repo}/team-conventions/` | 团队约定（代码规范、Review标准） | 团队共享 | Git push/pull |
| Layer 1 | `{knowledge-repo}/tech-wiki/` | 技术知识（语言/框架/模式/反模式） | 团队共享，按技术栈过滤 | Git push/pull + 冲突解决 |
| Layer 2 | `{knowledge-repo}/biz-wiki/{domain}/` | 业务知识（实体/规则/流程/踩坑） | 团队共享，按业务领域过滤 | Git push/pull + 冲突解决 |
| Layer 3 | `{project}/.ai-team/` | 项目上下文（配置/缓存/本地约定） | 仅当前项目 | 跟随项目仓库 |

> `{knowledge-repo}` = `project.yaml` 中 `knowledge_repo.local_path` 指定的本地路径（通常为 `~/.ai-team/team-knowledge`）

**运行时查询优先级**：Layer 3 > Layer 2 > Layer 1 > Layer 0-T > Layer 0-P

**知识仓库结构**：
```
{knowledge-repo}/                          # 独立 Git 仓库
├── .knowledge-config.yaml                 # 团队配置（成员、冲突策略）
├── team-conventions/                      # Layer 0-T: 团队约定
│   ├── coding-standards.md
│   ├── commit-conventions.md
│   └── log.md
├── tech-wiki/                             # Layer 1: 技术知识
│   ├── index.md / index.json / log.md
│   ├── languages/ / frameworks/ / patterns/ / devops/ / anti-patterns/
├── biz-wiki/                              # Layer 2: 业务知识
│   ├── domains.yaml
│   ├── _cross-domain/
│   └── {domain}/ (index.md / index.json / log.md / entities/ / relations/ / rules/ / flows/ / pitfalls/)
└── contributions/                         # 贡献暂存区
    ├── pending/                            # 待合并的贡献清单
    └── conflicts/                         # 检测到的冲突
```

### 2.6 团队协作机制

#### 2.6.1 贡献模式 — "贡献暂存 + 异步合并"

借鉴区块链三个核心思想，但使用 Git 作为实现载体：

| 区块链思想 | ai-team 实现 | 机制 |
|-----------|-------------|------|
| 不可篡改的追加日志 | log.md 只追加不修改 | 每条变更记录贡献者、时间、会话哈希 |
| 贡献可溯源 | evidence.contributors[] | 类似 Git blame，粒度为知识条目级 |
| 共识机制 | maturity 多人验证提升 | draft→verified: 1人验证; verified→proven: ≥2人+≥2项目 |

#### 2.6.2 冲突解决流程

当多名团队成员同时执行 ARCHIVE 并推送知识时，按以下策略自动处理：

| 冲突类型 | 描述 | 处理方式 |
|---------|------|---------|
| **纯新增** (additive) | 两人加了不同的知识条目 | 自动合并，两条都保留 |
| **证据追加** (evidence_append) | 两人验证了同一条知识 | 自动合并，evidence 数组合并去重 |
| **成熟度提升** (maturity_upgrade) | 一人触发了 draft→verified | 自动合并 |
| **内容矛盾** (content_conflict) | 同一条目内容相反 | 写入 contributions/conflicts/，通知 maintainer 裁决 |
| **成熟度冲突** (maturity_conflict) | 一人升级一人降级 | 保留较低成熟度 + 标记 contradiction |

#### 2.6.3 团队角色

| 角色 | 权限 | 适用人群 |
|------|------|---------|
| `maintainer` | 解决 content_conflict、审批 proven 提升、管理成员 | 团队负责人 |
| `contributor` | 通过工作流自动贡献（create/verify/flag_contradiction） | 正式成员 |
| `reader` | 只消费知识（查询/注入），不贡献 | 新成员试用期 |

#### 2.6.4 知识条目团队化 front-matter

```yaml
evidence:
  contributors:                            # 所有贡献者（区块链签名链）
    - name: "Steven"
      action: "create"
      date: "2026-04-09"
      project: "cloud-mall"
      workflow: "20260409-商品分类优化"
    - name: "Alice"
      action: "verify"
      date: "2026-04-12"
      project: "vibe-mall"
      workflow: "20260412-商品列表优化"
  verified_in_projects: ["cloud-mall", "vibe-mall"]
  last_referenced: "2026-04-12"
  contradiction_flags: []
```

**知识条目 ID 前缀规则**：
- Layer 1 技术知识：`TK-{领域}-{序号}`（如 TK-SB-001, TK-JAVA-002）
- Layer 2 业务知识：`BK-{domain}-{类型}{序号}`（如 BK-ECOM-E001, BK-ECOM-BR001）
- Layer 3 项目知识：沿用原 `{TYPE}-{序号}` 格式（如 ADR-001, BP-001）

---

## 3. 知识分类

### 3.1 知识类型定义

| 类型 ID | 名称 | 来源 | 成熟度 | 示例 |
|---------|------|------|--------|------|
| `adr` | 架构决策记录 | ARCHITECT_* 阶段产物 | draft → verified → proven | "为什么选择事件驱动而非 RPC 同步" |
| `best-practice` | 最佳实践 | IMPLEMENT + BUILD_VERIFY 成功模式 | draft → verified → proven | "公共模块变更后的兼容性检查清单" |
| `anti-pattern` | 反模式警告 | BUILD_VERIFY 回退 + 修复记录 | draft → verified → proven | "循环依赖导致编译失败的常见场景" |
| `faq` | 常见问题 | CLARIFY_* 阶段回填内容 | draft → verified → proven | "跨租户数据隔离的标准问答" |
| `template-evolution` | 模板进化 | 多次工作流对比 | draft → verified → proven | "domain-tech-requirements 模板新增字段" |
| `risk-pattern` | 风险模式 | risks.json 统计分析 | draft → verified → proven | "涉及支付模块时必检查的风险清单" |

**三级成熟度定义**：
- `draft`: 导入或新提取，仅有单一来源
- `verified`: 至少在 1 个工作流中被成功使用且无矛盾
- `proven`: 在 ≥2 个不同项目中被验证

### 3.2 知识存储结构（团队共享架构）

> 以下路径中 `{knowledge-repo}` 指 `.ai-team/project.yaml` 中 `knowledge_repo.local_path` 指向的本地克隆路径。

**Layer 1 — 技术知识**（团队共建）：
```
{knowledge-repo}/tech-wiki/
├── index.md / index.json / log.md
├── languages/{lang}/TK-{LANG}-{seq}.md
├── frameworks/{framework}/TK-{FW}-{seq}.md
├── patterns/TK-PAT-{seq}.md
├── devops/TK-OPS-{seq}.md
└── anti-patterns/TK-AP-{seq}.md
```

**Layer 2 — 业务知识**（团队共建，每个领域独立 Wiki）：
```
{knowledge-repo}/biz-wiki/{domain}/
├── index.md / index.json / log.md
├── entities/BK-{DOM}-E{seq}.md         # 业务实体
├── relations/entity-graph.md            # 实体关系图（Mermaid）
├── rules/BK-{DOM}-BR{seq}.md           # 业务规则
├── flows/BK-{DOM}-F{seq}.md            # 业务流程
└── pitfalls/BK-{DOM}-P{seq}.md         # 业务踩坑
```

**Layer 3 — 项目上下文**（保持项目内）：
```
{project}/docs/knowledge-base/          # 项目特有，不适合提升的知识
{project}/docs/knowledge-import/        # 导入产物缓存
```

### 3.3 三层渐进式索引（LLM Wiki 模式增强版）

> **设计来源**：借鉴 Karpathy 的 LLM Wiki Pattern，增强为三层渐进式加载。Agent 不再被动接收 Top-N 推送，而是主动按需查阅——先看目录，再看清单，最后读完整条目。

#### Layer A — 知识全景目录（knowledge-catalog.md）

**位置**：`{knowledge-repo}/knowledge-catalog.md`（团队仓库根目录）
**大小**：≤50 行，Agent 零成本读取
**维护方**：archiver 每次 ARCHIVE 完成后自动重新生成

格式：
```markdown
# 团队知识库全景目录

> 最后更新: {ISO-8601} | 总条目: {N} | proven: {P} | verified: {V} | draft: {D}

## 按阶段推荐

| 你当前阶段 | 推荐查阅 | 路径 |
|-----------|---------|------|
| ANALYSE_PRODUCT | 业务规则、实体关系、历史需求 | biz-wiki/{domain}/catalog.md |
| ANALYSE_TECH | 技术决策、框架经验、反模式 | tech-wiki/catalog.md |
| ARCHITECT | ADR、架构模式、实体关系图 | tech-wiki/patterns/catalog.md + biz-wiki/{domain}/relations/ |
| IMPLEMENT | 最佳实践、反模式、编码规范 | tech-wiki/catalog.md + team-conventions/ |
| BUILD_VERIFY | 反模式、已知编译问题 | tech-wiki/anti-patterns/catalog.md |

## 知识库统计

| 分类 | 条目数 | proven | 路径 |
|------|--------|--------|------|
| {分类名} | {N} | {P} | {catalog.md 路径} |

## 项目级知识

| 分类 | 条目数 | 路径 |
|------|--------|------|
| 项目知识库 | {N} | docs/knowledge-base/index.md |
| 归档工作流 | {N} | docs/workflows/archived/index.md |
| 项目记忆 | {N} | .codebuddy/memory/ |
```

#### Layer B — 分类清单（catalog.md）

**位置**：每个知识子目录下都有一个 `catalog.md`
```
tech-wiki/catalog.md
tech-wiki/frameworks/catalog.md
tech-wiki/anti-patterns/catalog.md
biz-wiki/{domain}/catalog.md
biz-wiki/{domain}/entities/catalog.md
biz-wiki/{domain}/rules/catalog.md
```

**大小**：每个 ≤300 行（每条知识一行摘要）
**维护方**：知识条目新增/更新时同步维护

格式：
```markdown
# {分类名}知识清单

> 条目数: {N} | proven: {P} | verified: {V} | draft: {D}

## {子分类} — {M} 条

| ID | 标题 | 成熟度 | 标签 | 适用阶段 |
|----|------|--------|------|---------|
| TK-SB-001 | 多租户拦截器设计模式 | proven | #multi-tenant #spring-boot | ARCHITECT |
| TK-SB-002 | Optional依赖传递陷阱 | verified | #dependency | IMPLEMENT |
```

**关键字段：`适用阶段`** — 阶段感知维度。Agent 读 catalog.md 时可按当前阶段快速过滤。

#### Layer C — 完整知识条目

即现有的 TK-*.md、BK-*.md 等文件，Agent 按需读取。

#### 归档工作流索引（archived/index.md）

**位置**：`docs/workflows/archived/index.md`
**维护方**：archiver 每次归档时自动追加

格式：
```markdown
# 归档工作流索引

> 总数: {N} | 最后更新: {ISO-8601}

## 按功能域分类

### {功能域名} ({M} 个需求)
| 需求ID | 名称 | 关键词 | 平台 | 归档日期 | SUMMARY路径 |
|--------|------|--------|------|---------|------------|
| {ID} | {名称} | {keywords} | {platforms} | {日期} | archived/{ID}/SUMMARY.md |
```

Agent 通过此索引定位相关历史需求，然后按需读取 SUMMARY.md 正文或 architecture.md。

**维护规则**：
- 每次 ARCHIVE 完成时追加当前需求到 index.md
- index.md 按功能域和技术主题双维度分类
- 追加而非重写，保持高效

#### log.md — 追加式变更时间线

所有知识变更事件按时间追加记录，支持 `grep "^## \[" log.md | tail -10` 快速检索：

```markdown
# Knowledge Evolution Log

## [2026-04-09] ingest | [Steven] | 门店履约视图归档 | +1 ADR, +2 BP | #a3f8c2
- 新增 ADR-005: 地图组件选型（腾讯地图 GL JS SDK）
- 新增 BP-012: fitBounds 在 flexbox 布局中的替代方案
- 更新 BP-003: 公共模块变更检查清单（新增地图依赖检查项）

## [2026-04-08] ingest | [Alice] | 商详页UI重构归档 | +1 BP, +1 TE | #b4e9d1
- 新增 BP-011: CSS 变量双轨方案（品牌色 CSS 变量 + 文字色 SCSS 变量）
- 新增 TE-002: 小程序纯前端需求交付模板 v2

## [2026-04-08] lint | [system] | 定期健康检查 | -2 archived
- 归档 FAQ-003: 已 6 个月未引用
- 归档 IMP-BP-002: 导入知识未通过验证

## [2026-04-09] promote | [Steven] | 技术知识提升 | +2 TK, +1 BK | #a3f8c2
- 提升 BP-012 → TK-MAP-001 (Layer 1 tech-wiki)
- 提升 ADR-005 → TK-MAP-002 (Layer 1 tech-wiki)
- 提升 BP-008 → BK-ECOM-BR001 (Layer 2 biz-wiki/ecommerce)

## [2026-04-12] verify | [Alice] | 跨项目验证 | maturity↑ 2 | #c5f0e2
- TK-SB-003 "分页查询延迟关联优化" (verified→proven, 2 projects)
```

**维护规则**：
- 每次知识变更（新增/更新/归档/Lint/提升）追加一条记录
- 格式：`## [{日期}] {操作类型} | [{贡献者}] | {摘要} | {变更统计}`
- 操作类型：`ingest`（提取）、`update`（更新）、`lint`（健康检查）、`query-backfill`（查询回流）、`promote`（知识提升）
- 仅追加，不修改历史记录（区块链不可变日志思想）
- 每条记录带会话哈希，可追溯到具体工作流

---

## 4. 知识提取规则

### 4.1 自动提取触发点

| 触发时机 | 提取内容 | 输出知识类型 |
|---------|---------|-------------|
| 工作流进入 ARCHIVE 阶段 | 全流程回顾分析 | adr, best-practice, risk-pattern |
| CLARIFY_* 阶段完成 | 澄清问答对提取 | faq |
| BUILD_VERIFY 回退 ≥2 次 | 失败模式分析 | anti-pattern |
| IMPLEMENT 阶段完成 | 代码模式提取 | best-practice |
| 同类需求完成 ≥3 个 | 跨需求模式对比 | template-evolution, best-practice |

### 4.2 提取流程

```
工作流完成 (ARCHIVE)
    │
    ├──→ 步骤 1: 收集本次工作流的全部产物
    │     - analysis/*.md (需求分析文档)
    │     - architecture/**/*.md (架构设计文档)
    │     - implementation/**/*-report.md (实现报告)
    │     - testing/*.md (测试文档)
    │     - state.json (状态历史)
    │     - risks.json (风险记录)
    │
    ├──→ 步骤 2: 分析决策链路
    │     - 提取架构决策点及其理由
    │     - 识别需求澄清中的关键问答
    │     - 记录编译回退的根因和修复方案
    │
    ├──→ 步骤 3: 对比已有知识库（三层扫描）
    │     - Layer 3: {project}/docs/knowledge-base/ 中查找相似条目
    │     - Layer 2: {knowledge-repo}/biz-wiki/{domain}/ 中查找相似条目
    │     - Layer 1: {knowledge-repo}/tech-wiki/ 中查找相似条目
    │     - 如果有 → 更新/合并（知识进化）
    │     - 如果没有 → 新建条目
    │
    ├──→ 步骤 4: 生成知识条目
    │     - 结构化写入到 docs/knowledge-base/（Layer 3）
    │     - 更新 index.json 索引
    │     - 输出提取摘要报告
    │
    └──→ 步骤 5: 知识提升判定（§4.5）
          - 对每条新提取的知识执行提升判定
          - 符合条件的提升到 Layer 1 或 Layer 2
```

### 4.3 知识条目模板

```markdown
---
id: {ID}
layer: tech | biz | project
domain: {domain-id 或 null}
title: {标题}
one_line: {一句话摘要，用于 catalog.md 展示}
applicable_phases: [ANALYSE_TECH, IMPLEMENT]   # 适用的工作流阶段
created: {ISO-8601}
updated: {ISO-8601}
maturity: draft | verified | proven
evidence:
  contributors:
    - name: "{贡献者姓名}"
      action: "create"
      date: "{ISO-8601}"
      project: "{项目名}"
      workflow: "{需求ID}"
  verified_in_projects: ["{项目名}"]
  last_referenced: null
  contradiction_flags: []
source_references:                             # 原始产物引用（可追溯完整上下文）
  - path: "docs/workflows/archived/{需求ID}/architecture/backend/architecture.md"
    section: "{章节标题}"
    context: "{引用上下文简述}"
tags: ["{标签}"]
related: ["{关联ID}"]
---

# {标题}

## 背景

{知识产生的背景和上下文}

## 内容

{知识的核心内容}

## 适用场景

{什么情况下应该使用这个知识}

## 相关知识

- [{关联知识ID}]({相对路径})
```

**新增字段说明**：
- `one_line`：一句话摘要，用于 catalog.md 清单中的展示（≤100 字），让 Agent 不读完整条目也能判断相关性
- `applicable_phases`：知识在哪些工作流阶段最有用。Agent 读 catalog.md 时按当前阶段过滤
- `source_references`：指向原始归档产物（架构文档、SUMMARY.md 等）。Agent 需要更多细节时可沿引用深入读取，避免知识摘要丢失推导过程

### 4.4 导入知识的进化策略

> 当工作流在已有导入知识（`evidence.source_projects` 包含 `imported-*` 前缀）的项目上完成时，执行以下特殊进化逻辑。

#### 4.4.1 验证与提升

将工作流中实际使用的技术决策与导入的 ADR 条目对比：

```
对比流程:
1. 从 ARCHITECT_BACKEND 产物中提取实际技术决策
2. 搜索 docs/knowledge-base/adr/ 下 ID 含 "IMP" 的条目
3. 逐条对比:
   - 一致 → maturity 从 draft 提升到 verified（追加 verified_in_workflows）
   - 部分一致 → maturity 保持 draft，追加工作流验证注释到 evidence
   - 不一致 → 创建新 ADR 记录变更理由，旧条目 maturity 降级为 draft 并添加 contradiction_flags
```

#### 4.4.2 补充与丰富

从工作流产物中提取新知识，补充导入时缺失的部分：

```
补充规则:
- 新发现的约定 → 追加 Best Practice（maturity: draft，有完整工作流证据链）
- 新发现的反模式 → 创建 Anti-Pattern（maturity: draft）
- 导入时 missing 的维度在工作流中被覆盖 → 更新 knowledge-baseline.json 对应维度
```

#### 4.4.3 去标记

当导入条目的 maturity 达到 verified 时：

```
去标记流程:
1. 移除 evidence.source_projects 中的 "imported-" 前缀标记
2. 追加当前项目名到 evidence.source_projects
3. 追加当前工作流 ID 到 evidence.verified_in_workflows
4. 条目正式融入常规知识库，与工作流产出的知识同等对待
```

#### 4.4.4 清理

连续 3 个工作流都未引用的导入条目：

```
清理策略:
1. 降级 maturity 到 draft
2. 标记为 "unvalidated-import"（添加到 evidence.contradiction_flags）
3. 在知识库健康检查中（§6.3）标记为待审核
4. 不自动删除，等待人工审核或在下次健康检查时归档
```

### 4.5 知识提升机制（Promote）

ARCHIVE 阶段完成知识提取后，对每条新知识执行提升判定：

**判定流程**：
```
对每条提取的知识条目：
  ↓
Q1: 是否包含项目特定代码实现细节？（如具体类名、数据库表名）
  ├─ 否 → Q2
  └─ 是 → Q3
  
Q2: 是否为跨项目通用的技术知识？
  ├─ 是 → 提升到 Layer 1 (tech-wiki)
  │   - 按 tech_stack 标签分类到对应子目录
  │   - ID 格式: TK-{领域}-{序号}
  │   - maturity: draft（首次提升）
  └─ 否 → Q3

Q3: 是否为通用业务规则/实体/流程？（不依赖特定代码）
  ├─ 是 → 提升到 Layer 2 (biz-wiki)
  │   - 匹配 domains.yaml 中的领域（或创建新领域）
  │   - ID 格式: BK-{domain}-{类型}{序号}
  │   - maturity: draft
  └─ 否 → 保留在 Layer 3 (项目内)
```

**跨项目合并**：提升时检查目标层是否已有相似条目
- 已有 → 合并更新：追加 source_projects、更新 evidence
- 如果已有条目 maturity=draft 且新来源来自不同项目 → 提升为 verified

---

## 5. 知识消费机制（按需查询）

> **设计理念**：不推送固定数量的知识给 Agent，而是提供高效的索引结构，让 Agent 在工作过程中主动按需查询。知识库是全能的，Agent 按需取用。

### 5.1 渐进式查询流程

```
Agent 在决策点需要知识时：

Step 1: 读全景目录（~50 行，零成本）
  → {knowledgeRepoLocalPath}/knowledge-catalog.md
  → 了解知识库有什么分类、每类多少条
  → 根据当前阶段定位推荐查阅的 catalog.md 路径

Step 2: 读分类清单（~100-300 行，低成本）
  → 对应分类的 catalog.md
  → 每条知识一行摘要（ID + 标题 + 成熟度 + 标签 + 适用阶段）
  → 按 applicable_phases 过滤当前阶段相关的条目
  → 按 tags 过滤与当前任务相关的条目

Step 3: 读完整条目（按需，每条 50-200 行）
  → 具体的 TK-*.md 或 BK-*.md
  → 获取完整知识内容（背景、内容、适用场景）

Step 4: 读原始产物（深入，可选）
  → 沿知识条目的 source_references 追溯
  → 读归档的 architecture.md、SUMMARY.md 正文
  → 获取原始推导过程和完整上下文
```

### 5.2 查询入口

每个 Agent 可访问以下查询入口：

| 入口 | 路径 | 内容 | 成本 |
|------|------|------|------|
| **团队知识全景** | `{knowledgeRepoLocalPath}/knowledge-catalog.md` | 分类统计 + 阶段推荐 | ~50 行 |
| **技术知识清单** | `{knowledgeRepoLocalPath}/tech-wiki/catalog.md` | 所有技术知识一行一条 | ~100-300 行 |
| **业务知识清单** | `{knowledgeRepoLocalPath}/biz-wiki/{domain}/catalog.md` | 领域业务知识一行一条 | ~100-300 行 |
| **团队约定** | `{knowledgeRepoLocalPath}/team-conventions/` | 编码规范、Review 标准 | ~50-100 行 |
| **项目知识库** | `docs/knowledge-base/index.md` | 项目内知识条目清单 | ~50 行 |
| **归档工作流索引** | `docs/workflows/archived/index.md` | 历史需求按功能域分类 | ~200 行 |
| **项目记忆** | `.codebuddy/memory/` | 历史经验和踩坑记录 | 按日期文件 |
| **个人偏好** | `~/.ai-team/preferences/coding-style.md` | 个人编码风格 | ~50 行 |

### 5.3 各阶段查询预算

> catalog.md 不计入配额（太轻量），只有完整条目和归档产物计入。

| 阶段 | Agent | 完整条目配额 | 归档产物配额 | 查询重点 |
|------|-------|------------|------------|---------|
| ANALYSE_PRODUCT | @product-collector | 5 | 3 | 业务规则、实体关系、历史需求 |
| ANALYSE_PRODUCT | @product-extractor | 5 | 2 | 同域业务规则参考 |
| ANALYSE_TECH | @tech-explorer | 8 | 5 | ADR、技术模式、反模式、历史架构 |
| ANALYSE_TECH | @tech-designer | 5 | 3 | 架构模式、框架经验 |
| ARCHITECT | @backend-architect 等 | 8 | 5 | ADR、实体关系、历史架构 |
| IMPLEMENT | 各开发 Agent | 5 | 2 | 最佳实践、反模式、编码规范 |
| BUILD_VERIFY | 各验证 Agent | 3 | 0 | 反模式、已知编译问题 |

### 5.4 查询触发时机（按需，非启动时一次性）

知识查询不在 Agent 启动时一次性完成，而是在**具体决策点**按需触发：

```
@tech-explorer 示例：

Step 1: 初始化
  → 读 knowledge-catalog.md（全景了解）
  → 读 tech-wiki/catalog.md（技术知识概览）

Step 2: 复用探索（每个需求点）
  → 先执行 3 轮代码搜索
  → 如果搜索结果不足 → 在 catalog.md 中查找相关的 TK-*.md
  → 读取匹配的完整条目 → 引用到复用评级中
  → 如果需要更多上下文 → 沿 source_references 读归档产物

Step 3: 输出
  → tech-exploration-result.json 新增：knowledgeReferences[]
  → 记录引用了哪些知识条目（ID + 标题），供下游追溯
```

```
@product-collector 示例：

Step 1: 初始化
  → 读 knowledge-catalog.md
  → 读 biz-wiki/{domain}/catalog.md（业务知识概览）
  → 读 docs/workflows/archived/index.md（历史需求索引）

Step 2: 迭代判定
  → 在 archived/index.md 中搜索同功能域的历史需求
  → 如果找到 → 读对应 SUMMARY.md 正文的"经验教训"章节
  → 迭代判定第 4 层信号权重从"低"提升为"中"（有具体历史证据支撑）

Step 3: 输出
  → _product-collection.json 新增：knowledgeReferences[]
```

### 5.5 知识引用追踪

Agent 查询知识后，在其输出产物中记录引用：

```json
{
  "knowledgeReferences": [
    { "id": "TK-SB-003", "title": "分页查询延迟关联优化", "usedIn": "复用评级 Step 2" },
    { "id": "BK-ECOM-BR004", "title": "商品分类树查询规则", "usedIn": "业务规则参考" }
  ]
}
```

ARCHIVE 阶段七读取各阶段产物中的 `knowledgeReferences`，批量更新 `evidence.last_referenced` 字段。这形成自动化的引用追踪闭环。

---

## 6. 知识进化规则

### 6.1 知识生命周期（三级成熟度）

```
draft（导入/新提取/矛盾降级）
  ↓ 在 1 个工作流中被成功引用（ARCHIVE 阶段自动判定）
verified（单项目验证）
  ↓ 在 ≥2 个不同项目中被验证（跨项目提升自动判定）
proven（成熟/可信赖）
  ↓ 12 月未引用
verified（衰减）
  ↓ 6 月未引用
draft（进一步衰减）
  ↓ 6 月未引用 + Lint 标记
archived（归档，移出活跃索引）
```

### 6.2 冲突处理

当新提取的知识与已有条目冲突时，按团队协作机制（§2.6.2）处理：

```
冲突处理策略:
1. 纯新增（不同条目）→ 自动合并，两条都保留
2. 同一条目追加证据 → 自动合并，evidence.contributors 数组合并去重
3. 同一条目内容矛盾 → 写入 {knowledge-repo}/contributions/conflicts/，通知 maintainer 裁决
4. 涉及架构决策 (ADR) → 不自动覆盖，创建新 ADR 记录旧决策的变更理由
5. 冲突条目的 maturity 自动降级为 draft，直到矛盾解决
6. 所有冲突和解决记录追加到 log.md（不可变追加日志）
```

### 6.3 知识库 Lint（健康检查）

> **设计来源**：借鉴 Karpathy LLM Wiki 的 Lint 操作——定期识别矛盾、孤儿页、缺失交叉引用和数据缺口。

**触发方式**：
- 自动触发：每完成 10 个工作流后
- 手动触发：`/evolve` 命令包含知识库健康检查
- 定期触发：连续 30 天未执行时，下次 `/flow:run` 启动时提醒

**Lint 检查项**：

| 检查项 | 检测方法 | 处理方式 |
|--------|---------|---------|
| **索引不一致** | 对比 index.json 条目与实际文件列表（团队知识仓库各层均检查） | 自动修复：补充缺失条目 / 移除悬空引用 |
| **孤儿条目** | 无交叉引用（`related` 字段为空）且无 `evidence.source_projects` | 标记为待审核，降级 maturity 到 draft |
| **矛盾检测** | 同一主题的多条知识，结论相反 | 创建 `conflict-{ID}` 标记，降级 maturity 到 draft，等待人工审核 |
| **过时检测** | maturity 为 draft 且 6 个月未引用 | 自动归档到 `archive/` 目录 |
| **导入未验证** | `imported-` 前缀条目且连续 3 个工作流未引用 | 降级 maturity 到 draft，标记 `unvalidated-import` |
| **重复/相似** | 标题或内容语义高度重合（含跨层重复检测） | 标记为合并候选，建议人工合并 |
| **成熟度衰减** | proven 条目 12 月未引用 / verified 条目 6 月未引用 | 按生命周期规则（§6.1）自动降级 maturity |

**Lint 报告格式**：

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 知识库健康检查报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

检查时间: {ISO-8601}
知识条目总数: {N} | proven: {P} | verified: {V} | draft: {D}
三层分布: Layer 1({L1}) | Layer 2({L2}) | Layer 3({L3})

✅ 通过项: {列表}
⚠️ 需关注: {列表及建议}
❌ 需修复: {列表及自动修复结果}

自动执行的修复:
- 补充 index.json 缺失条目: {N} 条
- 归档过时条目: {M} 条
- maturity 衰减降级: {K} 条
- 更新 index.md / log.md

待人工审核:
- 矛盾条目: {列表}
- 合并候选: {列表}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Lint 结果写入**：
- 自动修复结果写入 log.md（操作类型 `lint`）
- 更新 index.json 统计数据
- 更新 index.md（移除归档条目）

## 6.5 知识库主动查询（Query 操作）

> **设计来源**：Karpathy LLM Wiki 的 Query 操作——用户随时向知识库提问，获得合成答案并附带引用。高质量查询结果自动回流为新知识。

### 6.5.1 触发方式

- 触发关键词："知识库里有没有..."、"上次关于 xxx 的经验"、"查一下之前的决策"、"历史上怎么处理..."
- 也可在工作流执行中由 Agent 主动调用（通过知识推送机制 §5 的扩展）

### 6.5.2 查询流程

```
用户提问
  ↓
Step 1: 关键词提取 — 从问题中提取领域、模块、技术栈等关键词
  ↓
Step 2: 渐进式检索 — 按三层索引结构：
  a) 读 {knowledge-repo}/knowledge-catalog.md → 定位相关分类
  b) 读对应 catalog.md → 扫描一行摘要，筛选相关条目
  c) 读匹配的完整条目 → 获取知识内容
  d) （可选）读归档产物 → 沿 source_references 获取原始上下文
  e) 读 docs/workflows/archived/index.md → 搜索历史需求
  f) Layer 0-P: ~/.ai-team/preferences/ → 个人偏好注入
  ↓
Step 3: 相关性排序 — 按 maturity 降序（proven > verified > draft）+ 关键词匹配度排序
  ↓
Step 4: 答案合成 — 读取匹配的完整条目，合成结构化回答
  ↓
Step 5: 回流判定 — 若回答质量高且具有复用价值，自动存为新知识条目
```

### 6.5.3 查询结果格式

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 知识库查询结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

查询: "{用户原始问题}"
匹配条目: {N} 条 | 最高成熟度: {maturity}

📋 综合回答:
{基于知识条目合成的回答}

📖 引用来源:
1. [{条目ID}] {标题} (maturity: {level}, layer: {layer}) — {摘要}
2. [{条目ID}] {标题} (maturity: {level}, layer: {layer}) — {摘要}
...

💡 相关推荐:
- {可能感兴趣的关联知识条目}

{若无匹配: "⚠️ 知识库中暂无相关记录。建议在下次相关工作流完成后通过 ARCHIVE 阶段自动提取。"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6.5.4 查询回流（Query Backfill）

当查询结果满足以下条件时，自动创建新知识条目：
- 合成答案引用了 ≥3 个条目（说明问题涉及跨领域综合）
- 用户对回答表示肯定（"这个很有用"、"正是我需要的"）
- 查询问题具有通用性（非一次性特定问题）

回流的知识条目：
- 类型为 `faq`（最常见）或 `best-practice`
- 初始 maturity 为 verified（有多条来源支撑）
- evidence.source_projects 继承引用条目的来源
- evidence.verified_in_workflows 继承引用条目的工作流记录
- 在 log.md 中记录操作类型为 `query-backfill`

---

## 7. 使用方式

### 7.1 触发关键词

- "知识沉淀"、"经验总结"、"最佳实践"
- "历史复盘"、"教训总结"、"知识库"
- "为什么之前决定用..."、"上次遇到这个问题是怎么解决的"
- "技术决策记录"、"ADR"

### 7.2 使用示例

```
用户: 总结一下最近完成的需求有哪些经验教训
→ 扫描最近 DONE 状态的工作流，提取知识条目，执行提升判定，生成回顾报告

用户: 这个模块之前有什么已知的坑吗？
→ 多层搜索 knowledge-base 中与该模块相关的 anti-pattern 和 risk-pattern（Layer 3 + Layer 2 + Layer 1，从团队知识仓库查询）

用户: 查看知识库状态
→ 展示知识库统计: 条目数量、三层分布、成熟度分布、最近更新

用户: 上次架构设计为什么选择了事件驱动？
→ 多层搜索 ADR 记录，展示决策背景和理由
```

---

## 8. 与其他 Skill 的协作

| 协作 Skill | 协作方式 | 方向 |
|-----------|---------|------|
| workflow-orchestrator | ARCHIVE 阶段触发知识提取 + 提升判定；Agent 启动时注入多层知识推荐 | 双向 |
| team-hub | 知识库健康度（含三层统计）作为团队看板指标 | → team-hub |
| capability-router | 知识推荐辅助路由决策（基于历史成功率调整 Skill 权重） | → capability-router |
| quality-guardian | 质量问题转化为 anti-pattern 知识条目（可提升到 Layer 1） | quality-guardian → |

---

## 9. 行为约束

### 9.1 必须做的（DO）

- ✅ 每次提取前先搜索已有条目避免重复（团队知识仓库各层均需扫描）
- ✅ 所有知识条目必须包含完整的 evidence（contributors, verified_in_projects）
- ✅ 保持各层 index.json 与实际文件同步
- ✅ 知识更新时保留版本历史（通过 Git diff）
- ✅ 推送知识时标注 maturity 和 layer，让接收方判断参考价值
- ✅ 提取后必须执行提升判定（§4.5），通用知识不应滞留在 Layer 3
- ✅ 团队知识贡献必须通过 Git 分支 + 合并流程，不直接写 main 分支
- ✅ 每条知识变更必须记录贡献者信息（evidence.contributors）

### 9.2 禁止做的（DON'T）

- ❌ 禁止在工作流执行中修改正在进行的产物
- ❌ 禁止将 draft 级别知识作为强制规则推送
- ❌ 禁止自动删除知识条目（只允许归档）
- ❌ 禁止在知识推送中暴露其他需求的敏感细节
- ❌ 禁止绕过质量门禁直接推送未验证的知识
- ❌ 禁止跳过提升判定直接写入 Layer 1/Layer 2
- ❌ 禁止修改 log.md 中的历史记录（只允许追加）
- ❌ 禁止 contributor 角色直接修改他人创建的 proven 条目
