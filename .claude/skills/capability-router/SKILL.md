---
name: capability-router
description: "能力路由器。当用户的请求意图不明确、涉及多个 Skill 协作、或需要推荐最合适的处理方式时触发此技能。作为 Skills 系统的智能前端，分析用户意图并路由到最适合的 Skill 或组合。"
---

# 能力路由器

## 1. 角色定位

本技能是 **Skills 系统的智能前端路由层**。核心职责：

- **识别**用户请求的核心意图（开发、管理、工具、创作）
- **匹配**意图到最合适的 Skill 或 Skill 组合
- **路由**请求到目标 Skill，附带结构化的上下文信息
- **协调**多 Skill 协作场景的执行顺序和数据流转

> **关键原则：能力路由器不执行具体任务，只负责意图识别和路由分发。**

---

## 2. 路由架构

```
用户请求 → [意图识别] → [Skill 匹配] → [路由决策] → 目标 Skill
                                          ↓
                                    [多 Skill 编排] (可选)
```

### 2.1 路由模式

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| **直达路由** | 意图明确，单一 Skill 匹配 | 直接转发到目标 Skill |
| **推荐路由** | 意图模糊，多个 Skill 可能匹配 | 展示候选列表，让用户选择 |
| **组合路由** | 请求涉及多个 Skill 的能力 | 编排多个 Skill 的协作执行 |
| **兜底路由** | 无 Skill 匹配 | 使用通用 Agent 能力处理，或建议用户细化需求 |

---

## 3. Skill 注册表

### 3.1 已注册 Skills

能力路由器维护一份动态的 Skill 注册表，从 `.claude/skills/` 目录扫描：

| Skill ID | 能力域 | 意图关键词 | 优先级 |
|----------|--------|-----------|--------|
| `workflow-orchestrator` | 开发流水线 | 启动工作流、新建需求、继续工作流、需求开发、工作流编排 | P0 |
| `team-hub` | 团队协作 | 团队看板、角色任务、瓶颈分析、多需求协调 | P0 |
| `prd-creator` | 需求创作 | 创建需求、新建 PRD、写需求文档 | P1 |
| `tapd-toolkit` | 项目管理工具 | TAPD、上传图片、上传附件、下载附件 | P1 |
| `git-push-helper` | 代码管理 | git push、推送代码、提交代码 | P2 |
| `send-flow-message` | 通知集成 | 发送企微消息、通知企微、群通知 | P2 |
| `skill-creator` | 元工具 | 创建 skill、改进 skill、评估 skill | P2 |

### 3.2 动态发现

路由器启动时自动扫描 `.claude/skills/*/SKILL.md` 的 frontmatter：

```
扫描规则:
1. 遍历 .claude/skills/ 下的一级子目录
2. 读取每个子目录的 SKILL.md 文件
3. 解析 frontmatter 中的 name 和 description
4. 从 description 中提取触发关键词
5. 构建 Skill 注册表缓存
```

> **注意**：`capability-router` 自身不出现在路由表中，避免递归路由。

---

## 4. 意图识别

### 4.1 意图分类体系

```
意图树:
├── 开发类 (development)
│   ├── 全流程开发 → workflow-orchestrator
│   ├── 需求文档 → prd-creator
│   ├── 代码提交 → git-push-helper
│   └── 技术问答 → 通用能力
│
├── 管理类 (management)
│   ├── 团队协作 → team-hub
│   ├── 项目管理 → tapd-toolkit
│   └── 进度追踪 → team-hub
│
├── 工具类 (tooling)
│   ├── 文件操作 → 通用能力
│   ├── 消息通知 → send-flow-message
│   └── Skill 管理 → skill-creator
│
└── 复合类 (composite)
    ├── 需求 + 开发 → prd-creator → workflow-orchestrator
    ├── 开发 + 通知 → workflow-orchestrator + send-flow-message
    └── 看板 + 分析 → team-hub
```

### 4.2 意图识别规则

```
优先级匹配策略:

1. 精确匹配（最高优先级）
   - 用户消息包含 Skill 的触发关键词 → 直达路由
   - 例: "启动工作流" → workflow-orchestrator

2. 语义匹配
   - 用户消息不含精确关键词，但语义匹配能力域
   - 例: "我有一个新功能要做" → 推荐 workflow-orchestrator 或 prd-creator

3. 上下文匹配
   - 根据当前活跃的工作流状态推断意图
   - 例: 已有活跃工作流在 IMPLEMENT 阶段 → "继续" 匹配 workflow-orchestrator

4. 兜底策略
   - 无法匹配任何 Skill → 使用通用 Agent 能力
   - 同时展示可用 Skills 列表供用户选择
```

### 4.3 歧义消解

当多个 Skill 同等匹配时，使用以下策略：

```
消解优先级:
1. 用户历史偏好（最近使用的 Skill 优先）
2. 当前上下文相关性（活跃工作流 > 无工作流）
3. Skill 注册表中的优先级（P0 > P1 > P2）
4. 交互确认（展示候选列表让用户选择）
```

---

## 5. 路由执行

### 5.1 直达路由流程

```
1. 识别意图 → 匹配到唯一 Skill
2. 提取用户请求中的关键参数
3. 构建路由上下文:
   - targetSkill: Skill ID
   - userIntent: 用户原始请求
   - extractedParams: 提取的关键参数
   - activeWorkflows: 当前活跃的工作流列表（如果有）
4. 输出路由建议（展示给用户确认或自动执行）
```

### 5.2 推荐路由流程

