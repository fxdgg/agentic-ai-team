# AI Team — CodeBuddy 原生 AI 工程交付编排系统

> 基于 CodeBuddy IDE 的 Skill / Command / Rule 体系，实现多 Agent 协作的全流程需求交付自动化。
> **核心理念**：不另起炉灶，增强 IDE 原生能力 — 文件系统即状态机，知识闭环驱动持续进化。

### 设计哲学

| 原则 | 实现 |
|------|------|
| **IDE 原生** | 通过 `.codebuddy/` 目录结构驱动，无独立平台、无数据库 |
| **文件即状态** | `state.json` 管理工作流状态，阶段产物即进度凭证 |
| **人机协同** | 三步模式（Preview → Execute → Summary）确保每一步人工可控 |
| **知识驱动** | 每次交付自动沉淀知识，下次交付自动消费，越用越聪明 |
| **安全降级** | Agent Teams 三级降级 + 检查点断点恢复，保障交付可靠性 |

## 🏗️ 架构概览

![工作流全流程深度剖析](<img width="" src="/uploads/07b80b94fd604ec3ad03159b45462398/image.png" alt="image.png" />
)

<details>
<summary>📐 文本版架构图（点击展开）</summary>

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         用户交互层 (Commands)                           │
│                                                                         │
│  /flow:run        /flow:import       /flow:status     /evolve          │
│  启动交付工作流    历史知识导入        查看工作流状态    分析改进建议       │
│  /evolve:apply    /guard                                                │
│  落地改进          守护检查                                               │
└──────────┬──────────────────────────────────┬───────────────────────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────────────┐  ┌───────────────────────────────────────┐
│  🧠 编排引擎 (Orchestrator)  │  │  🛡️ 辅助 Skills                       │
│                              │  │                                       │
│  16 阶段状态机               │  │  prd-creator      PRD 创建             │
│  ┌────────────────────────┐  │  │  git-push-helper  智能提交推送         │
│  │ Step 0: 项目状态探测   │  │  │  figma-d2c        设计稿转代码         │
│  │   知识分+代码分→类型判定│  │  │  tapd-toolkit     TAPD 集成            │
│  ├────────────────────────┤  │  │  capability-router 意图路由            │
│  │ IntentGate 意图分析层  │  │  │  model-router     多模型路由           │
│  │   四分类+歧义检测+路由  │  │  │  token-budget     预算管理             │
│  ├────────────────────────┤  │  │  quality-guardian  质量守卫             │
│  │ ANALYSE_PRODUCT        │  │  │  team-hub         团队协作             │
│  │   4-5 成员 Agent Teams │  │  │  mcp-setup-guide  MCP 配置引导         │
│  │   +知识基线+视觉分析    │  │  └───────────────────────────────────────┘
│  ├────────────────────────┤  │
│  │ ANALYSE_TECH           │  │  ┌───────────────────────────────────────┐
│  │   3 成员 Agent Teams   │  │  │  📥 知识导入分支 (/flow:import)        │
│  │   +代码画像注入         │  │  │                                       │
│  ├────────────────────────┤  │  │  @doc-collector → @codebase-profiler  │
│  │ ARCHITECT → IMPLEMENT  │  │  │       → @knowledge-builder            │
│  │   检查点保护+断点恢复   │  │  │  产出 → 知识闭环层消费                 │
│  ├────────────────────────┤  │  └───────────────────────────────────────┘
│  │ BUILD_VERIFY → TEST    │  │
│  │   LSP预扫描+多平台验证  │  │
│  ├────────────────────────┤  │
│  │ VISUAL_REVIEW          │  │
│  │   设计稿vs实现AI验收    │  │
│  ├────────────────────────┤  │
│  │ ARCHIVE                │  │
│  │   归档+知识提取+推送    │  │
│  └────────────────────────┘  │
│                              │
│  Preview → Execute → Summary │
│  (每阶段三步，人工可控)       │
└──────────┬───────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     🔄 知识闭环层 (Knowledge Loop)                      │
│                                                                         │
│  ┌── 沉淀 ──────────────────┐     ┌── 消费 ──────────────────────┐     │
│  │                           │     │                               │     │
│  │  📦 归档沉淀              │     │  🔍 历史归档检索               │     │
│  │  SUMMARY.md + memory      │◄───►│  PRD 创建时关键词匹配         │     │
│  │                           │     │                               │     │
│  │  🧬 知识进化              │     │  💡 知识推送                   │     │
│  │  6类知识 + confidence评分 │◄───►│  Agent 启动时 Top-5 注入      │     │
│  │                           │     │                               │     │
│  │  📥 历史知识导入          │     │  📊 迭代基线对比               │     │
│  │  /flow:import → 知识基线  │◄───►│  增量变更分析                  │     │
│  │  confidence 0.5-0.6 起始  │     │                               │     │
│  │                           │     │  ♻️ 复用评级                   │     │
│  │  🔧 流水线进化            │     │  🟢🟡🟠🔴⚪ 五级强制复用        │     │
│  │  Bug→Agent根因→改进建议   │◄───►│                               │     │
│  │                           │     │  ⬆️ 流水线升级                 │     │
│  └───────────────────────────┘     │  Owner 审阅→Agent/Rule 升级   │     │
│                                    └───────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     📁 基础设施层 (文件系统即状态机)                      │
│                                                                         │
│  state.json           docs/workflows/        docs/knowledge-base/       │
│  工作流状态+上下文健康度  阶段产物+归档           结构化知识库              │
│                                                                         │
│  .codebuddy/memory/   docs/prd/              docs/knowledge-import/     │
│  组织记忆               需求文档                历史知识导入产物           │
└─────────────────────────────────────────────────────────────────────────┘
```

</details>

## 📦 一键安装

> **无需 clone 整个仓库**。在你的项目中打开 CodeBuddy，粘贴以下提示词给 Agent 即可自动拉取。

```
请帮我从远程仓库拉取 ai-team 工作流系统到当前工作区。按顺序执行以下命令：

