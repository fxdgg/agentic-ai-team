# Java 领域开发 Agent 模板目录

> **重要说明**: 本目录下的 Agent 定义文件是以**电商项目（7 个微服务）为例**的参考实例。
> 
> 所有业务领域 Agent（除 `common-developer.md` 外）均基于 `_template.md` 通用模板生成。
> 当应用到新项目时，只需复制模板并填写领域配置即可。

## 架构概览

```
java-domain-developers/
├── _template.md                          # 🔧 通用模板（包含所有 {{占位符}}）
├── _template-variables.md                # 📖 占位符完整说明文档
├── common-developer.md                   # ⚙️ 公共模块（特殊结构，不使用通用模板）
├── user-center-developer.md              # 实例：用户中心
├── product-center-developer.md           # 实例：商品中心
├── merchant-center-developer.md          # 实例：商户中心
├── marketing-center-developer.md         # 实例：营销中心
├── trade-center-developer.md             # 实例：交易中心
├── logistics-center-developer.md         # 实例：物流中心
└── README.md                             # 本文件
```

## 模板与实例的关系

### 通用模板 `_template.md`

模板包含了业务领域 Agent 约 **90%** 的通用内容，包括：
- 代码溯源标记机制（`@changelog`）
- 写前必读机制
- 引用必读流程（Builder 检查、语义字段一致性、API 版本兼容性等 8 项 CRITICAL 检查）
- 包结构一致性预检
- Convert 类规范
- 规则引用体系（强制 + 条件）
- 完成检查清单

### 各实例文件仅包含领域差异

每个实例 Agent 文件是模板的完整渲染结果，领域差异部分包括：

| 占位符 | 含义 | 示例（用户中心） |
|--------|------|------------------|
| `{{DOMAIN_CN}}` | 领域中文名 | 用户中心 |
| `{{DOMAIN_ID}}` | 领域英文标识 | user-center |
| `{{SERVICE_NAME}}` | 微服务目录名 | vibe-user-center |
| `{{EXPERTISE_*}}` | 专业背景描述 | 精通用户体系与认证授权系统设计 |
| `{{CAPABILITY_1~3}}` | 核心能力 | 用户体系设计能力、安全编码能力... |
| `{{COLLABORATION_LINES}}` | 上下游依赖 | 被调用方: trade-center / marketing-center |
| `{{FORBIDDEN_DIRECTORIES}}` | 禁止操作目录 | 除自身外的所有微服务 |
| `{{DOMAIN_RESPONSIBILITIES}}` | 领域职责表 | 用户注册、登录、会员体系... |
| `{{EXTRA_IMPL_RULES}}` | 额外实现规则 | trade-center: 金额用 BigDecimal |
| `{{EXTRA_QUALITY_CHECKS}}` | 额外检查项 | trade-center: 分布式事务方案合理 |

完整的占位符说明见 `_template-variables.md`。

### `common-developer.md` 为何不使用模板

公共模块有以下根本性差异，不适合套用通用模板：
1. **无领域职责表** — 公共模块不属于任何业务领域
2. **无 Feign 依赖** — 公共模块不调用其他微服务
3. **特殊约束** — 禁止反向依赖业务层、严格复用原则、强制向下兼容
4. **无 Convert 规范** — 公共模块通常不直接处理业务 DTO
5. **输入不同** — 使用 `priority-list.md` 而非 `dependency-graph.md`
6. **强制引用规则不同** — 不含 `api-convention.md` 和 `database-design.md`

## 新增领域 Agent

### 步骤

1. **复制模板**: `cp _template.md {new-domain}-developer.md`
2. **全局替换基础占位符**:
   - `{{SERVICE_NAME}}` → 实际微服务目录名（如 `vibe-payment-center`）
   - `{{DOMAIN_CN}}` → 中文名（如 `支付中心`）
   - `{{DOMAIN_ID}}` → 英文标识（如 `payment-center`）
3. **填写领域专有部分**:
   - 专业背景 + 核心能力
   - 协作关系（上下游依赖）
   - 禁止操作目录列表
   - 领域职责表
   - 额外实现规则（如有）
   - 额外检查项（如有）
4. **在编排器中注册**: 新 Agent 会被 `SKILL.md` §12.2 动态注册机制自动发现

### 维护原则

- **修改通用逻辑**（如新增 CRITICAL 检查项）→ 先改 `_template.md`，再同步到所有实例
- **修改某领域特有逻辑** → 只改对应实例文件
- **新增领域** → 从模板派生，只填差异部分
