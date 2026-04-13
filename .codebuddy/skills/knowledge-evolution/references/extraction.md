# 知识提取规则

> 本文件从 SKILL.md 拆分而来，被 ARCHIVE 阶段和 /knowledge promote 操作按需加载。

---

## 4. 知识提取规则

### 4.1 自动提取触发点

| 触发时机 | 提取内容 | 输出知识类型 |
|---------|---------|-------------|
| 工作流进入 ARCHIVE 阶段 | 全流程回顾分析 | decision, guideline, pitfall |
| CLARIFY_* 阶段完成 | 澄清问答对提取 | guideline, model, pitfall（按内容判断） |
| BUILD_VERIFY 回退 ≥2 次 | 失败模式分析 | pitfall, guideline(avoid) |
| IMPLEMENT 阶段完成 | 代码模式提取 | guideline(recommend) |
| 同类需求完成 ≥3 个 | 跨需求模式对比 | guideline(recommend), model |
| ANALYSE_PRODUCT 阶段 | 业务分析产物 | model, process |

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
type: model | decision | guideline | pitfall | process
polarity: recommend | avoid              # 仅 type=guideline 时必填
layer: tech | biz | project
domain: {domain-id 或 null}
title: {标题}
one_line: {一句话摘要，用于 catalog.md 展示}
applicable_phases: [ANALYSE_TECH, IMPLEMENT]   # 适用的工作流阶段
created: {ISO-8601}
updated: {ISO-8601}
maturity: draft | verified | proven
source:                                        # 知识来源（溯源分析用）
  phase: "{提取自哪个阶段}"                      # ARCHITECT / IMPLEMENT / BUILD_VERIFY / CLARIFY / ARCHIVE / import
  trigger: "{触发原因}"                          # rollback / success / clarify / import / cross-workflow
  workflow: "{需求ID}"
  confidence: 0.7
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
- `type` + `polarity`：知识类型按内容维度分类（model/decision/guideline/pitfall/process），guideline 通过 polarity 区分推荐做法(recommend)和禁止做法(avoid)
- `source`：知识来源的元数据，记录从哪个阶段、什么触发条件提取。用于溯源分析（如某阶段频繁产出 pitfall，说明该阶段 Agent 需优化），不作为分类依据
- `one_line`：一句话摘要，用于 catalog.md 清单中的展示（≤100 字），让 Agent 不读完整条目也能判断相关性
- `applicable_phases`：知识在哪些工作流阶段最有用。Agent 读 catalog.md 时按当前阶段过滤
- `source_references`：指向原始归档产物（架构文档、SUMMARY.md 等）。Agent 需要更多细节时可沿引用深入读取，避免知识摘要丢失推导过程

### 4.4 导入知识的进化策略

> 当工作流在已有导入知识（`evidence.source_projects` 包含 `imported-*` 前缀）的项目上完成时，执行以下特殊进化逻辑。

#### 4.4.1 验证与提升

将工作流中实际使用的技术决策与导入的 decision 条目对比：

```
对比流程:
1. 从 ARCHITECT_BACKEND 产物中提取实际技术决策
2. 搜索 docs/knowledge-base/ 下 type=decision 且 ID 含 "IMP" 的条目
3. 逐条对比:
   - 一致 → maturity 从 draft 提升到 verified（追加 verified_in_workflows）
   - 部分一致 → maturity 保持 draft，追加工作流验证注释到 evidence
   - 不一致 → 创建新 decision 记录变更理由，旧条目 maturity 降级为 draft 并添加 contradiction_flags
```

#### 4.4.2 补充与丰富

从工作流产物中提取新知识，补充导入时缺失的部分：

```
补充规则:
- 新发现的约定 → 追加 guideline (polarity=recommend)（maturity: draft，有完整工作流证据链）
- 新发现的反模式 → 创建 pitfall 或 guideline (polarity=avoid)（maturity: draft）
- 导入时 missing 的维度在工作流中被覆盖 → 更新知识仓库中对应维度的条目
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