1. 在当前工作区内浅克隆仓库（--depth 1 仅拉最新一次提交，速度快）：
   cd {当前工作区根目录}
   git clone --depth 1 git@git.woa.com:Agentic-CE-Infra/ai-team.git .ai-team-install

2. 将 .codebuddy/ 目录拷贝到工作区根目录：
   cp -r .ai-team-install/.codebuddy ./

3. 清理克隆目录：
   rm -rf .ai-team-install

4. 重要：不要在当前工作区执行 git init 或任何 git 配置操作，仅拷贝 .codebuddy/ 目录即可。

5. 验证安装成功：检查 .codebuddy/skills/ 和 .codebuddy/commands/ 目录是否存在。

完成后告诉我安装结果。
```

> **提示**：安装后 `.codebuddy/` 目录立即被 IDE 识别，可直接使用所有命令。此操作不改变工作区 Git 配置。后续更新重新执行即可覆盖。

## 🚀 快速开始

```bash
# 0. 首次使用：初始化项目配置，连接团队知识仓库（仅首次需要）
/team:init

# 1. 导入历史项目知识（已有代码库推荐先执行）
/flow:import

# 2. 启动交付工作流
/flow:run                              # 从上下文推断需求
/flow:run docs/my-requirement.md       # 从需求文档启动
/flow:run 实现用户注册功能              # 从文字描述启动

# 3. 查看工作流状态
/flow:status

# 4. 流程自进化
/evolve                                # 分析改进建议 + 上下文复盘
/evolve:apply                          # 审阅并落地改进

