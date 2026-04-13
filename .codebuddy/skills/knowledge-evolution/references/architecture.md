# 知识体系架构与分类

> 本文件从 SKILL.md 拆分而来，被 /knowledge status、/knowledge lint、/knowledge promote 等操作按需加载。

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
{knowledge-repo}/                          # 独立 Git 仓库（唯一的知识存储）
├── knowledge-catalog.md                   # Layer A: 全景目录
├── .knowledge-config.yaml                 # 团队配置（成员、冲突策略）
├── team-conventions/                      # Layer 0-T: 团队约定
│   ├── coding-standards.md
│   ├── commit-conventions.md
│   └── log.md
├── tech-wiki/                             # Layer 1: 技术知识
│   ├── catalog.md / index.json / log.md
│   ├── languages/ / frameworks/ / patterns/ / devops/ / anti-patterns/
│   ├── ui-patterns/                       # UI 模式（原 baselineUIPatterns 归宿）
│   │   ├── web/
│   │   └── miniprogram/
│   └── conventions/                       # 编码约定（原 codebase-profile.conventions 归宿）
├── biz-wiki/                              # Layer 2: 业务知识
│   ├── domains.yaml
│   ├── _cross-domain/
│   └── {domain}/
│       ├── catalog.md / index.json / log.md
│       ├── entities/                      # 业务实体（原 baselineDataEntities 归宿）
│       ├── relations/                     # 实体关系图
│       ├── rules/                         # 业务规则（原 baselineBusinessRules 归宿）
│       ├── flows/                         # 业务流程/用户故事（原 baselineUserStories 归宿）
│       └── pitfalls/                      # 踩坑记录
├── project-profiles/                      # 项目画像（原 codebase-profile.json 归宿）
│   └── {project-name}.yaml               # 每个项目一个画像文件
└── contributions/
    ├── pending/
    └── conflicts/
```

> **统一存储原则**：flow-import 和 ARCHIVE 写入同一个仓库。flow-import 批量灌入 draft 级别条目，ARCHIVE 增量追加 + 验证提升。本地不再维护 `knowledge-baseline.json` 和 `codebase-profile.json`。

---

## 3. 知识分类

### 3.1 知识类型定义

> **分类原则**：按「知识描述的是什么」分类（客观、稳定、MECE），而非按「从哪个阶段产出」分类。来源信息记录在 `source` 元数据字段中，用于溯源分析（如某阶段频繁产出 pitfall，说明该阶段 Agent 需优化）。

| 类型 ID | 名称 | 定义 | 子字段 | 示例 |
|---------|------|------|--------|------|
| `model` | 领域模型 | 实体定义、数据结构、关系图、概念模型 | — | "广告计划包含预算/出价/投放时段三个核心字段" |
| `decision` | 决策记录 | 技术选型、架构决策、方案取舍及理由 | — | "选择事件驱动而非 RPC 同步，因为广告状态变更需要解耦" |
| `guideline` | 行为准则 | 推荐做法或禁止做法 | `polarity: recommend \| avoid` | recommend: "公共模块变更后的兼容性检查清单" / avoid: "禁止在 Controller 直接返回 Entity" |
| `pitfall` | 已知陷阱 | 已知风险、故障模式、排查步骤、踩坑记录 | — | "广告预算扣减在高并发下会超扣，需用 Redis+Lua 保证原子性" |
| `process` | 流程定义 | 业务流程、状态机、操作步骤、用户旅程 | — | "广告审核流程：提交→机审→人审→上线，人审超时自动拒绝" |

**与旧类型的映射关系**（迁移参考）：
- `adr` → `decision`
- `best-practice` → `guideline` (polarity=recommend)
- `anti-pattern` → `guideline` (polarity=avoid) 或 `pitfall`（规范性的归 guideline，叙事性的归 pitfall）
- `faq` → 按内容拆散（排查步骤→pitfall，规则说明→guideline，概念解释→model）
- `risk-pattern` → `pitfall`
- `template-evolution` → 移出知识体系，作为系统元数据记录在 log.md 中

**与存储目录的对应关系**：

| 类型 | tech-wiki/ 子目录 | biz-wiki/{domain}/ 子目录 |
|------|-------------------|--------------------------|
| model | frameworks/, languages/ | entities/, relations/ |
| decision | patterns/ | （按领域存放） |
| guideline (recommend) | patterns/, conventions/ | rules/ |
| guideline (avoid) | anti-patterns/ | rules/ |
| pitfall | anti-patterns/ | pitfalls/ |
| process | devops/ | flows/ |

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

## [2026-04-09] ingest | [Steven] | 门店履约视图归档 | +1 decision, +2 guideline | #a3f8c2
- 新增 DEC-005: 地图组件选型（腾讯地图 GL JS SDK）
- 新增 GL-012: fitBounds 在 flexbox 布局中的替代方案 (polarity=recommend)
- 更新 GL-003: 公共模块变更检查清单（新增地图依赖检查项）

## [2026-04-08] ingest | [Alice] | 商详页UI重构归档 | +1 guideline, +1 process | #b4e9d1
- 新增 GL-011: CSS 变量双轨方案（品牌色 CSS 变量 + 文字色 SCSS 变量）(polarity=recommend)
- 新增 PRC-002: 小程序纯前端需求交付流程 v2

## [2026-04-08] lint | [system] | 定期健康检查 | -2 archived
- 归档 PIT-003: 已 6 个月未引用
- 归档 GL-IMP-002: 导入知识未通过验证

## [2026-04-09] promote | [Steven] | 技术知识提升 | +2 TK, +1 BK | #a3f8c2
- 提升 GL-012 → TK-MAP-001 (Layer 1 tech-wiki)
- 提升 DEC-005 → TK-MAP-002 (Layer 1 tech-wiki)
- 提升 GL-008 → BK-AD-G001 (Layer 2 biz-wiki/ad)

## [2026-04-12] verify | [Alice] | 跨项目验证 | maturity↑ 2 | #c5f0e2
- TK-SB-003 "分页查询延迟关联优化" (verified→proven, 2 projects)
```

**维护规则**：
- 每次知识变更（新增/更新/归档/Lint/提升）追加一条记录
- 格式：`## [{日期}] {操作类型} | [{贡献者}] | {摘要} | {变更统计}`
- 操作类型：`ingest`（提取）、`update`（更新）、`lint`（健康检查）、`query-backfill`（查询回流）、`promote`（知识提升）
- 仅追加，不修改历史记录（区块链不可变日志思想）
- 每条记录带会话哈希，可追溯到具体工作流
