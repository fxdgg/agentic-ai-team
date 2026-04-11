# 数据模型设计模板

> **触发条件**: 当服务需要定义数据表、索引时加载此模板
> **加载位置**: 追加到 API 设计之后
> **规则引用**: `rules/java-backend/database-design.md`

---

## 4. 数据模型

### 4.1 表清单

| 表名 | 中文名 | 描述 | 预估数据量 |
|------|--------|------|------------|
| | | | |

### 4.2 BaseEntity 审计字段 DDL 类型映射（CRITICAL — 所有业务表必须遵循）

| Java 字段 (BaseEntity) | Java 类型 | DDL 列名 | DDL 类型 | 默认值 |
|------------------------|-----------|----------|----------|--------|
| `id` | `Long` | `id` | `BIGINT` | 无（主键） |
| `tenantId` | `Long` | `tenant_id` | `BIGINT NOT NULL` | `0` |
| `createdBy` | `String` | `created_by` | `VARCHAR(64) NOT NULL` | `''` |
| `createdTime` | `LocalDateTime` | `created_time` | `DATETIME NOT NULL` | `CURRENT_TIMESTAMP` |
| `updatedBy` | `String` | `updated_by` | `VARCHAR(64) NOT NULL` | `''` |
| `updatedTime` | `LocalDateTime` | `updated_time` | `DATETIME NOT NULL` | `CURRENT_TIMESTAMP ON UPDATE` |
| `deleted` | `Integer` | `deleted` | `TINYINT NOT NULL` | `0` |

> **CRITICAL**: 禁止在 DDL 中使用与上表不一致的类型。若 BaseEntity 字段类型发生变更，必须同步更新此映射表。

### 4.3 数据库表设计

#### 4.3.1 表名: `{table_name}`

**表描述**: {表的业务描述}

**字段定义**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | BIGINT | ✅ | AUTO | 主键 |
| tenant_id | BIGINT | ✅ | - | 租户ID |
| | | | | |
| is_deleted | TINYINT(1) | ✅ | 0 | 逻辑删除标记 |
| create_by | BIGINT | ✅ | - | 创建人ID |
| create_time | DATETIME | ✅ | CURRENT_TIMESTAMP | 创建时间 |
| update_by | BIGINT | ❌ | - | 更新人ID |
| update_time | DATETIME | ❌ | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**DDL**
```sql
CREATE TABLE `{table_name}` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    `tenant_id` BIGINT NOT NULL COMMENT '租户ID',
    -- 业务字段
    
    `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0-未删除, 1-已删除',
    `create_by` BIGINT NOT NULL COMMENT '创建人ID',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
    `update_time` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{表中文名}';
```

### 4.4 索引设计

#### 表 `{table_name}` 索引

| 索引名 | 类型 | 字段 | 用途 |
|--------|------|------|------|
| PRIMARY | 主键 | id | 主键索引 |
| idx_tenant_id | 普通 | tenant_id | 租户数据隔离 |
| | | | |

### 4.5 数据归属说明

```markdown
## 数据所有权
- 主数据: 该服务是此数据的唯一写入方
- 引用数据: 该服务只读，数据由其他服务维护

## 数据同步策略（如有）
- 同步方式: Feign 调用 / 消息订阅 / 数据冗余
- 一致性要求: 强一致 / 最终一致
```

---

## 数据模型检查清单

- [ ] 表命名符合规范（小写下划线）
- [ ] 必须包含审计字段（create_by, create_time, update_by, update_time）
- [ ] 必须包含逻辑删除字段（is_deleted）
- [ ] 必须包含租户字段（tenant_id）
- [ ] 索引设计已考虑查询场景
- [ ] 字段类型选择合理（禁止 double 存金额）
