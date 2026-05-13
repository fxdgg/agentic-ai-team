# 知识进化规则

> 本文件从 SKILL.md 拆分而来，被 /knowledge lint、/knowledge query、/knowledge sync 操作按需加载。

---

## 6. 知识进化规则

### 6.1 知识生命周期（三级成熟度）

知识生命周期由两组正交信号驱动：**时间信号**（是否被引用）和 **事实信号**（代码事实是否改变）。

#### 6.1.1 主流转

```
draft（导入/新提取/矛盾降级）
  ↓ 在 1 个工作流中被成功引用（ARCHIVE 阶段自动判定）
verified（单项目验证）
  ↓ 在 ≥2 个不同项目中被验证（跨项目提升自动判定）
proven（成熟/可信赖）
```

#### 6.1.2 时间信号衰减（默认 12/6/6 月阈值）

```
proven 12 月未引用 → verified
verified 6 月未引用 → draft
draft 6 月未引用 + Lint 标记 → archived
```

> **模块活跃度抑制**（archiver §17）：时间衰减触发时，会查询知识条目的关联模块在 `project-profile.modules[].last_active_at` 中的活跃度。若模块已 6~24 月未迭代（休眠中），则**抑制本次降级**并打标 `dormant-module-skipped-decay`，避免误伤季节性活跃模块（如对账/结算）。模块超过 24 月未动则强制衰减。阈值可通过 `.knowledge-config.yaml.decay_rules` 自定义。
>
> 导入条目（`source.trigger == "import"`）不参与活跃度抑制，因其关联可能与当前项目画像不匹配。

#### 6.1.3 事实信号衰减（archiver §17.5）

> 代码事实校对每次 ARCHIVE 针对"本次变更涉及的模块"的关联知识执行，基于符号存在性做确定性检测：

```
引用的源码文件整体消失     → 降级一级 + contradiction_flags += "stale-source-reference"
条目中描述的关键符号消失   → maturity 不变 + contradiction_flags += "code-fact-drift"（需人工复查）
符号仍在变更文件中出现     → 不改状态，仅列入观察清单（弱信号）
```

事实信号与时间信号**独立作用**，都在 `contradiction_flags` 留痕，同一条目可能被两者同时命中并各自打标。

### 6.2 冲突处理

当新提取的知识与已有条目冲突时，按团队协作机制（§2.6.2）处理：

```
冲突处理策略:
1. 纯新增（不同条目）→ 自动合并，两条都保留
2. 同一条目追加证据 → 自动合并，evidence.contributors 数组合并去重
3. 同一条目内容矛盾 → 写入 {knowledge-repo}/contributions/conflicts/，通知 maintainer 裁决
4. 涉及架构决策 (type=decision) → 不自动覆盖，创建新 decision 条目记录旧决策的变更理由
5. 冲突条目的 maturity 自动降级为 draft，直到矛盾解决
6. 所有冲突和解决记录追加到 log.md（不可变追加日志）
```

### 6.3 知识库 Lint（健康检查）

> **设计来源**：借鉴 Karpathy LLM Wiki 的 Lint 操作——定期识别矛盾、孤儿页、缺失交叉引用和数据缺口。

**触发方式**：
- 自动触发：每完成 10 个工作流后
- 手动触发：`/evolve` 命令包含知识库健康检查
- 定期触发：连续 30 天未执行时，下次 `/flow-run` 启动时提醒

**Lint 检查项**：

| 检查项 | 检测方法 | 处理方式 |
|--------|---------|---------|
| **索引不一致** | 对比 index.json 条目与实际文件列表（团队知识仓库各层均检查） | 自动修复：补充缺失条目 / 移除悬空引用 |
| **孤儿条目** | 无交叉引用（`related` 字段为空）且无 `evidence.source_projects` | 标记为待审核，降级 maturity 到 draft |
| **矛盾检测** | 同一主题的多条知识，结论相反 | 创建 `conflict-{ID}` 标记，降级 maturity 到 draft，等待人工审核 |
| **过时检测** | maturity 为 draft 且 6 个月未引用 | 自动归档到 `archive/` 目录 |
| **导入未验证** | `imported-` 前缀条目且连续 3 个工作流未引用 | 降级 maturity 到 draft，标记 `unvalidated-import` |
| **重复/相似** | 标题或内容语义高度重合（含跨层重复检测） | 标记为合并候选，建议人工合并 |
| **成熟度衰减** | proven 条目 12 月未引用 / verified 条目 6 月未引用 | 按生命周期规则（§6.1）自动降级 maturity（含模块活跃度抑制判定）|
| **事实漂移待审** | 条目 `contradiction_flags` 含 `code-fact-drift`（由 archiver §17.5 打标） | 列入"待人工审核"清单，建议 maintainer 通过 `/knowledge update` 修订正文或执行归档 |
| **休眠抑制待复查** | 条目 `contradiction_flags` 含 `dormant-module-skipped-decay` 且距首次抑制 > 3 月 | 列入"待人工复查"清单，提示 maintainer 检查关联模块是否仍在业务路线图内；若模块已废弃则手动归档知识 |

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

💤 因模块休眠被抑制衰减: {S} 条（archiver §17 打标，此处汇总）
- {ID}: {title} — 关联模块 {modules}（最后活跃 {date}，距今 {X} 月）
- ... 
- 建议：确认关联模块是否仍在业务路线图内；若已废弃，手动归档对应知识

⚠️ 代码事实漂移待审（archiver §17.5 打标）: {F} 条
- {ID}: {title} — 缺失符号 {symbols}（打标于 {date}）
- ...
- 建议：运行 /knowledge update 修订正文，或确认事实变更后归档

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
- 类型根据内容判定：排查类→`pitfall`，规范类→`guideline`，概念类→`model`，流程类→`process`
- 初始 maturity 为 verified（有多条来源支撑）
- source.trigger 为 `query-backfill`
- evidence.source_projects 继承引用条目的来源
- evidence.verified_in_workflows 继承引用条目的工作流记录
- 在 log.md 中记录操作类型为 `query-backfill`
