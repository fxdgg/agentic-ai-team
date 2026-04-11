---
description: Java 类名命名后缀规范。当任务涉及新建类、类命名、类重命名、VO/DTO/Entity/Request/Query/Convert/Controller/Service/Mapper 命名时加载此规则。
alwaysApply: false
enabled: true
---

# Java 类名命名后缀规范

> 本规则约束所有 Java 类的**类名后缀**命名规则，是全项目强制标准。

## 1. 总原则

- **CRITICAL**: 每个 Java 类的类名**必须**通过后缀清晰表达其职责类型。
- **CRITICAL**: 同一类型的后缀在全项目范围内必须统一，禁止混用。
- **REQUIRED**: 类名采用大驼峰命名法（UpperCamelCase），后缀为该类型的英文关键词。

## 2. 后缀对照表（强制）

| 类型 | 强制后缀 | 所属包 | 示例 |
|------|----------|--------|------|
| 数据库实体 | `Entity` | `entity/{domain}/` | `MemberEntity.java`、`SpuEntity.java`、`SysMenuEntity.java` |
| 接口出参（视图对象） | `VO` | `vo/{domain}/`（Common 模块） | `MemberVO.java`、`SpuVO.java`、`MenuTreeVO.java` |
| 明细出参 | `DetailVO` | `vo/{domain}/`（Common 模块） | `MemberDetailVO.java`、`TemplateDetailVO.java` |
| 接口入参（写操作） | `Request` | `dto/{domain}/`（Common 模块） | `CreateMenuRequest.java`、`UpdateTenantRequest.java` |
| 接口入参（普通查询） | `Query` | `dto/{domain}/`（Common 模块） | `MemberListQuery.java` |
| 接口入参（分页查询） | `PageQuery` | `dto/{domain}/`（Common 模块） | `SpuPageQuery.java` |
| 接口出参（非 VO 场景） | `Response` | `vo/{domain}/`（Common 模块） | `PhoneLoginResponse.java` |
| MapStruct 转换器 | `Convert` | `convert/{domain}/`（Service 模块） | `MemberConvert.java`、`SpuConvert.java` |
| 控制器 | `Controller` | `controller/{domain}/`（Admin/App 模块） | `MemberController.java`、`SpuController.java` |
| 业务接口 | `Service` | `service/{domain}/` | `MemberService.java`、`SpuService.java` |
| 业务实现 | `ServiceImpl` | `service/{domain}/impl/` | `MemberServiceImpl.java`、`SpuServiceImpl.java` |
| 数据访问层 | `Mapper` | `mapper/{domain}/` | `MemberMapper.java`、`SpuMapper.java` |
| 枚举 | **不带** `Enum` 后缀，使用业务语义命名 | `enums/{domain}/` | `MemberStatus.java`、`SpuStatus.java` |
| 常量类 | `Constants` | `constant/` 或 `constants/` | `MemberConstants.java` |
| 配置类 | `Config` 或 `Properties` | `config/` | `AsyncConfig.java`、`SmsCodeProperties.java` |
| 异常类 | `Exception` | `exception/` | `BusinessException.java` |
| 工具类 | `Util` 或 `Utils` | `util/` | `PhoneDesensitizeUtil.java`、`BeanCopyUtils.java` |
| Feign 客户端 | `Client` 或 `FeignClient` | `client/` | `OrderClient.java` |
| 事件监听器 | `Listener` | `listener/` | `MemberImportListener.java` |
| 定时任务 | `Job` 或 `Task` | `job/` | `ExportCleanupJob.java` |
| AOP 切面 | `Aspect` | `aspect/` | `LogAspect.java` |
| Excel 数据模型 | `Data`（EasyExcel 场景） | `excel/` | `MemberImportData.java`、`MemberExportData.java` |

## 3. 入参命名模式规则（CRITICAL）

### 3.1 写操作入参 → `Request` 后缀

- **CRITICAL**: 所有创建、更新、删除等写操作的入参对象，类名必须以 `Request` 结尾。
- 命名模板：`{动作}{业务名}Request`
- 示例：`CreateMenuRequest`、`UpdateTenantRequest`、`AuditTenantRequest`、`BatchCustomMenuRequest`

### 3.2 查询入参 → `Query` / `PageQuery` 后缀

- **CRITICAL**: 普通列表查询的入参对象，类名必须以 `Query` 结尾。
- **CRITICAL**: 分页查询的入参对象（继承 `PageQuery` 基类），类名必须以 `PageQuery` 结尾。
- **CRITICAL**: 禁止使用 `QueryDTO` 或 `PageQueryDTO` 后缀。
- 命名模板：`{业务名}ListQuery`（普通查询）、`{业务名}PageQuery`（分页查询）
- 示例：`MemberListQuery`、`SpuPageQuery`

### 3.3 禁止使用 `DTO` 后缀

- **CRITICAL**: 本项目**不使用** `DTO` 作为类名后缀。入参统一使用 `Request` 或 `Query`/`PageQuery`，出参使用 `VO` 或 `Response`。
- **CRITICAL**: 禁止出现 `XxxDTO.java`、`XxxQueryDTO.java`、`XxxPageQueryDTO.java` 等命名。

