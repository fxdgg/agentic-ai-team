# AI Team Skills 注册表

本目录包含 AI Team 项目中 Agent 可调用的所有 Skill 定义。

## 📋 可用 Skills

| Skill | 描述 | 触发关键词 | 依赖 |
|-------|------|-----------|------|
| **tapd-toolkit** | TAPD 扩展技能集：图片上传、附件上传/查询/下载，补充 MCP 原生工具不支持的本地操作 | TAPD、上传图片、上传附件、下载附件 | Python3, tapd-python-sdk |
| **git-push-helper** | Git 自动化推送：暂存 → AI 生成 commit message → 推送 | git push、推送代码、提交并推送 | git |
| **prd-creator** | 苏格拉底式渐进提问引导创建 PRD 需求文档 | 创建需求文档、新建 PRD、写需求 | 无 |
| **send-flow-message** | 通过 Redis 消息队列向企业微信群发送通知 | 发送企微消息、通知企微、企微通知 | Python3, Redis 连接 |
| **skill-creator** | 创建新 Skill、改进现有 Skill、评估 Skill 性能的元工具 | 创建 skill、改进 skill | Python3 |
| **workflow-orchestrator** | 需求驱动的 AI 开发流水线控制器，编排多个专业子 Agent 按 16 阶段状态机执行开发任务 | 启动工作流、新建需求、继续工作流、工作流编排、开发流水线 | 无 |
| **figma-d2c** | Figma 设计稿转代码，16 步检查点协议（CP-0 到 CP-M），单 Agent 模式，IMPLEMENT 阶段自然调度 | D2C、设计稿转代码、figma to code、还原设计稿 | 无 |
| **mcp-setup-guide** | MCP 服务配置引导，引导用户完成 MCP 配置文件创建、Token 申请和连通性验证 | MCP 配置、MCP 连接、配置 TAPD、配置 iWiki、配置 Figma | 无 |
| **team-hub** | 团队级多需求协同管理器，提供角色化看板、瓶颈分析、资源冲突检测（只读聚合器） | 团队看板、角色任务、瓶颈分析、多需求协调、工作量统计 | 无 |
| **capability-router** | Skills 系统的智能前端路由层，分析用户意图并路由到最合适的 Skill 或组合 | 用哪个 skill、推荐处理方式、能力路由、列出 skills | 无 |
| **knowledge-evolution** | 知识进化引擎，从已完成工作流中自动提取可复用知识模式（ADR、最佳实践、反模式、FAQ） | 知识沉淀、经验总结、最佳实践、历史复盘、ADR | 无 |
| **quality-guardian** | 质量守卫，持续监控工作流全流程质量指标，提供质量看板、回退分析、趋势对比和改进建议 | 质量报告、质量看板、回退分析、质量趋势、技术债务 | 无 |
| **model-router** | 多模型智能路由，根据任务复杂度、上下文长度和成本预算智能选择最合适的底层模型 | 模型选择、模型切换、模型成本、模型性能 | 无 |
| **skill-learner** | Skill 自学习引擎，基于工作流历史数据持续评估和优化各 Skill/Agent 的表现 | Skill 评分、Agent 表现、优化建议、效率分析 | 无 |
| **token-budget-manager** | Token 预算管理器，实时追踪 Token 消耗、预算预警、成本优化建议 | Token 消耗、成本报告、预算管理、Token 优化 | 无 |

## 🔧 Skill 调用方式

### 方式一：Agent 工作流自动调用

在 `agent-catalog/` 中定义的 Agent YAML 可声明依赖的 skills：

```yaml
skills:
  - tapd-toolkit
  - git-push-helper
```

### 方式二：后端服务层调用

后端 `app/services/` 中已封装的 Skill：
- `tapd_skill.py` — TAPD 集成能力（通过 tapd-python-sdk 直接调用 TAPD API）

### 方式三：直接 CLI 调用

每个 Skill 的 `SKILL.md` 文档中包含完整的命令行调用示例。

## 📁 目录结构

```
skills/
├── README.md                # 本文件
├── tapd-toolkit/            # TAPD 扩展技能集（图片/附件上传）
│   ├── SKILL.md
│   ├── references/          # 功能参考文档
│   └── scripts/             # Python 脚本 + 公共包
├── git-push-helper/         # Git 推送助手
│   └── SKILL.md
├── prd-creator/             # PRD 需求文档创建
│   └── SKILL.md
├── send-flow-message/       # 企微消息发送
│   ├── SKILL.md
│   └── send.py
├── skill-creator/           # Skill 创建/改进元工具
│   ├── SKILL.md
│   ├── agents/
│   ├── assets/
│   ├── eval-viewer/
│   ├── references/
│   └── scripts/
├── team-hub/               # 团队协作中心（只读聚合器）
│   └── SKILL.md
├── capability-router/      # 能力路由器（意图识别 + Skill 分发）
│   └── SKILL.md
├── knowledge-evolution/    # 知识进化引擎（知识提取 + 沉淀 + 推送）
│   └── SKILL.md
├── quality-guardian/       # 质量守卫（质量监控 + 趋势分析 + 改进建议）
│   └── SKILL.md
├── model-router/          # 多模型智能路由（任务→模型匹配 + 成本优化）
│   └── SKILL.md
├── skill-learner/         # Skill 自学习引擎（评估 + 分析 + 优化建议）
│   └── SKILL.md
├── token-budget-manager/  # Token 预算管理器（消耗追踪 + 预警 + 优化）
│   └── SKILL.md
├── figma-d2c/             # Figma D2C（设计稿转代码，16 步检查点协议）
│   ├── SKILL.md
│   ├── references/        # D2C 参考文档
│   └── scripts/           # D2C 辅助脚本
├── mcp-setup-guide/       # MCP 配置引导（含全局配置同步）
│   └── SKILL.md
└── workflow-orchestrator/   # 工作流编排（多 Agent 开发流水线）
    ├── SKILL.md
    ├── README.md
    ├── agents/              # 子 Agent 定义
    ├── phases/              # 阶段规则片段
    ├── references/          # 数据结构定义
    ├── templates/           # 产物模板
    ├── rules/               # 开发规范
    └── scripts/             # 辅助脚本
```

## 🔗 与 Agent Catalog 的关系

- `agent-catalog/` — 定义 Agent 的角色、能力、工作流程
- `skills/` — 定义 Agent 可调用的外部能力/工具集成
- Agent 在执行任务时，根据 Skill 的触发条件自动加载相关 Skill
