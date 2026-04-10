---
description: Package 命名与组织规范、领域层级约定。当任务涉及新建类、新建包、项目结构、分层约定、目录组织时加载此规则。
alwaysApply: false
enabled: true
---

# Package 命名与组织规范 + 领域层级约定

> 本规则覆盖：根包规范、命名规则、推荐分层结构、分包职责约束、依赖方向约束、领域层级约定。

## 1. 根包规范
- **REQUIRED**: 所有 Java 类必须放在统一根包下。
- **RECOMMENDED**: 根包采用 `com.company.{business}.{service}` 格式。
- 示例：`com.demo.mall.order`、`com.demo.mall.user`、`com.demo.mall.inventory`。

## 2. Package 命名规则
- **REQUIRED**: package 名称统一使用小写字母。
- **CRITICAL**: 禁止使用中文、拼音缩写不清、无业务语义的命名。
- **CRITICAL**: 禁止使用无明确语义 package（`common1`、`temp`、`test2`、`utils`、`handler2`）。

## 3. 推荐分层 Package 结构
- `controller`: 对外 HTTP 接口层
- `service`: 业务接口层
- `service.{domain}.impl`: 业务实现层（impl 跟随业务域子包，而非集中在 service 下）
- `mapper`: 数据访问层
- `entity`: 数据库实体（直接位于根包下，不再包裹 `model/` 层级）
- `convert`: 手写对象转换器
- `client` / `remote`: Feign 客户端
- `config`: Spring 配置类
- `exception`: 异常类与全局异常处理
- `enums`: 枚举定义
- `constant`: 常量定义
- `util`: 通用工具类
- `support`: 领域支撑类、非核心基础能力
- `listener`: 消息监听器
- `job`: 定时任务
- `aspect`: AOP 切面
- `manager`（如团队允许）: 第三方能力封装、复杂流程编排

## 4. 分包职责约束
- **CRITICAL**: `controller` 包下禁止出现核心业务实现代码。
- **CRITICAL**: `mapper` 包下禁止出现业务编排逻辑。
- **CRITICAL**: `entity` 包下禁止放接口出参对象。
- **CRITICAL**: `dto` 包下禁止混放数据库实体。
- **CRITICAL**: `vo` 包下禁止承载数据库持久化语义。
- **REQUIRED**: `config` 包仅放配置类，不放业务逻辑。
- **REQUIRED**: `exception` 包统一放业务异常、错误码、全局异常处理器。
- **REQUIRED**: `client` / `remote` 包仅放远程调用接口及其专属模型。

## 5. 分包风格强制约束（CRITICAL）

### 5.1 本项目强制风格：扁平式分包 + 技术层内业务域子包

- **CRITICAL**: 本项目**强制采用扁平式分包**，即根包下**直接**按技术层分包（`controller`、`service`、`mapper`、`model`、`convert` 等）。
- **CRITICAL**: **严禁**在根包下直接创建业务域包（如 `根包/menu/`、`根包/tenant/`、`根包/order/`），这属于业务域式分包，在本项目中被禁止。
- **CRITICAL**: 业务域的划分**只允许在技术层包内部**进行，即在 `controller/`、`service/`、`mapper/`、`convert/`、`entity/` 等技术层包内部，按业务域创建子包。
- **CRITICAL**: 无论该业务域下当前文件数量是多少（即使只有 1 个），都**必须**按业务域分子包，保持规则一致性。
- **CRITICAL**: `service` 层的 `impl` 包必须**跟随业务域子包**，即 `service/{domain}/impl/`，**严禁**将 `impl` 集中在 `service/impl/` 下再分业务域。这样设计的目的是让接口与实现保持在同一业务域目录下，提高内聚性和可读性。

### 5.2 正确结构示例

