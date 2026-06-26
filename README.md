# AI Team — AI 工程交付编排系统

> 基于 CodeBuddy IDE 的 Skill / Command / Rule 体系，实现多 Agent 协作的全流程需求交付自动化。
> **核心理念**：文件系统即状态机，团队知识持续沉淀，越用越聪明。

---

## 这是什么

AI Team 是一套**工作流引擎**，安装到你的业务项目后，用一条命令 `/flow-run` 驱动 AI Agent 完成从需求分析到代码归档的全流程。它不是一个独立平台，而是一组 IDE 原生识别的 Skill / Agent / Command 定义文件——`.codebuddy/` 给 CodeBuddy 用、`.claude/` 给 Claude Code 用，**双平台镜像维护、功能完全等价**。

**核心价值**：Skill、Agent、工具链会随模型迭代更新，但**领域知识是永恒的**。AI Team 的每次交付都自动沉淀知识到团队共享仓库，所有成员共建共享，新工作流启动时自动站在前人肩上。

<img width="" src="/uploads/d949dcaa81064a538e4c4dc3406af2cc/image.png" alt="image.png" />

---

## 部署拓扑

支持单仓和多仓（小仓/微服务拆分），统一 `repos[]` 模型，无需切换模式。

**单仓模式**（一个 Git 仓库包含所有代码）：
```
工作区根/（= Git 仓库根）
├── .codebuddy/  +  .claude/      ← 引擎副本（双平台镜像）
├── .ai-team/project.yaml          ← 知识锚点
├── docs/workflows/                ← 工作流产物
├── src/                           ← 你的代码
└── pom.xml / package.json

→ repos[]: [{ name: "my-project", path: "./", type: "fullstack" }]
```

**多仓模式**（多个独立 Git 仓库，微服务拆分）：
```
工作区根/（CodeBuddy 打开的父目录，不是 Git 仓库）
├── .codebuddy/  +  .claude/       ← 引擎副本（双平台镜像）
├── .ai-team/project.yaml          ← 知识锚点
├── project-docs/      (.git/)     ← 文档仓（type=docs，承载 docs/workflows/）
│
├── ad-service/        (.git/)     ← Git 仓库 A（后端微服务）
├── creative-service/  (.git/)     ← Git 仓库 B（后端微服务）
└── ad-frontend/       (.git/)     ← Git 仓库 C（前端）

→ repos[]: [
    { name: "project-docs",     path: "project-docs/",     type: "docs"     },
    { name: "ad-service",       path: "ad-service/",       type: "backend"  },
    { name: "creative-service", path: "creative-service/", type: "backend"  },
    { name: "ad-frontend",      path: "ad-frontend/",      type: "frontend" }
  ]
```

两种模式的工作流完全一致：`/team-init` 引导填充 `repos[]`，后续阶段遍历 `repos[]` 执行。多仓模式下 `docs/` 由独立的 `type=docs` 仓库承载（`projectConfig.docsRoot` 自动解析路径，Agent 无需感知单仓/多仓差异）。

**团队知识仓库**（独立 Git 仓库，所有成员 clone，跨项目/跨工作区共享）：
```
team-knowledge.git
├── knowledge-catalog.md      ← 全景目录（Agent 按需查询入口）
├── tech-wiki/                ← 技术知识（按语言/框架/模式）
├── biz-wiki/{domain}/        ← 业务知识（按领域）
├── team-conventions/         ← 团队编码约定
└── contributions/            ← 贡献暂存与冲突记录
```

**三类仓库各司其职**：
- **ai-team 仓库**（本仓库）：工作流引擎代码，复制到各工作区使用
- **业务项目仓库**（一个或多个）：你的实际代码
- **团队知识仓库**：跨项目共享的知识库，通过 `/team-init` 连接，不同工作区可连同一个

---

## 安装

在你的业务项目中打开 CodeBuddy 或 Claude Code，粘贴给 Agent：

```
请帮我从远程仓库拉取 ai-team 工作流系统到当前工作区。按顺序执行：

1. cd {当前工作区根目录}
   git clone --depth 1 git@git.woa.com:Agentic-CE-Infra/ur-ai-team.git .ai-team-install

2. cp -r .ai-team-install/.codebuddy ./
   cp -r .ai-team-install/.claude ./        # 双平台同步部署

3. rm -rf .ai-team-install

4. 验证：检查 .codebuddy/skills/、.codebuddy/commands/、.claude/skills/、.claude/commands/ 目录是否存在。

完成后告诉我安装结果。
```

安装后两个目录立即被对应 IDE 识别。后续可使用 `/flow-upgrade` 命令版本对比 + 选择性更新（双平台同步）。

---

## 快速开始

```bash
# 1. 首次使用：连接团队知识仓库（每个项目执行一次）
/team-init

# 2. 已有代码库：导入历史知识（可选但推荐）
/flow-import

# 3. 日常开发：启动交付工作流
/flow-run                              # 从上下文推断需求
/flow-run docs/prd/my-requirement.md   # 从 PRD 文档启动

# 4. 查看进度
/flow-status

# 5. 知识库维护
/knowledge status                      # 查看知识库状态
/knowledge lint                        # 健康检查（含模块活跃度抑制 + 事实漂移扫描）
/knowledge sync                        # 同步团队知识仓库
/knowledge fact-check                  # 手动触发代码事实校对（重构后立即用）

# 6. 复盘改进
/evolve                                # 分析改进建议
/evolve-apply                          # 落地改进

# 7. 更新工作流引擎
/flow-upgrade                          # 版本对比 + 选择性更新
```

---

## 工作流：15 阶段状态机

```
/flow-run 启动后自动流转（15 个合法阶段，含 4 个澄清阶段）：

INIT
  → ANALYSE_PRODUCT  → CLARIFY_PRODUCT
  → ANALYSE_TECH     → CLARIFY_TECH
  → ARCHITECT_BACKEND  → CLARIFY_ARCH_BACKEND
  → ARCHITECT_FRONTEND → CLARIFY_ARCH_FRONTEND
  → IMPLEMENT → BUILD_VERIFY → VISUAL_REVIEW
  → E2E_VERIFY → TEST → ARCHIVE → DONE
```

