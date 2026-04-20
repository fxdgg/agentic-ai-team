# 知识消费机制

> 本文件从 SKILL.md 拆分而来，被工作流各阶段 Agent 按需查询时加载。

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
| **个人偏好** | `~/.ai-team/preferences/coding-style.md` | 个人编码风格 | ~50 行 |

### 5.3 各阶段查询预算

> catalog.md 不计入配额（太轻量），只有完整条目和归档产物计入。

| 阶段 | Agent | 完整条目配额 | 归档产物配额 | 查询的存储层 | 重点知识类型 |
|------|-------|------------|------------|------------|------------|
| ANALYSE_PRODUCT | @product-collector | 5 | 3 | Layer 2 (biz-wiki) + 归档索引 | model, process, pitfall |
| ANALYSE_PRODUCT | @product-extractor | 5 | 2 | Layer 2 (biz-wiki) | guideline, model |
| ANALYSE_TECH | @tech-explorer | 8 | 5 | Layer 1 (tech-wiki) + 归档索引 | decision, guideline(avoid), pitfall |
| ANALYSE_TECH | @tech-designer | 5 | 3 | Layer 1 (tech-wiki) | decision, guideline(recommend) |
| ARCHITECT | @backend-architect 等 | 8 | 5 | Layer 1 patterns + Layer 2 relations | decision, model |
| IMPLEMENT | 各开发 Agent | 5 | 2 | Layer 1 + Layer 0-T | guideline, pitfall |
| BUILD_VERIFY | 各验证 Agent | 3 | 0 | Layer 1 anti-patterns | pitfall, guideline(avoid) |

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
    { "id": "TK-SB-003", "title": "分页查询延迟关联优化", "type": "guideline", "usedIn": "复用评级 Step 2" },
    { "id": "BK-AD-G004", "title": "广告预算扣减并发控制规则", "type": "guideline", "usedIn": "业务规则参考" }
  ]
}
```

ARCHIVE 阶段七读取各阶段产物中的 `knowledgeReferences`，批量更新 `evidence.last_referenced` 字段。这形成自动化的引用追踪闭环。

---

## 5.6 角色对消费行为的影响

知识消费与团队角色无关——**所有角色（maintainer/contributor/reader）都可自由查询知识库**。角色仅影响贡献（写入）：

| 角色 | 查询（消费） | 贡献（写入 tech-wiki / biz-wiki） |
|------|-------------|--------------------------------|
| maintainer | ✅ | ✅（+ 审批 proven 提升） |
| contributor | ✅ | ✅ |
| reader | ✅ | ❌ ARCHIVE 阶段七跳过 Step 4-11（贡献写入） |

> 角色从 `state.json` 的 `knowledgeContext.contributorRole` 读取。详见 `rules/knowledge-query-protocol.md` §6 和 `agents/archiver.md` 阶段七前置条件。