```
com.vibe.mall.user/                    ← 根包
├── controller/                        ← 技术层（扁平式顶层）
│   ├── auth/                          ← 业务域子包
│   │   └── AuthController.java
│   └── menu/
│       └── SysMenuController.java
├── service/                           ← 技术层
│   ├── auth/                          ← 业务域子包
│   │   ├── AuthService.java           ← 接口
│   │   └── impl/                      ← impl 跟随业务域
│   │       └── AuthServiceImpl.java   ← 实现
│   ├── menu/
│   │   ├── SysMenuService.java
│   │   └── impl/
│   │       └── SysMenuServiceImpl.java
│   └── tenant/
│       ├── TenantService.java
│       └── impl/
│           └── TenantServiceImpl.java
├── mapper/                            ← 技术层
│   ├── auth/
│   │   └── AdminUserMapper.java
│   └── menu/
│       └── SysMenuMapper.java
├── convert/                           ← 技术层
│   ├── auth/
│   │   └── AdminUserConvert.java
│   ├── menu/
│   │   └── MenuConvert.java
│   └── tenant/
│       └── TenantConvert.java
├── entity/                            ← 技术层（直接在根包下，不包裹 model/）
│   ├── auth/
│   │   └── AdminUserEntity.java
│   └── menu/
│       └── SysMenuEntity.java
├── config/                            ← 全局配置（无需业务域子包）
├── exception/                         ← 全局异常（无需业务域子包）
├── enums/                             ← 可按业务域分子包
│   ├── auth/
│   └── menu/
└── constant/                          ← 可按业务域分子包
```

### 5.3 错误结构示例（严禁出现）

```
❌ com.vibe.mall.user/
   ├── menu/                           ← 禁止！业务域包出现在根包下
   │   ├── controller/
   │   ├── service/
   │   ├── mapper/
   │   └── convert/
   ├── tenant/                         ← 禁止！业务域包出现在根包下
   │   ├── service/
   │   └── convert/
   ├── service/                        ← 根级技术层
   └── mapper/
```

```
❌ com.vibe.mall.user/
   └── service/
       ├── auth/
       │   └── AuthService.java
       ├── menu/
       │   └── SysMenuService.java
       └── impl/                       ← 禁止！impl 集中在 service 下
           ├── auth/
           │   └── AuthServiceImpl.java
           └── menu/
               └── SysMenuServiceImpl.java
```

### 5.4 一致性校验规则

- **CRITICAL**: 同一项目内所有微服务必须遵循同一分包风格，禁止随意混搭。
- **CRITICAL**: 架构师 Agent 在输出文件级改动清单时，包路径必须严格遵循本规范，不得自创业务域式分包。
- **CRITICAL**: 开发 Agent 在实现代码前，必须校验技术需求文档中的包路径是否符合本规范，若发现违规路径，应先纠正路径后再实现。

## 6. 特殊对象 Package 约束
- 配置类 → `config`
- 全局异常处理 → `exception` 或 `web`
- 枚举 → `enums`
- 常量 → `constant`
- Feign 相关 → `client`、`client.dto`、`client.vo`（或 `remote`）
- 多租户上下文 → `tenant`、`context` 或 `support.tenant`

## 7. 工具类约束
- **REQUIRED**: `util` 包仅放无状态、可复用、与具体业务弱相关的工具类。
- **CRITICAL**: 禁止将核心业务逻辑塞入 `util` 包。
- **CRITICAL**: 禁止出现"大而全"的 `CommonUtil`、`BaseUtil`、`MiscUtil`。
- **REQUIRED**: 工具类命名需体现单一职责（`DateTimeUtil`、`JsonUtil`、`MaskUtil`）。

## 8. 包依赖方向约束
- **REQUIRED**: 依赖方向：`controller` → `service` → `mapper` / `client`，`convert` 为辅助层。
- **CRITICAL**: 禁止 `mapper` 反向依赖 `controller`。
- **CRITICAL**: 禁止 `entity` 依赖 `controller`、`service`。
- **CRITICAL**: 禁止 `client` 依赖本地 `controller`。
- **REQUIRED**: 包之间不得形成循环依赖。

## 9. 命名一致性要求
- **REQUIRED**: package 名应与服务名、模块名、业务域保持一致。
- **CRITICAL**: 禁止服务名是订单服务，但主包名仍沿用历史无关命名。

### 类名后缀命名规范

