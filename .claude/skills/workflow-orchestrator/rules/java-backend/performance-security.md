---
description: 性能与安全规范。当任务涉及 Redis 缓存设计、TTL、安全审计、SQL 注入防护、越权防护、审计日志时加载此规则。
alwaysApply: false
enabled: true
---

# 性能与安全规范

> 本规则覆盖：缓存规范、安全规范。

## 1. 缓存规范
- 默认使用 Redis。
- Key 必须带租户前缀：`app:tenant:{id}:cache:{key}`
- **REQUIRED**: 必须设置合理 TTL，避免永久缓存脏数据。
- **REQUIRED**: 更新数据库后需考虑缓存一致性。

### 1.1 Redis 状态机操作时序（当 Redis 用于维护状态机时强制遵守）

- **CRITICAL**: 当使用 Redis 存储状态（如任务状态 RUNNING/CANCELLED/COMPLETED），
  且在同一代码路径中需要**读取状态**和**删除 key** 两个操作时，
  **必须先读取状态，再删除 key**（先读后删）。
- **禁止**: 将状态读取放在资源清理（finally 块、@PreDestroy）之后，
  因为清理操作可能删除 key 导致后续读取返回 null。
- **推荐模式**:
  ```java
  // ✅ 正确: 先读后删
  boolean cancelled = stateTracker.isTaskCancelled(id);  // 读取状态
  stateTracker.completeTask(id);                          // 删除 key
  if (cancelled) { /* 处理取消逻辑 */ }

  // ❌ 错误: finally 中先删后读
  try { ... } finally { stateTracker.completeTask(id); }  // 先删
  boolean cancelled = stateTracker.isTaskCancelled(id);    // 读取 → 永远 null
  ```
- **异常路径**: catch 块中可以立即清理（因为异常路径不需要读取状态），
  但正常路径必须保证"先读后删"。

## 2. 安全规范
- **CRITICAL**: 禁止拼接 SQL。
- **CRITICAL**: 禁止信任前端传入的租户 ID 进行数据权限控制。
- **CRITICAL**: 所有涉及数据访问的逻辑必须考虑越权与租户穿透风险。
- **REQUIRED**: 敏感操作应记录审计日志。
- **CRITICAL**: 微服务调用链中必须防止上下文丢失导致的租户数据串读。