每个非 INIT 阶段遵循**三步模式**：Preview（预览计划）→ Execute（执行）→ Summary（总结确认），确保每一步人工可控。`CLARIFY_*` 仅当对应澄清文件有 `pending` 问题时进入，否则自动跳过（记录 `status: "skipped"`）。**只有 ARCHIVE 阶段的 `@archiver` Agent 才能将 `currentPhase` 设为 `DONE`**——BUILD_VERIFY PASS ≠ 工作流完成。

### 各阶段做什么

| # | 阶段 ID | Agent | 做什么 |
|---|--------|-------|--------|
| 0 | `INIT` | 编排器 | 解析 PRD、加载 `repos[]`、注入团队知识仓库路径、TAPD 检测、IntentGate 意图分析（自动流转，唯一无需用户确认） |
| 1 | `ANALYSE_PRODUCT` | 4 成员产品 Agent Teams | 需求分析：迭代判定、基线对比、用户故事/业务规则提取、视觉分析 |
| 2 | `CLARIFY_PRODUCT` | 编排器 | 读取产品澄清问题，向用户提问，回填答案 |
| 3 | `ANALYSE_TECH` | 4 成员技术 Agent Teams | 技术分析：按 `repos[]` 逐仓库扫描、3 轮递进搜索、技术方案设计、分端拆解、校审 |
| 4 | `CLARIFY_TECH` | 编排器 | 技术澄清问题处理 |
| 5 | `ARCHITECT_BACKEND` | 全局架构师 + 领域架构师×N | 三级降级（Agent Teams → Task 流水线 → 单体兜底）+ 领域确认检查点 + 数据库 / API 契约 |
| 6 | `CLARIFY_ARCH_BACKEND` | 编排器 | 后端架构澄清 |
| 7 | `ARCHITECT_FRONTEND` | 资深前端架构师 | Web / 小程序架构设计 |
| 8 | `CLARIFY_ARCH_FRONTEND` | 编排器 | 前端架构澄清 |
| 9 | `IMPLEMENT` | 各端开发 Agent 并行 | 按 `domain-registry.json` 分配领域所有权，每个领域独立 Agent，LSP 实时诊断；前端可由 D2C 直通完成 |
| 10 | `BUILD_VERIFY` | 后端/Web/小程序验证 Agent | **P0 质量门禁**，Agent Teams 模式下按平台并行验证（B1/B2/B3），精细化回退仅重跑失败平台 |
| 11 | `VISUAL_REVIEW` | 视觉验收 Agent | **P1 质量门禁**（可选），AI 对比设计稿 vs 实现截图，还原度评分（A/B/C/D/F），无设计稿时自动跳过 |
| 12 | `E2E_VERIFY` | 端到端链路验证 Agent | 跨组件 / 跨服务运行时依赖验证（7 维度） |
| 13 | `TEST` | 测试验证 Agent | 生成测试方案并执行验证（3 层测试体系） |
| 14 | `ARCHIVE` | `@archiver` + `@fact-checker` | 汇总变更报告、知识提取与提升判定、团队知识仓库 push、TAPD 附件回写、企微归档通知 |
| 15 | `DONE` | — | 终态（仅 ARCHIVE 阶段可流转至此） |

### 核心工程机制

| 机制 | 说明 |
|------|------|
| **上下文防火墙** | 搜索密集型工作在独立 Agent Teams 上下文窗口执行，仅将结构化结论（~10x 压缩）传递给下游成员 |
| **三级降级** | L1 Agent Teams → L2 Task 串行管道 → L3 编排器直接执行（ANALYSE_PRODUCT / ARCHITECT_BACKEND 适用） |
| **IntentGate 意图分析** | INIT 后前置执行：5 类意图分类（`new-feature` / `feature-modify` / `bug-fix` / `tech-refactor` / `d2c-to-workflow`）+ 歧义检测 + 影响范围预估 + 路由提示，写入 `state.json.intentAnalysis` |
| **检查点恢复** | ARCHITECT_BACKEND 四阶段（global_pending → global_completed → domains_confirmed → domains_completed）；ANALYSE_PRODUCT 三级恢复（teams / pipeline / fallback） |
| **流转守卫** | 每次更新 `currentPhase` 前查 `references/phase-transitions.json`，非法跳跃强制阻断；DONE 终态保护（写入前校验所有 14 个前置阶段均有 phaseHistory 记录） |
| **阶段计时协议** | `phaseHistory` 5 时间戳：`startedAt`（预览开始）/ `confirmedAt`（用户确认）/ `executionStartedAt` / `executionCompletedAt` / `completedAt`（总结确认）逐轮填充 |
| **运行时上下文健康度** | 每次阶段切换估算工具调用次数与压缩事件，写入 `contextHealth.phaseMetrics`，>150 次累计建议 `/compact` |
| **搜索预算** | 每个 Agent 有独立配额（搜索密集型 ≤60、设计型 ≤5、开发型 ≤30/领域、验证型 ≤20）；优先链：`read_lints` → LSP → Grep → Glob → `codebase_search` |
| **LSP 诊断** | IMPLEMENT 每次写入后 `read_lints`，BUILD_VERIFY 全项目扫描，预防 80% 编译失败 |
| **knowledgeReferences 校验** | 每个阶段总结确认时强制检查核心产物含 `knowledgeReferences` 字段（即使为 `[]`），缺失则标 🟡 warn |
| **代码溯源（@changelog）** | 每个源文件头部维护 `\| 版本 \| REQ:{需求ID} \| TECH:{方案文档} \| 摘要 \| 日期 \|` 表格 + `@author agent:{name}`，实现 O(1) 需求-代码关联查找 |
| **通知机制** | `architect_review` / `build_verify_fail` / `visual_review_fail` / `workflow_done` 四类事件经 `send-flow-message` 主动推送到企微（探测到技能时自动启用） |

