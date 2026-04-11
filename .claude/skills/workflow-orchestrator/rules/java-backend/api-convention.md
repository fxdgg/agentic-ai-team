---
description: 接口规范与分页排序查询规范。当任务涉及 Controller 编写、接口设计、参数校验、分页查询、排序、列表接口时加载此规则。
alwaysApply: false
enabled: true
---

# 接口规范与分页排序查询规范

> 本规则覆盖：返回结构、异常处理、API 风格、参数校验、分页请求与返回、排序、查询条件设计。

## 1. 返回结构
- 必须使用 `Result<T>` 统一包装返回结果。
  - 成功：`Result.success(data)`
  - 失败：`Result.failed(ErrorCodeEnum)`

## 2. 异常处理
- **CRITICAL**: 禁止使用 `try-catch` 吞掉异常。
- 业务异常统一使用 `BusinessException` 抛出，并由全局异常处理器统一处理。
- **REQUIRED**: 非业务预期异常必须记录错误日志。

## 3. API 风格
- 遵循 RESTful 风格。
- 路径使用小写字母，多个单词使用中划线 `-`。

## 4. 参数校验
- Controller 层仅负责参数接收、基础校验与路由分发。
- **REQUIRED**: 请求对象使用 `jakarta.validation` 注解进行校验。
- **REQUIRED**: Controller 参数需配合 `@Valid` 或 `@Validated` 使用。
- **CRITICAL**: 凡是使用了 `jakarta.validation` 注解（如 `@NotBlank`、`@NotNull`、`@Pattern` 等）的模块，其 `pom.xml` 中必须显式声明 `spring-boot-starter-validation` 依赖。不得依赖上游模块的间接传递，因为 `vibe-common` 中该依赖被标记为 `<optional>true</optional>`，不会传递给下游模块。

---

## 5. 分页请求规范
- **REQUIRED**: 所有分页查询统一使用分页请求对象，例如 `PageQuery` 或业务查询对象继承统一分页基类。
- 分页基础字段建议包含：
  - `pageNum`: 页码，从 `1` 开始
  - `pageSize`: 每页条数
- **REQUIRED**: 默认值必须明确：`pageNum = 1`，`pageSize = 20`。
- **REQUIRED**: 必须限制最大页大小（最大 `100` 或按团队标准）。
- **CRITICAL**: 禁止允许前端传入超大 `pageSize` 导致数据库与内存压力失控。
- **REQUIRED**: 对非法分页参数进行兜底或校验失败处理。

## 6. 分页返回规范
- **REQUIRED**: 分页结果必须使用统一结构 `PageResult<T>`。
- 分页返回建议包含：`records`、`total`、`pageNum`、`pageSize`、`totalPages`。
- **REQUIRED**: Controller 返回结构使用 `Result<PageResult<T>>` 包装。
- **CRITICAL**: 禁止分页接口直接裸返回 `List<T>`。

## 7. 分页实现规范
- **REQUIRED**: 使用 MyBatis Plus 分页能力统一实现分页查询。
- **REQUIRED**: 分页逻辑放在 Service 或 Mapper 层，Controller 不负责拼接复杂分页逻辑。
- **CRITICAL**: 禁止通过先查全量再在内存中分页的方式处理正常业务列表。
- **REQUIRED**: 高并发、高数据量场景需评估深分页问题。
- **RECOMMENDED**: 对超大翻页场景采用游标、ID 翻页或其他替代方案。

## 8. 排序规范
- **REQUIRED**: 排序必须显式受控，禁止直接信任前端传入任意字段名。
- **CRITICAL**: 禁止将前端传入排序字段直接拼接到 SQL 中。
- **REQUIRED**: 排序字段必须走白名单机制。
- **REQUIRED**: 排序方向仅允许 `asc` / `desc`。
- **REQUIRED**: 若未指定排序规则，应提供默认排序（如 `created_time desc, id desc`）。
- **RECOMMENDED**: 分页场景下默认使用稳定排序，避免翻页结果抖动。

