# AI Team — AI 工程交付编排系统

> 基于 CodeBuddy IDE 的 Skill / Command / Rule 体系，实现多 Agent 协作的全流程需求交付自动化。
> **核心理念**：文件系统即状态机，团队知识持续沉淀，越用越聪明。

---

## 这是什么

AI Team 是一套**工作流引擎**，安装到你的业务项目后，用一条命令 `/flow-run` 驱动 AI Agent 完成从需求分析到代码归档的全流程。它不是一个独立平台，而是一组 `.codebuddy/` 目录下的 Skill、Agent、Command 定义文件，被 CodeBuddy IDE 原生识别和执行。

**核心价值**：Skill、Agent、工具链会随模型迭代更新，但**领域知识是永恒的**。AI Team 的每次交付都自动沉淀知识到团队共享仓库，所有成员共建共享，新工作流启动时自动站在前人肩上。

<img width="" src="/uploads/d949dcaa81064a538e4c4dc3406af2cc/image.png" alt="image.png" />

---

## 部署拓扑

支持单仓和多仓（小仓/微服务拆分），统一 `repos[]` 模型，无需切换模式。

**单仓模式**（一个 Git 仓库包含所有代码）：
```
工作区根/（= Git 仓库根）
├── .codebuddy/               ← 引擎副本
├── .ai-team/project.yaml     ← 知识锚点
├── docs/workflows/            ← 工作流产物
├── src/                       ← 你的代码
└── pom.xml / package.json

→ repos[]: [{ name: "my-project", path: "./", type: "fullstack" }]
```

**多仓模式**（多个独立 Git 仓库，微服务拆分）：
```
工作区根/（CodeBuddy 打开的父目录，不是 Git 仓库）
├── .codebuddy/               ← 引擎副本
├── .ai-team/project.yaml     ← 知识锚点
├── docs/workflows/            ← 工作流产物（不属于任何 Git 仓库）
│
├── ad-service/        (.git/) ← Git 仓库 A（后端微服务）
├── creative-service/  (.git/) ← Git 仓库 B（后端微服务）
└── ad-frontend/       (.git/) ← Git 仓库 C（前端）

→ repos[]: [
    { name: "ad-service",       path: "ad-service/",       type: "backend" },
    { name: "creative-service", path: "creative-service/",  type: "backend" },
    { name: "ad-frontend",      path: "ad-frontend/",       type: "frontend" }
  ]
```

两种模式的工作流完全一致：INIT 自动扫描填充 `repos[]`，后续阶段遍历 `repos[]` 执行。

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

在你的业务项目中打开 CodeBuddy，粘贴给 Agent：

```
请帮我从远程仓库拉取 ai-team 工作流系统到当前工作区。按顺序执行：

1. cd {当前工作区根目录}
   git clone --depth 1 git@git.woa.com:Agentic-CE-Infra/ur-ai-team.git .ai-team-install

2. cp -r .ai-team-install/.codebuddy ./

3. rm -rf .ai-team-install

4. 验证：检查 .codebuddy/skills/ 和 .codebuddy/commands/ 目录是否存在。

完成后告诉我安装结果。
```

安装后 `.codebuddy/` 目录立即被 IDE 识别。后续更新重新执行即可覆盖。

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

## 工作流：16 阶段状态机

```
/flow-run 启动后自动流转：

INIT → ANALYSE_PRODUCT → ANALYSE_TECH → ARCHITECT_BACKEND → ARCHITECT_FRONTEND
  → ARCHITECT_MINIPROGRAM → IMPLEMENT → BUILD_VERIFY → VISUAL_REVIEW
  → E2E_VERIFY → TEST → ARCHIVE → DONE
```

每个阶段遵循**三步模式**：Preview（预览计划）→ Execute（执行）→ Summary（总结确认），确保每一步人工可控。

### 各阶段做什么

| 阶段 | Agent | 做什么 |
|------|-------|--------|
| **ANALYSE_PRODUCT** | 4-5 成员 Agent Teams | 需求分析：迭代判定、基线对比、用户故事/业务规则提取、视觉分析 |
| **ANALYSE_TECH** | 4 成员 Agent Teams | 技术分析：按 repos[] 逐仓库扫描、3 轮递进复用搜索、技术方案设计、分端拆解、校审 |
| **ARCHITECT** | 架构师 Agent | 后端/前端/小程序架构设计，数据库设计，API 契约定义 |
| **IMPLEMENT** | 各端开发 Agent 并行 | 按 repos[] 分配文件所有权，每个仓库独立 Agent，LSP 实时诊断 |
| **BUILD_VERIFY** | 验证 Agent | 按 repos[] 逐仓库编译（各自 buildCommand），LSP 预扫描 |
| **VISUAL_REVIEW** | 视觉验收 Agent | AI 对比设计稿 vs 实现截图，还原度评分（A/B/C/D/F） |
| **ARCHIVE** | @archiver | 归档 + 知识提取 + 团队知识仓库同步（Git push） |