### Agent 编制全景

`workflow-orchestrator/agents/` 下的 Agent 按团队/职责划分（不含项目运行时动态生成的领域 Agent）：

| 团队 / 单体 | 成员 | 调用阶段 |
|------------|------|---------|
| **产品分析团队**（4 成员）| `@product-collector` · `@baseline-differ` · `@product-extractor` · `@quality-assessor` | ANALYSE_PRODUCT |
| **技术分析团队**（4 成员）| `@tech-explorer` · `@tech-designer` · `@tech-splitter` · `@tech-reviewer` | ANALYSE_TECH |
| **后端架构团队**（动态）| `@global-architect` + `@domain-architect-{N}`（≤8） | ARCHITECT_BACKEND |
| **后端开发**（动态领域）| 共享 `backend-dev-specification.md` 通用规范，按 `domain-registry.json` 实例化 | IMPLEMENT |
| **构建验证团队**（3 成员）| `@backend-build-verifier` · `@web-build-verifier` · `@miniprogram-build-verifier` | BUILD_VERIFY |
| **知识导入团队**（3 成员）| `@doc-collector` · `@codebase-profiler` · `@knowledge-builder` | `/flow-import` |
| **单体 / 降级 Agent** | `product-analyst` · `fullstack-analyst` · `build-verifier`（三级降级时使用） | 对应阶段 |
| **架构师** | `java-architect`（Java 专版） · `backend-architect`（通用版） · `frontend-architect` | ARCHITECT_* |
| **前端开发** | `web-developer` · `miniprogram-developer` | IMPLEMENT |
| **验证 / 验收 / 归档** | `e2e-link-verifier` · `test-engineer` · `visual-reviewer` · `archiver` · `fact-checker` | E2E_VERIFY/TEST/VISUAL_REVIEW/ARCHIVE |

### D2C 双模式

Figma 设计稿转代码（`figma-d2c` Skill）有两种与工作流的集成方式，通过 `state.json.intentAnalysis.d2cConfig.mode` 区分：

| 模式 | 触发场景 | 工作流路径 |
|------|---------|----------|
| **standalone**（直通模式） | 用户直接粘贴 Figma 链接、无 PRD 上下文 | D2C 完成 → 自动生成 PRD → `intentType = d2c-to-workflow` → 简化执行 ANALYSE/ARCHITECT_FRONTEND → IMPLEMENT 前端部分**跳过**（D2C 已完成）→ BUILD_VERIFY 起正常 |
| **embedded**（嵌入模式） | 已有 PRD + 关联 Figma | 正常执行 ANALYSE/ARCHITECT，IMPLEMENT 阶段前端开发 Agent 调用 D2C 生成基础代码后做业务增强 |

两种模式均支持 16 步检查点协议（CP-0 → CP-M），断点续传、回归对比、视觉验收自动衔接。

### 多仓文档仓（docsRoot / docsRepoMode）

多仓模式下 `docs/workflows/` 不属于任何业务 Git 仓库——通过 `projectConfig.docsRoot` + `docsRepoMode` 解决：

| 字段 | 取值 | 含义 |
|------|------|------|
| `docsRoot` | `"./"` / `"project-docs/"` | 文档仓根相对 workspace 的路径 |
| `docsRepoMode` | `embedded` / `standalone` | 内嵌（单仓 docs 在业务仓内）/ 独立（多仓独立 Git）|

INIT 阶段自动检测：单仓 → `embedded`；多仓且 `repos[].type=docs` 已配置 → `standalone`；多仓但 workspace 根已有 `docs/`（存量项目）→ 提示用户在 workspace 根「原地 Git 化」或迁移到 `project-docs/`。Agent 文档中所有 `docs/` 前缀路径保持不变，**编排器运行时拼接 `{docsRoot}` 解析为绝对路径**，Agent 完全无感。

---

## 知识体系

> 这是整个系统最重要的设计。Skill、Agent、工具链会随模型迭代更新，但**领域知识是永恒的**。

### 核心概念

知识体系由三个正交维度组成：

| 维度 | 问题 | 定义 |
|------|------|------|
| **存储层（在哪）** | 知识存在哪里？ | Layer 0-P/0-T/1/2/3 — 从个人到团队到项目 |
| **知识类型（是什么）** | 知识描述的是什么？ | model / decision / guideline / pitfall / process — 按内容维度分类 |
| **成熟度（多可信）** | 知识经过多少验证？ | draft → verified → proven（仅知识条目有，规范/偏好没有） |

#### 存储层 × 知识类型 × 成熟度的关系

```
Layer 0-P  个人偏好（~/.ai-team/preferences/）         ← 没有类型和成熟度，是配置
Layer 0-T  团队约定（{知识仓库}/team-conventions/）     ← 没有类型和成熟度，是规范

Layer 3    项目知识（{项目}/docs/knowledge-base/）      ← 知识条目的初始着陆层
              │  所有 5 种类型都可能存在，maturity 为 draft
              │
              ├──→ 提升判定 Q1: 是否项目特有？ → 是：留在 Layer 3
              ├──→ 提升判定 Q2: 是否通用技术？ → 是：提升到 Layer 1
              └──→ 提升判定 Q3: 是否通用业务？ → 是：提升到 Layer 2

Layer 1    技术知识（{知识仓库}/tech-wiki/）            ← decision、guideline、pitfall、model
Layer 2    业务知识（{知识仓库}/biz-wiki/{domain}/）    ← model、process、guideline、pitfall
              ↑ 提升到 Layer 1/2 的条目 maturity 为 draft
              ↑ 被其他工作流引用后自动升为 verified → proven
```

### 知识如何流动

```
/flow-import（一次性）           /flow-run（每次）
      │                              │
      ▼                              ▼
 冷启动导入                     INIT: git pull 知识仓库 + 注入查询入口
 3 Agent 管道                        │
 → 知识写入团队仓库                 │  ← Agent 在各阶段按需查询（三级索引）
 → 代码画像写入仓库                 │
                                     ▼
                               ARCHIVE: 知识提取 + 提升判定
                                     │
                                     ├→ Layer 3（项目内）: docs/knowledge-base/
                                     ├→ Layer 1（技术）: tech-wiki/  ← git push
                                     └→ Layer 2（业务）: biz-wiki/  ← git push
                                                     │
                                                     ▼
                                              下一个人的 /flow-run 自动受益
```

