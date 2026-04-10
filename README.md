# AI Team — AI 工程交付编排系统

> 基于 CodeBuddy IDE 的 Skill / Command / Rule 体系，实现多 Agent 协作的全流程需求交付自动化。
> **核心理念**：文件系统即状态机，团队知识持续沉淀，越用越聪明。

---

## 这是什么

AI Team 是一套**工作流引擎**，安装到你的业务项目后，用一条命令 `/flow:run` 驱动 AI Agent 完成从需求分析到代码归档的全流程。它不是一个独立平台，而是一组 `.codebuddy/` 目录下的 Skill、Agent、Command 定义文件，被 CodeBuddy IDE 原生识别和执行。

**核心价值**：Skill、Agent、工具链会随模型迭代更新，但**领域知识是永恒的**。AI Team 的每次交付都自动沉淀知识到团队共享仓库，所有成员共建共享，新工作流启动时自动站在前人肩上。

---

## 部署拓扑

```
本仓库（ai-team）                       你的业务项目（如 cloud-mall）
  └── .codebuddy/  ── cp -r ──────►  ├── .codebuddy/          ← 引擎副本，IDE 识别后驱动一切
      工作流引擎源码                    ├── .ai-team/project.yaml ← /team:init 创建的知识锚点
                                      ├── src/                  ← 你的业务代码
                                      └── docs/workflows/       ← 工作流产物（state.json、分析文档、架构、归档）
                                             │
                                             │ ARCHIVE 阶段自动 git push
                                             ▼
                                      团队知识仓库（独立 Git 仓库，所有成员 clone）
                                        ├── knowledge-catalog.md   ← 全景目录（Agent 查询入口）
                                        ├── tech-wiki/             ← 技术知识（按语言/框架/模式）
                                        ├── biz-wiki/{domain}/     ← 业务知识（按领域）
                                        ├── team-conventions/      ← 团队编码约定
                                        └── contributions/         ← 贡献暂存与冲突记录
```

**三个独立仓库，各司其职**：
- **ai-team 仓库**（本仓库）：工作流引擎代码，复制到各业务项目使用
- **业务项目仓库**：你的实际代码 + 工作流产物
- **团队知识仓库**：跨项目共享的知识库，通过 `/team:init` 连接

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
/team:init

# 2. 已有代码库：导入历史知识（可选但推荐）
/flow:import

# 3. 日常开发：启动交付工作流
/flow:run                              # 从上下文推断需求
/flow:run docs/prd/my-requirement.md   # 从 PRD 文档启动

# 4. 查看进度
/flow:status

# 5. 复盘改进
/evolve                                # 分析改进建议
/evolve:apply                          # 落地改进
```

---

## 工作流：16 阶段状态机

```
/flow:run 启动后自动流转：

INIT → ANALYSE_PRODUCT → ANALYSE_TECH → ARCHITECT_BACKEND → ARCHITECT_FRONTEND
  → ARCHITECT_MINIPROGRAM → IMPLEMENT → BUILD_VERIFY → VISUAL_REVIEW
  → E2E_VERIFY → TEST → ARCHIVE → DONE
```

每个阶段遵循**三步模式**：Preview（预览计划）→ Execute（执行）→ Summary（总结确认），确保每一步人工可控。

### 各阶段做什么

| 阶段 | Agent | 做什么 |
|------|-------|--------|
| **ANALYSE_PRODUCT** | 4-5 成员 Agent Teams | 需求分析：迭代判定、基线对比、用户故事/业务规则提取、视觉分析 |
| **ANALYSE_TECH** | 4 成员 Agent Teams | 技术分析：代码全景扫描、3 轮递进复用搜索、技术方案设计、分端拆解、校审 |
| **ARCHITECT** | 架构师 Agent | 后端/前端/小程序架构设计，数据库设计，API 契约定义 |
| **IMPLEMENT** | 各端开发 Agent 并行 | 代码实现，文件所有权声明，LSP 实时诊断 |
| **BUILD_VERIFY** | 验证 Agent | LSP 预扫描 + 终端编译双保险 |
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

> 这是整个系统最重要的设计。

### 知识如何流动

```
/flow:import（一次性）           /flow:run（每次）
      │                              │
      ▼                              ▼
 冷启动导入                     INIT: git pull 知识仓库 + 注入查询入口
 3 Agent 管道                        │
 → knowledge-baseline.json          │  ← Agent 在各阶段按需查询知识库
 → codebase-profile.json            │
                                     ▼
                               ARCHIVE: 知识提取 + 提升判定
                                     │
                                     ├→ Layer 3（项目内）: docs/knowledge-base/
                                     ├→ Layer 1（技术）: tech-wiki/  ← git push
                                     └→ Layer 2（业务）: biz-wiki/  ← git push
                                                     │
                                                     ▼
                                              下一个人的 /flow:run 自动受益