### 核心工程机制

| 机制 | 说明 |
|------|------|
| **上下文防火墙** | 搜索密集型工作在独立上下文窗口执行，仅将结构化结论（~10x 压缩）传递给下游 |
| **IntentGate** | INIT 后自动意图分析：四分类 + 歧义检测 + 影响估算 + 路由提示 |
| **三级降级** | L1 Agent Teams → L2 Task 串行管道 → L3 编排器直接执行 |
| **检查点恢复** | ARCHITECT 四阶段追踪，ANALYSE_PRODUCT 三级恢复 |
| **LSP 诊断** | IMPLEMENT 每次写入后 `read_lints`，BUILD_VERIFY 全项目扫描 |
| **搜索预算** | 每个 Agent 有独立搜索配额，LSP → Grep → Glob → codebase_search 优先链 |

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

| 命令 | 用途 |
|------|------|
| `/flow-run` | 启动交付工作流 |
| `/flow-import` | 历史项目知识导入（支持 Git/TAPD/iwiki/本地文档/口述） |
| `/flow-upgrade` | 工作流版本更新（版本对比 + 选择性更新） |
| `/flow-status` | 查看工作流状态 |
| `/team-init` | 初始化项目配置，连接团队知识仓库 |
| `/knowledge` | 知识库维护（status/lint/sync/query/add/fact-check/promote） |
| `/evolve` | 分析改进建议 |
| `/evolve-apply` | 落地改进 |
| `/guard` | SKILL/Rule 变更守护检查 |

## 可用 Skills

| Skill | 用途 |
|-------|------|
| `workflow-orchestrator` | 核心编排 — 16 阶段状态机 + Agent Teams + 知识闭环 |
| `knowledge-evolution` | 知识进化引擎 — 提取 + 存储 + 按需查询 + 生命周期 |
| `figma-d2c` | Figma 设计稿转代码（16 步检查点协议） |
| `prd-creator` | 结构化 PRD 创建 |
| `git-push-helper` | 智能 Git 提交推送 + MR + 通知 |
| `quality-guardian` | 全流程质量监控 |
| `capability-router` | 意图分析与 Skill 路由 |
| `tapd-toolkit` | TAPD 集成 |
| `team-hub` | 多角色协作 |
| `model-router` | 多模型路由 |
| `skill-learner` | Skill 效果分析与优化 |
| `token-budget-manager` | Token 预算管理 |

<img width="" src="/uploads/7dcc47b8fb7440f0b3836c09dff6400a/image.png" alt="image.png" />

---

## 目录结构

```
.codebuddy/
├── skills/                              # Skill 定义
│   ├── workflow-orchestrator/           # 🧠 核心编排器
│   │   ├── SKILL.md                     #   16 阶段状态机 + Agent Teams
│   │   ├── agents/                      #   子 Agent 定义（动态调度）
│   │   ├── phases/                      #   阶段调度规则
│   │   ├── references/                  #   Schema 定义（state-schema.json 等）
│   │   ├── rules/                       #   编码规范、诊断策略、视觉协议
│   │   └── templates/                   #   Agent Prompt 模板
│   ├── knowledge-evolution/             # 知识进化引擎
│   ├── figma-d2c/                       # Figma D2C
│   ├── prd-creator/                     # PRD 创建器
│   ├── quality-guardian/                # 质量守卫
│   └── ...                              # 其余 Skills
│
├── commands/                            # 用户命令
│   ├── flow-run.md                      # 启动交付工作流
│   ├── flow-import.md                   # 历史知识导入
│   ├── flow-upgrade.md                  # 工作流版本更新
│   ├── flow-status.md                   # 工作流状态查看
│   ├── knowledge.md                     # 知识库维护
│   ├── team-init.md                     # 初始化+连接知识仓库
│   └── ...                              # evolve, guard 等
│
├── rules/                               # 编码规则（java-backend, tcb, anydev）
└── memory/                              # 组织记忆
```

---

## 设计哲学

| 原则 | 实现 |
|------|------|
| **IDE 原生** | `.codebuddy/` 目录驱动，无独立平台、无数据库 |
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

## License

MIT
