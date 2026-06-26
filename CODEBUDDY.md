
# AI 协作约定（ai-team 引擎仓库）

> 本文件是 **ai-team 引擎仓库自身**的 AI 协作约定，仅在直接迭代本仓库（修改 `.claude/` / `.codebuddy/` 下的工作流文件，或 `scripts/` / `meta/` / `ARCHITECTURE.md` 等仓库根开发者文件）时生效。
> 当本仓库被安装到业务项目作为工作流引擎使用时，本文件不参与运行时——运行时规则定义在 `.claude/skills/` 与 `.codebuddy/skills/` 中。

---

## 1. 对话开始：先读 README 门户，再通读 ARCHITECTURE 权威源

**每次新对话开始时，AI 必须先快速浏览仓库根的 [`README.md`](./README.md)（薄门户，约 150 行）建立全景，再通读 [`ARCHITECTURE.md`](./ARCHITECTURE.md)（单一架构权威源）了解细节**，建立以下背景认知后再回答用户问题：

- 项目定位：基于 IDE 的 Skill/Command/Rule 体系，多 Agent 协作的工作流引擎
- 部署拓扑：单仓 / 多仓统一 `repos[]` 模型 + 独立的团队知识仓库（ARCHITECTURE §2）
- 16 阶段状态机的整体流程（ARCHITECTURE §4）
- 知识体系（Layer 0-P/0-T/1/2/3 + 5 种知识类型 + 三级成熟度，ARCHITECTURE §6）
- 双平台镜像维护与方言对照（见本文件 §3 + ARCHITECTURE §3）
- **开发者工具链 12 维度体检 + DSL 单一真相源 + 平台方言豁免**（见本文件 §4 / §5）

> README 是面向使用者的薄门户，ARCHITECTURE 是面向维护者的架构权威源——两者职责不重叠，遇到架构细节以 ARCHITECTURE 为准。

## 2. 工作流变更：同步更新文档（README 门户 + ARCHITECTURE 权威源）

**当本次对话涉及对以下任一目录的实质性变更（新增/删除/重命名 skill/command/agent，或修改 16 阶段状态机、知识体系结构、命令清单等架构性内容）时，必须同步更新文档：**

涉及的目录：
- `.claude/skills/` 与 `.codebuddy/skills/`
- `.claude/commands/` 与 `.codebuddy/commands/`
- `.claude/rules/` 与 `.codebuddy/rules/`
- `.claude/references/` 与 `.codebuddy/references/`
- `meta/`（DSL 真相源）
- `scripts/`（开发者工具链）

**文档分工**：README 只承载使用者可见的「命令清单 / Skills 清单 / 安装 / 快速开始」；其余架构性内容一律以 ARCHITECTURE 为单一权威源。需要同步更新的位置（按变更类型对应）：

| 变更类型 | 需更新的文档位置 |
|---------|---------------------|
| 新增/删除/重命名 command | README「可用命令」表 + 「快速开始」+ ARCHITECTURE §11.3 |
| 新增/删除/重命名 skill | README「可用 Skills」表 + ARCHITECTURE §10.2 / §11.2 |
| 修改 16 阶段流程 | ARCHITECTURE §4（流程图 + 阶段全表）+ §11.5 |
| 修改 Agent Teams / 三级降级 / IntentGate 等核心机制 | ARCHITECTURE §7（核心工程机制）+ §5 |
| 修改知识体系（层级/类型/成熟度/查询预算） | ARCHITECTURE §6 全章 |
| 修改 `repos[]` / 单仓多仓拓扑 | ARCHITECTURE §2 |
| 修改 `/flow-import` 流程 | ARCHITECTURE §9.3 |
| 修改目录结构（新增顶层目录、调整 skills 内部组织） | ARCHITECTURE §10 |
| 新增/修改开发者脚本（`scripts/*.py`） | [`scripts/README.md`](./scripts/README.md) + ARCHITECTURE §10.4 |
| 新增/修改体检维度 | 本文件 §4.3 + [`scripts/README.md`](./scripts/README.md) |

**判定原则**：如果用户运行 `/flow-run`、`/knowledge`、`/team-init` 等命令时**可观察到的行为**发生了变化，README 的命令 / Skills 清单必须同步；架构细节始终同步到 ARCHITECTURE。仅修改 prompt 措辞、修复笔误、调整内部实现细节（用户不可见）则无需更新。