```

### 按需查询，不是 Top-N 推送

Agent 不被动接收固定数量的知识推荐，而是通过**三层渐进式索引**主动按需查阅：

```
Layer A: knowledge-catalog.md（~50 行）→ 知识库全貌，哪些分类各多少条
Layer B: catalog.md（~100-300 行）     → 每条知识一行摘要，按适用阶段过滤
Layer C: 完整条目（~50-200 行）        → 按需读取，可沿 source_references 追溯原始产物
```

各阶段有独立的查询预算（catalog 不计入配额）：

| 阶段 | Agent | 完整条目 | 归档产物 | 重点 |
|------|-------|---------|---------|------|
| ANALYSE_PRODUCT | @product-collector | 5 | 3 | 业务规则、历史需求 |
| ANALYSE_TECH | @tech-explorer | 8 | 5 | ADR、反模式、历史架构 |
| ARCHITECT | @backend-architect | 8 | 5 | ADR、实体关系 |
| IMPLEMENT | 各开发 Agent | 5 | 2 | 最佳实践、反模式 |
| BUILD_VERIFY | 各验证 Agent | 3 | 0 | 反模式、编译问题 |

### 知识存储分层

| 层级 | 位置 | 共享 | 内容 |
|------|------|------|------|
| Layer 0-P | `~/.ai-team/preferences/` | 不共享 | 个人编码风格偏好 |
| Layer 0-T | `{知识仓库}/team-conventions/` | 团队 Git | 团队编码规范、Review 标准 |
| Layer 1 | `{知识仓库}/tech-wiki/` | 团队 Git | 技术知识（按语言/框架/模式/反模式） |
| Layer 2 | `{知识仓库}/biz-wiki/{domain}/` | 团队 Git | 业务知识（实体/规则/流程/踩坑） |
| Layer 3 | `{项目}/docs/knowledge-base/` | 项目仓库 | 项目特有知识 |

### 六种知识类型

| 类型 | 来源 | 示例 |
|------|------|------|
| `ADR` | ARCHITECT 阶段 | "选择 Redis 而非 Memcached 的原因" |
| `best-practice` | IMPLEMENT + BUILD_VERIFY | "React 状态管理推荐模式" |
| `anti-pattern` | BUILD_VERIFY 回退 ≥2 次 | "循环依赖导致编译失败" |
| `FAQ` | CLARIFY 阶段 | "接口返回 403 排查步骤" |
| `risk-pattern` | risks.json 分析 | "涉及支付模块时必检查项" |
| `template-evolution` | 同类需求 ≥3 个 | "CRUD 需求标准模板 v3" |

### 三级成熟度

```
draft（新提取，单一来源）→ verified（≥1 人验证）→ proven（≥2 项目 + ≥2 贡献者验证）
```

每条知识带 `evidence.contributors[]` 追踪贡献者、`source_references` 追溯原始产物、`applicable_phases` 标注适用阶段。借鉴区块链思想：工作流成功执行 = 工作量证明，`log.md` 追加式不可变。

### 团队协作

通过 `/team:init` 连接独立 Git 知识仓库。所有成员的工作流 ARCHIVE 阶段自动提取知识并 push。

**冲突解决**：纯新增/证据追加 → 自动合并；内容矛盾 → 写入 `contributions/conflicts/`，maintainer 裁决。

**角色**：maintainer（裁决冲突、审批 proven）、contributor（自动贡献）、reader（只消费）。

---

## 冷启动：/flow:import

对已有代码库，先跑一次 `/flow:import` 构建知识基线：

```
@doc-collector → 多源资料收集（文档/TAPD/口述/代码扫描）
  ↓
@codebase-profiler → 代码画像（技术栈/模块/依赖/模式，60 次搜索预算）
  ↓
@knowledge-builder → 知识标准化（4 维基线 + ≤13 条知识条目 + 归档总结）
```

产出 `knowledge-baseline.json`（四维度：用户故事/业务规则/数据实体/UI 模式），后续工作流的 ANALYSE 阶段自动消费。

---

## 可用命令

| 命令 | 用途 |
|------|------|
| `/flow:run` | 启动交付工作流 |
| `/flow:import` | 历史项目知识导入 |
| `/flow:status` | 查看工作流状态 |
| `/team:init` | 初始化项目配置，连接团队知识仓库 |
| `/evolve` | 分析改进建议 |
| `/evolve:apply` | 落地改进 |
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

---

## 目录结构

```
.codebuddy/
├── skills/                              # Skill 定义
│   ├── workflow-orchestrator/           # 🧠 核心编排器
│   │   ├── SKILL.md                     #   16 阶段状态机 + Agent Teams
│   │   ├── agents/                      #   35 个子 Agent 定义
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
│   ├── flow:run.md                      # 启动交付工作流
│   ├── flow:import.md                   # 历史知识导入
│   ├── team:init.md                     # 初始化+连接知识仓库
│   └── ...
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
| **人机协同** | 三步模式（Preview → Execute → Summary），每步人工可控 |
| **安全降级** | Agent Teams 三级降级 + 检查点断点恢复 |

## 设计灵感

- **[Karpathy LLM Wiki](https://gist.github.com/karpathy/1dd0294ef9567971c1e4348a90d69285)** — 知识复合增长：Ingest + Query + Lint
- **[vibe-coding](../vibe-coding/)** — 生产验证的文件状态机 + Agent 编排模式
- **[oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode)** — IDE 原生 Skill/Rule 架构

## License

MIT