```
当意图模糊时，展示推荐列表:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔀 能力路由建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

您的请求: "{用户原始请求}"

推荐处理方式:
┌─────────────────────────────────────┐
│ ① 🎯 workflow-orchestrator         │
│    适合: 需要完整的开发流水线       │
│    匹配度: ⭐⭐⭐⭐                │
├─────────────────────────────────────┤
│ ② 📋 prd-creator                   │
│    适合: 先梳理需求文档再开发       │
│    匹配度: ⭐⭐⭐                  │
├─────────────────────────────────────┤
│ ③ 💬 通用对话                       │
│    适合: 只是讨论技术方案           │
│    匹配度: ⭐⭐                    │
└─────────────────────────────────────┘

请选择处理方式（输入编号或直接描述）:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5.3 组合路由流程

```
多 Skill 协作执行顺序:

1. 分析请求中涉及的多个意图
2. 确定 Skill 间的依赖关系（有依赖 → 串行，无依赖 → 可并行）
3. 为每个 Skill 构建独立的上下文
4. 按顺序执行或提示用户分步操作

示例 — "写好需求文档后启动开发":
  Step 1: prd-creator → 输出需求文档
  Step 2: workflow-orchestrator → 以需求文档为输入启动工作流
```

---

## 6. 与其他 Skill 的关系

### 6.1 协作关系图

```
capability-router (路由层)
    │
    ├── workflow-orchestrator (开发编排)
    │       ├── 接收: 需求描述、需求文档路径
    │       └── 返回: 工作流状态、阶段进度
    │
    ├── team-hub (团队协作)
    │       ├── 接收: 角色查询、看板请求
    │       └── 返回: 团队视图、瓶颈分析
    │
    ├── prd-creator (需求创作)
    │       ├── 接收: 需求描述
    │       └── 返回: PRD 文档路径
    │
    ├── tapd-toolkit (项目管理)
    │       ├── 接收: TAPD 操作请求
    │       └── 返回: 操作结果
    │
    ├── git-push-helper (代码管理)
    │       ├── 接收: 推送请求
    │       └── 返回: 推送结果
    │
    ├── send-flow-message (通知)
    │       ├── 接收: 消息内容、目标群
    │       └── 返回: 发送结果
    │
    └── skill-creator (元工具)
            ├── 接收: Skill 定义需求
            └── 返回: Skill 文件路径
```

### 6.2 数据流约定

路由器向目标 Skill 传递的上下文结构：

```json
{
  "route": {
    "from": "capability-router",
    "to": "{target-skill-id}",
    "mode": "direct | recommend | composite",
    "timestamp": "ISO-8601"
  },
  "intent": {
    "raw": "用户原始请求",
    "category": "development | management | tooling | composite",
    "confidence": 0.95,
    "extractedParams": {}
  },
  "context": {
    "activeWorkflows": [],
    "recentSkills": [],
    "currentPhase": null
  }
}
```

---

## 7. 使用方式

### 7.1 自动路由（默认模式）

当 Claude Code 接收到用户请求时，capability-router 在后台进行意图匹配：
- 高置信度（≥0.8）→ 自动路由到目标 Skill
- 中置信度（0.5~0.8）→ 展示推荐列表
- 低置信度（<0.5）→ 使用通用能力处理

### 7.2 显式路由

用户可通过以下方式显式指定目标：

```
用户: 用 workflow-orchestrator 启动一个新需求
→ 跳过意图识别，直接路由到 workflow-orchestrator

用户: 列出所有可用的 Skills
→ 展示 Skill 注册表

用户: 这个请求应该用哪个 Skill 处理？
→ 展示分析过程和推荐结果
```

### 7.3 触发关键词

- "用哪个 skill"、"推荐处理方式"、"能力路由"
- "列出 skills"、"可用技能"、"有哪些能力"
- 任何无法直接匹配到已有 Skill 的模糊请求

---

## 8. 行为约束

### 8.1 必须做的（DO）

- ✅ 每次路由前重新扫描 Skills 目录（确保发现新增 Skill）
- ✅ 在推荐模式下明确展示匹配度和理由
- ✅ 记录路由决策日志（便于回溯和优化）
- ✅ 尊重用户的显式选择（用户指定优先于算法推荐）
- ✅ 组合路由时明确展示执行顺序和依赖关系

### 8.2 禁止做的（DON'T）

- ❌ 禁止自行执行目标 Skill 的具体任务（只路由不执行）
- ❌ 禁止修改任何 Skill 的定义文件
- ❌ 禁止在高置信度匹配时还强制用户确认（减少交互摩擦）
- ❌ 禁止路由到自身（避免递归）
- ❌ 禁止忽略用户的显式指定（用户说用 A 就用 A）

---

## 9. 扩展机制

### 9.1 新增 Skill 接入

新 Skill 只需遵循标准结构即可自动被路由器发现：

```
.claude/skills/{new-skill-name}/
└── SKILL.md    # frontmatter 中包含 name 和 description
```

路由器下次扫描时会自动：
1. 读取 SKILL.md 的 frontmatter
2. 从 description 提取意图关键词
3. 注册到路由表中

### 9.2 路由规则自定义

支持通过配置文件自定义路由优先级和别名：

```json
// docs/router-config.json (可选)
{
  "aliases": {
    "开发": "workflow-orchestrator",
    "需求": "prd-creator",
    "团队": "team-hub"
  },
  "overrides": {
    "workflow-orchestrator": { "priority": "P0" },
    "prd-creator": { "priority": "P0" }
  },
  "defaultSkill": null
}
```

### 9.3 未来演进

| 阶段 | 能力 | 说明 |
|------|------|------|
| Phase 3 | 知识进化集成 | 路由决策可基于历史成功率自动调整权重 |
| Phase 4 | 多模型路由 | 不同 Skill 可配置不同的底层模型 |
| Phase 4 | Token 预算感知 | 根据剩余 Token 预算选择轻量/重量级处理路径 |