**更新日志强制项**：除了修正对应章节外，**还必须在 [`ARCHITECTURE.md` 附录 A](./ARCHITECTURE.md#附录-a更新日志) 追加一条记录**（格式见附录 A 内的「格式约定」），这是了解项目演化脉络的唯一入口，不可省略。

**执行时机**：在本次对话的最后一步（commit 之前）批量更新 README + ARCHITECTURE 附录 A，并在交付总结中明确告知用户「文档已同步更新」。

## 3. 双平台镜像方向（v2 修正）

> ⚠️ **重要纠正**：早期文档（含 v1 plan）写「`.claude/` 为权威源，`.codebuddy/` 为镜像目标」是错的。v2 已修正为下列规则。

### 3.1 实际工作流

```
.codebuddy/  （前线）  →  人工或脚本对账  →  .claude/  （同步副本）
   ↑                                              
 维护者优先在这里改
```

- **`.codebuddy/` 是前线**：维护者（用 CodeBuddy IDE）日常迭代时优先在此目录改
- **`.claude/` 是同步副本**：从 `.codebuddy/` 同步过来时**需要做平台适配翻译**（工具名 / IDE 名 / 路径 / 术语等方言对应），**不能简单 cp**
- **方言差异是 feature，不是 bug**：见 [`ARCHITECTURE.md` §3.3 平台方言对照](./ARCHITECTURE.md#33-平台方言对照已确认的映射对) 和 [`meta/platform-divergence.yaml`](./meta/platform-divergence.yaml) 的 `paired_translation` 段（17 条已确认映射）
- **`scripts/mirror_platforms.py --status`**：列出未豁免的真漂移（方言-only 差异自动静默）
- **`ai-team-project/` 和 `git-viewer/ur-ai-team/` 目录文件不要直接修改**——它们通过本仓库 push 后从远程同步

### 3.2 改双平台文件的 SOP

每次改 `.codebuddy/` 或 `.claude/` 的同名文件时：

1. **先改 `.codebuddy/`**（前线）
2. **人工翻译同步到 `.claude/`**（按方言对照表）
3. 跑 `python3 scripts/consistency_check.py --scope=platforms` 看 `platform-symmetry` 维度
4. 若是方言-only 差异 → 自动 PASS（被 `paired_translation` 段豁免）
5. 若是真功能差异 → FAIL，必须人工同步内容

> 不引入自动翻译镜像（误伤风险 + testCases 0 覆盖率，详见 [`ARCHITECTURE.md` 附录 C.5](./ARCHITECTURE.md)）。

## 4. 修改时必跑的命令（机器化纪律）

> ⚠️ **新对话开始时 Agent 必须意识到**：本仓库有完整的开发者工具链（`scripts/`），任何代码改动都有对应的"必跑命令"。**忽略这些命令会导致漂移，体检会暴露但已经太晚**。

### 4.1 按改动类型 → 必跑命令

| 你改了什么 | 必跑命令 | 作用 |
|-----------|---------|------|
| `scripts/lib/*.py`（共享库） | `python3 -m pytest scripts/tests` | **测试先行**：先在 `scripts/tests/test_*.py` 写 pytest 用例（FAIL）→ 实施 → PASS |
| `scripts/*.py`（主脚本） | `python3 scripts/<改的脚本>.py --format=json` 端到端跑通 | 行为验证 |
| `meta/phases.yaml` 或 `meta/state-schema.yaml` | `python3 scripts/render_artifacts.py --write-json --write` | 重新编译 disk JSON（双平台 4 个文件） |
| 改 `meta/*.yaml` 之后 | `python3 scripts/validate_meta.py` | DSL 内部一致性 + DSL ↔ JSON canonical-equal 校验 |
| `meta/platform-divergence.yaml`（豁免清单） | `python3 scripts/consistency_check.py --scope=platforms` | 验证豁免规则生效 |
| `.{platform}/skills/.../SKILL.md` 的 §2.1 / §10 | `python3 scripts/render_artifacts.py --rerender --write` | 更新 AUTO-GEN 区段 hash |
| `ARCHITECTURE.md` §4.2 阶段表 | 同上 | 同上 |
| `README.md` 的「可用命令」表 | 同上 | 同上 |
| 任意 `.codebuddy/` 文件 | 1) 改完  2) 人工翻译同步到 `.claude/` 3) `python3 scripts/mirror_platforms.py --status` | v2 修正：codebuddy 是前线 |
| Agent 文件（`.{platform}/skills/.../agents/*.md`） | `python3 scripts/consistency_check.py --scope=agents` | agent-registry + agent-frontmatter 校验 |
| `phases/` / `agents/` / `rules/` / `templates/` / `references/` / `SKILL.md` 任一变化 | `python3 scripts/render_visualization.py --write` | 重新生成 `docs/workflow-visualization.html`（pre-commit hook 也会自动跑） |
| **任何代码改动 commit 前** | `python3 scripts/consistency_check.py` | 12 维度全量体检 |