### 五种知识类型

> **分类原则**：按「知识描述的是什么」分类（客观、稳定、MECE），来源阶段记录在 `source` 元数据中用于溯源分析。

| 类型 | 定义 | 子字段 | 典型存储层 | 示例 |
|------|------|--------|-----------|------|
| `model` | 实体定义、数据结构、关系图 | — | Layer 2 entities/relations | "广告计划包含预算/出价/投放时段三个核心字段" |
| `decision` | 技术选型、架构决策、方案取舍及理由 | — | Layer 1 patterns | "选择事件驱动而非 RPC 同步，因为广告状态变更需要解耦" |
| `guideline` | 推荐做法或禁止做法 | `polarity: recommend \| avoid` | Layer 1 / Layer 0-T | recommend: "公共模块变更后的兼容性检查清单" |
| `pitfall` | 已知风险、故障模式、排查步骤 | — | Layer 1 anti-patterns / Layer 2 pitfalls | "广告预算扣减在高并发下会超扣" |
| `process` | 业务流程、状态机、操作步骤 | — | Layer 2 flows | "广告审核：提交→机审→人审→上线" |

### 三级成熟度

```
draft（新提取，单一来源）→ verified（在 1 个工作流中被成功引用）→ proven（在 ≥2 个不同项目中被验证）
```

**双信号衰减**：成熟度由两组正交信号共同维护——
- **时间信号**：proven 12 个月未引用 → verified；verified 6 个月未引用 → draft；draft 持续未引用 → Lint 标记后归档。判定时引入"模块活跃度抑制"，避免误伤季节性活跃模块（如对账/结算只在月末/年末活跃），关联模块休眠 6~24 月时跳过降级，超过 24 月强制衰减。
- **事实信号**：每次 ARCHIVE 由 `@fact-checker` 子 Agent 针对本次变更模块的关联知识做符号级校对——引用文件整体消失则降级，关键符号消失则打标 `code-fact-drift` 待人工复查。可通过 `/knowledge fact-check` 手动触发（支持指定模块或最近变更范围）。

阈值通过 `{知识仓库}/.knowledge-config.yaml` 的 `decay_rules` 和 `fact_check` 段配置。

> 成熟度仅适用于知识条目（Layer 1/2/3），不适用于个人偏好（Layer 0-P）和团队约定（Layer 0-T）。

### 按需查询：三级索引

Agent 不被动接收固定数量的知识推荐，而是通过**三级渐进式索引**主动按需查阅：

| 级别 | 文件 | 大小 | 作用 |
|------|------|------|------|
| **全景目录** | `{知识仓库}/knowledge-catalog.md` | ~50 行 | 知识库有哪些分类、各多少条，按阶段推荐查阅路径 |
| **分类清单** | 各目录下的 `catalog.md` | ~100-300 行 | 每条知识一行摘要（ID + 标题 + 成熟度 + 适用阶段），可快速过滤 |
| **完整条目** | 具体的 TK-*.md / BK-*.md | ~50-200 行 | 完整知识内容，可沿 `source_references` 追溯原始产物 |

### 各阶段查询什么

各阶段有独立的查询预算（分类清单不计入配额，只有完整条目和归档产物计入）：

| 阶段 | Agent | 完整条目 | 归档产物 | 查询的存储层 | 重点知识类型 |
|------|-------|---------|---------|------------|------------|
| ANALYSE_PRODUCT | @product-collector | 5 | 3 | Layer 2 (biz-wiki) + 归档索引 | model, process, pitfall |
| ANALYSE_PRODUCT | @product-extractor | 5 | 2 | Layer 2 (biz-wiki) | guideline, model |
| ANALYSE_TECH | @tech-explorer | 8 | 5 | Layer 1 (tech-wiki) + 归档索引 | decision, guideline(avoid), pitfall |
| ANALYSE_TECH | @tech-designer | 5 | 3 | Layer 1 (tech-wiki) | decision, guideline(recommend) |
| ARCHITECT | @backend-architect 等 | 8 | 5 | Layer 1 patterns + Layer 2 relations | decision, model |
| IMPLEMENT | 各开发 Agent | 5 | 2 | Layer 1 + Layer 0-T | guideline, pitfall |
| BUILD_VERIFY | 各验证 Agent | 3 | 0 | Layer 1 anti-patterns | pitfall, guideline(avoid) |

### 团队协作

通过 `/team-init` 连接独立 Git 知识仓库。所有成员的工作流 ARCHIVE 阶段自动提取知识并 push。

**冲突解决**：纯新增/证据追加 → 自动合并；内容矛盾 → 写入 `contributions/conflicts/`，maintainer 裁决。

**角色**：maintainer（裁决冲突、审批 proven）、contributor（自动贡献）、reader（只消费）。

---

## 冷启动：/flow-import

对已有代码库，先跑一次 `/flow-import` 构建知识基线：

```
@doc-collector → 多源资料收集（文档/TAPD/iwiki/口述/代码扫描）
  ↓
@codebase-profiler → 代码画像（技术栈/模块/依赖/模式，60 次搜索预算）
  ↓
@knowledge-builder → 知识标准化（4 维基线 + ≤13 条知识条目 + 归档总结）
```

产出直接写入团队知识仓库（`knowledge-baseline.json` 四维度：用户故事/业务规则/数据实体/UI 模式），所有条目初始 maturity 为 draft，后续工作流的 ANALYSE 阶段自动消费。

---

## 可用命令