## 9. 查询对象设计规范
- **REQUIRED**: 列表查询应定义独立查询 DTO（如 `OrderQueryDTO`、`UserPageQueryDTO`）。
- **CRITICAL**: 禁止使用 Entity 直接作为查询入参。
- **REQUIRED**: 查询对象字段必须只保留真实可筛选条件。
- **REQUIRED**: 查询 DTO 应区分：精确查询字段、模糊查询字段、范围查询字段、排序字段、分页字段。

## 10. 条件查询规范
- **REQUIRED**: 精确查询优先使用等值条件。
- **REQUIRED**: 模糊查询必须明确适用字段，避免对大字段、高基数字段滥用模糊匹配。
- **CRITICAL**: 禁止在无索引、高数据量字段上无约束执行全表模糊查询。
- **REQUIRED**: 范围查询应使用清晰命名（`startTime`、`endTime`、`minAmount`、`maxAmount`）。

## 11. 时间区间查询规范
- **REQUIRED**: 时间区间统一使用成对字段（`startTime` / `endTime`）。
- **REQUIRED**: 必须明确是否包含边界值。
- **CRITICAL**: 禁止同一项目内边界规则不一致而无说明。
- **REQUIRED**: 时间查询需考虑时区与格式统一。

### 日期时间格式规范
- **CRITICAL**: 项目统一日期时间格式为 `yyyy-MM-dd HH:mm:ss`（LocalDateTime）、`yyyy-MM-dd`（LocalDate）、`HH:mm:ss`（LocalTime），禁止各接口自行定义不同格式。
- **CRITICAL**: DTO/Query 对象中的 `LocalDateTime`/`LocalDate`/`LocalTime` 类型字段，如果用于 **GET 请求的 query 参数绑定**（非 `@RequestBody`），**必须**添加 `@DateTimeFormat(pattern = "...")` 注解。
- **REQUIRED**: DTO 对象中的日期时间类型字段，如果用于 **POST 请求的 `@RequestBody` JSON 反序列化**，应通过全局 Jackson 配置或 `@JsonFormat(pattern = "...")` 注解统一格式。
- **RECOMMENDED**: 建议 `@DateTimeFormat` 和 `@JsonFormat` 同时添加，以兼容不同参数传递方式（防御性编码）。

### 枚举参数传递规范
- **REQUIRED**: GET 请求 DTO 中的枚举值字段，**建议使用基本类型**（`Integer`/`String`）接收，在 Service 层手动转换为枚举。
- **CRITICAL**: 若 DTO 中直接使用枚举类型作为 GET 请求参数，**必须**注册对应的 `Converter<String, XxxEnum>` 以支持按 code 值匹配，不得依赖 Spring 默认的 `name()` 匹配。

### 金额/精度数值规范
- **REQUIRED**: 金额字段统一使用 `BigDecimal` 类型，前端传递**纯数字字符串**（如 `99.99`），禁止千位分隔符。
- **REQUIRED**: 金额精度统一保留 2 位小数。

## 12. 查询条件构造规范
- **REQUIRED**: 使用 MyBatis Plus `LambdaQueryWrapper` / `LambdaUpdateWrapper` 构造查询条件。
- **REQUIRED**: 对可选条件使用显式判空处理。
- **CRITICAL**: 禁止出现大量 if-else 嵌套导致查询逻辑不可维护。
- **RECOMMENDED**: 按"固定条件 → 可选条件 → 排序 → 分页"顺序组织查询代码。

## 13. 导出与大数据量查询规范
- **CRITICAL**: 导出接口不得直接复用普通分页接口并简单将 `pageSize` 调大。
- **REQUIRED**: 导出应走独立接口、独立服务逻辑或异步导出方案。
- **RECOMMENDED**: 对超大导出采用分批查询、流式处理、异步任务。

## 14. 安全规范
- **CRITICAL**: 排序字段、模糊查询字段、筛选字段必须防止 SQL 注入。
- **CRITICAL**: 查询接口必须默认受租户隔离约束保护。
- **REQUIRED**: 涉及数据权限的列表查询，除租户隔离外还需叠加用户权限范围控制。
- **CRITICAL**: 禁止使用前端传入 `tenantId` 作为查询归属判断依据。

## 15. 默认分页与排序建议
- `pageNum = 1`、`pageSize = 20`、`maxPageSize = 100`
- 默认排序：`created_time desc, id desc`
