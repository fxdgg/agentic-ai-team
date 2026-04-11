# ur-ai-team Agent 文档索引

> **生成日期**: 2026-04-10  
> **更新频率**: 定期更新与 Agent 定义保持同步  
> **访问方式**: 本目录中的 Markdown 文件

---

## 📚 文档体系

本 Agent 文档包含以下几层级结构：

### 第 1 层：参考资料（Reference）

这一层是原始的 Agent 定义文件和工作流规范：

#### Agent 定义文件

位置: `../workflow-orchestrator/agents/`

| 文件 | 用途 | 阶段 | 说明 |
|-----|------|------|------|
| product-analyst.md | 产品需求分析 | ANALYSE_PRODUCT | 4 个成员的 Parallel Agent |
| fullstack-analyst.md | 技术需求分析 | ANALYSE_TECH | 全栈设计，4 个成员 |
| java-architect.md | Java 后端架构设计 | ARCHITECT_BACKEND | Java/Spring Cloud 专业化 |
| backend-architect.md | 通用后端架构设计 | ARCHITECT_BACKEND | 支持 Node.js/Python/Go |
| frontend-architect.md | 前端架构设计 | ARCHITECT_FRONTEND | Web + 小程序 |
| web-developer.md | Web 前端开发 | IMPLEMENT | React/Vue 等 |
| miniprogram-developer.md | 小程序开发 | IMPLEMENT | Taro 小程序 |
| build-verifier.md | 编译验证 | BUILD_VERIFY | 通用 + 平台特定 |
| e2e-link-verifier.md | 端到端链路验证 | E2E_VERIFY | 7 维度验证 |
| test-engineer.md | 测试验证 | TEST | 3 层测试体系 |
| visual-reviewer.md | 视觉验收 | VISUAL_REVIEW | AI 驱动的设计对比 |
| archiver.md | 归档总结 | ARCHIVE | 汇总、知识库推送 |

#### 后端领域开发 Agent

位置: `../workflow-orchestrator/agents/backend-developers/`

| 文件 | 用途 |
|-----|------|
| backend-dev-specification.md | 通用后端开发规范（所有领域 Agent 共享） |

> **说明**: 后端领域开发 Agent 不再使用预注册的独立文件，而是由编排器根据 `domain-registry.json` 动态生成。领域差异通过 Prompt 注入和 `extraRules` / `extraQualityChecks` 字段表达。

#### 工作流规范

位置: `../workflow-orchestrator/phases/` 和 `../workflow-orchestrator/rules/`

关键规范文件：
- phases/analyse-product-rules.md
- phases/analyse-tech-rules.md
- phases/architect-backend-rules.md
- phases/implement-rules.md
- phases/build-verify-rules.md
- rules/java-backend/api-convention.md
- rules/java-backend/database-design.md
- rules/java-backend/feign-communication.md
- ...等 (详见 workflow-orchestrator 目录)

### 第 2 层：综合指南（这一层）

**位置**: 本目录 (`agent-catalog/`)

高层次的综合整理和导航文档：

| 文档 | 用途 | 推荐读者 |
|-----|------|---------|
| **AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md** | 完整 Agent 系统参考 | 所有人（首先阅读） |
| **JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md** | Java 领域 Agent 快速参考 | 后端开发、架构师 |
| **WORKFLOW_ORCHESTRATION_GUIDE.md** | 工作流编排机制详解 | 编排器管理员、流程设计者 |
| **INDEX.md** | 本文档，导航指南 | 所有人（查找时阅读） |

---

## 🎯 快速导航

### 我需要...

#### 了解整个 Agent 系统

**推荐路径**: 
1. 阅读 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` 的"系统架构"部分 (5 分钟)
2. 阅读"Agent 完整清单"部分 (15 分钟)
3. 阅读"工作流阶段与 Agent 映射"部分 (10 分钟)

**预计耗时**: 30 分钟

---

#### 深入理解 Java 领域开发 Agent 体系

**推荐路径**:
1. 阅读 `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md` (20 分钟)
2. 查看 7 个领域 Agent 的描述 (5 分钟)
3. 了解通用约束（@changelog、8 项强制规范等）(10 分钟)

**预计耗时**: 35 分钟

---

#### 实现某个具体的 Java 领域功能

**推荐路径**:
1. 快速查看 `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md` 中对应领域的描述 (2 分钟)
2. 阅读相应的 Agent 定义文件 (如 `user-center-developer.md`) (10 分钟)
3. 查看"8 项强制规范"对应的规范文件 (20 分钟)
4. 开始实现，参考"完成检查清单" (全程)

**预计耗时**: 32 分钟 + 开发时间

---

#### 理解工作流编排机制

**推荐路径**:
1. 阅读 `WORKFLOW_ORCHESTRATION_GUIDE.md` 的"工作流状态机"部分 (10 分钟)
2. 阅读"核心调度规则"部分 (15 分钟)
3. 阅读"Parallel Agent 调度协作"部分 (15 分钟)

**预计耗时**: 40 分钟

---

#### 查找特定 Agent 的职责

**快速方法**:
1. 打开 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md`
2. 在"Agent 完整清单"中按阶段查找

