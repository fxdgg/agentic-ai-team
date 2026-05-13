# 团队协作机制

> 本文件从 SKILL.md 拆分而来，被 /knowledge sync 和团队知识贡献流程按需加载。

---

## 2.6 团队协作机制

### 2.6.1 贡献模式 — "贡献暂存 + 异步合并"

借鉴区块链三个核心思想，但使用 Git 作为实现载体：

| 区块链思想 | ai-team 实现 | 机制 |
|-----------|-------------|------|
| 不可篡改的追加日志 | log.md 只追加不修改 | 每条变更记录贡献者、时间、会话哈希 |
| 贡献可溯源 | evidence.contributors[] | 类似 Git blame，粒度为知识条目级 |
| 共识机制 | maturity 多人验证提升 | draft→verified: 1人验证; verified→proven: ≥2人+≥2项目 |

### 2.6.2 冲突解决流程

当多名团队成员同时执行 ARCHIVE 并推送知识时，按以下策略自动处理：

| 冲突类型 | 描述 | 处理方式 |
|---------|------|---------|
| **纯新增** (additive) | 两人加了不同的知识条目 | 自动合并，两条都保留 |
| **证据追加** (evidence_append) | 两人验证了同一条知识 | 自动合并，evidence 数组合并去重 |
| **成熟度提升** (maturity_upgrade) | 一人触发了 draft→verified | 自动合并 |
| **内容矛盾** (content_conflict) | 同一条目内容相反 | 写入 contributions/conflicts/，通知 maintainer 裁决 |
| **成熟度冲突** (maturity_conflict) | 一人升级一人降级 | 保留较低成熟度 + 标记 contradiction |

### 2.6.3 团队角色

| 角色 | 权限 | 适用人群 | 分配时机 |
|------|------|---------|---------|
| `maintainer` | 解决 content_conflict、审批 proven 提升、管理成员 | 团队负责人 | 知识仓库首个成员自动分配（仓库创建者） |
| `contributor` | 通过工作流自动贡献（create/verify/flag_contradiction） | 正式成员 | `/team-init` Step 6 用户选择"正式成员"时分配；`profile.yaml` 中 `trial: false` |
| `reader` | 只消费知识（查询/注入），不贡献；ARCHIVE 阶段跳过 Step 4-11（贡献写入），仅保留本地归档和索引维护 | 新成员试用期 | `/team-init` Step 6 用户选择"试用期"时分配；`profile.yaml` 中 `trial: true` |

**角色在工作流中的生效点**：
- `knowledge-query-protocol.md` §6：reader 可查询但不贡献
- `archiver.md` 阶段七前置条件：检测到 `contributorRole == "reader"` 时跳过贡献写入
- **角色升级**：reader 用户将 `profile.yaml` 的 `trial` 改为 `false` 后，下次 `/team-init` 会提示升级到 contributor

### 2.6.4 知识条目团队化 front-matter

```yaml
evidence:
  contributors:                            # 所有贡献者（区块链签名链）
    - name: "Steven"
      action: "create"
      date: "2026-04-09"
      project: "cloud-mall"
      workflow: "20260409-商品分类优化"
    - name: "Alice"
      action: "verify"
      date: "2026-04-12"
      project: "vibe-mall"
      workflow: "20260412-商品列表优化"
  verified_in_projects: ["cloud-mall", "vibe-mall"]
  last_referenced: "2026-04-12"
  contradiction_flags: []
```

**知识条目 ID 前缀规则**：
- Layer 1 技术知识：`TK-{领域}-{序号}`（如 TK-SB-001, TK-JAVA-002）
- Layer 2 业务知识：`BK-{domain}-{类型缩写}{序号}`（如 BK-AD-M001, BK-AD-G001）
- Layer 3 项目知识：`{类型缩写}-{序号}` 格式（如 DEC-001, GL-001, PIT-001）

**类型缩写表**：

| 类型 | 缩写 | ID 示例（Layer 3） | ID 示例（Layer 2） |
|------|------|-------------------|-------------------|
| model | MOD | MOD-001 | BK-AD-M001 |
| decision | DEC | DEC-001 | BK-AD-D001 |
| guideline | GL | GL-001 | BK-AD-G001 |
| pitfall | PIT | PIT-001 | BK-AD-T001 |
| process | PRC | PRC-001 | BK-AD-P001 |

### 2.6.5 团队级配置：`.knowledge-config.yaml`

知识仓库根目录的 `.knowledge-config.yaml` 除成员和冲突策略外，还包含 **知识衰减与事实校对** 的阈值配置。所有字段均为可选，缺失时使用默认值。

```yaml
# 成员与冲突（已有段落，示意）
members:
  - name: "Steven"
    role: "maintainer"
  - name: "Alice"
    role: "contributor"
conflict_policy:
  auto_merge_strategies: [additive, evidence_append, maturity_upgrade]
  maintainer_review_required: [content_conflict]

# ─────────────────────────────────────────
# 知识衰减规则（archiver §17 使用）
# ─────────────────────────────────────────
decay_rules:
  knowledge_inactive_months: 12      # 知识多久未引用进入衰减判定（默认 12）
  module_active_threshold_months: 6  # 模块多久内有变更算"活跃"——活跃则正常衰减（默认 6）
  module_dormancy_cap_months: 24     # 模块休眠上限——超过则强制衰减，避免永久保留（默认 24）

# ─────────────────────────────────────────
# 代码事实校对（archiver §17.5 + fact-checker 子 Agent 使用）
# ─────────────────────────────────────────
fact_check:
  enabled: true                      # 总开关（默认 true）
  max_entries_per_archive: 20        # 单次 ARCHIVE 最多校对的候选条目数（默认 20）
  max_symbols_per_entry: 5           # 每条候选最多提取的可验证符号数（默认 5）
  skip_maturity: [draft]             # 跳过哪些成熟度的条目（默认 draft，因其本就不可信）
```

**字段如何起效**：

| 字段 | 影响的逻辑 | 调整建议 |
|-----|-----------|---------|
| `knowledge_inactive_months` | 控制 proven 衰减触发时间 | 业务迭代快的团队可调小（如 6），稳定项目可调大 |
| `module_active_threshold_months` | 控制"活跃模块"的定义边界 | 小于实际迭代周期将失效抑制；大于业务周期会保留过多老知识 |
| `module_dormancy_cap_months` | 防止休眠抑制形成"永不衰减"的僵尸条目 | 通常设为 `knowledge_inactive_months × 2` |
| `fact_check.max_entries_per_archive` | 控制 archiver 单次开销 | 团队知识量大时保持 20；小型团队可调高到 50 |
| `fact_check.max_symbols_per_entry` | 控制 search_content 扫描量 | 典型值 3-10，超过 10 会显著增加 token 消耗 |

**配置热更新**：修改后下次 ARCHIVE 时生效，无需重启工作流。