# 5. 防护模式
/guard                                 # 对 SKILL/Rule 修改进行守护检查
```

> **最佳实践**：对已有代码库的项目，先 `/team:init` 连接团队知识仓库，再 `/flow:import` 构建知识基线，最后 `/flow:run` 启动新需求。

## 🧠 核心能力：工作流编排器

### 16 阶段状态机

```
START → ANALYSE_PRODUCT → ANALYSE_TECH → ARCHITECT_BACKEND → ARCHITECT_FRONTEND
  → ARCHITECT_MINIPROGRAM → IMPLEMENT → BUILD_VERIFY → VISUAL_REVIEW
  → E2E_VERIFY → TEST → ARCHIVE → DONE
```

每个阶段支持三步模式（Preview → Execute → Summary），质量门禁和回退机制。

### Agent Teams 多 Agent 协作

| 阶段 | 模式 | 协作方式 |
|------|------|---------|
| ANALYSE_PRODUCT | 4-5 成员串行 | 上下文防火墙 + 三级降级 + 知识基线注入 + 视觉分析 |
| ANALYSE_TECH | 3 成员串行 | 代码画像注入，3 轮递进复用搜索 |
| ARCHITECT_BACKEND | 2 步混合 | 全局→领域架构，检查点保护 |
| IMPLEMENT | 并行领域开发 | 文件所有权声明 + LSP 实时诊断 |
| BUILD_VERIFY | 并行平台验证 | LSP 预扫描 + 终端编译双保险 |
| VISUAL_REVIEW | 设计还原度验收 | AI 驱动设计稿 vs 实现截图对比，评分+质量门禁 |
| knowledge-import | 3 成员串行 | 独立导入分支，产物文件即状态 |

### 核心工程机制

**上下文防火墙** — Agent Teams 的核心设计模式。搜索密集型工作在独立上下文窗口中执行，仅将结构化结论（~10 倍压缩）通过文件系统传递给下游，保持下游上下文窗口清洁。

**IntentGate 意图分析** — 轻量级前置层，在 INIT 之后自动执行：意图四分类（new-feature / feature-modify / bug-fix / tech-refactor）+ 歧义检测 + 影响范围估算 + 路由提示。

**运行时上下文健康度监控** — 全阶段工具调用计数（三级阈值预警）+ 压缩事件检测 + 预防性建议，数据持久化到 `state.json` 供 `/evolve` 复盘。

**LSP 实时诊断** — 编码即检查：IMPLEMENT 阶段每次文件写入后立即 `read_lints`，BUILD_VERIFY 阶段终端编译前 LSP 全项目扫描，5 步完成验证协议（IDENTIFY → LSP_SCAN → RUN → READ → CLAIM）。

**视觉分析与验收** — 设计稿/原型图结构化理解，驱动前端架构；VISUAL_REVIEW 阶段 AI 对比设计稿 vs 实现截图，还原度评分（A/B/C/D/F）与质量门禁。

**检查点与断点恢复** — ARCHITECT_BACKEND 状态追踪四阶段自动恢复；ANALYSE_PRODUCT 三级恢复（团队进度 → 断点 Task → 已有产物复用）。

**三级降级调度** — L1 Agent Teams（4-5 成员独立上下文）→ L2 Task 串行管道（角色合并）→ L3 orchestrator 直接执行。

## 🔄 知识传承 — 团队共建，越用越聪明

> **这是整个系统最重要的设计。** 知识是最有价值的资产——Skill、Agent、工具链都会随模型迭代更新，但**领域知识是永恒的**。AI Team 通过团队共享知识仓库，让每次交付自动沉淀经验，所有团队成员共建共享，每次启动自动站在前人肩上。

### 部署拓扑：.codebuddy 与知识仓库的关系

```
ai-team 项目（工作流引擎源码）
  /path/to/ai-team/
  └── .codebuddy/                    ← 工作流引擎定义（Skill + Agent + Command）
                                        这是"软件本身"

         ┌──── 一键安装：cp -r .codebuddy/ → 业务项目 ────┐
         ▼                                                ▼
