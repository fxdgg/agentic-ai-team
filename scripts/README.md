# scripts/ — ai-team 引擎工具链

> **⚠️ 受众边界（重要）**
>
> 本目录是**引擎维护者专属**的静态工具链。
>
> - **团队小伙伴**（工作流使用者）：在你的业务项目 `cp -r .codebuddy/` + `cp -r .claude/` 即可，**不需要拷贝本目录**。`/flow-run` / `/knowledge` / `/team-init` 等运行时命令与本目录完全解耦。
> - **引擎维护者**（改 `ai-team` 引擎本身者）：完整 clone 本仓库，本目录提供一致性体检、影响分析、dry-run 等工具。

本目录是 ai-team 引擎仓库自身的静态校验/渲染/镜像工具链，用于治理工作流引擎本身的复杂度。所有脚本是**纯静态、零运行时依赖**的，不会被 `/flow-run` 等运行时命令读取，**也不会被 `cp -r` 部署到业务项目**。

## 与 `.claude/skills/workflow-orchestrator/scripts/` 的边界

| 目录 | 用途 | 运行时机 |
|------|------|---------|
| `scripts/`（本目录） | 引擎仓库**作者**用的元工具（DSL 校验、渲染、双平台镜像、影响分析、dry-run） | 仅在迭代引擎仓库时由维护者手动 / pre-commit / CI 运行 |
| `.claude/skills/workflow-orchestrator/scripts/` | 编排器**运行时**辅助脚本（如 `resolve_agent_paths.py`） | `/flow-run` 调用 Agent 时由编排器调用 |

## 工具链分层

| 层 | 脚本 | 作用 | 状态 |
|---|------|------|------|
| **L0 验证** | `validate_meta.py` | DSL 内部一致性（流转闭环 / 字段引用 / Agent 阶段绑定） | Phase 2 引入 |
| **L1 渲染** | `render_artifacts.py` | DSL / 现有 JSON → SKILL.md 区段 / ARCHITECTURE 表格 / README 表格 | Phase 1 引入 |
| **L2 镜像** | `mirror_platforms.py` | `.claude/` → `.codebuddy/` 单向镜像（含偏差豁免） | Phase 3 引入 |
| **L3 体检** | `consistency_check.py` | 10 维度全量体检 | **Phase 0** ✅ |
| **L4 影响** | `impact_analyzer.py` | 输入改动文件，输出待同步目标 + 已同步状态 | **Phase 0** ✅ |
| **L5 dry-run** | `dry_run.py` | 模拟 15 阶段流转 + IntentGate / D2C / 三级降级 | **Phase 0**（基础版） |

## 快速开始

### 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### Phase 0 立即可用

```bash
# 1. 全量一致性体检（10 维度）
python scripts/consistency_check.py

# 2. 影响分析：改完代码后调用一次
python scripts/impact_analyzer.py --changed=.claude/skills/workflow-orchestrator/references/state-schema.json

# 3. dry-run：模拟跑一遍 15 阶段
python scripts/dry_run.py
```

### 退出码约定

| 退出码 | 含义 |
|--------|------|
| `0` | PASS — 全部通过 |
| `1` | WARN — 存在告警，不阻断 |
| `2` | FAIL — 存在硬性漂移，需要修复 |
| `3` | ERROR — 脚本内部异常（配置/IO 错误等） |

### 输出格式

所有脚本支持 `--format=console|md|json`：
- `console`（默认）：彩色 ANSI 输出，适合本地终端
- `md`：Markdown 报告，适合贴到 PR 评论或保存
- `json`：结构化输出，适合 CI/进一步处理

## 目录结构

```
scripts/
├── README.md                    # 本文件
├── requirements.txt             # 第三方依赖（PyYAML、jsonschema、Jinja2）
│
├── lib/                         # 共享库
│   ├── __init__.py
│   ├── paths.py                 # 仓库根目录与关键路径定位
│   ├── md_parser.py             # Markdown 解析（quote-block frontmatter / 表格 / AUTO-GEN 区段）
│   ├── autogen_block.py         # AUTO-GEN 区段读写 + sha256 hash
│   ├── dependency_graph.py      # 文件依赖图（基于 ARCHITECTURE.md §2 映射表 + 文件命名）
│   ├── platform_mirror.py       # 双平台对账
│   ├── meta_loader.py           # （Phase 2）加载 meta/*.yaml DSL
│   └── reporters.py             # 报告格式化（console / md / json）
│
├── consistency_check.py         # L3 体检（Phase 0）
├── impact_analyzer.py           # L4 影响分析（Phase 0）
├── dry_run.py                   # L5 dry-run（Phase 0）
├── render_artifacts.py          # L1 渲染（Phase 1）
├── validate_meta.py             # L0 DSL 校验（Phase 2）
├── mirror_platforms.py          # L2 镜像（Phase 3）
│
└── hooks/
    ├── install.sh               # 一键安装 Git pre-commit hook
    └── pre-commit               # pre-commit 钩子内容
```

## 一致性体检维度（Phase 0 已覆盖）

| # | 维度 | 数据源 |
|---|------|--------|
| 1 | 阶段流转闭环（INIT → DONE 可达） | `phase-transitions.json` + `state-schema.json#PhaseId` |
| 2 | PhaseId 枚举一致性（schema vs transitions） | 两个 JSON 比对 |
| 3 | SKILL.md §2.1 阶段表对齐 | 解析 SKILL.md 表格 |
| 4 | Agent 注册完备（SKILL.md §3 ↔ agents/*.md ↔ phases/*-rules.md） | 三方对账 |
| 5 | 双平台对称（`.claude/` ↔ `.codebuddy/`） | 文件树 + sha256 |
| 6 | ARCHITECTURE 章节同步 | 解析 md 表 |
| 7 | CLAUDE.md ↔ CODEBUDDY.md 100% 一致 | sha256 |
| 8 | state-schema.json 字段命名（camelCase） | 正则扫描 |
| 9 | AUTO-GEN 区段 hash（Phase 1+ 启用） | sha256 比对 |
| 10 | 阶段产物 knowledgeReferences 字段（Phase 1+ 启用） | 解析 templates/*.md |

## 设计原则

1. **零侵入**：所有脚本仅读 + 在仓库内可控位置写，**不修改运行时文件**（Phase 0/1 完全不动 JSON Schema）
2. **零运行时依赖**：脚本不会被 `/flow-run` 调用，不影响业务项目部署
3. **快速反馈**：全量体检 <5 秒，影响分析 <1 秒，dry-run <2 秒
4. **可选启用**：默认不阻塞编辑；CI 与 pre-commit 是强制点
5. **结构化输出**：所有报告含「文件 + 行 + 修复提示」，对齐 SKILL.md §2.3 质量门禁约定

## 相关文档

- [ARCHITECTURE.md](../ARCHITECTURE.md) §7.2 防漂移防线总览
- [CLAUDE.md](../CLAUDE.md) §3 双平台对称约束 + 自检清单
- [Plan](/root/.codebuddy-server-cn/data/User/globalStorage/tencent-cloud.coding-copilot/plans/) workflow-meta-model-dsl-refactor
