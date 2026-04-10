---
description: 微服务通信规范（Nacos + Feign）。当任务涉及 Feign 客户端、服务间调用、远程调用、服务注册发现、上下文透传、熔断降级时加载此规则。
alwaysApply: false
enabled: true
---

# 微服务通信规范（Nacos + Feign）

> 本规则覆盖：服务注册与发现、Feign 客户端使用、租户上下文透传、容错与超时、调用边界、接口设计。

## 1. 服务注册与发现
- **REQUIRED**: 所有微服务必须注册到 Nacos。
- **REQUIRED**: 服务间调用必须优先通过服务名发现，不允许硬编码 IP、端口。
- **CRITICAL**: 禁止在业务代码中写死下游服务地址。
- 服务命名统一使用小写中划线风格：`user-service`、`order-service`、`inventory-service`。

## 2. Feign 客户端使用规范
- **REQUIRED**: 服务间 HTTP 调用统一使用 Feign 客户端。
- **REQUIRED**: Feign 接口统一放置在 `client` 或 `remote` 包下。
- **REQUIRED**: 使用 `@FeignClient(name = "xxx-service")` 基于服务名调用。
- **REQUIRED**: Feign 方法签名应与下游接口语义一致，避免参数含义模糊。
- **CRITICAL**: 禁止在 Feign 接口中直接暴露 Entity 作为入参或返回值。
- **REQUIRED**: Feign 的入参与返回对象应定义为独立的 `DTO/VO` 或 `RemoteDTO/RemoteVO`。
- **REQUIRED**: Feign 调用返回结果若为统一结构，需显式处理成功失败分支，不可默认成功。
- **RECOMMENDED**: 为每个下游服务拆分独立 Feign Client，避免单个 Client 过于臃肿。

## 3. 租户上下文透传
- **CRITICAL**: 微服务间调用必须透传租户上下文。
- **REQUIRED**: 通过 Feign `RequestInterceptor` 自动透传 `tenantId`、`traceId`、用户身份等上下文信息。
- **CRITICAL**: 禁止依赖前端重复传递租户 ID 来实现跨服务租户隔离。
- **REQUIRED**: 下游服务接收到请求后，必须将透传的租户信息写入上下文，再进入业务逻辑。

## 4. Feign 容错与超时
- **REQUIRED**: 必须配置合理的连接超时、读取超时。
- **REQUIRED**: 对下游调用失败场景，必须有明确处理策略：失败返回、降级、重试或抛出业务异常。
- **CRITICAL**: 禁止无限重试，避免级联故障。
- **RECOMMENDED**: 对核心链路配置熔断、隔离、限流能力。
- **REQUIRED**: Feign 异常需统一封装，避免将底层 HTTP 异常直接暴露到 Controller。

## 5. Feign 调用边界
- **CRITICAL**: Feign 调用只用于服务间通信，不得替代内部 Service 调用。
- **CRITICAL**: 同一服务内部模块之间禁止使用 Feign 自调用。
- **REQUIRED**: 能通过本地 Service 完成的逻辑，不得绕路调用远程服务。
- **REQUIRED**: 跨服务调用前应明确调用必要性，避免产生"聊天式"远程调用。

## 6. 接口设计要求
- **REQUIRED**: 下游服务对外暴露的接口必须稳定，避免频繁破坏性变更。
- **REQUIRED**: 若接口存在版本升级，优先采用兼容式演进。
- **RECOMMENDED**: 远程接口按业务域划分（用户域、订单域、库存域）。
- **CRITICAL**: 不允许将仅供前端使用的 Controller 接口直接作为内部 Feign 接口复用，内部接口应有清晰边界。
