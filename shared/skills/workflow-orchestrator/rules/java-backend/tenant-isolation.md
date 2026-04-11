---
description: 多租户隔离规范。当任务涉及租户上下文、tenant_id、数据隔离、缓存隔离、配置隔离时加载此规则。
alwaysApply: false
enabled: true
---

# 多租户隔离规范 (CRITICAL)

> 本规则覆盖：租户上下文、数据隔离、配置隔离、缓存隔离。

## 1. 租户上下文
- 所有业务逻辑必须通过 `TenantContextHolder.getTenantId()` 获取租户 ID。
- **CRITICAL**: 禁止通过前端入参、URL 路径、Header 中的裸值直接替代系统租户上下文参与数据库过滤。

### 1.1 tenant_id 统一类型标准（CRITICAL）
- **CRITICAL**: `tenant_id` 在所有层级必须统一为以下类型，禁止混用：
  - **Java 实体层**：`Long`（包括 `BaseEntity.tenantId`、`LoginUser.tenantId`、所有 DTO/VO 中的 tenantId）
  - **数据库 DDL 层**：`BIGINT NOT NULL DEFAULT 0`
  - **TenantContextHolder**：`ThreadLocal<Long>`
  - **HTTP Header 透传**：`String`（仅在 HTTP 传输层通过 `String.valueOf()` 转换）
- **CRITICAL**: 禁止在任何 Java 类中将 `tenantId` 声明为 `String` 类型。
- **CRITICAL**: 禁止在 DDL 中将 `tenant_id` 声明为 `VARCHAR` 类型。
- **REQUIRED**: 不同类中语义相同的字段（如 `BaseEntity.tenantId` 和 `LoginUser.tenantId`）必须使用完全相同的 Java 类型。

## 2. 数据隔离
- 所有数据库表必须包含 `tenant_id` 字段。
- 使用 MyBatis Plus 多租户拦截器自动注入 `tenant_id` 过滤条件。
- **CRITICAL**: 禁止在 Mapper 手写 `where tenant_id = ?`，除非是框架明确无法覆盖的特殊场景，并需注明原因。
- **CRITICAL**: 任意查询、更新、删除操作都不得绕过租户隔离能力。
- **REQUIRED**: 新增数据时必须自动写入当前上下文中的 `tenant_id`。

## 3. 配置隔离
- 租户私有配置存储在 Nacos。
- Key 命名规范：`{tenantId}.{configName}`

## 4. 缓存隔离
- Redis Key 必须带租户前缀：
  - `app:tenant:{tenantId}:cache:{key}`

## 5. 微服务间租户透传
- **CRITICAL**: 微服务间调用必须透传租户上下文。
- **REQUIRED**: 通过 Feign `RequestInterceptor` 自动透传 `tenantId`、`traceId`、用户身份等上下文信息。
- **CRITICAL**: 禁止依赖前端重复传递租户 ID 来实现跨服务租户隔离。
- **REQUIRED**: 下游服务接收到请求后，必须将透传的租户信息写入上下文，再进入业务逻辑。
- **CRITICAL**: 微服务调用链中必须防止上下文丢失导致的租户数据串读。