### 4.2 当前体检基线（v2 末尾）

> 改完代码后跑体检，**不应让指标变差**：

```
exit=2  PASS=9  INFO=1  WARN=7  FAIL=13  ERROR=0
```

- `FAIL=13` 全部是 `platform-symmetry` 维度的真功能差异（如 `commands/flow-run.md` 双平台多/少 70 行）
- 其他 11 维度全部 PASS / WARN（无 FAIL）
- 你的改动**应让 FAIL ≤ 13**；若引入新 FAIL 必须先消除或登记到 `meta/platform-divergence.yaml`

### 4.3 12 维度体检速查

| 维度 | 检查内容 | 触发改动 |
|-----|---------|---------|
| `phase-flow-closure` | 阶段流转图无环 + 可达 DONE | 改 `meta/phases.yaml` next/canSkipTo |
| `phase-id-enum-sync` | PhaseId enum 与 phases.yaml id 一致 | 改 `meta/phases.yaml` 或 state-schema |
| `skill-phase-table` | SKILL.md §2.1 阶段表与 phases 一致 | 改 SKILL.md §2.1 |
| `agent-registry` | Agent 文件存在 + 在 SKILL.md §10 注册 | 新增/重命名 agent |
| `agent-frontmatter` | Agent frontmatter 必填字段齐全 | 改 agent .md |
| `platform-symmetry` | 双平台对称（启用方言豁免后） | 改 `.codebuddy/` 或 `.claude/` |
| `architecture-sync` | ARCHITECTURE 章节与代码一致 | 改架构性内容 |
| `collab-docs-identical` | CLAUDE.md ≡ CODEBUDDY.md byte-equal | 改本文件 |
| `state-schema-naming` | state.json 字段命名规范 | 改 state-schema |
| `autogen-blocks` | 6 个 AUTO-GEN 区段 hash 完整 | 改包裹的内容 |
| `dsl-equivalence` | DSL ↔ disk JSON canonical-equal | 改 `meta/` 或 disk JSON |
| `dsl-source-marker` | disk JSON 头部含 `$generatedFrom` sentinel | 改 disk JSON 或 DSL |

## 5. v2 工程纪律（5 条铁律，违反必须显式说明原因）

> v1 的失败教训：宏大承诺 → 暗自降级 → 凯旋宣言 → 维护者交接时炸雷。v2 用 5 条铁律根除：

### 铁律 1：测试先行（lib/ 改动必守）

任何 `scripts/lib/*.py` 函数的新增 / 修改 / 重构，**必须**：

1. 先在 `scripts/tests/test_<module>.py` 写 pytest 用例（覆盖正例 + 反例 + 边界）
2. 跑 `pytest` 应 FAIL（确认测试在测对的东西）
3. 实施代码
4. 再跑 `pytest` 应 PASS

> 当前测试基线：**115 用例 / < 8s**。改动应让基线增长，绝不允许减少。

### 铁律 2：承诺三段式（Phase 设计必守）

任何新 Phase 的 plan 必须明确写出：

- ✅ **硬承诺**：必须兑现的，未兑现就是 plan 失败
- 💡 **软承诺**：尽力达到的，未达到要在交付时显式说明
- ❌ **不承诺**：明确放弃的，登记到 [`ARCHITECTURE.md` 附录 C](./ARCHITECTURE.md) 候选项

