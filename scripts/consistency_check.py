#!/usr/bin/env python3
"""L3 一致性体检：扫描整个 ai-team 引擎仓库的 10 个漂移维度。

用法：
    python scripts/consistency_check.py [选项]

选项：
    --scope all|phases|agents|platforms|docs|state-schema|autogen
            指定体检范围，默认 all
    --format console|md|json
            输出格式，默认 console
    --fail-on warn|fail
            退出码门槛：warn 表示 WARN 及以上视为失败（>=1），fail 表示仅 FAIL/ERROR 视为失败（>=2）
            默认 fail

退出码：
    0 PASS · 1 WARN · 2 FAIL · 3 ERROR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 允许直接执行：scripts/consistency_check.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths, md_parser, autogen_block, platform_mirror, reporters
from lib.reporters import Severity, Finding, CheckResult, Report


# ----------------------------------------------------------------------------
# 加载基础数据（懒加载 + 缓存）
# ----------------------------------------------------------------------------

class Context:
    """单次体检的上下文（缓存所有重复 IO）。"""

    def __init__(self) -> None:
        self._state_schema: dict | None = None
        self._phase_trans: dict | None = None
        self._skill_md_text: str | None = None
        self._architecture_md_text: str | None = None
        self._readme_md_text: str | None = None
        self._claude_md_text: str | None = None
        self._codebuddy_md_text: str | None = None

    @property
    def state_schema(self) -> dict:
        if self._state_schema is None:
            self._state_schema = json.loads(paths.STATE_SCHEMA.read_text(encoding="utf-8"))
        return self._state_schema

    @property
    def phase_trans(self) -> dict:
        if self._phase_trans is None:
            self._phase_trans = json.loads(paths.PHASE_TRANSITIONS.read_text(encoding="utf-8"))
        return self._phase_trans

    @property
    def skill_md(self) -> str:
        if self._skill_md_text is None:
            self._skill_md_text = paths.WF_SKILL_MD.read_text(encoding="utf-8")
        return self._skill_md_text

    @property
    def architecture_md(self) -> str:
        if self._architecture_md_text is None:
            self._architecture_md_text = paths.ARCHITECTURE_MD.read_text(encoding="utf-8")
        return self._architecture_md_text

    @property
    def readme_md(self) -> str:
        if self._readme_md_text is None:
            self._readme_md_text = paths.README_MD.read_text(encoding="utf-8")
        return self._readme_md_text

    @property
    def claude_md(self) -> str:
        if self._claude_md_text is None:
            self._claude_md_text = paths.CLAUDE_MD.read_text(encoding="utf-8")
        return self._claude_md_text

    @property
    def codebuddy_md(self) -> str:
        if self._codebuddy_md_text is None:
            self._codebuddy_md_text = paths.CODEBUDDY_MD.read_text(encoding="utf-8")
        return self._codebuddy_md_text


# ----------------------------------------------------------------------------
# 维度 1：阶段流转闭环
# ----------------------------------------------------------------------------

def check_phase_flow_closure(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="phase-flow-closure",
        description="阶段流转闭环：INIT 可达 DONE，所有 next/canSkipTo 指向的阶段在 PhaseId 枚举内",
    )
    transitions = ctx.phase_trans["transitions"]
    phase_ids = set(ctx.state_schema["definitions"]["PhaseId"]["enum"])

    # 1.1 所有 next / canSkipTo 必须在 PhaseId 内
    for phase, rule in transitions.items():
        if phase not in phase_ids:
            check.findings.append(Finding(
                check_id=check.check_id,
                severity=Severity.FAIL,
                title=f"transitions key '{phase}' 不在 PhaseId 枚举内",
                file=str(paths.to_relative(paths.PHASE_TRANSITIONS)),
                fix_hint="将该 key 添加到 state-schema.json#definitions.PhaseId.enum 或修正拼写",
            ))
        for slot in ("next", "canSkipTo"):
            v = rule.get(slot)
            if v is None:
                continue
            if v not in phase_ids:
                check.findings.append(Finding(
                    check_id=check.check_id,
                    severity=Severity.FAIL,
                    title=f"{phase}.{slot} = '{v}' 不在 PhaseId 枚举内",
                    file=str(paths.to_relative(paths.PHASE_TRANSITIONS)),
                    fix_hint="检查 PhaseId enum 或修正阶段名拼写",
                ))

    # 1.2 INIT → DONE 可达性
    visited: set[str] = set()
    stack = ["INIT"]
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        rule = transitions.get(cur, {})
        for slot in ("next", "canSkipTo"):
            v = rule.get(slot)
            if v and v not in visited:
                stack.append(v)
    if "DONE" not in visited:
        check.findings.append(Finding(
            check_id=check.check_id,
            severity=Severity.FAIL,
            title="从 INIT 出发不可达 DONE",
            message=f"已访问阶段集：{sorted(visited)}",
            fix_hint="补全 transitions 链路使 DONE 可达",
        ))

    # 1.3 所有 PhaseId 都应有 transitions 条目
    for pid in phase_ids:
        if pid not in transitions:
            check.findings.append(Finding(
                check_id=check.check_id,
                severity=Severity.FAIL,
                title=f"PhaseId '{pid}' 在 transitions 中未声明",
                file=str(paths.to_relative(paths.PHASE_TRANSITIONS)),
                fix_hint=f"添加 \"{pid}\": {{ \"next\": ..., \"canSkipTo\": ... }}",
            ))

    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title=f"流转闭环正常（共 {len(phase_ids)} 阶段，全部可达 DONE）",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 2：PhaseId 枚举一致性（state-schema vs phase-transitions）
# ----------------------------------------------------------------------------

def check_phase_id_enum_sync(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="phase-id-enum-sync",
        description="PhaseId 枚举一致性：state-schema.json 与 phase-transitions.json 键集合一致",
    )
    schema_ids = set(ctx.state_schema["definitions"]["PhaseId"]["enum"])
    trans_keys = set(ctx.phase_trans["transitions"].keys())
    only_schema = schema_ids - trans_keys
    only_trans = trans_keys - schema_ids
    for pid in sorted(only_schema):
        check.findings.append(Finding(
            check_id=check.check_id,
            severity=Severity.FAIL,
            title=f"PhaseId '{pid}' 在 state-schema 但不在 phase-transitions",
            file=str(paths.to_relative(paths.PHASE_TRANSITIONS)),
            fix_hint=f"添加 \"{pid}\": {{ \"next\": null, \"canSkipTo\": null }}",
        ))
    for pid in sorted(only_trans):
        check.findings.append(Finding(
            check_id=check.check_id,
            severity=Severity.FAIL,
            title=f"PhaseId '{pid}' 在 phase-transitions 但不在 state-schema enum",
            file=str(paths.to_relative(paths.STATE_SCHEMA)),
            fix_hint="将该 ID 加入 definitions.PhaseId.enum",
        ))
    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title=f"两个 JSON 文件的 PhaseId 集合完全一致（{len(schema_ids)} 项）",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 3：SKILL.md §2.1 阶段表对齐
# ----------------------------------------------------------------------------

PHASE_TABLE_HEADING_PAT = r"^###\s+2\.1\s+阶段定义"


def check_skill_phase_table(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="skill-phase-table",
        description="SKILL.md §2.1 阶段表中阶段 ID 与 PhaseId 枚举一致",
    )
    table = md_parser.find_table_under_heading(ctx.skill_md, PHASE_TABLE_HEADING_PAT)
    if table is None:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title="未找到 SKILL.md §2.1 阶段定义表",
            file=str(paths.to_relative(paths.WF_SKILL_MD)),
            fix_hint="确认 §2.1 标题与表格存在",
        ))
        return check

    # 表格的"阶段 ID"列可能叫 "阶段 ID" 或 "Phase ID" 或第二列
    col_name = None
    for candidate in ("阶段 ID", "阶段ID", "Phase ID", "PhaseId"):
        if table.has_column(candidate):
            col_name = candidate
            break
    if col_name is None and len(table.headers) >= 2:
        # 退化策略：取第二列（按现有表结构 "# | 阶段 ID | 名称 | ..."）
        col_name = table.headers[1]

    if col_name is None:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title="无法识别 §2.1 表的阶段 ID 列",
            file=str(paths.to_relative(paths.WF_SKILL_MD)),
            line=table.start_line,
        ))
        return check

    ids_in_table_raw = table.column(col_name)
    # 单元格内可能含反引号
    ids_in_table = [re.sub(r"[`*]", "", v).strip() for v in ids_in_table_raw if v.strip()]
    ids_in_schema = ctx.state_schema["definitions"]["PhaseId"]["enum"]

    in_table = set(ids_in_table)
    in_schema = set(ids_in_schema)
    only_table = in_table - in_schema
    only_schema = in_schema - in_table

    for pid in sorted(only_table):
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"SKILL.md §2.1 中的阶段 '{pid}' 不在 state-schema PhaseId 枚举",
            file=str(paths.to_relative(paths.WF_SKILL_MD)),
            line=table.start_line,
            fix_hint="修正阶段 ID 拼写或同步到 PhaseId enum",
        ))
    for pid in sorted(only_schema):
        # DONE 阶段在原 §2.1 表中是 "DONE | 已完成 | 无 | 终态"，应该存在；缺失则报错
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"PhaseId enum 中的 '{pid}' 缺失于 SKILL.md §2.1 表",
            file=str(paths.to_relative(paths.WF_SKILL_MD)),
            line=table.start_line,
            fix_hint="在 §2.1 表添加对应行",
        ))

    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title=f"SKILL.md §2.1 阶段表与 PhaseId 枚举一致（{len(in_table)} 项）",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 4：Agent 注册完备（SKILL.md §3 ↔ agents/*.md ↔ phases/*-rules.md）
# ----------------------------------------------------------------------------

AGENT_REGISTRY_HEADING_PAT = r"^##\s+3\.\s+子\s*Agent\s*注册表"


def _collect_agent_files() -> list[Path]:
    """收集所有 agents/*.md 与 agents/{team}/*.md。"""
    out: list[Path] = []
    if not paths.WF_AGENTS.is_dir():
        return out
    for p in paths.WF_AGENTS.rglob("*.md"):
        out.append(p)
    return sorted(out)


def check_agent_registry(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="agent-registry",
        description="Agent 注册完备：SKILL.md §3 ↔ agents/*.md 文件 三方对账",
    )

    # A. 从 SKILL.md §3 表抽取声明的 Agent 文件路径
    table = md_parser.find_table_under_heading(ctx.skill_md, AGENT_REGISTRY_HEADING_PAT)
    declared_files: set[str] = set()
    if table is None:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title="未找到 SKILL.md §3 子 Agent 注册表",
            file=str(paths.to_relative(paths.WF_SKILL_MD)),
        ))
    else:
        # 第一列通常是 "Agent 文件"，单元格形如 "`agents/foo.md`"
        col_name = None
        for cand in ("Agent 文件", "Agent文件", "文件"):
            if table.has_column(cand):
                col_name = cand
                break
        if col_name is None and table.headers:
            col_name = table.headers[0]
        if col_name:
            for cell in table.column(col_name):
                m = re.search(r"`?(agents/[^`\s|]+\.md)`?", cell)
                if m:
                    declared_files.add(m.group(1))

    # B. 实际存在的 Agent 文件
    actual_files: set[str] = set()
    for p in _collect_agent_files():
        rel = p.relative_to(paths.WF_CLAUDE).as_posix()
        actual_files.add(rel)

    only_declared = declared_files - actual_files
    only_actual = actual_files - declared_files

    for f in sorted(only_declared):
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"SKILL.md §3 声明的 Agent 文件不存在：{f}",
            file=str(paths.to_relative(paths.WF_SKILL_MD)),
            fix_hint=f"创建文件 .claude/skills/workflow-orchestrator/{f} 或从 §3 表删除该行",
        ))
    for f in sorted(only_actual):
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title=f"存在 Agent 文件但 SKILL.md §3 未注册：{f}",
            file=str(paths.to_relative(paths.WF_CLAUDE / f)),
            fix_hint="在 SKILL.md §3 注册表追加一行，或确认此文件是否为非 Agent 文档（如 README）",
        ))

    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title=f"Agent 注册表与实际文件一致（{len(actual_files)} 项）",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 5：双平台对称
# ----------------------------------------------------------------------------

def check_platform_symmetry(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="platform-symmetry",
        description="双平台对称：.claude/ ↔ .codebuddy/ 文件树与内容一致（豁免清单除外）",
    )
    mirror = platform_mirror.collect_mirror_report()

    for rel in mirror.only_claude:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"仅 .claude/ 存在，缺失 .codebuddy/ 对称文件",
            file=f".claude/{rel}",
            fix_hint=f"cp .claude/{rel} .codebuddy/{rel} 或在 platform-divergence 豁免清单登记",
        ))
    for rel in mirror.only_codebuddy:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"仅 .codebuddy/ 存在，缺失 .claude/ 对称文件",
            file=f".codebuddy/{rel}",
            fix_hint=f"cp .codebuddy/{rel} .claude/{rel} 或在 platform-divergence 豁免清单登记",
        ))
    for rel in mirror.content_diff:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"双平台内容不一致",
            file=f".claude/{rel}  ≠  .codebuddy/{rel}",
            fix_hint="检查 sha256 差异，决定以哪边为准后同步另一边",
        ))

    summary = (
        f"豁免 {len(mirror.waived)} 项；"
        f"only-claude {len(mirror.only_claude)}，"
        f"only-codebuddy {len(mirror.only_codebuddy)}，"
        f"内容差异 {len(mirror.content_diff)}"
    )
    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title=f"双平台镜像一致（{summary}）",
        ))
    else:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.INFO,
            title=f"统计：{summary}",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 6：ARCHITECTURE 章节与 JSON Schema / SKILL 表同步（轻量校验）
# ----------------------------------------------------------------------------

def check_architecture_sync(ctx: Context) -> CheckResult:
    """轻量校验：ARCHITECTURE.md §4.2 / §8.1 表是否能定位且行数合理。

    Phase 0 仅做"存在性 + 阶段数 / 字段数" 抽查，深度对账留给 Phase 1 AUTO-GEN 区段 hash。
    """
    check = CheckResult(
        check_id="architecture-sync",
        description="ARCHITECTURE.md 关键表格存在性与体量抽查",
    )
    txt = ctx.architecture_md

    # §4.2 阶段全表
    table_42 = md_parser.find_table_under_heading(txt, r"^###\s+4\.2\s+阶段全表")
    if table_42 is None:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title="未找到 ARCHITECTURE §4.2 阶段全表",
            file="ARCHITECTURE.md",
        ))
    else:
        # 阶段数应等于 PhaseId 枚举大小（含 DONE 行）
        expected = len(ctx.state_schema["definitions"]["PhaseId"]["enum"])
        actual = len(table_42.rows)
        # 容忍 ±1（DONE 行可能合并 / 拆开）
        if abs(expected - actual) > 1:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.WARN,
                title=f"§4.2 阶段全表行数 {actual} 与 PhaseId 数 {expected} 差异较大",
                file="ARCHITECTURE.md",
                line=table_42.start_line,
                fix_hint="对照 PhaseId enum 增删行",
            ))

    # §8.1 顶层字段总览
    table_81 = md_parser.find_table_under_heading(txt, r"^###\s+8\.1\s+顶层字段总览")
    if table_81 is None:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title="未找到 ARCHITECTURE §8.1 顶层字段总览",
            file="ARCHITECTURE.md",
        ))

    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="ARCHITECTURE 关键表格存在",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 7：CLAUDE.md ↔ CODEBUDDY.md 100% 一致
# ----------------------------------------------------------------------------

def check_collab_docs_identical(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="collab-docs-identical",
        description="CLAUDE.md ↔ CODEBUDDY.md 必须 100% 一致",
    )
    a = ctx.claude_md
    b = ctx.codebuddy_md
    if a == b:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="两份文件 byte-equal",
        ))
        return check

    # 找出第一处差异行
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    first_diff = -1
    for i in range(min(len(a_lines), len(b_lines))):
        if a_lines[i] != b_lines[i]:
            first_diff = i + 1
            break
    if first_diff < 0:
        first_diff = min(len(a_lines), len(b_lines)) + 1

    check.findings.append(Finding(
        check_id=check.check_id, severity=Severity.FAIL,
        title="CLAUDE.md 与 CODEBUDDY.md 内容不一致",
        file="CLAUDE.md",
        line=first_diff,
        message=f"行数 CLAUDE.md={len(a_lines)} CODEBUDDY.md={len(b_lines)}；首处差异在行 {first_diff}",
        fix_hint="决定以哪份为权威，再将另一份 cp 覆盖",
    ))
    return check


# ----------------------------------------------------------------------------
# 维度 8：state-schema.json 字段命名 camelCase
# ----------------------------------------------------------------------------

CAMEL_OK_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
SNAKE_LIKE_RE = re.compile(r"_")

# 已知合法但非 camelCase 的字段（如验证维度代号 B1/B2/B3a/B3b）
NAMING_WAIVED_FIELDS: set[str] = {
    "B1", "B2", "B2.5", "B3a", "B3b",       # BUILD_VERIFY 验证维度代号
}


def check_state_schema_naming(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="state-schema-naming",
        description="state-schema.json 所有 properties 键为 camelCase（杜绝 auto_commit 蛇形漂移）",
    )

    def walk(obj, path: str = "$") -> None:
        if isinstance(obj, dict):
            props = obj.get("properties")
            if isinstance(props, dict):
                for k, v in props.items():
                    full = f"{path}.{k}"
                    if k in NAMING_WAIVED_FIELDS:
                        pass
                    elif SNAKE_LIKE_RE.search(k):
                        check.findings.append(Finding(
                            check_id=check.check_id, severity=Severity.FAIL,
                            title=f"字段 '{full}' 含下划线（疑似蛇形）",
                            file=str(paths.to_relative(paths.STATE_SCHEMA)),
                            fix_hint=f"重命名为 camelCase（如 {to_camel(k)}）",
                        ))
                    elif not CAMEL_OK_RE.match(k):
                        # 容忍少量大写开头（如类型名作 key）的情况，但 properties 内通常都是小驼峰
                        check.findings.append(Finding(
                            check_id=check.check_id, severity=Severity.WARN,
                            title=f"字段 '{full}' 非标准 camelCase",
                            file=str(paths.to_relative(paths.STATE_SCHEMA)),
                        ))
                    walk(v, full)
            # 同时下钻 items / definitions / 其他字典字段
            for k, v in obj.items():
                if k == "properties":
                    continue
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(ctx.state_schema)

    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="state-schema 所有字段命名符合 camelCase",
        ))
    return check


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ----------------------------------------------------------------------------
# 维度 9：AUTO-GEN 区段 hash（Phase 1 启用，Phase 0 仅扫描存在性）
# ----------------------------------------------------------------------------

AUTOGEN_SCOPE_FILES = [
    paths.WF_SKILL_MD,
    paths.ARCHITECTURE_MD,
    paths.README_MD,
]


def check_autogen_blocks(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="autogen-blocks",
        description="AUTO-GEN 区段格式与 hash 校验（Phase 1 起强制）",
    )
    total = 0
    invalid = 0
    for f in AUTOGEN_SCOPE_FILES:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        try:
            blocks = autogen_block.find_blocks(text)
        except ValueError as e:
            invalid += 1
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.FAIL,
                title=f"区段格式错误：{e}",
                file=str(paths.to_relative(f)),
            ))
            continue
        for b in blocks:
            total += 1
            valid = b.is_hash_valid()
            if valid is False:
                check.findings.append(Finding(
                    check_id=check.check_id, severity=Severity.FAIL,
                    title=f"区段 '{b.section_id}' hash 与声明不符",
                    file=str(paths.to_relative(f)),
                    line=b.begin_line,
                    message=f"声明={b.declared_hash}  实际={b.computed_hash()}",
                    fix_hint="区段内容被人工修改但未更新 hash；运行 render_artifacts.py 重新渲染",
                ))
            elif valid is None and b.section_id:
                check.findings.append(Finding(
                    check_id=check.check_id, severity=Severity.WARN,
                    title=f"区段 '{b.section_id}' 未声明 hash",
                    file=str(paths.to_relative(f)),
                    line=b.begin_line,
                    fix_hint="可在 BEGIN 注释中添加 hash=<sha256> 字段",
                ))

    if total == 0:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.INFO,
            title="未发现 AUTO-GEN 区段（Phase 1 之后会逐步引入）",
        ))
    elif not any(f.severity in (Severity.FAIL, Severity.WARN) for f in check.findings):
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title=f"全部 {total} 个 AUTO-GEN 区段 hash 校验通过",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 10：Agent 文件 quote-block frontmatter 含「调用阶段」
# ----------------------------------------------------------------------------

# 已知的非 Agent 文件（豁免）
AGENT_FILE_WHITELIST_SKIP = {
    "agents/README.md",
}


def check_agent_frontmatter(ctx: Context) -> CheckResult:
    check = CheckResult(
        check_id="agent-frontmatter",
        description="agents/*.md 含 quote-block frontmatter 且声明「调用阶段」",
    )
    phase_ids = set(ctx.state_schema["definitions"]["PhaseId"]["enum"])
    # 允许的非阶段 keyword（如 knowledge-import 命令、平台后缀等）
    NON_PHASE_KEYWORDS = {
        "knowledge-import",
        "/flow-import",
        "web", "miniprogram", "backend",
    }

    for p in _collect_agent_files():
        rel = p.relative_to(paths.WF_CLAUDE).as_posix()
        if rel in AGENT_FILE_WHITELIST_SKIP:
            continue
        try:
            fm = md_parser.parse_file_quote_frontmatter(p)
        except Exception as e:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.ERROR,
                title=f"解析 frontmatter 失败：{e}",
                file=str(paths.to_relative(p)),
            ))
            continue

        # 查找「调用阶段」字段（key 已经归一化为小写 + dash）
        phase_val = None
        for key in ("调用阶段", "调用-阶段"):
            if key in fm.fields:
                phase_val = fm.fields[key]
                break

        if not phase_val:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.WARN,
                title="缺少 quote-block frontmatter 字段「调用阶段」",
                file=str(paths.to_relative(p)),
                fix_hint="在文件开头添加 `> **调用阶段**: ANALYSE_PRODUCT` 等",
            ))
            continue

        # 鲁棒识别策略：在原文中搜索任一 PhaseId 枚举值（精确大写匹配）
        # 这样可以同时支持简单值（"ANALYSE_PRODUCT"）、组合值（"ANALYSE_PRODUCT, ANALYSE_TECH"）
        # 以及描述性句子（"由 archiver §17.5 在 ARCHIVE 阶段末尾委派调用"）
        found_phases = [pid for pid in phase_ids if re.search(rf"\b{pid}\b", phase_val)]
        # 同时识别允许的关键词（避免句子里没有 PhaseId 但是已知模式如 knowledge-import）
        found_keywords = [kw for kw in NON_PHASE_KEYWORDS if kw in phase_val]

        if not found_phases and not found_keywords:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.WARN,
                title="frontmatter「调用阶段」未识别到任一 PhaseId",
                file=str(paths.to_relative(p)),
                message=f"原值：{phase_val}",
                fix_hint="确保值中包含至少一个合法的 PhaseId 枚举值（如 ANALYSE_PRODUCT）",
            ))

    if not check.findings:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="所有 Agent frontmatter 的「调用阶段」字段合法",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 11：DSL（meta/）与现有 JSON 等价性（Phase 2 引入）
# ----------------------------------------------------------------------------

def check_dsl_equivalence(ctx: Context) -> CheckResult:
    """委托给 validate_meta.py 的核心逻辑：DSL ↔ JSON 对象树等价。

    DSL 文件不存在时返回 INFO（向后兼容：Phase 2 之前的状态）。
    """
    check = CheckResult(
        check_id="dsl-equivalence",
        description="meta/ DSL ↔ 现有 JSON 对象树等价（Phase 2 起启用）",
    )

    try:
        from lib import meta_loader
        meta = meta_loader.load_all()
    except ImportError as e:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title=f"meta_loader 不可用：{e}",
            fix_hint="pip install -r scripts/requirements.txt",
        ))
        return check
    except Exception as e:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.ERROR,
            title=f"加载 meta/*.yaml 异常：{type(e).__name__}: {e}",
        ))
        return check

    # DSL 全部缺失 → INFO（Phase 2 未启用）
    if all(meta[k] is None for k in ("phases", "state_schema", "commands")):
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.INFO,
            title="meta/ 目录无 DSL 文件（Phase 2 之前为正常状态）",
        ))
        return check

    # 调用 validate_meta 的等价性校验
    try:
        import validate_meta
    except ImportError as e:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.ERROR,
            title=f"validate_meta 模块不可用：{e}",
        ))
        return check

    failures = 0
    for fn in (validate_meta.check_phases_equivalence, validate_meta.check_state_schema_equivalence):
        sub = fn(meta)
        for f in sub.findings:
            if f.severity in (Severity.PASS, Severity.INFO):
                continue
            failures += 1
            check.findings.append(Finding(
                check_id=check.check_id,
                severity=f.severity,
                title=f.title,
                file=f.file,
                line=f.line,
                message=f.message,
                fix_hint=f.fix_hint or "运行 python3 scripts/validate_meta.py 查看详情",
            ))

    if failures == 0:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="DSL 与现有 JSON 对象树完全等价",
        ))
    return check


# ----------------------------------------------------------------------------
# 维度 12：DSL 来源声明 sentinel（Phase 2.5 引入）
# ----------------------------------------------------------------------------

# 期望含 sentinel 的 JSON 文件清单（相对仓库根的逻辑名 → 期望的 $generatedFrom 值）
_DSL_SOURCE_MARKER_TARGETS = [
    # (相对路径生成函数, 期望的 generatedFrom 值)
    ("references/state-schema.json", "meta/state-schema.yaml"),
    ("references/phase-transitions.json", "meta/phases.yaml"),
]


def check_dsl_source_marker(ctx: Context) -> CheckResult:
    """检查 state-schema.json / phase-transitions.json 双平台头部含 ``$generatedFrom`` sentinel。

    sentinel 字段说明该 JSON 由 ``meta/*.yaml`` DSL 编译产出（Phase 2.5 引入），
    任何手工编辑应改 DSL 后跑 ``render_artifacts.py --write-json --write`` 重生成。

    严重程度策略：
        - 缺失 ``$generatedFrom`` → WARN（向后兼容，给 v1 仓库渐进迁移空间）
        - ``$generatedFrom`` 值与期望不一致 → FAIL（说明声明指向错误的 DSL 源）
    """
    check = CheckResult(
        check_id="dsl-source-marker",
        description="state-schema.json / phase-transitions.json 头部含 $generatedFrom sentinel（Phase 2.5 起启用）",
    )

    # 检查双平台 4 个 JSON 文件
    wf_rel = "skills/workflow-orchestrator"
    bases = [
        ("claude", paths.CLAUDE_ROOT / wf_rel),
        ("codebuddy", paths.CODEBUDDY_ROOT / wf_rel),
    ]

    any_finding = False
    for platform, base in bases:
        for rel, expected_source in _DSL_SOURCE_MARKER_TARGETS:
            jp = base / rel
            if not jp.is_file():
                continue
            try:
                data = json.loads(jp.read_text(encoding="utf-8"))
            except Exception as e:
                any_finding = True
                check.findings.append(Finding(
                    check_id=check.check_id, severity=Severity.ERROR,
                    title=f"无法解析 JSON：{type(e).__name__}",
                    file=str(paths.to_relative(jp)),
                ))
                continue

            actual = data.get("$generatedFrom") if isinstance(data, dict) else None
            if actual is None:
                any_finding = True
                check.findings.append(Finding(
                    check_id=check.check_id, severity=Severity.WARN,
                    title=f"缺 $generatedFrom（{platform}）",
                    file=str(paths.to_relative(jp)),
                    fix_hint=f"运行 python3 scripts/render_artifacts.py --write-json --write 注入 sentinel（期望值：{expected_source}）",
                ))
            elif actual != expected_source:
                any_finding = True
                check.findings.append(Finding(
                    check_id=check.check_id, severity=Severity.FAIL,
                    title=f"$generatedFrom 值错误（{platform}）",
                    file=str(paths.to_relative(jp)),
                    message=f"实际：{actual}；期望：{expected_source}",
                    fix_hint="改正 $generatedFrom 字段或重跑 render_artifacts.py --write-json --write",
                ))

    if not any_finding:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="所有目标 JSON 文件均含正确的 $generatedFrom sentinel",
        ))
    return check


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------

DIMENSIONS = {
    "phase-flow-closure": (check_phase_flow_closure, "phases"),
    "phase-id-enum-sync": (check_phase_id_enum_sync, "phases"),
    "skill-phase-table": (check_skill_phase_table, "phases"),
    "agent-registry": (check_agent_registry, "agents"),
    "agent-frontmatter": (check_agent_frontmatter, "agents"),
    "platform-symmetry": (check_platform_symmetry, "platforms"),
    "architecture-sync": (check_architecture_sync, "docs"),
    "collab-docs-identical": (check_collab_docs_identical, "docs"),
    "state-schema-naming": (check_state_schema_naming, "state-schema"),
    "autogen-blocks": (check_autogen_blocks, "autogen"),
    "dsl-equivalence": (check_dsl_equivalence, "dsl"),
    "dsl-source-marker": (check_dsl_source_marker, "dsl"),
}

SCOPE_ALIASES = {"all", "phases", "agents", "platforms", "docs", "state-schema", "autogen", "dsl"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="consistency_check",
        description="ai-team 引擎仓库一致性体检（10 维度）",
    )
    ap.add_argument("--scope", default="all",
                    help=f"体检范围：{'|'.join(sorted(SCOPE_ALIASES))}")
    ap.add_argument("--format", default="console", choices=["console", "md", "json"])
    ap.add_argument("--fail-on", default="fail", choices=["warn", "fail"])
    args = ap.parse_args(argv)

    if args.scope not in SCOPE_ALIASES:
        print(f"未知 scope: {args.scope}", file=sys.stderr)
        return 3

    ctx = Context()
    report = Report(title="ai-team 一致性体检报告")

    for check_id, (func, group) in DIMENSIONS.items():
        if args.scope != "all" and args.scope != group:
            continue
        try:
            result = func(ctx)
        except Exception as e:
            result = CheckResult(check_id=check_id, description=f"({group})")
            result.findings.append(Finding(
                check_id=check_id, severity=Severity.ERROR,
                title=f"维度执行异常：{type(e).__name__}",
                message=str(e),
            ))
        report.checks.append(result)

    report.summary = {
        "repo_root": str(paths.REPO_ROOT),
        "checked_dimensions": len(report.checks),
        "scope": args.scope,
    }

    exit_code = reporters.emit(report, fmt=args.format)
    if args.fail_on == "warn" and exit_code in (0, 1):
        return exit_code
    if args.fail_on == "fail" and exit_code == 1:
        # 用户希望 WARN 不算失败
        return 0
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