- **CRITICAL**: 所有 Java 类的类名后缀必须严格遵守 `naming-convention.md` 中定义的后缀规则。
- **CRITICAL**: 新建任何类之前，必须先确认其类型对应的强制后缀，不得随意自创后缀。

## 10. 领域层级约定

| 层级 | 职责 |
|---|---|
| `controller` | 仅处理参数校验、协议转换、路由分发 |
| `service` | 业务逻辑接口定义 |
| `service.{domain}.impl` | 核心业务逻辑实现，impl 跟随业务域子包，注意事务边界 |
| `entity` | 数据库实体对象（直接位于根包下，不包裹 `model/` 层级） |
| `convert` | 手写对象转换（Convert 类） |
| `mapper` | 数据访问层 |
| `client` / `remote` | Feign 客户端定义及专属 DTO/VO |

### 分层职责
- **CRITICAL**: Controller 不写业务逻辑。
- **CRITICAL**: Mapper 不承载业务逻辑。
- **CRITICAL**: Entity 不直接作为接口出参与入参。
- **REQUIRED**: DTO、Entity、VO 之间的转换统一由 `convert` 包中的手写 Convert 类完成（本项目不使用 MapStruct）。

## 11. Common 模块分包约定

> 本节约束所有微服务的 `xxx-common` 共享模块（如 `vibe-user-center-common`）的包结构。

### 11.1 Common 模块的角色定位

Common 模块用于存放**需要被多个子模块共享**的对象，包括但不限于：
- **DTO**：Controller 入参对象
- **VO**：Controller 出参对象
- **枚举（enums）**：跨模块使用的业务枚举
- **常量（constant）**：跨模块使用的常量

### 11.2 Common 模块不使用 `model` 包前缀

- **CRITICAL**: Common 模块中的 DTO 和 VO **直接**放在根包下的 `dto/` 和 `vo/` 中，**不再**包裹 `model/` 层级。
- 原因：Common 模块的根包（如 `com.vibe.mall.user.common`）已有清晰的语义边界，`model` 层级在此处是冗余的。

**正确路径**：
```
com.vibe.mall.user.common/
├── dto/
│   ├── auth/
│   │   ├── PhoneLoginRequest.java
│   │   └── SendSmsCodeRequest.java
│   └── menu/
│       ├── CreateMenuRequest.java
│       ├── CreateTemplateRequest.java
│       └── ...
├── vo/
│   ├── auth/
│   │   ├── LoginUserInfo.java
│   │   └── PhoneLoginResponse.java
│   └── menu/
│       ├── MenuTreeVO.java
│       ├── TemplateDetailVO.java
│       └── ...
├── enums/
│   ├── auth/
│   │   └── AdminUserStatus.java
│   ├── menu/
│   │   └── MenuStatus.java
│   └── tenant/
│       └── TenantStatus.java
└── constant/
    ├── auth/
    └── menu/
```

**禁止路径**：
```
❌ com.vibe.mall.user.common/model/dto/  ← 禁止！不需要 model 层级
❌ com.vibe.mall.user.common/model/vo/   ← 禁止！
```

### 11.3 业务域子包一致性约束（CRITICAL）

- **CRITICAL**: Common 模块中 DTO/VO/枚举的**业务域子包名称**，必须与 service 模块中 `entity/`、`mapper/`、`service/`、`convert/` 的业务域子包**保持完全一致**。
- **CRITICAL**: 禁止在 common 模块中创建与 service 模块不同的业务域子包（如 service 模块用 `menu` 域，common 模块却用 `template` 域）。
- **CRITICAL**: 当子概念（如"菜单模板"）属于某个主域（如"菜单"）时，其 DTO/VO 必须归入主域的子包中，不得独立成域。

### 11.4 所有 DTO/VO/枚举必须按业务域分子包

- **CRITICAL**: 无论该业务域下 DTO/VO 数量多少（即使只有 1 个），都**必须**按业务域分子包。
- **CRITICAL**: **严禁**将 DTO/VO 直接放在 `dto/` 或 `vo/` 根目录下（如 `dto/PhoneLoginRequest.java`），必须放入对应的业务域子包中（如 `dto/auth/PhoneLoginRequest.java`）。
