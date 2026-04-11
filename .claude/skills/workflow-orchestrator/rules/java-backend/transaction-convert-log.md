---
description: 事务规范、转换对象规范、日志规范。当任务涉及事务管理、@Transactional、对象转换、Convert、BeanCopyUtils、日志记录、SLF4J 时加载此规则。
alwaysApply: false
enabled: true
---

# 事务规范、转换对象规范、日志规范

> 本规则覆盖：事务边界与管理、手写 Convert 对象转换、SLF4J 日志规范。

---

## 1. 事务规范

- **REQUIRED**: 涉及多表写操作、状态流转、库存/金额/配额变更时，必须明确事务边界。
- `@Transactional` 应放在 Service 实现层。
- **CRITICAL**: 禁止在 Controller 层开启事务。
- **REQUIRED**: 只读查询场景避免滥用事务。
- **CRITICAL**: 事务方法内禁止执行无控制的长耗时远程调用。
- **REQUIRED**: 若事务中必须调用 Feign，应评估超时、回滚、一致性与补偿机制。

---

## 2. 转换对象规范

- **CRITICAL**: 本项目**不使用 MapStruct**，所有 DTO、Entity、VO 转换统一采用**手写 Convert 类**。
- **CRITICAL**: Controller 不得返回 Entity。
- **CRITICAL**: Feign Client 不得直接返回数据库 Entity。
- **REQUIRED**: 对敏感字段进行脱敏或剔除后再返回给前端。

### Convert 类编写规范（CRITICAL）

- **REQUIRED**: Convert 类为 `final class`，提供 `public static final XXXConvert INSTANCE = new XXXConvert()` 单例字段，调用方式统一为 `XXXConvert.INSTANCE.toVO(entity)`。
- **REQUIRED**: 每个转换方法必须处理 `null` 入参（返回 `null` 或空集合），禁止抛出 NPE。
- **REQUIRED**: 集合转换方法基于单对象转换方法 + `Stream.map()` 实现，空集合返回 `Collections.emptyList()`。
- **REQUIRED**: Convert 类放在 `convert/{domain}/` 包下，一个业务域一个 Convert 类。

  ```java
  // ✅ 正确示例
  public final class MemberConvert {
      public static final MemberConvert INSTANCE = new MemberConvert();
      private MemberConvert() {}

      public MemberVO toVO(Member member) {
          if (member == null) { return null; }
          MemberVO vo = new MemberVO();
          vo.setId(member.getId());
          vo.setNickname(member.getNickname());
          // ... 逐字段赋值
          return vo;
      }

      public List<MemberVO> toVOList(List<Member> members) {
          if (members == null || members.isEmpty()) { return Collections.emptyList(); }
          return members.stream().map(this::toVO).collect(Collectors.toList());
      }
  }
  ```

### BeanCopyUtils 兜底（RECOMMENDED）

- 对于字段名完全一致的简单拷贝场景，可使用 `com.vibe.mall.common.util.BeanCopyUtils`（基于 Spring BeanUtils 封装）：
  - `BeanCopyUtils.copy(source, TargetClass.class)` — 单对象拷贝
  - `BeanCopyUtils.copyList(sourceList, TargetClass.class)` — 列表拷贝
- **CRITICAL**: 存在字段名不同、类型转换、脱敏等特殊逻辑时，**禁止**使用 BeanCopyUtils，必须手写 Convert。

---

## 3. 日志规范

- 使用 SLF4J，禁止使用 `System.out.println`。
- 重要业务逻辑必须记录 `log.info`。
- 异常场景必须记录 `log.error`，并附带异常堆栈。
- **REQUIRED**: 日志中应尽可能包含以下关键信息：
  - `tenantId`
  - `traceId`
  - 服务名
  - 下游服务名
  - 业务主键（如 `orderId`、`userId`）
- **CRITICAL**: 禁止打印密码、密钥、完整身份证号、完整手机号等敏感信息。