<!-- BEGIN AUTO-GEN: readme-commands-table hash=3df811f8b308b810 source=commands/*.md frontmatter + 现状 -->

| 命令 | 用途 |
|------|------|
| `/flow-run` | 启动交付工作流（支持附带 PRD 文档启动 / 文字描述 / 直接启动三种入口） |
| `/flow-import` | 历史项目知识导入（支持 Git/TAPD/iwiki/本地文档/口述） |
| `/flow-upgrade` | 工作流版本更新（远程对比 + 选择性更新 `.codebuddy/` 与 `.claude/` 双平台同步） |
| `/flow-status` | 查看所有需求的进度、当前阶段、风险汇总（无需启动编排器） |
| `/team-init` | 初始化项目配置，连接团队知识仓库，绑定 `repos[]`、业务领域和技术栈 |
| `/knowledge` | 知识库维护（status / lint / sync / query / add / fact-check / promote） |
| `/evolve` | 流水线进化分析（基于 Bug 追溯 Agent 环节，产出改进建议存入进化日志） |
| `/evolve-apply` | 流水线进化落地（仅 Owner 使用，浏览 pending 记录后逐条审阅落地） |
| `/guard` | 守卫模式开关（开启后 AI 不直接执行操作，逐步确认推进） |

<!-- END AUTO-GEN: readme-commands-table -->

## 可用 Skills

> 双平台镜像维护，`.codebuddy/` 与 `.claude/` 各自的 `skills/` 目录中均包含以下 Skills（标 ⚠️ 的为单平台特例，详见末尾「待办」）。

**核心工作流类**

| Skill | 用途 |
|-------|------|
| `workflow-orchestrator` | 核心编排 — 15 阶段状态机 + Agent Teams + 三级降级 + 知识闭环 |
| `knowledge-evolution` | 知识进化引擎 — 提取 + 存储 + 按需查询 + 生命周期 + 衰减 |
| `figma-d2c` | Figma 设计稿转代码（16 步检查点协议 CP-0 → CP-M） |
| `prd-creator` | 苏格拉底式渐进提问引导创建 PRD |
| `quality-guardian` | 全流程质量监控（质量看板、回退分析、趋势对比） |
| `team-hub` | 团队级多需求协同管理（角色看板、瓶颈分析、资源冲突检测） |

**集成 / 协作类**

| Skill | 用途 |
|-------|------|
| `tapd-toolkit` | TAPD 集成（图片上传、附件上传/查询/下载，补充 MCP 原生工具） |
| `git-push-helper` | Git 自动化推送（暂存 → AI 生成 commit message → 推送 + MR + 通知） |
| `send-flow-message` | 通过 Redis 消息队列向企微群发送通知（卡片 / Markdown） |
| `iwiki-operation` ⚠️ | iWiki 文档创建/修改（仅 `.codebuddy/`，依赖 iwiki MCP） |
| `mcp-setup-guide` | MCP 服务配置引导（TAPD / iWiki / Figma 等） |

**元能力 / 优化类**

| Skill | 用途 |
|-------|------|
| `capability-router` | 意图分析与 Skill 路由（Skills 系统的智能前端） |
| `model-router` | 多模型路由（按任务复杂度/上下文长度/成本预算选模型） |
| `skill-learner` | Skill 自学习引擎（基于历史数据评估优化 Skill / Agent 表现） |
| `skill-creator` | 创建 / 改进 / 评测 Skill 的元工具 |
| `token-budget-manager` | Token 预算管理（消耗追踪、预警、成本优化） |

**通用文档处理类**（来自 Anthropic 官方 Skills）

| Skill | 用途 |
|-------|------|
| `pdf` | PDF 读写（提取/合并/分割/旋转/水印/OCR/表单） |
| `docx` | Word 文档处理（创建、读取、编辑 .docx，支持表格、目录、图片） |

<img width="" src="/uploads/7dcc47b8fb7440f0b3836c09dff6400a/image.png" alt="image.png" />

---

## 开发者工具链（仓库根 `scripts/` + `meta/`）

> **⚠️ 仅引擎维护者使用** — 团队小伙伴在业务项目使用工作流时，按上方「[安装](#安装)」段落 `cp -r .codebuddy/` + `cp -r .claude/` 即可，**完全不需要拷贝 `scripts/` / `meta/` / `ARCHITECTURE.md` 等**。`/flow-run` 等运行时命令与本工具链完全解耦。
>
> 需要 Python 3.8+。`pip3 install -r scripts/requirements.txt` 安装依赖（jsonschema / PyYAML / Jinja2 / pytest）。

### 已交付（端到端实测通过）

| 工具 | 何时跑 | 解决什么 | 实测状态 |
|------|------|---------|---------|
| `python3 scripts/consistency_check.py` | 改完代码 / pre-commit | **12 维度**一致性体检（双平台对称、阶段流转、Agent 注册、AUTO-GEN 区段 hash、DSL ↔ JSON 等价、DSL sentinel 等） | ✅ 实测通过 |
| `python3 scripts/impact_analyzer.py --git-status` | 改完待 commit | 列出本次改动需要同步的 ARCHITECTURE 章节 / 双平台镜像目标 | ✅ 实测通过 |
| `python3 scripts/dry_run.py` | 改完阶段流转后 | **仅校验状态机骨架**（图遍历级，非业务路径） | ✅ 实测通过 |
| `python3 scripts/render_artifacts.py` | 改完 4 个核心大表 | AUTO-GEN 区段 hash 校验（保护模式，hash 失配触发警告） | ✅ 实测通过 |
| `python3 scripts/render_artifacts.py --write-json --write` | 改完 `meta/*.yaml` DSL | **DSL → JSON 编译**（双平台 4 个 JSON 重写 + sentinel 注入），canonical 格式 | ✅ Phase 2.5 引入 |
| `python3 scripts/validate_meta.py` | 改完 `meta/*.yaml` DSL | DSL 内部一致性 + DSL ↔ JSON canonical-equal 校验 | ✅ 实测通过 |
| `python3 scripts/mirror_platforms.py --status` | 双平台同步前 | 列出**未豁免**的真实漂移（方言-only 差异自动静默） | ✅ Phase 3-new 引入 |
| `python3 scripts/mirror_platforms.py --mirror=<file> --from=codebuddy --write` | 单文件同步 | 把 `.codebuddy/<file>` 全量覆盖到 `.claude/<file>`（**不翻译**，覆盖前看 diff） | ✅ Phase 3-new 引入 |
| `python3 -m pytest scripts/tests` | lib/ 改动后 | lib/ 共享库单元测试（**115 个用例 < 8s**） | ✅ Phase R / V 引入 |
| `python3 scripts/render_visualization.py --write` | 改完 `phases/` / `agents/` / `rules/` / `templates/` / `references/` / `SKILL.md` | 重新生成 `docs/workflow-visualization.html`（**单文件零依赖**交互式工作流地图，pre-commit hook 自动跑） | ✅ Phase V 引入 |
| `bash scripts/hooks/install.sh` | 仅需一次 | 安装 Git pre-commit hook（warn 模式默认；严格模式见 [hooks/README.md](./scripts/hooks/README.md)） | ✅ 端到端实测 |

所有脚本支持 `--format=console|md|json`，退出码 `0` PASS / `1` WARN / `2` FAIL / `3` ERROR。详见 [`scripts/README.md`](./scripts/README.md)。

### 显式不做（Plan v2 主体声明）

为避免 v1 教训（宏大承诺—暗自降级），v2 显式声明**不做**以下事项：

- ❌ **不做自动方言翻译** — `.codebuddy/` ↔ `.claude/` 工具名 / IDE 名等方言差异由维护者人工同步；mirror 工具仅做对账与单文件覆盖
- ❌ **不做 30 条业务路径模拟** — `dry_run.py` 仅做图遍历级状态机骨架自检
- ❌ **不强求 byte-equal** — DSL 编译产出与现有 JSON 仅要求对象树等价（canonical-equal），不强求字符级一致
- ❌ **不做 SKILL.md 全文拆分** — 76KB 单文件已通过 4 个 AUTO-GEN 区段缓解关键漂移
- ❌ **不引入运行时校验** — state.json 实际读写正确性靠真实跑 `/flow-run` 验证
- ❌ **不引入 CI**（候选项，登记在 ARCHITECTURE 附录 C，按需启动）

### 已知 v1 遗留问题

- ~~`meta/state-schema.yaml` 比 `.claude/.../state-schema.json` 多一个 `docsRepoCommitLog` 字段~~ **Phase 2.5 已修复**：disk JSON 现含 `docsRepoCommitLog` 完整字段定义 + `$generatedFrom` sentinel
- 双平台 13 项内容差异（**Phase 3-new 已消除 76% 噪声**：从 54 → 13；剩余 13 项是真功能差异，需维护者人工同步——不在工具自动覆盖范围）

### AUTO-GEN 区段（Phase 1 引入）

SKILL.md §2.1/§10、ARCHITECTURE.md §4.2、README.md 命令表已用 `<!-- BEGIN AUTO-GEN: ... hash=<sha256> -->` 包裹。改完区段内容后必须运行 `python3 scripts/render_artifacts.py --rerender --write` 更新 hash。

### DSL 单一真相源（Phase 2 引入，Phase 2.5 落地权威切换）

`meta/phases.yaml` / `state-schema.yaml` / `commands.yaml` / `platform-divergence.yaml` 是阶段定义 / state.json schema / 命令清单 / 双平台豁免的"作者源"。详见 [`meta/README.md`](./meta/README.md)。

**Phase 2.5 起，`.{platform}/.../references/state-schema.json` + `phase-transitions.json` 头部含 `$generatedFrom` sentinel**，明示该 JSON 由 DSL 编译产出。直接编辑 disk JSON 会被 `dsl-equivalence` / `dsl-source-marker` 体检维度捕捉。改完 DSL 后运行 `python3 scripts/render_artifacts.py --write-json --write` 重生成。

### 平台方言豁免（Phase 3-new 引入）

`meta/platform-divergence.yaml` 的 `paired_translation` 段登记 17 条已确认方言映射对（5 类：term / tool_name / ide_name / path / config_file）。`platform-symmetry` 体检在判定双平台 content-diff 时，先 normalize（把双方文本中所有 claude 形式替换为 codebuddy 基线），相等则视为方言-only 差异，自动豁免。**不引入自动翻译镜像** — 维护者改完 `.codebuddy/` 后人工翻译同步到 `.claude/`，工具只做对账：

```bash
# 列出需要人工同步的真漂移
python3 scripts/mirror_platforms.py --status

# 全量覆盖单文件（不翻译，覆盖前看 diff）
python3 scripts/mirror_platforms.py --mirror=commands/flow-run.md --from=codebuddy --write
```

### Phase 进度（诚实清单）

- ✅ **Phase 0** — 静态校验三件套（体检 / 影响分析 / dry-run）已交付
- ✅ **Phase 1** — 4 个核心大表 AUTO-GEN 区段化已交付
- ✅ **Phase 2** — DSL canonical-equal 校验已交付
- ✅ **Phase R**（v2 收口）— pytest 套件 61+ 用例、pre-commit hook 端到端实测、文档诚实化
- ✅ **Phase 2.5** — DSL 真权威源切换（`$generatedFrom` sentinel 注入 + `--write-json` 模式 + 第 12 体检维度）
- ✅ **Phase 3-new** — 方言豁免清单 + normalize 体检静默（FAIL 从 54 → 13，76% 噪声消除）
- ⏳ **Phase 4 候选项** — 30 条业务路径模拟 / 自检清单机器化 / CI 集成（按需启动，登记在 ARCHITECTURE 附录 C）

详细演化脉络见 [`ARCHITECTURE.md` 附录 A](./ARCHITECTURE.md#附录-a更新日志)。

---

## 目录结构

```
仓库根/
├── README.md                          # 本文件（项目全景 + 更新日志）
├── CLAUDE.md  +  CODEBUDDY.md          # AI 协作约定（迭代本仓库时生效，详见文件本身）
│
├── .codebuddy/   ←─┐                   # CodeBuddy 平台
└── .claude/      ←─┘                   # Claude Code 平台（与 .codebuddy/ 镜像维护）
    ├── skills/                         # Skill 定义（19 / 18 个）
    │   ├── workflow-orchestrator/      # 🧠 核心编排器
    │   │   ├── SKILL.md                #   15 阶段状态机 + Agent Teams + 流转守卫
    │   │   ├── agents/                 #   子 Agent 定义
    │   │   │   ├── product-analysts/   #     ANALYSE_PRODUCT 4 成员团队
    │   │   │   ├── tech-analysts/      #     ANALYSE_TECH 4 成员团队
    │   │   │   ├── backend-developers/ #     IMPLEMENT 后端领域开发通用规范
    │   │   │   ├── build-verifiers/    #     BUILD_VERIFY 多平台并行验证
    │   │   │   ├── import-agents/      #     /flow-import 3 Agent 串行管道
    │   │   │   └── *.md                #     单体/降级 Agent + 架构师 + 验收/归档
    │   │   ├── phases/                 #   阶段调度规则（按需加载）
    │   │   │   ├── architect-backend-level{1,2,3}.md   #   三级降级独立文件
    │   │   │   ├── analyse-product-rules.md / ...      #   各阶段主规则
    │   │   │   └── output-formats/     #     预览/总结/澄清的格式模板
    │   │   ├── references/             #   Schema (state/risks/clarify/import/...)
    │   │   ├── rules/                  #   编码规范、LSP、视觉协议、知识查询协议
    │   │   ├── templates/              #   Agent Prompt 模板
    │   │   └── scripts/                #   resolve_agent_paths.py 等
    │   ├── knowledge-evolution/        # 知识进化引擎
    │   ├── figma-d2c/                  # Figma D2C
    │   ├── prd-creator/ / quality-guardian/ / team-hub/ / capability-router/
    │   ├── tapd-toolkit/ / git-push-helper/ / send-flow-message/ / mcp-setup-guide/
    │   ├── model-router/ / skill-learner/ / skill-creator/ / token-budget-manager/
    │   ├── pdf/ / docx/                # 通用文档处理
    │   └── iwiki-operation/            # ⚠️ 仅 .codebuddy/
    │
    ├── commands/                       # 9 个用户命令
    │   ├── flow-run.md / flow-import.md / flow-upgrade.md / flow-status.md
    │   ├── team-init.md / knowledge.md
    │   ├── evolve.md / evolve-apply.md
    │   └── guard.md                    # 守卫模式开关
    │
    ├── references/                     # 顶层引用资料
    │   ├── agent-catalog/              # 第 2 层综合指南（Agent 系统全景导航）
    │   ├── workflow-templates/         # 工作流模板
    │   └── legacy-docs/                # 历史文档归档
    │
    ├── rules/                          # 业务项目用编码规则（与本引擎自身无关）
    │   ├── tcb/                        # CloudBase 开发指南
    │   └── anydev/                     # AnyDev 开发指南
    │
    └── plans/                          # 临时规划草稿（非核心，可忽略）
```

> 「业务项目用编码规则」与「引擎自身协作约定」的边界：`.{platform}/rules/` 是**业务项目集成的**编码规则，会随 `.codebuddy/` 一起部署到业务项目；`CLAUDE.md` / `CODEBUDDY.md` 是**仅本仓库迭代时生效**的协作约定，不会被部署。

---

## 设计哲学

| 原则 | 实现 |
|------|------|
| **IDE 原生** | `.codebuddy/` + `.claude/` 双平台镜像目录驱动，无独立平台、无数据库 |
| **文件即状态** | `state.json` 管理工作流，阶段产物即进度凭证 |
| **知识是核心资产** | 团队共享 Git 知识仓库，三级成熟度 + 贡献追踪 + 不可变日志 |
| **按需消费** | 三层渐进索引，Agent 主动查询而非被动推送 |
| **单仓多仓统一** | `repos[]` 模型，单仓 = 1 个元素，多仓 = N 个元素，零分支判断 |
| **人机协同** | 三步模式（Preview → Execute → Summary），每步人工可控 |
| **安全降级** | Agent Teams 三级降级 + 检查点断点恢复 |

## 设计灵感

- **[Karpathy LLM Wiki](https://gist.github.com/karpathy/1dd0294ef9567971c1e4348a90d69285)** — 知识复合增长：Ingest + Query + Lint
- **[vibe-coding](../vibe-coding/)** — 生产验证的文件状态机 + Agent 编排模式
- **[oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode)** — IDE 原生 Skill/Rule 架构

---

## 更新日志

> 用于记录引擎自身的架构性迭代历史，便于新对话开始时快速了解项目演化脉络。
> 维护约定见 [`CLAUDE.md`](./CLAUDE.md) / [`CODEBUDDY.md`](./CODEBUDDY.md) — 凡是涉及命令/Skill/Agent/16 阶段流程/知识体系/部署拓扑等"用户可见行为"的变更，都需要在此追加一条记录。

### 格式约定

每条记录使用 `### YYYY-MM-DD — 一句话主题` 作为小节标题，正文按以下结构组织（无内容的小节可省略）：

- **背景 / 动机**：为什么做这次变更
- **变更内容**：具体改了什么（按 commands / skills / agents / phases / knowledge / docs 分类）
- **影响面**：用户可观察到的行为变化、是否需要重新部署 / 重新跑 `/team-init`
- **关联文件**：本次变更涉及的核心文件路径

### 2026-05-28 — 修复 TEST → ARCHIVE 不自动流转的工作流缺陷

- **背景 / 动机**：团队反馈"执行完需求流程后没有自动触发 archive 流程"。排查发现：`BUILD_VERIFY` / `VISUAL_REVIEW` 两阶段在各自的 `phases/*-rules.md` 末尾都有显式的「完成处理 → 流转下一阶段」分步表（更新 `state.json.currentPhase` + 进入下一阶段预览 + 严禁操作清单），但 `TEST` 阶段在 `agents/test-engineer.md` 末尾**仅有 qualityGate 的文案性"提示进入 ARCHIVE"**，没有同等强度的指令。叠加 SKILL.md §10 阶段规则按需加载映射表中没有 `TEST` / `ARCHIVE` 行（仓库内根本不存在 `phases/archive-rules.md`）、§2.2 流转守卫只有「BUILD_VERIFY PASS ≠ 工作流完成」而没有「TEST PASS ≠ 工作流完成」、TEST 又被 §12.3 通知映射归类为"低人工介入、不发送通知"的阶段，导致编排器在 TEST 总结展示后极易误判工作流到此结束，静悄悄停在 `currentPhase = TEST`。
- **变更内容**：
  - `agents/test-engineer.md`：在「编排器对接行为（TEST 阶段）」末尾新增 §「TEST 完成后的流转指令（CRITICAL）」，含 5 步流转分步表（含加载 `phases/archive-rules.md` + 更新 `currentPhase` → `ARCHIVE` + 进入 ARCHIVE 预览）+「严禁操作」清单 +「常见漂移场景提醒」+ 完整剩余流程图（TEST → ARCHIVE → DONE）。
  - `phases/archive-rules.md`：**新建**，定义 ARCHIVE 进入条件、三步模式（预览/执行/总结确认）、状态机约束（`DONE` 写入唯一入口 = archiver Agent）、严禁操作、回退行为、完成检查清单。
  - `SKILL.md` §10 阶段规则按需加载映射表：补充 `TEST`（指向 test-engineer.md 末尾流转指令）和 `ARCHIVE`（指向 `phases/archive-rules.md` + `agents/archiver.md`）两行。
  - `SKILL.md` §2.2 流转守卫：在「BUILD_VERIFY PASS ≠ 工作流完成」之后追加「TEST PASS ≠ 工作流完成」防漂移条款，明确 TEST 总结确认后必须立即更新 `currentPhase` → `ARCHIVE`。
  - `agents/archiver.md` 协作关系图：把模糊描述「编排器: 所有阶段完成后触发 ARCHIVE」改为精确指令（依据 `phase-transitions.json` 守卫 + 加载 `phases/archive-rules.md` + 进入 ARCHIVE 三步模式）。
  - `commands/flow-status.md`：阶段总数 `({N}/13)` → `({N}/15)` 与实际状态机对齐（顺手修正历史遗留的过时常数）。
- **影响面**：用户可观察到的行为变化 — 完成 `TEST` 阶段并选择"继续"后，编排器会立即进入 `ARCHIVE` 阶段的预览（而不再是停在 TEST 不动）；归档完成后 `state.json.currentPhase` 会被 archiver 写为 `DONE`，工作流正常收尾。无需重新部署 / 无需重跑 `/team-init`；正在进行中的工作流如果当前已停留在 `TEST` 阶段，下次对编排器发指令"继续"即可正常推进到 `ARCHIVE`。
- **关联文件**：`.claude/skills/workflow-orchestrator/agents/test-engineer.md`、`.claude/skills/workflow-orchestrator/agents/archiver.md`、`.claude/skills/workflow-orchestrator/phases/archive-rules.md`（新建）、`.claude/skills/workflow-orchestrator/SKILL.md`、`.claude/commands/flow-status.md`，以及 `.codebuddy/` 下全部对称文件。

### 2026-05-27 — README 深度梳理 + 引入更新日志机制

- **背景**：随着引擎 19 个 Skill / 25+ 个 Agent / 15 阶段状态机持续演进，原 README 存在多处事实漂移（如「16 阶段」「12 个 Skills」「`/guard` 用途描述」等），且没有迭代历史的沉淀位置。
- **变更内容**：
  - `README.md`：
    - 修正「16 阶段」→「15 阶段」，重画状态机流程图（补全 4 个 `CLARIFY_*` 阶段）；
    - 阶段表从 7 行扩展到完整 16 行（0=INIT … 15=DONE），新增 Agent / 行为列；
    - 「核心工程机制」从 6 项扩到 11 项（新增流转守卫、阶段计时协议、运行时上下文健康度、knowledgeReferences 校验、@changelog 溯源、通知机制等）；
    - 新增「Agent 编制全景」「D2C 双模式（standalone / embedded）」「多仓文档仓（docsRoot / docsRepoMode）」三个小节；
    - 「可用 Skills」从 12 个补全到 19 个，按「核心工作流 / 集成协作 / 元能力 / 通用文档处理」四组重新分组；
    - 「可用命令」修正 `/guard` 描述（守卫模式开关 ≠ 变更守护检查）；
    - 「安装」「部署拓扑」「目录结构」「设计哲学」全部升级为双平台（`.codebuddy/` + `.claude/`）描述；
    - 引入本「更新日志」板块。
  - `CLAUDE.md` / `CODEBUDDY.md`（昨日已新建）：作为「迭代本仓库时」的 AI 协作约定，要求每次对话先读 README、架构性变更同步 README、双平台对称维护。
- **影响面**：纯文档变更，不影响任何运行时行为。新建对话时 AI 将自动读取 README + CLAUDE.md/CODEBUDDY.md 建立项目背景认知。
- **关联文件**：`README.md`、`CLAUDE.md`、`CODEBUDDY.md`。

---

## 已知待办（不对称项 / 待回归项）

> 这些是当前已知但尚未处理的不一致项，记录于此防止遗忘。处理后请移到「更新日志」并删除本条目。

- [ ] **`iwiki-operation` Skill 仅存在于 `.codebuddy/skills/`**，`.claude/skills/` 缺失。需评估是否将其同步到 Claude Code 平台（或在 README 显式标注为单平台特例并保持现状）。
- [ ] **`.codebuddy/plans/` 含 1 个临时草稿文件**（`team-sharing-blog-post_*.md`），`.claude/` 无对应目录。需决定是删除草稿、转入 `references/` 还是双平台对齐。
- [ ] **`.codebuddy/skills/README.md`** 中列出的 Skills 共 15 个，与实际目录数（19 个）不一致，待与本 README 表格对齐。

---

## License

MIT
