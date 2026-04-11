---
description: 数据库设计与持久层规范。当任务涉及建表、DDL、SQL、Entity、Mapper、字段设计、索引、主键、审计字段、逻辑删除、MyBatis Plus 使用时加载此规则。
alwaysApply: false
enabled: true
---

# 数据库设计与持久层规范

> 本规则覆盖：数据库设计原则、通用字段、主键策略、逻辑删除、审计字段自动填充、索引与唯一约束、DDL 文件管理、MyBatis Plus 使用。

## 1. 数据库设计基本原则
- **REQUIRED**: 表结构设计必须优先满足多租户隔离、可维护性、可审计性要求。
- **CRITICAL**: 所有业务主表、明细表、配置表、关系表必须包含 `tenant_id` 字段，除非明确认定为全局字典表或系统级公共表。
- **REQUIRED**: 表名、字段名统一使用小写下划线风格。
- **REQUIRED**: 字段命名必须具备明确业务语义，禁止使用 `a`、`b`、`c1`、`temp_value`。
- **REQUIRED**: 能通过字段表达清楚的数据，不得过度依赖 `json/text` 大字段存储结构化信息。
- **RECOMMENDED**: 对高频查询条件、唯一约束字段、关联字段建立合理索引。
- **CRITICAL**: 禁止无约束地创建冗余索引。

## 2. 通用字段规范
每张业务表建议至少包含：
- `id`: 主键（`bigint`）
- `tenant_id`: 租户 ID（`bigint`，NOT NULL DEFAULT 0）— **CRITICAL**: 统一使用 `BIGINT`，禁止使用 `VARCHAR`，与 Java 实体层 `Long` 类型对应
- `created_by`: 创建人
- `created_time`: 创建时间（`datetime` 或 `timestamp`）
- `updated_by`: 更新人
- `updated_time`: 更新时间（`datetime` 或 `timestamp`）
- `deleted`: 逻辑删除标识（`tinyint`，默认值 `0`）

## 3. 主键策略规范
- **REQUIRED**: 所有表必须有主键，且策略在同一项目内必须统一。
- **RECOMMENDED**: 微服务分布式场景优先使用雪花 ID 或等价分布式主键方案。
- **CRITICAL**: 禁止将业务含义强绑定到主键生成规则上。
- **REQUIRED**: 若使用 MyBatis Plus 主键策略，必须统一配置并在 Entity 中显式声明。

## 4. 逻辑删除规范
- **REQUIRED**: 默认采用逻辑删除，字段统一使用 `deleted`。
- **REQUIRED**: 取值统一：`0`=未删除，`1`=已删除。
- **CRITICAL**: 禁止在不同表中混用 `is_deleted`、`delete_flag`、`del_flag`。
- **CRITICAL**: 所有查询、更新操作都必须保证逻辑删除条件生效。
- **REQUIRED**: 仅在归档、清理、合规要求明确的场景下才允许物理删除。

## 5. 审计字段自动填充规范
- **REQUIRED**: `created_by`、`created_time`、`updated_by`、`updated_time` 必须通过统一机制自动填充。
- **REQUIRED**: `tenant_id` 在新增数据时必须自动填充。
- **REQUIRED**: 使用 MyBatis Plus `MetaObjectHandler` 统一处理。
- **CRITICAL**: 禁止在各个 Service 中手工重复写入通用审计字段逻辑。

### 新增时自动填充
`tenant_id`、`created_by`、`created_time`、`updated_by`、`updated_time`、`deleted = 0`

### 更新时自动填充
`updated_by`、`updated_time`

### 审计字段值来源
- `tenant_id` → `TenantContextHolder.getTenantId()`
- `created_by` / `updated_by` → 统一登录上下文（系统任务可用 `system`/`job`/`scheduler`）
- `created_time` / `updated_time` → 服务端当前时间
- **CRITICAL**: 禁止信任前端传入 `createdBy`、`updatedBy`、`createdTime`、`updatedTime`。

## 6. Entity 字段注解规范
- **REQUIRED**: 审计字段应在 Entity 上声明自动填充策略：
  - `created_time` → `FieldFill.INSERT`
  - `updated_time` → `FieldFill.INSERT_UPDATE`
  - `created_by` → `FieldFill.INSERT`
  - `updated_by` → `FieldFill.INSERT_UPDATE`
- **REQUIRED**: 逻辑删除字段应配合 MyBatis Plus 逻辑删除能力配置。
- **REQUIRED**: `tenant_id` 若由自动填充写入，应在 Entity 中明确字段定义。

## 7. 索引与唯一约束规范
- **REQUIRED**: 高频查询字段必须评估索引。
- **REQUIRED**: 唯一业务约束必须通过数据库唯一索引兜底。
- **CRITICAL**: 多租户场景下，唯一约束必须考虑 `tenant_id` 维度（如 `(tenant_id, code)`）。
- **CRITICAL**: 禁止忽略租户维度导致跨租户唯一冲突。

