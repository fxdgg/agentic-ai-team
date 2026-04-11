---
description: 配置文件与配置中心分层规范。当任务涉及 yml 配置、Nacos 配置中心、bootstrap、application、环境配置、敏感配置、动态刷新时加载此规则。
alwaysApply: false
enabled: true
---

# 配置文件与配置中心分层规范

> 本规则覆盖：本地配置分层、Nacos 配置分层、配置优先级、命名规范、敏感配置、动态刷新。

## 1. 总体原则
- **REQUIRED**: 配置实行"本地最小化 + Nacos 集中化"原则。
- **REQUIRED**: 不同层级配置必须职责清晰，禁止将所有配置混杂在单一文件或单一 DataId 中。
- **CRITICAL**: 敏感配置、环境差异配置、可动态调整配置，不得散落在代码中硬编码。

## 2. 本地配置文件分层

### bootstrap.yml / bootstrap.yaml
- **REQUIRED**: 仅用于配置应用启动早期必须加载的内容。
- 包括：`spring.application.name`、`spring.profiles.active`、`spring.cloud.nacos.server-addr`、`spring.cloud.nacos.username/password`、配置中心命名空间、分组、扩展配置声明。

### application.yml / application.yaml
- **REQUIRED**: 存放当前服务本地默认配置。
- 包括：通用 Spring Boot 配置、本地日志基础配置、Jackson / MVC / 线程池等默认参数。

### application-{profile}.yml
- **REQUIRED**: 存放环境差异化配置（`dev`、`test`、`prod`）。
- **CRITICAL**: 禁止将生产配置写入 `dev` 文件，或将测试配置写入 `prod` 文件。
- **REQUIRED**: 环境文件中仅保留该环境差异项，不重复定义公共配置。

## 3. Nacos 配置分层

### 3.1 共享配置
- 用于多个服务复用的公共配置（数据库连接池、Redis、Feign 超时等）。
- **REQUIRED**: 共享配置应抽取为独立 DataId，不得复制粘贴到每个服务。
- **RECOMMENDED**: 命名示例：`common-datasource.yaml`、`common-redis.yaml`、`common-feign.yaml`。

### 3.2 服务级配置
- 每个服务独有的业务配置。
- **REQUIRED**: 每个服务必须有独立服务配置，只保存该服务专属参数。
- 示例：`order-service.yaml`、`user-service.yaml`。

### 3.3 环境级配置
- **REQUIRED**: 不同环境必须使用不同 Namespace 或 Group 做隔离。
- **CRITICAL**: 禁止开发环境误读生产环境配置。

### 3.4 租户级配置
- Key 命名规范：`{tenantId}.{configName}`
- 示例：`tenant_1001.sms-sign`、`tenant_1001.invoice-rule`
- **CRITICAL**: 租户配置必须与共享配置、服务配置严格隔离。
- **CRITICAL**: 禁止将租户专属配置写入公共配置 DataId。

## 4. 配置优先级
- **REQUIRED**: 配置覆盖顺序（从高到低）：
  1. 租户级配置
  2. 服务级 Nacos 配置
  3. 共享 Nacos 配置
  4. 本地 `application-{profile}.yml`
  5. 本地 `application.yml`
- **CRITICAL**: 禁止出现"同名配置散落多处但无人知晓最终生效来源"的情况。

## 5. 配置命名规范
- **REQUIRED**: 配置项命名统一使用小写中划线或小写点分风格。
- **REQUIRED**: DataId 命名需体现作用域与归属。
- 推荐示例：`common-feign.yaml`、`order-service.yaml`、`order-service-dev.yaml`。

## 6. 本地配置与 Nacos 配置边界

**优先放本地启动配置**：应用名、Profile、Nacos 地址、Nacos 命名空间、配置拉取入口参数。

**优先放 Nacos**：数据源业务参数、Redis 参数、Feign 超时参数、业务开关、限流/熔断/降级参数、可动态调整的业务配置。

- **CRITICAL**: 禁止把频繁变更的业务参数硬编码到本地 `application.yml` 中。
- **CRITICAL**: 禁止把启动必需且依赖配置中心本身的参数下沉到普通业务配置中。

## 7. 敏感配置规范
- **CRITICAL**: 密码、密钥、Token、证书等敏感信息必须受控存储。
- **REQUIRED**: 敏感配置应结合 Nacos 加密能力或外部密钥管理方案。
- **CRITICAL**: 禁止将敏感配置明文提交到 Git 仓库。
- **CRITICAL**: 禁止在日志中打印敏感配置值。

