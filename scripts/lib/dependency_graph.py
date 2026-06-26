"""文件依赖图：基于 ARCHITECTURE.md §2 「变更类型 ↔ 章节」映射表 + 文件命名约定，
构建「改了哪些文件 → 需要同步哪些目标」的双向依赖图。

设计原则：
    1. 依赖关系**显式声明**而非动态推断（避免误报）
    2. 关系按"变更类型"分组，与 ARCHITECTURE.md §2 表格一一对应
    3. 影响目标用 `target_kind` 枚举（不直接列具体行，避免行号漂移）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import paths


# ----------------------------------------------------------------------------
# 变更类型与文件归类
# ----------------------------------------------------------------------------

class ChangeType:
    SKILL = "skill"                                  # 新增 / 删除 / 重命名 Skill
    COMMAND = "command"                              # 新增 / 删除 / 重命名 Command
    AGENT = "agent"                                  # 新增 / 删除 / 重命名 Agent
    PHASE_RULES = "phase-rules"                      # 修改阶段调度规则
    PHASE_FLOW = "phase-flow"                        # 修改 15 阶段流程
    STATE_SCHEMA = "state-schema"                    # 修改 state.json schema
    PHASE_TRANSITIONS = "phase-transitions"          # 修改流转规则
    SKILL_MD_CORE = "skill-md-core"                  # workflow-orchestrator SKILL.md 主体
    KNOWLEDGE_SYSTEM = "knowledge-system"            # 知识体系（层级 / 类型 / 成熟度 / 预算）
    INTENT_GATE = "intent-gate"                      # IntentGate / 三级降级
    REPOS_TOPOLOGY = "repos-topology"                # repos[] / 单仓多仓
    FLOW_IMPORT = "flow-import"                      # /flow-import 流程
    DOUBLE_PLATFORM = "double-platform"              # 双平台对称约束
    ANTI_DRIFT = "anti-drift"                        # 防漂移机制
    ARCHITECTURE_DOC = "architecture-doc"            # ARCHITECTURE.md 本身
    README_DOC = "readme-doc"                        # README.md 本身
    COLLAB_DOC = "collab-doc"                        # CLAUDE.md / CODEBUDDY.md
    RULES_FILE = "rules-file"                        # `.{platform}/rules/` 业务编码规则
    REFERENCES_FILE = "references-file"              # `.{platform}/references/` 顶层引用
    OTHER = "other"


@dataclass
class TargetSpec:
    """一个同步目标。"""
    kind: str                                        # 目标种类标识
    path: str                                        # 相对仓库根的目标路径
    section: str | None = None                       # 章节 / 表格 id（如适用）
    note: str = ""                                   # 人类可读说明


@dataclass
class ImpactRule:
    """一条影响规则。"""
    change_type: str
    targets: list[TargetSpec]


# ----------------------------------------------------------------------------
# 静态规则定义（与 ARCHITECTURE.md §2 表格一一对应）
# ----------------------------------------------------------------------------

def _arch(section: str, note: str = "") -> TargetSpec:
    return TargetSpec(kind="arch-section", path="ARCHITECTURE.md", section=section, note=note)


def _readme(section: str, note: str = "") -> TargetSpec:
    return TargetSpec(kind="readme-section", path="README.md", section=section, note=note)


def _appendix_a() -> TargetSpec:
    return TargetSpec(
        kind="appendix-a",
        path="ARCHITECTURE.md",
        section="附录 A 更新日志",
        note="必须追加一条 ### YYYY-MM-DD — 主题",
    )


def _platform_mirror(rel_path: str) -> TargetSpec:
    """要求 .claude/ ↔ .codebuddy/ 同步。`rel_path` 必须以 .claude/ 或 .codebuddy/ 开头。"""
    if rel_path.startswith(".claude/"):
        mirror = rel_path.replace(".claude/", ".codebuddy/", 1)
    elif rel_path.startswith(".codebuddy/"):
        mirror = rel_path.replace(".codebuddy/", ".claude/", 1)
    else:
        mirror = rel_path
    return TargetSpec(kind="platform-mirror", path=mirror, note="双平台对称同步")


def _claude_codebuddy_md_pair(source: str) -> TargetSpec:
    """CLAUDE.md ↔ CODEBUDDY.md 必须 byte-equal。"""
    mirror = "CODEBUDDY.md" if source == "CLAUDE.md" else "CLAUDE.md"
    return TargetSpec(kind="claude-codebuddy-pair", path=mirror, note="必须 100% 一致")


IMPACT_RULES: dict[str, ImpactRule] = {
    ChangeType.SKILL: ImpactRule(
        change_type=ChangeType.SKILL,
        targets=[
            _arch("§10.2 双平台并列结构", "Skills 数量与差异说明"),
            _arch("§5 Agent 编制全景", "若新 Skill 涉及 Agent 编制"),
            _readme("可用 Skills 表", "添加一行"),
            _appendix_a(),
        ],
    ),
    ChangeType.COMMAND: ImpactRule(
        change_type=ChangeType.COMMAND,
        targets=[
            _arch("§4 工作流 / §7 核心工程机制", "如与流程有交互"),
            _readme("可用命令表", "添加一行"),
            _readme("快速开始", "如新命令需引导"),
            _appendix_a(),
        ],
    ),
    ChangeType.AGENT: ImpactRule(
        change_type=ChangeType.AGENT,
        targets=[
            _arch("§5.1 静态 Agent 编制", "（单体 Agent）或 §5.2（动态 Agent）"),
            TargetSpec(
                kind="skill-md-section",
                path=str(paths.to_relative(paths.WF_SKILL_MD)),
                section="§3 子 Agent 注册表",
                note="必须添加 / 删除对应行",
            ),
            _appendix_a(),
        ],
    ),
    ChangeType.PHASE_FLOW: ImpactRule(
        change_type=ChangeType.PHASE_FLOW,
        targets=[
            _arch("§4.1 流程图（mermaid）", "节点 / 连线同步"),
            _arch("§4.2 阶段全表", "重新编号"),
            _arch("§4.3 三步模式 / §4.4 流转守卫", "如涉及"),
            _arch("§6.7 各阶段查询预算", "如新增阶段"),
            TargetSpec(
                kind="json-schema",
                path=str(paths.to_relative(paths.PHASE_TRANSITIONS)),
                note="transitions 表增删条目",
            ),
            TargetSpec(
                kind="json-schema",
                path=str(paths.to_relative(paths.STATE_SCHEMA)),
                section="definitions.PhaseId",
                note="enum 同步",
            ),
            TargetSpec(
                kind="skill-md-section",
                path=str(paths.to_relative(paths.WF_SKILL_MD)),
                section="§2.1 阶段定义 / §10 阶段规则映射",
                note="表格同步",
            ),
            _readme("15 阶段状态机", "如有"),
            _appendix_a(),
        ],
    ),
    ChangeType.INTENT_GATE: ImpactRule(
        change_type=ChangeType.INTENT_GATE,
        targets=[
            _arch("§5.3 三级降级", ""),
            _arch("§7.1 工程能力清单", ""),
            _appendix_a(),
        ],
    ),
    ChangeType.KNOWLEDGE_SYSTEM: ImpactRule(
        change_type=ChangeType.KNOWLEDGE_SYSTEM,
        targets=[
            _arch("§6 全章（知识体系）", ""),
            _appendix_a(),
        ],
    ),
    ChangeType.REPOS_TOPOLOGY: ImpactRule(
        change_type=ChangeType.REPOS_TOPOLOGY,
        targets=[
            _arch("§2.2 部署模式", ""),
            _arch("§8.2 关键字段交叉表", ""),
            _readme("部署示意", "如需更新"),
            _appendix_a(),
        ],
    ),
    ChangeType.FLOW_IMPORT: ImpactRule(
        change_type=ChangeType.FLOW_IMPORT,
        targets=[
            _arch("§9.3 冷启动管道", ""),
            _arch("§6.3 流动闭环图", ""),
            _appendix_a(),
        ],
    ),
    ChangeType.STATE_SCHEMA: ImpactRule(
        change_type=ChangeType.STATE_SCHEMA,
        targets=[
            _arch("§8.1 顶层字段总览", ""),
            _arch("§8.2 关键字段交叉表", ""),
            _arch("§11.6 新增 state.json 字段", ""),
            _appendix_a(),
        ],
    ),
    ChangeType.PHASE_TRANSITIONS: ImpactRule(
        change_type=ChangeType.PHASE_TRANSITIONS,
        targets=[
            _arch("§4.4 流转守卫", ""),
            _arch("§7.2 防漂移防线总览", "如涉及"),
            TargetSpec(
                kind="json-schema",
                path=str(paths.to_relative(paths.STATE_SCHEMA)),
                section="definitions.PhaseId",
                note="若 transitions key 集合变更需同步",
            ),
            _appendix_a(),
        ],
    ),
    ChangeType.DOUBLE_PLATFORM: ImpactRule(
        change_type=ChangeType.DOUBLE_PLATFORM,
        targets=[
            _arch("§3 全章（双平台镜像设计）", ""),
            _appendix_a(),
        ],
    ),
    ChangeType.ANTI_DRIFT: ImpactRule(
        change_type=ChangeType.ANTI_DRIFT,
        targets=[
            _arch("§7.2 防漂移防线总览", ""),
            _appendix_a(),
        ],
    ),
    ChangeType.PHASE_RULES: ImpactRule(
        change_type=ChangeType.PHASE_RULES,
        targets=[
            _arch("§4.2 阶段全表（说明列）", "如阶段行为有变"),
            _appendix_a(),
        ],
    ),
    ChangeType.SKILL_MD_CORE: ImpactRule(
        change_type=ChangeType.SKILL_MD_CORE,
        targets=[
            _arch("对应 §4 / §5 / §7 章节", "若用户可见行为变化"),
            _appendix_a(),
        ],
    ),
    ChangeType.RULES_FILE: ImpactRule(
        change_type=ChangeType.RULES_FILE,
        targets=[],
    ),
    ChangeType.REFERENCES_FILE: ImpactRule(
        change_type=ChangeType.REFERENCES_FILE,
        targets=[],
    ),
    ChangeType.ARCHITECTURE_DOC: ImpactRule(
        change_type=ChangeType.ARCHITECTURE_DOC,
        targets=[],
    ),
    ChangeType.README_DOC: ImpactRule(
        change_type=ChangeType.README_DOC,
        targets=[],
    ),
    ChangeType.COLLAB_DOC: ImpactRule(
        change_type=ChangeType.COLLAB_DOC,
        targets=[],
    ),
    ChangeType.OTHER: ImpactRule(
        change_type=ChangeType.OTHER,
        targets=[],
    ),
}


# ----------------------------------------------------------------------------
# 路径 → 变更类型分类
# ----------------------------------------------------------------------------

# 顺序很重要：更具体的规则在前
PATH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ARCHITECTURE / README / CLAUDE / CODEBUDDY 自身
    (re.compile(r"^ARCHITECTURE\.md$"), ChangeType.ARCHITECTURE_DOC),
    (re.compile(r"^README\.md$"), ChangeType.README_DOC),
    (re.compile(r"^(CLAUDE|CODEBUDDY)\.md$"), ChangeType.COLLAB_DOC),

    # workflow-orchestrator 的关键文件
    (re.compile(r"^\.(claude|codebuddy)/skills/workflow-orchestrator/references/state-schema\.json$"),
     ChangeType.STATE_SCHEMA),
    (re.compile(r"^\.(claude|codebuddy)/skills/workflow-orchestrator/references/phase-transitions\.json$"),
     ChangeType.PHASE_TRANSITIONS),
    (re.compile(r"^\.(claude|codebuddy)/skills/workflow-orchestrator/SKILL\.md$"),
     ChangeType.SKILL_MD_CORE),
    (re.compile(r"^\.(claude|codebuddy)/skills/workflow-orchestrator/agents/"),
     ChangeType.AGENT),
    (re.compile(r"^\.(claude|codebuddy)/skills/workflow-orchestrator/phases/"),
     ChangeType.PHASE_RULES),

    # 命令
    (re.compile(r"^\.(claude|codebuddy)/commands/[^/]+\.md$"), ChangeType.COMMAND),

    # Skills（除 workflow-orchestrator 本身已在前匹配）
    (re.compile(r"^\.(claude|codebuddy)/skills/[^/]+/SKILL\.md$"), ChangeType.SKILL),
    (re.compile(r"^\.(claude|codebuddy)/skills/(?!workflow-orchestrator)"), ChangeType.SKILL),

    # 业务编码规则
    (re.compile(r"^\.(claude|codebuddy)/rules/"), ChangeType.RULES_FILE),

    # 顶层引用
    (re.compile(r"^\.(claude|codebuddy)/references/"), ChangeType.REFERENCES_FILE),
]


def classify_path(rel_path: str) -> str:
    """返回变更类型（ChangeType.* 常量）。"""
    for pat, ct in PATH_PATTERNS:
        if pat.search(rel_path):
            return ct
    return ChangeType.OTHER


# ----------------------------------------------------------------------------
# 影响分析入口
# ----------------------------------------------------------------------------

@dataclass
class FileImpact:
    """单文件的影响分析结果。"""
    file: str
    change_type: str
    targets: list[TargetSpec] = field(default_factory=list)
    platform_mirror: TargetSpec | None = None        # 双平台镜像目标（如适用）


def analyze_changed_file(rel_path: str) -> FileImpact:
    """对单个改动文件做影响分析。"""
    ct = classify_path(rel_path)
    rule = IMPACT_RULES.get(ct, IMPACT_RULES[ChangeType.OTHER])
    impact = FileImpact(file=rel_path, change_type=ct, targets=list(rule.targets))

    # 双平台镜像目标
    if rel_path.startswith(".claude/") or rel_path.startswith(".codebuddy/"):
        # 排除 plans/ 与 iwiki-operation 单平台特例
        if "/plans/" not in rel_path and "iwiki-operation" not in rel_path:
            impact.platform_mirror = _platform_mirror(rel_path)

    # CLAUDE/CODEBUDDY 配对
    if rel_path in ("CLAUDE.md", "CODEBUDDY.md"):
        impact.platform_mirror = _claude_codebuddy_md_pair(rel_path)

    return impact


def analyze_changes(rel_paths: list[str]) -> list[FileImpact]:
    """批量影响分析。"""
    return [analyze_changed_file(p) for p in rel_paths]
