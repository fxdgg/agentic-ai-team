# 服务依赖设计模板

> **触发条件**: 当服务存在上下游依赖时加载此模板
> **加载位置**: 追加到数据模型之后
> **规则引用**: `rules/java-backend/feign-communication.md`

---

## 5. 服务依赖

### 5.1 上游依赖（我调用谁）

| 服务 | Feign 接口 | 调用场景 | 熔断策略 | 超时设置 |
|------|------------|----------|----------|----------|
| | | | | |

#### 上游接口详情

```java
// 示例: Feign Client 定义
@FeignClient(
    name = "{service-name}",
    path = "/internal/api/v1/{domain}",
    fallbackFactory = {Service}FeignFallbackFactory.class
)
public interface {Service}FeignClient {
    
    @GetMapping("/{id}")
    Result<{DTO}> getById(@PathVariable Long id);
}
```

### 5.2 下游依赖（谁调用我）

| 调用方服务 | 调用接口 | 调用场景 | SLA 要求 |
|------------|----------|----------|----------|
| | | | |

### 5.3 依赖关系图

```mermaid
graph LR
    subgraph 上游服务
        UP1[{上游服务1}]
        UP2[{上游服务2}]
    end
    
    subgraph 当前服务
        CURRENT[{当前服务}]
    end
    
    subgraph 下游服务
        DOWN1[{下游服务1}]
    end
    
    CURRENT -->|Feign| UP1
    CURRENT -->|Feign| UP2
    DOWN1 -->|Feign| CURRENT
```

### 5.4 上下文透传

```markdown
## 需要透传的上下文信息
- tenantId: 租户ID（必须）
- userId: 当前用户ID（必须）
- traceId: 链路追踪ID（自动）
- spanId: 跨度ID（自动）

## 透传实现
- 使用 Feign RequestInterceptor 自动注入 Header
- 下游服务使用 Filter 解析并存入 ThreadLocal
```

### 5.5 异步通信（消息队列）

| 消息主题 | 生产/消费 | 消息类型 | 说明 |
|----------|-----------|----------|------|
| | Producer/Consumer | | |

#### 消息定义示例

```java
// 示例: 领域事件消息
public class {Event}Message {
    private Long id;
    private Long tenantId;
    private LocalDateTime eventTime;
    // 业务字段
}
```

---

## 服务依赖检查清单

- [ ] 所有上游依赖已定义 Feign Client
- [ ] 熔断降级策略已配置
- [ ] 超时时间已合理设置
- [ ] 上下文透传已实现
- [ ] 下游接口 SLA 已确认
- [ ] 异步消息已定义（如有）
