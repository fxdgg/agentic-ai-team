# meta/ — 工作流元模型 DSL（单一真相源）

> **⚠️ 仅引擎维护者使用** — 团队小伙伴在业务项目使用工作流时不需要拷贝本目录。本目录是 Phase 2 引入的"作者源"，编排器（运行时）只读 `.claude/skills/` / `.codebuddy/skills/` 下的产物 JSON，不引用本目录。

## 这是什么

随着 ai-team 引擎演进到 16 阶段 / 34+ Agent / 31 个 state.json 字段，"改了 A 漏了 B" 成为最痛的迭代瓶颈。本目录把易漂移的元数据（阶段定义、流转规则、state.json schema、命令清单等）**集中**到 YAML 单一真相源，配套 `scripts/validate_meta.py` 做内部一致性 + 与现有 JSON 文件的对象树等价校验。

## 文件清单

| 文件 | 真相源职责 | 派生产出 |
|------|-----------|---------|
| `phases.yaml` | 16 阶段定义 + 流转 + 三步模式标志 + rules 段（forward / skipCondition / rollback / termination） | `.{platform}/skills/workflow-orchestrator/references/phase-transitions.json` |
| `state-schema.yaml` | state.json 顶层 31 字段 + `definitions.PhaseId` / `definitions.PlatformStatus` 共享类型 | `.{platform}/skills/workflow-orchestrator/references/state-schema.json` |
| `commands.yaml` | 9 个用户命令的 name / description / file 路径 | `.{platform}/commands/*.md` 的 frontmatter（仅校验，不渲染正文） |
| `platform-divergence.yaml` | 双平台已知偏差 + Phase 3-new 引入的 `paired_translation` 段（17 条方言映射对） | 体检 `platform-symmetry` 维度的豁免来源 |

> **Phase 2.5 更新**：`phase-transitions.json` / `state-schema.json` 头部含 `$generatedFrom` + `$doNotEdit` sentinel。这两个 JSON 现在是**纯派生产出**，直接编辑会被 `dsl-equivalence` / `dsl-source-marker` 体检维度捕捉。

## 如何使用

### 维护者改 DSL 的标准流程

```bash
# 1. 改 meta/phases.yaml（如新增一个阶段、调整流转）
vim meta/phases.yaml

# 2. 内部一致性校验
python3 scripts/validate_meta.py --scope=internal

# 3. 与现有 JSON 等价性校验（DSL ↔ JSON 必须对象树等价）
python3 scripts/validate_meta.py --scope=equivalence

# 4. 如果 DSL 比 JSON 多了改动，需要同步 JSON：
#    （Phase 2 暂不自动 --write JSON；Phase 4 再启用）
#    手动改 .{platform}/skills/workflow-orchestrator/references/phase-transitions.json
#    + 双平台 SKILL.md §2.1 表 + ARCHITECTURE.md §4.2 表

# 5. 跑全量体检确认无新漂移
python3 scripts/consistency_check.py
```

### 反向生成（首次种子 / 重置 DSL）

```bash
# 从现有 JSON Schema 反向生成 meta/*.yaml 草稿（首次引入时已用，平时不需要）
python3 scripts/seed_meta_from_existing.py --write [--force]
```

`--force` 会覆盖已存在的 DSL 文件，**仅在你确认要从 JSON 重新种子 DSL 时使用**。

## 设计原则

1. **DSL 是"作者源"，JSON 是"运行时事实"**：编排器只读 JSON，DSL 不被任何运行时读取
2. **canonical-equal 而非 byte-equal**：原 JSON 文件有手工对齐空格 / 选择性紧凑数组等格式偏好，强求字符级一致工作量大于价值；改用对象树等价（json.load 后两者完全相同）
3. **保序加载**：YAML/Python 3.7+ 保留字典插入顺序，避免编译时字段重排导致 diff 噪声
4. **缺失容忍**：DSL 文件缺失时 `validate_meta.py` 报 WARN，不阻断；这样 Phase 2 可以渐进式落地（先有 phases.yaml，后有 state-schema.yaml）

## DSL 与现有产物的关系

```
┌──────────────────────┐         ┌──────────────────────────────────┐
│  meta/ (DSL 作者源)  │         │  .{platform}/skills/... (产物)  │
│                      │         │                                  │
│  phases.yaml         │ ────→ │  references/phase-transitions.json │
│  state-schema.yaml   │ ────→ │  references/state-schema.json      │
│  commands.yaml       │ ──校验→│  commands/*.md frontmatter         │
│                      │         │  agents/*.md frontmatter          │
│                      │         │  SKILL.md §2.1 §3 §10            │
└──────────────────────┘         └──────────────────────────────────┘
        ↑                                          ↑
        │                                          │
   只在维护时编辑                              运行时读取
```

**Phase 2（当前）**：DSL 文件已生成，`validate_meta.py` 校验等价性。改 DSL 时如出现与 JSON 偏差，校验器立即 FAIL；维护者必须手动同步 JSON 才能通过。

**Phase 4（计划）**：渲染器 `render_artifacts.py` 切换数据源到 DSL，改完 DSL 一处后**自动同步**所有派生位置（state-schema.json / phase-transitions.json / SKILL.md AUTO-GEN 区段 / ARCHITECTURE.md AUTO-GEN 区段）。

## 元字段约定

每个 DSL 文件顶层支持 `$comment` 字段，记录文件来源 / 维护说明，编译时被剥离不进 JSON。

## 相关文档

- [`scripts/validate_meta.py`](../scripts/validate_meta.py) — DSL 校验器
- [`scripts/seed_meta_from_existing.py`](../scripts/seed_meta_from_existing.py) — 反向生成器
- [`scripts/lib/meta_loader.py`](../scripts/lib/meta_loader.py) — DSL 加载器
- [`ARCHITECTURE.md` 附录 A 更新日志](../ARCHITECTURE.md#附录-a更新日志) — Phase 2 引入记录