业务项目 A (cloud-mall)                    业务项目 B (vibe-mall)
  ├── .codebuddy/        ← 引擎副本       ├── .codebuddy/        ← 引擎副本
  ├── .ai-team/                           ├── .ai-team/
  │   └── project.yaml   ← 知识锚点       │   └── project.yaml   ← 知识锚点
  │       domain: ecommerce               │       domain: ecommerce
  │       knowledge_repo:                 │       knowledge_repo:
  │         url: git@.../team-knowledge   │         url: git@.../team-knowledge
  │         local_path: ~/.ai-team/...    │         local_path: ~/.ai-team/...
  ├── src/               ← 项目源码       ├── src/
  └── docs/workflows/    ← 工作流产物     └── docs/workflows/
         │                                        │
         │   ARCHIVE 阶段                          │   ARCHIVE 阶段
         │   自动提取+push                          │   自动提取+push
         ▼                                        ▼
    ┌──────────────────────────────────────────────────┐
    │  团队知识仓库 (独立 Git 仓库，所有成员 clone)        │
    │  git@github.com:team/team-knowledge.git           │
    │                                                    │
    │  ├── .knowledge-config.yaml   ← 团队配置+成员列表   │
    │  ├── team-conventions/        ← 团队编码约定         │
    │  ├── tech-wiki/               ← 技术知识（按技术栈） │
    │  ├── biz-wiki/                ← 业务知识（按领域）   │
    │  │   ├── domains.yaml                              │
    │  │   ├── ecommerce/           ← 电商领域             │
    │  │   └── payment/             ← 支付领域             │
    │  └── contributions/           ← 贡献暂存/冲突        │
    └──────────────────────────────────────────────────┘
         ▲                                        ▲
         │   INIT 阶段                             │   INIT 阶段
         │   自动 pull+注入                         │   自动 pull+注入
         │                                        │
    Steven 的机器                             Alice 的机器
    ~/.ai-team/                               ~/.ai-team/
    ├── preferences/  ← 个人偏好(不共享)       ├── preferences/
    └── team-knowledge/ ← 知识仓库本地克隆     └── team-knowledge/
```

**关键理解**：
- `.codebuddy/` 是工作流引擎，复制到每个业务项目中运行
- `.ai-team/project.yaml` 是桥梁，告诉引擎去哪里找知识仓库
- `~/.ai-team/team-knowledge/` 是团队知识仓库的本地克隆，所有项目共享
- 知识的流动方向：ARCHIVE 阶段提取→push 到仓库；INIT 阶段 pull→注入给 Agent

### 团队使用流程

```bash
# ━━━ 团队负责人（一次性） ━━━
# 1. 在 GitHub/GitLab 创建空仓库: team-knowledge.git
# 2. 在第一个业务项目中：
/team:init
#    → 输入仓库地址 → 初始化目录骨架 → 注册为 maintainer → push

# ━━━ 团队成员（每人一次） ━━━
# 3. 在自己的业务项目中：
/team:init
#    → 输入同一个仓库地址 → clone → 注册为 contributor

# ━━━ 日常使用（全自动） ━━━
# 4. 正常开发：
/flow:run
#    INIT 阶段: 自动 git pull 知识仓库 → 注入 Top-5 知识给 Agent
#    ... 正常工作流 ...
#    ARCHIVE 阶段: 自动提取知识 → git push 到仓库
#    → 下一个人的工作流自动受益
```

### 知识闭环总览

```
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  冷启动导入  │────►│  基线注入    │────►│  阶段消费    │
  │ /flow:import │     │ INIT 阶段   │     │ 各 Agent 按需│
  └─────────────┘     └─────────────┘     └──────┬──────┘
                                                  │
  ┌─────────────┐     ┌─────────────┐            │
  │  下轮消费    │◄────│  按需查询    │◄───────────┤
  │ 新工作流复用  │     │ 渐进式加载  │            │
  └─────────────┘     └─────────────┘     ┌──────▼──────┐
                                          │  知识提取    │
                                          │ 5 触发点自动  │
                                          └──────┬──────┘
                                                  │
                                          ┌──────▼──────┐
                                          │  进化存储    │
                                          │ 6类+成熟度  │
                                          └─────────────┘