## 8. 动态刷新规范
- **REQUIRED**: 仅对明确支持动态变更且线程安全的配置启用动态刷新。
- **CRITICAL**: 禁止对数据库连接核心参数、基础启动参数等高风险配置随意开启运行时刷新。
- **REQUIRED**: 动态刷新配置必须评估变更影响范围，并有回滚方案。

## 9. Spring Boot 自动配置类规范

### 9.1 加载顺序声明
- **CRITICAL**: 当自动配置类中使用 `@ConditionalOnBean` 或 `@ConditionalOnClass` 条件注册 Bean 时，
  **必须**同时声明 `@AutoConfigureAfter` 指定依赖的自动配置类，确保条件判断时目标 Bean 已被创建。
- 示例：
  ```java
  @Configuration
  @AutoConfigureAfter(RedisAutoConfiguration.class)  // CRITICAL: 确保 StringRedisTemplate 先创建
  public class CommonAutoConfiguration {
      @Bean
      @ConditionalOnBean(StringRedisTemplate.class)
      public DistributedLockUtil distributedLockUtil(StringRedisTemplate redisTemplate) {
          return new DistributedLockUtil(redisTemplate);
      }
  }
  ```
- **CRITICAL**: 禁止使用 `@ConditionalOnBean` 而不声明 `@AutoConfigureAfter`，因为自动配置的加载顺序不确定，
  条件评估时目标 Bean 可能尚未创建。

### 9.2 条件注册与硬依赖的匹配性
- **CRITICAL**: 当一个 Bean 通过 `@ConditionalOnBean` 条件注册时，下游所有依赖该 Bean 的注入点
  必须使用 `@Autowired(required = false)` 或 `Optional<T>` 做容错处理，
  或者确保条件 100% 能满足（通过 `@AutoConfigureAfter` + 明确的依赖声明）。
- **REQUIRED**: 若下游使用构造器注入（硬依赖），则上游 Bean 的条件注册必须有 `@AutoConfigureAfter` 保证。

## 10. 条件 Bean 使用规范（optional 依赖防护）

### 10.1 注入前置检查（CRITICAL）
当代码中通过构造器注入或 `@Autowired` 依赖来自 `vibe-common` 的 Bean 时，**必须**执行以下检查：

1. 打开 `vibe-common` 的 `CommonAutoConfiguration.java`，确认该 Bean 的注册是否有条件注解
2. 若存在 `@ConditionalOnClass(name = "xxx")`：
   - 确认 `xxx` 对应的 Maven artifact
   - 检查该 artifact 在 `vibe-common/pom.xml` 中是否为 `<optional>true</optional>`
   - 若为 optional → **必须**在当前模块的 `pom.xml` 中显式声明该依赖
3. 若存在 `@ConditionalOnBean(Xxx.class)`：
   - 递归检查 `Xxx` Bean 本身的注册条件
   - 确保整个条件链上所有 optional 依赖均已在当前模块中显式声明
4. 若存在 `@ConditionalOnProperty`：
   - 确认对应的配置项在当前微服务的配置文件中已正确设置

### 10.2 vibe-common 条件注册 Bean 清单（维护要求）
当 `vibe-common` 中新增或修改条件注册 Bean 时，common-developer **必须**在 `CommonAutoConfiguration`
类级别 Javadoc 中维护一份条件 Bean 清单，格式如下：

```java
/**
 * 公共自动配置
 *
 * <h3>条件注册 Bean 清单</h3>
 * <table>
 *   <tr><th>Bean</th><th>条件</th><th>需显式引入的依赖</th></tr>
 *   <tr><td>JwtUtil</td><td>@ConditionalOnClass("com.auth0.jwt.JWT")</td><td>com.auth0:java-jwt</td></tr>
 *   <tr><td>AuthInterceptor</td><td>@ConditionalOnBean(JwtUtil.class)</td><td>com.auth0:java-jwt（间接）</td></tr>
 *   <tr><td>DistributedLockUtil</td><td>@ConditionalOnBean(StringRedisTemplate.class)</td><td>spring-boot-starter-data-redis</td></tr>
 * </table>
 */
```

这样下游开发 Agent 在注入这些 Bean 时可以快速查阅所需的前置依赖。