### 铁律 3：承诺降级必修文档

如果实施过程中发现某条承诺需要降级（如 byte-equal → canonical-equal），**当时必须**：

1. 修改 plan 主体（不是只在附录补一笔）
2. 修改对应脚本顶部注释（如 `validate_meta.py` 顶部的「承诺降级声明」）
3. 修改 README / ARCHITECTURE 中所有提及该承诺的地方
4. 在附录 A 当条记录里诚实说明

### 铁律 4：每个 Phase 端到端 demo

每个 Phase 验收必须包含**一句命令跑完看效果**的 demo：

```bash
# 例：Phase 3-new 的 demo
echo "..." >> .codebuddy/some-file.md
python3 scripts/consistency_check.py --scope=platforms
# 期望：方言替换静默 / 真新增段落仍触发 FAIL
```

不允许"理论上能跑"或"看代码应该可以"。

### 铁律 5：小步可回滚

每个 Phase 必须独立可回滚（删掉对应文件 / git revert 一个 commit 即可恢复到上一阶段）。**禁止 Phase N 改动 Phase N-1 的核心资产**——如果必须改，先用单独的"修复"Phase 处理。

## 6. 显式不做的事（v2 plan 主体声明）

为避免 v1 教训重演，下列事项**主动放弃**，登记在 [`ARCHITECTURE.md` 附录 C](./ARCHITECTURE.md)：

- ❌ 自动方言翻译（误伤风险 + testCases 0 覆盖率）
- ❌ 30 条业务路径模拟（dry_run 仅做骨架自检）
- ❌ 字符级 byte-equal（canonical-equal 已够用）
- ❌ SKILL.md 全文拆分（76KB 单文件已通过 4 个 AUTO-GEN 区段缓解）
- ❌ 运行时校验（state.json 实际读写，超出静态工具链）
- ❌ CI 集成（候选项，按需启动）

要启动任何候选项，必须先用 `plan_create` 写新 plan + 走铁律 1-5。

---

## 速查：变更后的自检清单（v2 升级版）

在结束涉及工作流引擎变更的对话前，**逐项确认 + 跑命令验证**：

### 文件层
- [ ] `.claude/` 与 `.codebuddy/` 双平台都已同步修改？（先 codebuddy，再人工翻译到 claude）
- [ ] `meta/*.yaml` 改动后跑过 `python3 scripts/render_artifacts.py --write-json --write`？
- [ ] `SKILL.md §2.1 / §10` / `ARCHITECTURE §4.2` / `README 命令表` 改动后跑过 `python3 scripts/render_artifacts.py --rerender --write`？
- [ ] `scripts/lib/*.py` 改动后**先**写 pytest 用例 + 跑过 `python3 -m pytest scripts/tests` 全 PASS？
- [ ] `phases/` / `agents/` / `rules/` / `templates/` / `references/` / `SKILL.md` 改动后跑过 `python3 scripts/render_visualization.py --write`？（pre-commit hook 也会自动跑）

### 文档层
- [ ] 用户可见行为是否变化？若是，README 对应章节是否已更新？
- [ ] **`ARCHITECTURE.md` 附录 A 是否已追加本次变更条目**（含 YYYY-MM-DD 标题、变更内容、影响面、关联文件）？
- [ ] 「可用命令」/「可用 Skills」表格是否仍然准确？
- [ ] ARCHITECTURE §4「16 阶段状态机」流程图 / 阶段全表是否仍然准确？
- [ ] 承诺降级（如有）是否同时改了 plan 主体 + 脚本注释 + README + 附录 A 四处？

### 体检层
- [ ] `python3 scripts/consistency_check.py` 12 维度体检 FAIL ≤ 13（当前基线）？
- [ ] `python3 scripts/validate_meta.py` 全 PASS？
- [ ] `python3 scripts/render_artifacts.py --check` 6/6 PASS？
- [ ] `python3 -m pytest scripts/tests` 全 PASS？

### 一致性层
- [ ] CLAUDE.md 与 CODEBUDDY.md 内容是否仍保持 byte-equal？（`diff CLAUDE.md CODEBUDDY.md` 无输出）
- [ ] 所有「显式不做」的事项（§6）是否依然适用？若需启动某项，是否已写新 plan？