```

**完整数据流**：冷启动导入 → 基线注入 → 阶段按需查询 → 知识提取 → 进化存储 → 索引更新 → 下轮按需消费 → ∞

### 六层知识闭环机制

#### 第一层：冷启动导入（/flow:import）

对已有代码库的项目，提供独立于常规工作流的知识导入管道，帮助 AI 快速理解项目背景。

**三 Agent 串行流水线**：

| Agent | 职责 | 核心产出 |
|-------|------|---------|
| `@doc-collector` | 多源资料收集 — 文档 / TAPD 链接 / 口述 / 直接扫描 | `_doc-collection.json` |
| `@codebase-profiler` | 代码画像（60 次搜索预算）— 技术栈/模块/依赖/模式 | `codebase-profile.json` |
| `@knowledge-builder` | 知识标准化 — 4 维基线 + 知识库初始条目（≤13 条） | `knowledge-baseline.json` + `SUMMARY.md` |

**知识基线四维度**：用户故事（userStories）、业务规则（businessRules）、数据实体（dataEntities）、UI 模式（UIPatterns），每个维度包含条目列表和交叉验证信息。

**深度导入模式**：扫描模式下可启用，在核心模块目录生成 `CONTEXT.md`（模块职责/核心文件/对外接口/依赖关系/编码规范），IMPLEMENT 阶段开发 Agent 直接读取，减少 15-25% 上下文消耗。

> 所有导入知识的初始置信度 ≤ 0.6，标记 `imported-` 前缀，需在后续工作流中被验证和消费才能"毕业"。

#### 第二层：基线注入 + 查询入口（INIT 阶段）

工作流启动时，自动检测并注入已有知识资产和查询入口：

| 注入点 | 协议 | 作用 |
|--------|------|------|
| ANALYSE_PRODUCT | 知识基线注入 | `@product-collector` 参考 `importedKeywords` + `baselinePath`，辅助迭代判定 |
| ANALYSE_TECH | 代码画像注入 | `@tech-explorer` 跳过已画像模块，搜索预算节省 ~20-30% |
| PRD 创建 | 白名单式参考 | 仅读取 `SUMMARY.md` front-matter，严禁读取源码 |
| **各阶段 Agent** | **知识查询入口注入** | 注入 `knowledgeCatalogPath`，Agent 可按需查询团队知识库 |

`state.json` 的 `knowledgeContext` 字段记录：`baselineAvailable`、`baselinePath`、`knowledgeCatalogPath`、`knowledgeRepoLocalPath`、`contributorName`、`contributorRole`。

#### 第三层：阶段按需消费

工作流运行过程中，Agent 在**具体决策点**主动查询知识库（渐进式加载，非一次性推送）：

| 消费方式 | 时机 | 机制 |
|---------|------|------|
| **按需知识查询** | 各阶段决策点 | Agent 读 catalog.md 定位 → 读完整条目获取知识 → 沿 source_references 深入 |
| **历史归档检索** | PRD 创建 / 需求分析 | 通过 `archived/index.md` 按功能域定位历史需求 → 读 SUMMARY.md 正文 |
| **迭代基线对比** | 检测到迭代需求 | 前一版 PRD + 需求文档 → `_baseline-summary.json`（added/modified/removed/unchanged） |
| **复用评级** | ANALYSE_TECH | 3 轮递进搜索 + 知识库查询融合，五级评级 🟢🟡🟠🔴⚪ |
| **项目记忆** | Agent 启动 | `.codebuddy/memory/` 中的经验与踩坑记录自动注入上下文 |

> **强制复用规则**：🟢 完全复用 / 🟡 稍作调整 评级时**禁止新建代码**，最大化复用已有资产。

#### 第四层：知识提取（5 个自动触发点）

知识并非人工填写，而是从工作流执行过程中**自动提取**：

| 触发时机 | 提取内容 | 知识类型 |
|---------|---------|---------|
| 工作流进入 ARCHIVE | 全流程回顾 | ADR（架构决策记录）+ 最佳实践 + 风险模式 |
| CLARIFY 阶段完成 | 问答对提取 | FAQ（常见问题） |
| BUILD_VERIFY 回退 ≥2 次 | 失败模式分析 | 反模式（anti-pattern） |
| IMPLEMENT 完成 | 代码模式提取 | 最佳实践（best-practice） |
| 同类需求完成 ≥3 个 | 跨需求对比 | 模板进化（template-evolution） |

#### 第五层：进化存储（6 类知识 + 三级成熟度）

**六种知识类型**：

| 类型 | 说明 | 典型示例 |
|------|------|---------|
| `ADR` | 架构决策记录 | "选择 Redis 而非 Memcached 的原因及影响" |
| `best-practice` | 最佳实践 | "React 组件状态管理的推荐模式" |
| `anti-pattern` | 反模式 | "循环依赖导致的编译失败模式" |
| `FAQ` | 常见问题 | "接口返回 403 时的排查步骤" |
| `template-evolution` | 模板进化 | "CRUD 需求的标准交付模板 v3" |
| `risk-pattern` | 风险模式 | "涉及支付模块时必须增加的审核步骤" |

**三级成熟度驱动的生命周期**：

```
draft（新提取，单一来源）
  ↓ 在 1 个工作流中被成功引用
