# 知识查询协议（所有 Agent 统一引用）

> **定位**: 本文件为工作流所有 Agent 的**统一知识查询规范**，定义查询入口、预算、时机和引用追踪要求。
> **引用方式**: 每个 Agent 文件通过 "知识查询能力" 章节引用本协议 + 声明自身配额，不再重复完整规则。
> **设计来源**: 对齐 `knowledge-evolution/references/consumption.md` §5（三级渐进式查询）。

---

## 1. 为什么需要统一协议

早期每个 Agent 各自定义"知识查询能力"章节，导致：
- **覆盖不全**：13 个 Agent 中只有 7 个实现了查询能力，另 6 个（尤其 IMPLEMENT/BUILD_VERIFY 阶段的核心 Agent）缺失
- **规范漂移**：相似 Agent 之间查询入口表述、引用追踪字段不一致
- **维护成本高**：修改查询规则需要同步 N 个文件

本协议抽取公共部分，Agent 文件只需声明自己特有的配额和阶段焦点。

---

## 2. 统一查询入口（全局）

所有 Agent 共享以下查询入口（路径从 `state.json` 的 `knowledgeContext` 字段读取）：

| 入口 | 路径模板 | 大小 | 作用 |
|------|---------|------|------|
| **团队知识全景** | `{knowledgeRepoLocalPath}/knowledge-catalog.md` | ~50 行 | Layer A：知识库有什么 |
| **技术知识清单** | `{knowledgeRepoLocalPath}/tech-wiki/catalog.md` | ~100-300 行 | Layer B：每条一行摘要 |
| **业务知识清单** | `{knowledgeRepoLocalPath}/biz-wiki/{domain}/catalog.md` | ~100-300 行 | Layer B：按领域 |
| **团队约定** | `{knowledgeRepoLocalPath}/team-conventions/` | 直接阅读 | Layer 0-T 规范文件 |
| **项目知识库** | `docs/knowledge-base/index.md` | ~50 行 | Layer 3：项目内知识 |
| **归档工作流索引** | `docs/workflows/archived/index.md` | ~200 行 | 历史需求按功能域分类 |
| **个人偏好** | `~/.ai-team/preferences/` | 直接阅读 | Layer 0-P（可选） |

> **前置条件**：如果 `state.json` 的 `knowledgeContext.knowledgeRepoLocalPath` 为 null（项目未执行 `/team-init`），所有团队知识查询**自动跳过**，Agent 正常降级到本地知识库 + 代码搜索。

---

## 3. 三级渐进式查询流程（共享）

```
Step 1: 读全景目录（~50 行，零成本）
  → knowledge-catalog.md
  → 定位当前阶段推荐查阅的 catalog.md 路径

Step 2: 读分类清单（~100-300 行，低成本）
  → 对应分类的 catalog.md
  → 按 applicable_phases 过滤当前阶段相关条目
  → 按 tags 过滤与当前任务相关条目

Step 3: 读完整条目（按需，每条 50-200 行，记入配额）
  → TK-*.md / BK-*.md

Step 4: 读原始产物（深入，可选，记入归档配额）
  → 沿 source_references 读 architecture.md / SUMMARY.md
```

**查询铁律**：
- **catalog.md 读取不计入配额**（太轻量，鼓励充分扫描）
- **完整条目和归档产物按 Agent 定义的配额控制**
- **禁止递归展开**：读取归档产物时不再沿其引用链继续展开

---

## 4. 查询触发时机（共享模式）

所有 Agent 遵循统一的"两段式查询"：

### 4.1 初始化时（必执行）
1. 读 `knowledge-catalog.md` 了解知识库全貌
2. 读与本阶段强相关的 1-2 个 catalog.md（按当前阶段的"重点知识类型"选择）
3. 在脑中建立候选条目列表（记录 ID，不立即读全文）

### 4.2 决策点按需查询（按需触发）
- 先执行本阶段原有工作流（搜索、分析、设计）
- 当原有工作流结果不充分或需要历史参考时，读取候选条目的完整内容
- 达到配额上限后停止查询，在产物中记录"已穷尽查询预算"

> **禁止**：不允许在 Agent 启动时一次性读完所有完整条目（会导致上下文膨胀）。

---

## 5. knowledgeReferences 输出（强制）

**所有 Agent 的产物必须包含 `knowledgeReferences` 字段**，即使为空数组。这是 ARCHIVE 阶段 Step 13 引用追踪闭环的基础。

### 5.1 JSON 产物（`.json` 文件）

在产物根对象中追加字段：

```json
{
  "...": "其他业务字段",
  "knowledgeReferences": [
    {
      "id": "TK-SB-003",
      "title": "分页查询延迟关联优化",
      "type": "guideline",
      "usedIn": "需求点3复用评级"
    }
  ]
}
```

### 5.2 Markdown 产物（`.md` 文件）

在 YAML front-matter 中追加字段：

```yaml
---
qualityGate: pass
knowledgeReferences:
  - id: TK-PAT-001
    title: 事件驱动vs同步RPC选型
    type: decision
    usedIn: 架构选型决策
---
```

