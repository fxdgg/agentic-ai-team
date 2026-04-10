# 模板占位符完整说明

> 本文档详细说明 `_template.md` 中所有 `{{占位符}}` 的含义、格式要求和示例值。

---

## 基础标识占位符

### `{{DOMAIN_CN}}`
- **含义**: 领域中文名称
- **格式**: 不含"中心"二字以外的后缀
- **示例**: `用户中心`、`交易中心`、`物流中心`

### `{{DOMAIN_ID}}`
- **含义**: 领域英文短标识，用于 `@author` 标记和文件命名
- **格式**: 小写 kebab-case
- **示例**: `user-center`、`trade-center`、`logistics-center`
- **衍生用途**: `agent:{{DOMAIN_ID}}-developer` → `agent:user-center-developer`

### `{{SERVICE_NAME}}`
- **含义**: 微服务目录名（在 `microservice-group/` 下的子目录名）
- **格式**: 包含项目前缀
- **示例**: `vibe-user-center`、`vibe-trade-center`

---

## 角色定位占位符

### `{{EXPERTISE_LINE_1}}`
- **含义**: 专业背景第一行（紧跟在"10年以上 Java 后端开发经验，"之后）
- **格式**: 不含前导符号
- **示例**: `精通用户体系与认证授权系统设计`

### `{{EXPERTISE_EXTRA_LINES}}`
- **含义**: 专业背景的额外行（第 2~4 行）
- **格式**: 每行以 `- ` 开头
- **示例**:
```
- 深入理解 OAuth2、JWT、RBAC 等认证授权机制
- 精通用户画像、会员等级体系、用户行为分析等业务建模
- 熟悉 Spring Security、Sa-Token 等安全框架
```

### `{{CAPABILITY_1}}` / `{{CAPABILITY_2}}` / `{{CAPABILITY_3}}`
- **含义**: 核心能力第 1~3 条（第 4 条固定为"溯源标注能力"）
- **格式**: `**能力名称** — 能力描述`
- **示例**:
  - `**用户体系设计能力** — 构建完善的用户注册、登录、权限管理体系`
  - `**安全编码能力** — 防止 SQL 注入、XSS、越权等安全风险`
  - `**性能优化能力** — 高并发场景下的用户数据缓存与读写优化`

### `{{COLLABORATION_LINES}}`
- **含义**: 协作关系中的上下游依赖描述
- **格式**: 缩进 7 个空格，以 `↓` 开头
- **示例**（用户中心 — 被依赖方）:
```
       ↓ 提供: 用户基础服务（Feign 接口）
       ↓ 被调用方: trade-center / marketing-center / ...
```
- **示例**（交易中心 — 依赖方）:
```
       ↓ 依赖: vibe-user-center / vibe-product-center / vibe-marketing-center
       ↓ 被调用方: logistics-center
```

---

## 领域边界占位符

### `{{FORBIDDEN_DIRECTORIES}}`
- **含义**: 严禁操作的目录列表（排除自身的所有微服务）
- **格式**: Markdown 表格行，每行一个目录
- **示例**（用户中心）:
```
| `microservice-group/vibe-product-center/` | 商品中心代码 |
| `microservice-group/vibe-merchant-center/` | 商户中心代码 |
| `microservice-group/vibe-marketing-center/` | 营销中心代码 |
| `microservice-group/vibe-trade-center/` | 交易中心代码 |
| `microservice-group/vibe-logistics-center/` | 物流中心代码 |
```
- **规则**: 列出除自身以外的所有微服务目录

---

## 领域职责占位符

### `{{DOMAIN_RESPONSIBILITIES}}`
- **含义**: 领域核心业务能力表
- **格式**: Markdown 表格行
- **示例**（用户中心）:
```
| 用户注册 | 手机号注册、邮箱注册、第三方登录 |
| 用户登录 | 密码登录、验证码登录、Token 管理 |
| 用户信息管理 | 基本信息、收货地址、实名认证 |
| 会员体系 | 会员等级、积分管理、成长值 |
| 用户画像 | 用户标签、偏好分析 |
| 权限管理 | 角色权限、菜单权限（Web 端） |
```

---

## Changelog 示例占位符

### `{{CHANGELOG_EXAMPLE_CLASS_DESC}}`
- **含义**: Javadoc 中的类描述（一行）
- **示例**: `短信验证码登录服务实现`、`订单创建服务实现`

### `{{CHANGELOG_EXAMPLE_CLASS_DETAIL}}`
- **含义**: Javadoc 中的详细描述（`<p>` 标签内）
- **示例**: `负责处理运营端手机号+验证码的登录流程，包括验证码校验、用户身份验证、Token 签发等核心逻辑。`

---

## 扩展占位符（可选，领域特有部分）

### `{{EXTRA_IMPL_RULES}}`
- **含义**: 阶段二代码实现中的额外规则
- **格式**: 编号续接上文（如 `9.`）
- **默认值**: 空（大多数领域不需要）
- **示例**（交易中心）:
```
9. 涉及金额的字段和计算一律使用 BigDecimal
```

### `{{EXTRA_REPORT_ITEMS}}`
- **含义**: 输出报告中的额外条目
- **格式**: 以 `   - ` 开头（3 空格缩进）
- **默认值**: 空
- **示例**（交易中心）:
```
   - 分布式事务方案说明（如有）
```

### `{{EXTRA_MANDATORY_RULES}}`
- **含义**: 强制引用规则中的额外条目
- **格式**: Markdown 表格行
- **默认值**: 空
- **示例**（交易中心）:
```
| `../../rules/java-backend/transaction-convert-log.md` | 事务规范 | 涉及订单/支付事务时 |
```

### `{{EXTRA_QUALITY_CHECKS}}`
- **含义**: 完成检查清单中的额外检查项
- **格式**: 以 `- [ ] ` 开头
- **默认值**: 空
- **示例**（交易中心）:
```
- [ ] 金额计算使用 BigDecimal，禁止 double
- [ ] 分布式事务方案合理（如涉及）
```
- **示例**（营销中心）:
```
- [ ] 金额计算使用 BigDecimal，禁止 double
```

---

## 各领域实例的差异速查表

| 占位符 | user-center | product-center | merchant-center | marketing-center | trade-center | logistics-center |
|--------|-------------|----------------|-----------------|------------------|--------------|-----------------|
| `EXTRA_IMPL_RULES` | — | — | — | — | BigDecimal 金额 | — |
| `EXTRA_REPORT_ITEMS` | — | — | — | — | 分布式事务说明 | — |
| `EXTRA_MANDATORY_RULES` | — | — | — | — | 事务规范（全程） | — |
| `EXTRA_QUALITY_CHECKS` | — | — | — | BigDecimal | BigDecimal + 分布式事务 | — |