verified（至少 1 人验证）
  ↓ 在 ≥2 个不同项目 + ≥2 名贡献者验证
proven（团队共识，可信赖）
  ↓ 12 月未引用 → 衰减
```

- 所有知识条目带 `evidence.contributors[]` 追踪每位贡献者
- maturity 提升 = 团队"共识"（借鉴区块链工作量证明：工作流成功执行就是"证明"）
- `log.md` 为追加式不可变日志，记录所有变更（借鉴区块链不可篡改账本）

#### 第六层：按需查询与流水线进化

**三层渐进式索引** — Agent 不再被动接收 Top-N 推送，而是主动按需查阅：

```
Layer A: 全景目录（~50 行）     → Agent 零成本读取，了解知识库全貌
  knowledge-catalog.md             "有哪些分类，各多少条"

Layer B: 分类清单（~100-300 行） → Agent 按需读，扫描一行摘要
  tech-wiki/catalog.md             "每条知识的 ID + 标题 + 成熟度 + 适用阶段"
  biz-wiki/{domain}/catalog.md

Layer C: 完整条目（~50-200 行）  → Agent 精确读，按需获取
  TK-SB-003.md                     "完整内容 + source_references 追溯原始产物"
```

**各阶段查询预算**：

| 阶段 | Agent | 可查条目数 | 查询重点 |
|------|-------|----------|---------|
| ANALYSE_PRODUCT | @product-collector | 5+3 | 业务规则、历史需求 |
| ANALYSE_TECH | @tech-explorer | 8+5 | ADR、反模式、历史架构 |
| ARCHITECT | @backend-architect | 8+5 | ADR、实体关系、历史架构 |
| IMPLEMENT | 各开发 Agent | 5+2 | 最佳实践、反模式 |

> catalog.md 不计入配额（太轻量），只有完整条目和归档产物计入。

**流水线进化闭环**（`/evolve` → `/evolve:apply`）：

```
Bug 发生 → /evolve 分析 → Agent 根因映射 → 改进建议生成
    → Owner 人工审阅 → /evolve:apply 落地 → Agent/Rule 文件升级