### 5.3 字段语义

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 知识条目 ID（如 `TK-SB-003` / `BK-AD-G001` / `DEC-005`） |
| `title` | ✅ | 条目标题（便于人类 Review，冗余字段但必须冗余） |
| `type` | ✅ | 条目类型（model / decision / guideline / pitfall / process） |
| `usedIn` | ✅ | 在本 Agent 产物中的**具体引用点**（如"需求点3复用评级"、"架构选型决策"），用于 /evolve 分析知识使用模式 |

### 5.4 产出原则

- **未查询 → 空数组**：未触发知识查询的 Agent，写入 `"knowledgeReferences": []`
- **查了但没用 → 不记录**：读了完整条目但最终未纳入决策，**不写入**该条目
- **用了才记录**：只有真正影响产物决策的知识条目才记录（避免"虚假引用"污染追踪数据）

> **archiver 阶段七 Step 13** 会批量扫描所有产物中的 `knowledgeReferences`，更新被引用条目的 `evidence.last_referenced` 字段。这是知识衰减判定的核心数据来源，因此**不得伪造或漏记**。

---

## 6. 角色权限对查询的影响

查询**所有角色都可执行**，包括 `reader` 角色。但**贡献（写入知识仓库）**严格受角色控制：

| 角色 | 可查询 | 可触发 ARCHIVE Step 7 知识提升 |
|------|--------|------------------------------|
| `maintainer` | ✅ | ✅ |
| `contributor` | ✅ | ✅ |
| `reader` | ✅ | ❌（仅消费不贡献，archiver 跳过阶段七写入） |

> 角色从 `state.json` 的 `knowledgeContext.contributorRole` 读取，由 `/team-init` 注入。

---

## 7. 各 Agent 配额速查表

各 Agent 在自身文件的"知识查询能力"章节**仅需声明以下三项**，其他规则引用本协议：

```markdown
## 知识查询能力

遵循统一协议：`rules/knowledge-query-protocol.md`（查询入口/流程/knowledgeReferences 输出规范）。

### 本 Agent 专属配置

| 项 | 值 |
|---|---|
| 完整条目配额 | {N} 条 |
| 归档产物配额 | {M} 个 |
| 重点查询入口 | {列出本阶段最相关的 1-2 个入口} |
| 重点知识类型 | {列出本阶段最相关的类型，如 pitfall / guideline(avoid)} |
| 触发时机 | {本 Agent 的具体查询时机，如"复用探索第 1 轮无结果时"} |
```

**各 Agent 配额统一基准**（与 `knowledge-evolution/references/consumption.md` §5.3 对齐）：

| 阶段 | Agent | 完整条目 | 归档产物 | 重点类型 |
|------|-------|---------|---------|---------|
| ANALYSE_PRODUCT | @product-collector | 5 | 3 | model, process, pitfall |
| ANALYSE_PRODUCT | @product-extractor | 5 | 2 | guideline, model |
| ANALYSE_TECH | @tech-explorer | 8 | 5 | decision, guideline(avoid), pitfall |
| ANALYSE_TECH | @tech-designer | 5 | 3 | decision, guideline(recommend) |
| ARCHITECT_BACKEND | @backend-architect / @java-architect | 8 | 5 | decision, model |
| ARCHITECT_FRONTEND | @frontend-architect | 6 | 3 | decision, guideline(recommend) |
| IMPLEMENT | backend-developers（各领域） | 5 | 2 | guideline, pitfall |
| IMPLEMENT | @web-developer / @miniprogram-developer | 5 | 2 | guideline, pitfall |
| BUILD_VERIFY | @build-verifier / 子验证 Agent | 3 | 0 | pitfall, guideline(avoid) |

---

## 8. 搜索工具优先级（与知识查询的关系）

知识查询与代码搜索是互补关系，不是替代关系：

```
原则：代码搜索优先，知识查询补充

┌──────────────────────────────────────────────────┐
│  Step 1: 代码搜索（Grep/Glob/codebase_search）    │
│    → 找到具体实现 → 不需要知识查询                │
│    → 未找到或不充分 → 进入 Step 2                │
├──────────────────────────────────────────────────┤
│  Step 2: 知识查询（三级索引）                     │
│    → catalog.md 找相关条目                       │
│    → 读完整条目，获取最佳实践/已知陷阱            │
│    → 记录到 knowledgeReferences                  │
└──────────────────────────────────────────────────┘
```

**特殊情况**：BUILD_VERIFY 阶段编译失败时，**应优先查询 pitfall 类知识**（历史上这个错误是怎么修的），再决定修复方案——此时知识查询比代码搜索更有价值。

---

## 9. 常见错误与纠正

| 反模式 | 为什么错 | 正确做法 |
|-------|---------|---------|
| 启动时一次性 Read 所有 TK-*.md | 上下文爆炸 | 先读 catalog.md 筛选，按需 Read 完整条目 |
| 读了知识但不记 knowledgeReferences | 引用追踪闭环断裂 | 决策时用到的条目必须记录 |
| 记录了不相关的 knowledgeReferences 凑数 | 污染衰减判定 | 只记真正影响决策的条目 |
| knowledgeRepoLocalPath 为 null 仍尝试查询 | 路径错误报错 | 先检查路径，未配置则跳过 |
| 无限展开 source_references 链 | 上下文爆炸 | 归档产物最多读 1 层，不沿链递归 |

---

## 10. 版本

- v1.0（2026-04-20）：初版。抽取自各 Agent 文件的"知识查询能力"章节，首次覆盖全部 13 个 Agent。