## 4. 出参命名模式规则（CRITICAL）

### 4.1 标准出参 → `VO` 后缀

- **CRITICAL**: 绝大多数接口出参对象，类名必须以 `VO` 结尾。
- 命名模板：`{业务名}VO`
- 示例：`MemberVO`、`SpuVO`、`TenantVO`

### 4.2 明细出参 → `DetailVO` 后缀

- **REQUIRED**: 当存在列表 VO 和详情 VO 的区分时，详情对象使用 `DetailVO` 后缀。
- 示例：`MemberDetailVO`（详情）vs `MemberVO`（列表）

### 4.3 特殊出参 → `Response` 后缀

- **REQUIRED**: 当出参对象语义上不属于"视图展示"，而是特定接口的直接响应结构时，使用 `Response` 后缀。
- 示例：`PhoneLoginResponse`

### 4.4 操作结果 → `ResultVO` 后缀

- **REQUIRED**: 批量操作、导入导出等操作结果，使用 `ResultVO` 后缀。
- 示例：`SpuImportResultVO`、`ExportResultVO`、`SpuBatchUpdateResultVO`

## 5. Entity 命名规则（CRITICAL）

- **CRITICAL**: Entity 类名**必须加** `Entity` 后缀，便于人和 AI 阅读时一眼识别出这是数据库表的映射类。
- **CRITICAL**: 命名模板：`{业务名}Entity`。
- **CRITICAL**: 基类 `BaseEntity` 同样遵循此规则。
- 正确示例：`MemberEntity`、`SpuEntity`、`SkuEntity`、`SysMenuEntity`、`CategoryEntity`
- 错误示例：~~`Member`~~、~~`Spu`~~（缺少 Entity 后缀，无法直接判断类型）

## 6. Convert 命名规则

- **CRITICAL**: 转换器类名使用 `Convert` 后缀，**不使用** `Converter`。
- **REQUIRED**: 转换器以其主要转换的业务实体命名。
- 正确示例：`MemberConvert`、`SpuConvert`、`MenuConvert`
- 错误示例：~~`MemberConverter`~~、~~`MemberDTOConverter`~~

## 7. 禁止后缀清单

| 禁止后缀 | 应替换为 | 说明 |
|----------|----------|------|
| `*DTO.java` | `*Request.java` / `*Query.java` | 本项目不使用 DTO 后缀 |
| `*QueryDTO.java` | `*Query.java` / `*PageQuery.java` | 查询对象不带 DTO |
| `*Converter.java` | `*Convert.java` | 统一使用 Convert |
| `*Enum.java` | 去掉 Enum 后缀 | 枚举通过包路径标识 |
| `*Bo.java` / `*BO.java` | 不使用 | 本项目不引入 BO 层 |
| `*Model.java` | 视场景选择 VO/Request/Entity | 禁止笼统使用 Model |
| `*Bean.java` | 视场景选择具体后缀 | 禁止笼统使用 Bean |
| `*Pojo.java` / `*POJO.java` | 视场景选择具体后缀 | 禁止笼统使用 POJO |

## 8. 复合场景命名指引

| 场景 | 命名模板 | 示例 |
|------|----------|------|
| 创建接口入参 | `Create{业务}Request` | `CreateMenuRequest` |
| 更新接口入参 | `Update{业务}Request` | `UpdateTenantRequest` |
| 审核/状态变更入参 | `{动作}{业务}Request` | `AuditTenantRequest`、`UpdateMenuStatusRequest` |
| 批量操作入参 | `Batch{动作}{业务}Request` 或 `{业务}Batch{动作}Request` | `BatchCustomMenuRequest`、`SpuBatchUpdateRequest` |
| 导入/导出入参 | `{业务}{Import/Export}Request` | `MemberExportRequest` |
| 分页查询入参 | `{业务}PageQuery` | `SpuPageQuery` |
| 列表查询入参 | `{业务}ListQuery` | `MemberListQuery` |
| 列表出参 | `{业务}VO` | `MemberVO`、`SpuVO` |
| 详情出参 | `{业务}DetailVO` | `MemberDetailVO`、`TemplateDetailVO` |
| 树形出参 | `{业务}TreeVO` | `MenuTreeVO` |
| 下拉选项出参 | `{业务}OptionVO` | `CategoryOptionVO`、`GroupOptionVO` |
| 操作结果出参 | `{业务}{操作}ResultVO` | `SpuImportResultVO`、`ExportResultVO` |
| 任务状态出参 | `{业务}TaskVO` | `ExportTaskVO` |
| Tab 统计出参 | `{业务}TabCountVO` | `SpuTabCountVO` |

## 9. Feign 远程调用对象命名

- **REQUIRED**: Feign 接口专属入参使用 `Remote{业务}Request` 或直接复用已有 Request。
- **REQUIRED**: Feign 接口专属出参使用 `Remote{业务}VO` 或直接复用已有 VO。
- **CRITICAL**: 禁止在 Feign 接口中暴露 Entity。
