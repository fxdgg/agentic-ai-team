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

## 2. 模块化参考文件路由

> **⚠️ 按需加载原则**：本技能的详细规则已拆分为独立参考文件。根据当前操作类型，**仅加载对应的参考文件**，不要加载全部。

### 操作 → 参考文件映射

| 操作场景 | 需要加载的参考文件 | 说明 |
|---------|-------------------|------|
| `/knowledge status` | `references/architecture.md` §2-3 | 需要理解知识体系架构和分类 |
| `/knowledge lint` | `references/evolution.md` §6.3 | 需要 Lint 检查规则和报告格式 |
| `/knowledge sync` | `references/collaboration.md` | 需要团队协作和冲突解决策略 |
| `/knowledge query` | `references/evolution.md` §6.5 + `references/consumption.md` §5 | 需要查询流程和消费机制 |
| `/knowledge add` | `references/architecture.md` §3.1 + `references/extraction.md` §4.3 | 需要类型定义和条目模板 |
| `/knowledge promote` | `references/extraction.md` §4.5 | 需要提升判定规则 |
| ARCHIVE 阶段知识提取 | `references/extraction.md` + `references/consumption.md` | 需要提取规则和引用追踪 |
| Agent 运行时知识查询 | `references/consumption.md` §5 | 需要查询预算和入口 |

### 参考文件清单

| 文件 | 内容 | 对应原 SKILL.md 章节 |
|------|------|---------------------|
| `references/architecture.md` | 知识体系架构（5 层）、分类定义、三层索引、目录结构 | §2, §3 |
| `references/extraction.md` | 知识提取规则、条目模板、导入进化策略、提升机制 | §4 |
| `references/consumption.md` | 知识消费机制、查询流程、各阶段查询预算 | §5 |
| `references/evolution.md` | 知识生命周期、冲突处理、Lint 规则、Query 操作 | §6 |
| `references/collaboration.md` | 团队协作机制、贡献模式、冲突解决、角色定义 | §2.6 |

---

## 3. 核心概念速览

### 3.1 五层知识存储

| 层级 | 位置 | 内容 | 共享 |
|------|------|------|------|
| Layer 0-P | `~/.ai-team/preferences/` | 个人偏好 | 不共享 |
| Layer 0-T | `{knowledge-repo}/team-conventions/` | 团队约定 | Git |
| Layer 1 | `{knowledge-repo}/tech-wiki/` | 技术知识 | Git |
| Layer 2 | `{knowledge-repo}/biz-wiki/{domain}/` | 业务知识 | Git |
| Layer 3 | `{project}/docs/knowledge-base/` | 项目上下文 | 随项目 |

> `{knowledge-repo}` = `project.yaml` 中 `knowledge_repo.local_path`

### 3.2 五种知识类型

| 类型 | 定义 | 子字段 |
|------|------|--------|
| `model` | 实体定义、数据结构、关系图 | — |
| `decision` | 技术选型、架构决策及理由 | — |
| `guideline` | 推荐做法或禁止做法 | `polarity: recommend \| avoid` |
| `pitfall` | 已知风险、故障模式、排查步骤 | — |
| `process` | 业务流程、状态机、操作步骤 | — |

### 3.3 三级成熟度

```
draft → verified（1 个工作流验证）→ proven（≥2 个项目验证）
  ↑ 衰减：proven 12 月未引用 → verified → draft → archived
```

### 3.4 三层渐进式索引

```
Layer A: knowledge-catalog.md（~50 行，全景目录）
  ↓ 定位分类
Layer B: {分类}/catalog.md（~100-300 行，一行一条摘要）
  ↓ 筛选相关条目
Layer C: TK-*.md / BK-*.md（完整条目，按需读取）
```

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
→ 加载 references/extraction.md，扫描最近 DONE 工作流，提取知识

用户: 这个模块之前有什么已知的坑吗？
→ 加载 references/consumption.md，多层搜索 pitfall 和 guideline(avoid)

用户: 查看知识库状态
→ 加载 references/architecture.md，展示统计
```

---

## 8. 与其他 Skill 的协作

| 协作 Skill | 协作方式 | 方向 |
|-----------|---------|------|
| workflow-orchestrator | ARCHIVE 阶段触发知识提取 + 提升判定 | 双向 |
| team-hub | 知识库健康度作为团队看板指标 | → team-hub |
| quality-guardian | 质量问题转化为 pitfall 知识条目 | quality-guardian → |

---

## 9. 行为约束

### 9.1 必须做的（DO）

- ✅ **按需加载**：根据操作类型仅加载对应的参考文件（见 §2 路由表）
- ✅ 每次提取前先搜索已有条目避免重复
- ✅ 所有知识条目必须包含完整的 evidence
- ✅ 保持各层 index.json 与实际文件同步
- ✅ 提取后必须执行提升判定
- ✅ 团队知识贡献通过 Git 分支 + 合并流程

### 9.2 禁止做的（DON'T）

- ❌ 禁止一次性加载所有参考文件（按需加载！）
- ❌ 禁止在工作流执行中修改正在进行的产物
- ❌ 禁止将 draft 级别知识作为强制规则推送
- ❌ 禁止自动删除知识条目（只允许归档）
- ❌ 禁止跳过提升判定直接写入 Layer 1/Layer 2
- ❌ 禁止修改 log.md 中的历史记录（只允许追加）