```

> **核心哲学**：知识沉淀是全自动的，但流水线改进需要 Owner 人工审阅后才落地 — 确保人机协同的改进质量。

### 六组件协作生态

知识闭环不是单一组件的工作，而是六个 Skill 协同运转：

```
                    ┌─────────────────────┐
                    │  workflow-orchestrator│ ← 主编排器：知识注入 + 阶段消费 + 归档触发
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐  ┌────────────────────┐  ┌──────────────────┐
│ knowledge-    │  │ quality-guardian    │  │ skill-learner    │
│ evolution     │  │ 质量问题→反模式     │  │ Agent 优化→知识   │
│ 核心进化引擎   │  │ 回退≥3→anti-pattern │  │ Skill 评测→改进   │
└───────┬───────┘  └────────┬───────────┘  └────────┬─────────┘
        │                   │                       │
        │         ┌─────────▼─────────┐             │
        │         │ capability-router │             │
        │         │ 路由权重基于历史成功率│            │
        │         └───────────────────┘             │
        │                                           │
        └─────────────────┬─────────────────────────┘
                          ▼
                  团队知识仓库 (team-knowledge.git)
                  tech-wiki/ + biz-wiki/ + team-conventions/
                  三级成熟度 + 贡献者追踪 + 不可变日志
```

| 组件 | 知识贡献 |
|------|---------|
| **knowledge-evolution** | 核心引擎 — 提取、存储、推送、生命周期管理 |
| **quality-guardian** | 质量监控中反复出现的问题 → anti-pattern 知识条目 |
| **skill-learner** | Agent 性能评估 → 优化经验沉淀为知识 |
| **capability-router** | 基于知识库中的历史成功率调整路由权重 |
| **workflow-orchestrator** | 主流程中的知识注入点（INIT/ANALYSE）+ 提取触发点（ARCHIVE） |
| **team-hub** | 知识库健康度作为团队仪表板指标 |

### Step 0 — 项目状态智能探测

`/flow:run` 启动时，在 INIT 之前执行轻量级 Step 0（≤10 次工具调用）：

- 计算**知识分**（工作流历史、归档产物）和**代码分**（目录深度、文件数量）
- 权重矩阵自动判定：**全新项目** / **成熟项目** / **历史项目**
- 历史项目自动引导到 `/flow:import`（用户可跳过）
- 全新项目触发工作区布局决策（扁平/分离结构）

## 🔧 可用 Skills

| Skill | 用途 |
|-------|------|
| `workflow-orchestrator` | 核心工作流编排 — 16 阶段状态机 + Agent Teams + 知识闭环 |
| `figma-d2c` | Figma 设计稿转代码 — 16 步检查点协议，IMPLEMENT 阶段自然调度 |
| `prd-creator` | 结构化 PRD 创建（含历史知识白名单参考） |
| `git-push-helper` | 智能 Git 提交推送 + MR 链接 + 企微通知 |
| `send-flow-message` | 工作流消息通知（企微群） |
| `tapd-toolkit` | TAPD 集成 — 图片/附件上传下载 + 需求拉取 |
| `mcp-setup-guide` | MCP 服务配置引导（含全局配置同步） |
| `skill-creator` | 创建、修改和评测 Skill |
| `capability-router` | 智能意图分析与 Skill 路由 |
| `knowledge-evolution` | 知识进化引擎 — 提取+存储+推送+生命周期 |
| `quality-guardian` | 全流程质量监控与改进建议 |
| `team-hub` | 多角色协作任务管理 |
| `model-router` | 按任务复杂度智能选择底层模型 |
| `skill-learner` | 基于历史数据的 Skill 效果分析与优化 |
| `token-budget-manager` | Token 消耗追踪与预算预警 |

## 📂 目录结构

```
.codebuddy/
├── skills/                              # Skill 定义（核心能力）
│   ├── workflow-orchestrator/           # 🧠 核心编排器
│   │   ├── SKILL.md                     # 16 阶段状态机 + Agent Teams
│   │   ├── agents/                      # 子 Agent 定义（35 个）
│   │   ├── phases/                      # 阶段调度规则
│   │   ├── references/                  # Schema 定义
│   │   ├── rules/                       # 编码规范、诊断策略、视觉协议
│   │   ├── templates/                   # Agent Prompt 模板
│   │   └── scripts/                     # 辅助脚本
│   ├── figma-d2c/                       # Figma D2C（16 步检查点协议）
│   ├── knowledge-evolution/             # 知识进化引擎
│   ├── quality-guardian/                # 质量守卫
│   ├── prd-creator/                     # PRD 创建器
│   ├── capability-router/               # 能力路由器
│   ├── mcp-setup-guide/                 # MCP 配置引导
│   ├── tapd-toolkit/                    # TAPD 集成
│   ├── git-push-helper/                 # Git 推送助手
│   ├── send-flow-message/               # 消息通知
│   ├── skill-creator/                   # Skill 创建器
│   ├── team-hub/                        # 团队协作中心
│   ├── model-router/                    # 多模型路由
│   ├── skill-learner/                   # Skill 自学习引擎
│   └── token-budget-manager/            # Token 预算管理器
│
├── commands/                            # 用户命令
│   ├── flow:run.md                      # 启动交付工作流
│   ├── flow:import.md                   # 历史项目知识导入
│   ├── flow:status.md                   # 查看工作流状态
│   ├── team:init.md                     # 初始化项目配置，连接团队知识仓库
│   ├── evolve.md                        # 分析改进建议
│   ├── evolve:apply.md                  # 落地改进
│   └── guard.md                         # 防护模式
│
└── memory/                              # 组织记忆
```

## 🗺️ 演进路线图

| 阶段 | 目标 | 状态 |
|------|------|------|
| Phase 1 | CodeBuddy 原生化 — Skill/Command/Rule 体系 + Agent Teams | ✅ 完成 |
| Phase 2 | 深度编排 — 产品分析三级降级 + 上下文防火墙 | ✅ 完成 |
| Phase 3 | 团队协作 — team-hub + capability-router | ✅ 已就绪 |
| Phase 4 | 知识进化 — knowledge-evolution + quality-guardian | ✅ 已就绪 |
| Phase 5 | 高级特性 — model-router + skill-learner + token-budget | ✅ 已就绪 |
| Phase 6 | 历史知识导入 — /flow:import + 3 Agent 管道 + 知识闭环 | ✅ 完成 |
| Phase 7 | TAPD 深度集成 — INIT 自动检测 + 非阻断引导 | ✅ 完成 |
| Phase 8 | OMC/OMO 调研优化 — IntentGate + 上下文监控 + 视觉分析 | ✅ 完成 |
| Phase 9 | LSP 实时诊断 — read_lints 全 Agent 接入 + 错误左移 | ✅ 完成 |
| Phase 10 | 视觉验收闭环 — VISUAL_REVIEW + 设计还原度评分 | ✅ 完成 |
| Phase 11 | 新项目脚手架 — 一键安装 + 工作区布局决策 | ✅ 完成 |
| Phase 12 | D2C 流程简化 — 单 Agent 检查点协议回归 | ✅ 完成 |
| Phase 13 | 团队知识共享 — 独立知识仓库 + 团队共建 + 冲突解决 + /team:init | ✅ 完成 |
| Phase 14 | 按需知识消费 — 三层渐进索引 + Agent 主动查询 + 归档可检索 + 引用追踪 | ✅ 完成 |

> 各阶段详细变更日志见 [CHANGELOG.md](CHANGELOG.md)。

## 💡 设计灵感

- **[vibe-coding](../vibe-coding/)** — 生产验证的文件状态机 + Agent 编排模式
- **[oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode)** — IDE 原生 Skill/Rule 架构 + 验证协议 + 压缩检测
- **[oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent)** — Agent 协作编排 + IntentGate 意图分析

## 📄 License

MIT
