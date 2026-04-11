---
description: Java 微服务开发契约总纲。每次对话自动加载，用于判断当前任务场景并按需加载对应子规则。
alwaysApply: false
enabled: true
---

# Java 微服务开发契约 (v1.6) — 总纲

## 0. 规则优先级
- **CRITICAL**: 绝对强制，违反即视为不可接受。
- **REQUIRED**: 默认必须遵守，除非有明确说明。
- **RECOMMENDED**: 推荐遵守，若有更优方案需说明理由。

## 1. 核心技术栈
- Java 21、Spring Boot 3.3+、Spring Cloud Alibaba、Nacos、OpenFeign
- MyBatis Plus 3.5.x、Lombok
- MySQL 8.0 / TDSQL-C、Redis、SLF4J + Logback

## 2. 子规则调度表

根据当前任务的关键词和场景，**按需加载**对应的子规则。每次任务通常只需加载 1-3 个子规则。

| 子规则 | 适用场景 | 触发关键词 |
|---|---|---|
| `tenant-isolation` | 多租户隔离、租户上下文、数据隔离、缓存隔离 | tenant、租户、隔离、TenantContextHolder、tenant_id |
| `api-convention` | 接口设计、Controller、分页查询、排序、参数校验 | Controller、接口、API、分页、排序、PageQuery、PageResult、Result<T>、校验 |
| `config-management` | 配置文件、Nacos 配置中心、环境配置、敏感配置 | yml、yaml、配置、Nacos、bootstrap、application、DataId、环境 |
| `feign-communication` | 微服务间调用、Feign 客户端、服务注册发现、上下文透传 | Feign、远程调用、服务间通信、FeignClient、Interceptor、熔断、降级 |
| `package-structure` | 包结构、新建类、分层约定、目录组织 | package、包、目录、分层、controller、service、mapper、model |
| `database-design` | 建表、DDL、Entity、Mapper、审计字段、索引、MyBatis Plus | 表、DDL、SQL、Entity、Mapper、字段、索引、主键、审计、逻辑删除、数据库 |
| `transaction-convert-log` | 事务管理、手写 Convert 转换、日志规范 | 事务、Transactional、Convert、BeanCopyUtils、转换、日志、log、SLF4J |
| `performance-security` | 缓存设计、Redis、安全审计、SQL 注入防护 | 缓存、Redis、TTL、安全、注入、越权、审计日志 |
| `dependency-management` | 第三方依赖引入、pom.xml 修改、版本管理、SDK 引入 | pom、dependency、依赖、版本、Maven、SDK、第三方、引入、artifact |
| `codebuddy-output` | 代码生成约束、输出规范、默认开发原则 | 生成代码、输出、开发原则（建议在复杂代码生成任务时主动加载） |

## 3. 全局强制约束（精简版）

以下约束无论任何场景都必须遵守，无需加载子规则：

- **CRITICAL**: 严禁在 Controller 直接返回 Entity。
- **CRITICAL**: 所有接口返回值必须使用 `Result<T>` 统一包装。
- **CRITICAL**: 禁止 `try-catch` 吞掉异常，业务异常统一使用 `BusinessException`。
- **CRITICAL**: 禁止字符串拼接 SQL。
- **CRITICAL**: 禁止使用 `System.out.println`，必须使用 SLF4J。
- **CRITICAL**: 禁止信任前端传入的 `tenantId` 进行数据权限控制。
- **CRITICAL**: 禁止使用 `double` 存储金额。
- **CRITICAL**: 若需求涉及数据库结构变更，必须先审视 DDL 文件。

## 4. 调度规则

1. 分析用户当前任务的意图和关键词。
2. 对照上方调度表，确定需要加载的子规则（通常 1-3 个）。
3. 使用 `read_rules` 工具加载对应子规则后，再执行任务。
4. 若任务跨多个领域，可同时加载多个子规则。
5. 若任务简单且全局强制约束已覆盖，可不加载子规则。