## 8. 字段设计规范
- **REQUIRED**: 状态字段必须使用明确枚举语义，不得使用魔法值。
- **RECOMMENDED**: 金额使用分为单位的整数类型或统一精度的 `decimal`。
- **CRITICAL**: 禁止使用 `double` 存储金额。
- **REQUIRED**: 布尔语义字段统一使用明确命名（`enabled`、`locked`、`deleted`）。
- **REQUIRED**: 时间字段统一命名为 `xxx_time`。

## 9. 数据库默认值规范
- **REQUIRED**: 通用状态字段、逻辑删除字段应设置合理默认值。
- **CRITICAL**: 禁止数据库默认值与业务含义冲突。
- **RECOMMENDED**: 重要审计字段以应用自动填充为主，数据库默认值为辅。

## 10. 变更与脚本规范
- **REQUIRED**: 表结构变更必须通过规范化脚本管理。
- **REQUIRED**: 新增字段时必须评估：是否影响历史数据、是否需要默认值、是否需要回填、是否需要索引。
- **CRITICAL**: 禁止在高并发表上随意执行高风险 DDL 而无评估。

## 11. DDL 文件管理规范

### 11.1 存放位置
- **CRITICAL**: DDL 必须存储在各个域服务代码仓库内的 `sql` 文件夹下。
- **CRITICAL**: 禁止仅在线上数据库中存在表结构，而代码仓库中无对应 DDL。
- **CRITICAL**: 禁止将某个域服务的数据表 DDL 散落在其他服务仓库中。

### 11.2 推荐目录结构
```text
src/main/resources/sql/
├── ddl/
│   ├── V1__init_schema.sql
│   ├── V2__create_order_table.sql
│   └── V3__alter_order_add_status.sql
├── dml/
│   ├── init_data.sql
│   └── dict_data.sql
└── rollback/
    └── V2__rollback_create_order_table.sql
```

### 11.3 DDL 管理范围
- **REQUIRED**: 建表语句、字段变更、索引变更、唯一约束变更、初始化字典表结构、表结构演进脚本必须纳入管理。
- **CRITICAL**: 只要变更会影响 Entity、Mapper、查询条件、索引、事务行为或业务逻辑，就必须先更新 DDL。

### 11.4 变更前置原则
- **CRITICAL**: 修改 Entity、Mapper、Service、DTO、VO 之前，若涉及字段/索引/表结构变化，必须先审视 `sql` 目录中的 DDL。
- **CRITICAL**: 若 DDL 与当前代码结构不一致，必须优先修正 DDL 或显式指出不一致点。
- **REQUIRED**: 代码生成前必须确认：表名-Entity 对应、字段映射、类型映射、主键策略、逻辑删除、审计字段、索引、`tenant_id` 是否存在。

### 11.5 DDL 与代码一致性要求
- **CRITICAL**: DDL、Entity、Mapper、查询逻辑、转换对象之间必须保持一致。
- **CRITICAL**: 禁止：代码新增字段但 DDL 未更新、DDL 已新增字段但 Entity 未同步、表结构已改名但旧代码仍按旧字段操作。

### 11.6 DDL 命名规范
- **REQUIRED**: 格式 `V{版本号}__{动作}_{对象}.sql`。
- **CRITICAL**: 禁止使用无语义文件名（`1.sql`、`test.sql`、`temp_change.sql`）。

### 11.7 域边界约束
- **CRITICAL**: 一个域服务只能维护自己负责的数据表 DDL。
- **CRITICAL**: 禁止在 `order-service` 中维护 `user-service` 专属业务表结构。

### 11.8 变更脚本要求
- **REQUIRED**: 所有结构性变更必须以增量脚本形式记录。
- **REQUIRED**: 高风险变更建议提供回滚脚本或说明。
- **CRITICAL**: 禁止直接手工改库但不补充变更脚本。

### 11.9 自动生成代码前的 DDL 审视流程
- **CRITICAL**: 处理新增表/字段/索引/约束/审计字段调整前，必须优先检查 `sql/ddl`。
- 检查顺序：审视 DDL → 确认结构与需求是否匹配 → 不匹配则先输出 DDL → 再生成业务代码。
- **CRITICAL**: 若用户要求直接改业务代码但底层结构不匹配，必须先提醒"需先同步 DDL"。

## 12. MyBatis Plus 使用约束
- 优先使用 `BaseMapper`、`LambdaQueryWrapper`、`LambdaUpdateWrapper`。
- **REQUIRED**: 查询条件构造应具备可读性，避免硬编码字段名。
- **CRITICAL**: 禁止字符串拼接 SQL，避免 SQL 注入风险。
- **CRITICAL**: 涉及租户数据时，删除操作必须确保租户隔离仍然生效。
