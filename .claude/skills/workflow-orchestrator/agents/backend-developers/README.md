# 后端领域开发 Agent 规范目录

> **设计理念**: 不再为每个业务领域维护独立的 Agent 定义文件，而是通过一份通用规范 + `domain-registry.json` 动态驱动。
> 任何业务领域（广告、电商、社交、金融...）都无需预先创建 Agent 文件。

## 目录结构

```
backend-developers/
├── backend-dev-specification.md    # 通用后端开发规范（所有领域 Agent 共享）
└── README.md                       # 本文件
```

## 工作机制

### 动态调度流程

```
ARCHITECT_BACKEND 阶段
  → 架构师分析需求，确定领域划分
  → 用户确认后写入 domain-registry.json
       ↓
IMPLEMENT 阶段
  → 编排器读取 domain-registry.json
  → 为每个领域动态生成开发 Agent（Prompt 注入）
  → 每个 Agent 通过 Read 加载 backend-dev-specification.md 获得完整工程规范
  → 领域差异（边界、职责、额外规则）通过 Prompt 和 domain-registry.json 注入
```

### 领域差异如何表达

不再使用 `{{占位符}}` 模板机制，领域差异通过以下方式动态注入：

| 差异维度 | 来源 | 注入方式 |
|---------|------|---------|
| 领域名称/ID | `domain-registry.json → domains[].id/name` | Prompt 注入 |
| 领域模块列表 | `domain-registry.json → domains[].modules` | Prompt 注入 |
| 领域间依赖 | `domain-registry.json → domains[].dependencies` | Prompt 注入 |
| 领域边界（文件所有权） | 编排器根据 `domain-registry.json` 动态生成 | Prompt 注入 |
| 领域特有规则 | `domain-registry.json → domains[].extraRules` | Prompt 注入 + Agent 运行时读取 |
| 领域特有检查项 | `domain-registry.json → domains[].extraQualityChecks` | Prompt 注入 + Agent 运行时读取 |
| 通用工程规范 | `backend-dev-specification.md` | Agent 通过 Read 加载 |

### domain-registry.json 示例

```json
{
  "registryVersion": "1.0",
  "projectType": "java",
  "domains": [
    {
      "id": "common",
      "name": "公共基础模块",
      "modules": ["utils", "config", "middleware"],
      "dependencies": [],
      "extraRules": [],
      "extraQualityChecks": []
    },
    {
      "id": "ad-service",
      "name": "广告投放服务",
      "modules": ["campaign", "targeting", "bidding"],
      "dependencies": ["common"],
      "extraRules": ["竞价金额计算使用 BigDecimal，禁止浮点数"],
      "extraQualityChecks": ["广告计费逻辑已覆盖 CPC/CPM/CPA 三种模式"]
    },
    {
      "id": "creative-service",
      "name": "创意素材服务",
      "modules": ["creative", "review", "template"],
      "dependencies": ["common"],
      "extraRules": [],
      "extraQualityChecks": []
    }
  ]
}
```

## 维护原则

- **修改通用工程规范**（如新增 CRITICAL 检查项）→ 只改 `backend-dev-specification.md` 一个文件，所有领域自动生效
- **添加领域特有约束** → 在 `domain-registry.json` 的 `extraRules` / `extraQualityChecks` 中声明，无需创建文件
- **新增业务领域** → 无需任何操作，ARCHITECT_BACKEND 阶段会自动识别并写入 `domain-registry.json`