**示例**: 找 TEST 阶段的 Agent
```
AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md
  → 工作流阶段与 Agent 映射
  → BUILD_VERIFY/VISUAL_REVIEW/E2E_VERIFY/TEST
  → 找到 test-engineer.md
```

---

#### 了解某个 Agent 的输入/输出

**方法**:
1. 在 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` 中找到该 Agent
2. 查看对应行中的"输出"和"备注"列
3. 如需详细信息，打开对应的 Agent 定义文件

**示例**: fullstack-analyst 的输出
```
输出: tech-requirements.md + platform-specific docs + tech-clarify.json
```

---

### 我想查看...

#### 工作流的完整状态机图

→ `WORKFLOW_ORCHESTRATION_GUIDE.md` § "工作流状态机"

#### 7 个电商领域 Agent 的依赖关系

→ `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md` § "领域依赖关系图"

#### BUILD_VERIFY 的强制流转规则

→ `WORKFLOW_ORCHESTRATION_GUIDE.md` § "BUILD_VERIFY 强制流转"

#### 搜索预算控制策略

→ `WORKFLOW_ORCHESTRATION_GUIDE.md` § "搜索预算控制"

#### @changelog 标记示例

→ `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md` § "代码溯源标记"

#### Parallel Agent 调度的工作流程

→ `WORKFLOW_ORCHESTRATION_GUIDE.md` § "Parallel Agent 调度协作"

---

## 📖 文档结构

### AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md

**章节结构**:
1. 系统架构 - 核心设计原则和状态机
2. Agent 完整清单 - 按阶段分类的所有 Agent
3. 工作流阶段与 Agent 映射 - 阶段 ↔ Agent 关系表
4. Agent 分类与角色 - 按功能分类：分析/架构/开发/验证/归档
5. Java 领域开发 Agent 系统 - 7 个电商领域的详细说明
6. Agent 协作关系 - 数据流依赖图和协作约束
7. 关键调度规则 - IntentGate、澄清、回退等
8. 质量控制体系 - 质量门禁、评分维度、三步模式
9. 快速参考 - 常用路径、命令、检查清单
10. 附录 - Agent 文件清单

**最适合用于**: 全面了解系统、查找具体信息

---

### JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md

**章节结构**:
1. 7 个电商领域 Agent - 每个领域的详细说明
2. Java 领域 Agent 的通用约束 - @changelog、8 项规范、包结构、Convert 类
3. 调度规则 - 优先级执行顺序、Parallel Agent 创建指令
4. 领域依赖关系图 - Feign 通信约束
5. 质量检查维度 - 各领域的特殊检查项
6. 实现报告模板 - 完成后的汇报格式
7. 快速检查清单 - 实现前/中/后的检查清单

**最适合用于**: Java 后端开发、领域架构设计

---

### WORKFLOW_ORCHESTRATION_GUIDE.md

**章节结构**:
1. 工作流状态机 - 完整的 16 阶段状态转移图
2. 核心调度规则 - 澄清自动判断、三步模式、IntentGate、BUILD_VERIFY 强制流转等
3. Parallel Agent 调度协作 - 3 个应用场景的详细工作流
4. 搜索预算控制 - 优先级链、分级预算、@tech-explorer 3 轮策略
5. 上下文健康度监控 - 监控维度、输出字段
6. 常用编排器命令 - /start-workflow 等
7. 质量门禁等级 - P0 强制/P1 可选/其他不阻断
8. 回退机制 - 规则、允许情况、不允许情况
9. state.json 关键字段 - JSON 结构示例

**最适合用于**: 工作流设计、编排器管理

---

## 🔗 文档间的引用关系

```
AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md (主要参考)
  ↓ 详细信息 → JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md
  ↓ 详细信息 → WORKFLOW_ORCHESTRATION_GUIDE.md
  ↓ 原始定义 → workflow-orchestrator/agents/*.md
  
backend-developers/backend-dev-specification.md (后端开发通用规范)
  ↓ 领域差异 → domain-registry.json 动态注入
  ↓ 规范文件 → rules/java-backend/*.md
  
WORKFLOW_ORCHESTRATION_GUIDE.md (流程管理专用)
  ↓ 详细规范 → phases/{phase}-rules.md
  ↓ 调度逻辑 → phases/implement-rules.md
```

---

## ✅ 典型使用场景

### 场景 1：新员工入职

**第 1 天**:
- 阅读 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` 完整版 (2 小时)
- 了解工作流全貌、Agent 职能划分、输入输出关系

**第 2-3 天**:
- 根据职位方向选择深入：
  - 后端开发 → `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md`
  - 工作流管理 → `WORKFLOW_ORCHESTRATION_GUIDE.md`

**第 1 周**:
- 参与实际项目，按需查阅具体 Agent 定义文件

---

### 场景 2：设计新功能的技术方案

**步骤**:
1. 阅读 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` § "Agent 分类与角色" (10 分钟)
2. 确定涉及的领域（1-7 个） (5 分钟)
3. 查看 `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md` 中各领域的"被调用方"关系 (5 分钟)
4. 根据依赖关系确定实现顺序 (5 分钟)
5. 生成技术方案文档，包含 Agent 调度计划 (30 分钟)

**总耗时**: ~1 小时

---

### 场景 3：调查某个 Agent 的输出不符合预期

**步骤**:
1. 打开 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md`
2. 在"Agent 完整清单"中定位该 Agent (1 分钟)
3. 查看该 Agent 的"输出"和"质量门禁" (1 分钟)
4. 打开对应的 Agent 定义文件 (agents/xxxx.md) (5 分钟)
5. 查看"输出产物"和"质量评分"部分 (5 分钟)
6. 定位问题原因，提出改进建议 (10 分钟)

**总耗时**: ~22 分钟

---

## 📞 常见问题

### Q1: 我不确定从哪里开始阅读

**A**: 按以下顺序：
1. 本文档 (INDEX.md) - 2 分钟
2. `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` 的"系统架构" - 5 分钟
3. `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` 的"Agent 完整清单" - 20 分钟
4. 根据需要深入其他文档

---

### Q2: 我需要查看某个 Agent 的完整定义

**A**: 
1. 在 `AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md` 中找到该 Agent
2. 根据提示的"文件"列找到对应的 .md 文件
3. 打开 `workflow-orchestrator/agents/` 中的对应文件

**示例**: 查看后端领域开发 Agent 的通用规范
```
找到: agents/backend-developers/backend-dev-specification.md
打开并查看完整规范（工程实践、验证协议、完成检查清单等）
领域差异通过 domain-registry.json 动态注入
```

---

### Q3: 我需要理解 Parallel Agent 是如何工作的

**A**: 阅读 `WORKFLOW_ORCHESTRATION_GUIDE.md` § "Parallel Agent 调度协作"，包括 3 个具体场景示例

---

### Q4: 我需要找到 Java 后端的所有规范文件

**A**: 参见 `JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md` § "引用必读（8 项 CRITICAL）"

---

### Q5: 我想知道搜索预算如何分配

**A**: 参见 `WORKFLOW_ORCHESTRATION_GUIDE.md` § "搜索预算控制"，包括优先级链、分级预算、3 轮策略等

---

## 🔄 文档维护

### 更新时机

- Agent 定义有变更 → 对应的 Comprehensive Guide 中的"Agent 完整清单"需要更新
- 工作流流程有变更 → WORKFLOW_ORCHESTRATION_GUIDE.md 需要更新
- Java 领域 Agent 新增或修改 → JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md 需要更新
- 新增 Agent → 所有 3 个综合指南都需要更新

### 版本控制

所有文档都在 git 中版本控制，主要的变更应该伴随 commit message 说明

---

## 📊 文档统计

| 文档 | 字数 | 章节数 | 表格数 | 代码块 |
|-----|------|--------|--------|--------|
| AGENT_SYSTEM_COMPREHENSIVE_GUIDE.md | ~15,000 | 10 | 20+ | 5+ |
| JAVA_DOMAIN_DEVELOPERS_QUICK_REFERENCE.md | ~10,000 | 9 | 15+ | 3+ |
| WORKFLOW_ORCHESTRATION_GUIDE.md | ~12,000 | 9 | 18+ | 4+ |
| 总计 | ~37,000 | 28 | 53+ | 12+ |

---

**END OF INDEX**

> 本文档是 ur-ai-team Agent 文档体系的导航和索引。  
> 最后更新: 2026-04-10
