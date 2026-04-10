# Workflow Templates — 工作流模板库
# ====================================
#
# 工作流模板定义了不同交付场景下的标准化流程。
# workflow-orchestrator 根据需求类型选择合适的模板进行编排。

## 可用模板

| 模板 | 文件 | 适用场景 | 阶段数 |
|------|------|---------|--------|
| 全栈交付 | `fullstack-delivery.yaml` | 涉及前后端的完整需求交付 | 6 |
| 纯前端交付 | `frontend-only.yaml` | 纯前端页面/组件开发 | 5 |
| 热修复 | `hotfix.yaml` | 生产环境紧急 Bug 修复 | 4 |

## 全栈交付工作流 (fullstack-delivery)

```
ANALYSE_PRODUCT → ANALYSE_TECH → ARCHITECT → IMPLEMENT → VERIFY → ARCHIVE
```

- 标准六阶段全栈交付流程
- 每阶段支持三步模式（Preview → Execute → Summary）
- 支持阶段回退和跳过

## 纯前端交付工作流 (frontend-only)

```
ANALYSE_UI → DESIGN_FRONTEND → IMPLEMENT_FRONTEND → VERIFY_VISUAL → ARCHIVE
```

- 简化的 5 阶段流程
- 聚焦 UI/UX 设计和前端实现
- 包含视觉回归测试

## 热修复工作流 (hotfix)

```
ANALYSE_ISSUE → IMPLEMENT_FIX → VERIFY_FIX → ARCHIVE
```

- 4 阶段极简流程
- 跳过架构设计，聚焦快速修复
- 更高的质量门禁阈值（0.9）
- 12 小时超时限制

## 自定义模板

可以基于现有模板扩展，创建新的 YAML 文件：

1. 复制最接近需求的模板作为起点
2. 修改 `phases` 定义（增减阶段、调整依赖）
3. 修改 `transitions` 规则（回退、跳过策略）
4. 在 `flow:run` 命令中通过参数指定使用的模板

## 与 Agent Catalog 的关系

模板中的 `agent_role` 字段对应 `agent-catalog/` 中的 Agent 定义。
`dynamic_dispatch: true` 的阶段会根据 capability domain 动态分派 Agent。
