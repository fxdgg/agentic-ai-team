#!/usr/bin/env python3
"""L1 渲染器：从 DSL / 现有 JSON Schema / Agent frontmatter 渲染 AUTO-GEN 区段。

Phase 1（当前阶段）—— 区段标记 + 保护模式：
    将 SKILL.md / ARCHITECTURE.md / README.md 中易漂移的 4 个核心表格用
    `<!-- BEGIN AUTO-GEN: ... hash=<sha256> --> ... <!-- END AUTO-GEN -->`
    包裹，原内容 byte-equal 保留作为初始 body。后续任何人工编辑这些区段
    都会触发一致性体检的 hash 校验告警，强制更新 hash 才能 commit 通过。

Phase 2（DSL 引入后）—— 完全渲染模式：
    渲染器会从 meta/*.yaml DSL 重新计算每个区段的 body，与现有 hash 对比，
    不一致时（DSL 改了 / 表格改了）自动重新渲染并更新 hash。

支持的区段：
    - skill-phases-table       SKILL.md §2.1 阶段定义表
    - skill-phase-rules-loader SKILL.md §10 阶段规则按需加载映射表
    - arch-phase-table         ARCHITECTURE.md §4.2 阶段全表
    - readme-commands-table    README.md 命令表

CLI：
    python scripts/render_artifacts.py            # 默认 dry-run，预览所有区段渲染状态
    python scripts/render_artifacts.py --write    # 真正落盘
    python scripts/render_artifacts.py --section=skill-phases-table --write
    python scripts/render_artifacts.py --check    # 仅 hash 校验，等同于体检维度 9

退出码：
    0 — 全部已同步 / 写入成功
    1 — 存在待同步区段（dry-run 模式）
    2 — 渲染冲突（区段 ID 重复 / 范围非法等硬错误）
    3 — 脚本错误
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths, autogen_block, reporters
from lib.reporters import Severity, Finding, CheckResult, Report


# ----------------------------------------------------------------------------
# 表格定位规则（基于稳定的标题锚点 + GFM 表格结构）
# ----------------------------------------------------------------------------

@dataclass
class TableLocation:
    """一个待区段化的表格的定位与渲染元数据。"""
    section_id: str
    file: Path
    heading_pattern: str          # 表格所在小节的 H 标题正则（用于定位）
    description: str              # 人类可读说明
    source_label: str             # 渲染来源（写入 BEGIN 注释的 source 字段）
    mirror: bool = True           # 双平台镜像：True 表示同时渲染 .codebuddy/ 对称文件

    def render_strategy_phase1(self) -> str:
        """Phase 1 统一为'保护模式'（仅锁定 hash）。"""
        return "protect"


def _expand_targets(loc: TableLocation) -> list[TableLocation]:
    """按 mirror 字段扩展为双平台目标列表。"""
    out = [loc]
    if not loc.mirror:
        return out
    side = paths.is_in_platform(loc.file)
    if side == "claude":
        mirror_path = paths.claude_to_codebuddy(loc.file)
        if mirror_path.exists():
            out.append(TableLocation(
                section_id=loc.section_id,
                file=mirror_path,
                heading_pattern=loc.heading_pattern,
                description=f"{loc.description}（.codebuddy/ 镜像）",
                source_label=loc.source_label,
                mirror=False,  # 防止递归扩展
            ))
    elif side == "codebuddy":
        mirror_path = paths.codebuddy_to_claude(loc.file)
        if mirror_path.exists():
            out.append(TableLocation(
                section_id=loc.section_id,
                file=mirror_path,
                heading_pattern=loc.heading_pattern,
                description=f"{loc.description}（.claude/ 镜像）",
                source_label=loc.source_label,
                mirror=False,
            ))
    return out


TABLES: list[TableLocation] = [
    TableLocation(
        section_id="skill-phases-table",
        file=paths.WF_SKILL_MD,
        heading_pattern=r"^###\s+2\.1\s+阶段定义",
        description="SKILL.md §2.1 阶段定义表",
        source_label="state-schema.json#PhaseId + 现状",
    ),
    TableLocation(
        section_id="skill-phase-rules-loader",
        file=paths.WF_SKILL_MD,
        heading_pattern=r"^##\s+10\.\s+阶段规则按需加载映射表",
        description="SKILL.md §10 阶段规则按需加载映射表",
        source_label="phases/*-rules.md 文件清单 + 现状",
    ),
    TableLocation(
        section_id="arch-phase-table",
        file=paths.ARCHITECTURE_MD,
        heading_pattern=r"^###\s+4\.2\s+阶段全表",
        description="ARCHITECTURE.md §4.2 阶段全表",
        source_label="state-schema.json#PhaseId + 现状",
        mirror=False,  # 仓库根文件，无双平台镜像
    ),
    TableLocation(
        section_id="readme-commands-table",
        file=paths.README_MD,
        heading_pattern=r"^##\s+可用命令",
        description="README.md 可用命令表",
        source_label="commands/*.md frontmatter + 现状",
        mirror=False,  # 仓库根文件，无双平台镜像
    ),
]


# ----------------------------------------------------------------------------
# 表格定位
# ----------------------------------------------------------------------------

_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def find_table_range(text: str, heading_pattern: str) -> tuple[int, int] | None:
    """在文件中找出指定标题下方紧邻的第一个表格。

    返回 1-based 闭区间 (start_line, end_line)，包含表头 / 分隔行 / 所有数据行。
    若找不到返回 None。

    解析规则：
        1. 找到匹配 heading_pattern 的行（必须以 # / ## / ### 开头）
        2. 该 heading 等级以下的下一个同级 / 更高级标题之前的范围内查找
        3. 找到第一个连续的 `| ... |` + `| ---- |` 表格块
    """
    lines = text.splitlines()
    pat = re.compile(heading_pattern)

    heading_idx = -1  # 0-based
    heading_level = 0
    for i, line in enumerate(lines):
        if pat.search(line):
            heading_idx = i
            m = re.match(r"^(#+)\s+", line)
            heading_level = len(m.group(1)) if m else 6
            break
    if heading_idx < 0:
        return None

    # 寻找下一个同级或更高级标题（即 #数 <= heading_level 的）作为搜索上界
    upper_bound = len(lines)
    for j in range(heading_idx + 1, len(lines)):
        m = re.match(r"^(#+)\s+", lines[j])
        if m and len(m.group(1)) <= heading_level:
            upper_bound = j
            break

    # 在 (heading_idx, upper_bound) 区间内寻找第一个 GFM 表格
    in_code = False
    i = heading_idx + 1
    while i < upper_bound:
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        if _TABLE_LINE_RE.match(line) and i + 1 < upper_bound and _TABLE_DIVIDER_RE.match(lines[i + 1]):
            start_line = i + 1            # 1-based 表头行
            j = i + 2
            while j < upper_bound and _TABLE_LINE_RE.match(lines[j]):
                j += 1
            end_line = j                  # 1-based 表格末尾行（j 此时是表格之后的第一行的 0-based 索引，转为 1-based 闭区间 = j）
            return (start_line, end_line)
        i += 1
    return None


# ----------------------------------------------------------------------------
# 渲染主流程
# ----------------------------------------------------------------------------

@dataclass
class RenderOutcome:
    section_id: str
    status: str                   # 'wrapped' / 'already-wrapped' / 'hash-mismatch' / 'not-found' / 'error'
    file: str
    message: str = ""
    fix_hint: str = ""


def process_table(loc: TableLocation, dry_run: bool, check_only: bool) -> RenderOutcome:
    """处理单个表格区段。

    流程：
        1. 检查文件中是否已有同 section_id 的 AUTO-GEN 区段
        2. 已有 → 校验 hash（check_only 模式只做这一步）；hash 不一致则报告
        3. 未有 → 定位表格范围 → 调用 wrap_lines_in_file 首次区段化
    """
    if not loc.file.exists():
        return RenderOutcome(loc.section_id, "error", str(loc.file), "文件不存在")

    text = loc.file.read_text(encoding="utf-8")
    try:
        existing_blocks = autogen_block.find_blocks(text)
    except ValueError as e:
        return RenderOutcome(
            loc.section_id, "error", paths.to_relative(loc.file),
            f"AUTO-GEN 区段格式错误：{e}",
        )

    target = next((b for b in existing_blocks if b.section_id == loc.section_id), None)

    # Case A: 已包裹 — 仅校验 hash
    if target is not None:
        valid = target.is_hash_valid()
        if valid is False:
            return RenderOutcome(
                loc.section_id, "hash-mismatch", paths.to_relative(loc.file),
                message=f"声明 hash={target.declared_hash}  实际={target.computed_hash()}",
                fix_hint=f"运行 python3 scripts/render_artifacts.py --section={loc.section_id} --write",
            )
        if valid is None:
            return RenderOutcome(
                loc.section_id, "hash-missing", paths.to_relative(loc.file),
                message="区段 BEGIN 注释未声明 hash",
                fix_hint=f"运行 python3 scripts/render_artifacts.py --section={loc.section_id} --write 自动补 hash",
            )
        return RenderOutcome(
            loc.section_id, "already-wrapped", paths.to_relative(loc.file),
            f"hash 校验通过：{target.declared_hash}",
        )

    # Case B: 未包裹 — check_only 模式仅报告，不写入
    if check_only:
        return RenderOutcome(
            loc.section_id, "not-wrapped", paths.to_relative(loc.file),
            message="尚未添加 AUTO-GEN 区段标记",
            fix_hint=f"运行 python3 scripts/render_artifacts.py --section={loc.section_id} --write",
        )

    # 定位表格范围
    rng = find_table_range(text, loc.heading_pattern)
    if rng is None:
        return RenderOutcome(
            loc.section_id, "not-found", paths.to_relative(loc.file),
            f"未在 {loc.heading_pattern} 标题下找到 GFM 表格",
        )
    start_line, end_line = rng

    if dry_run:
        return RenderOutcome(
            loc.section_id, "wrap-pending", paths.to_relative(loc.file),
            message=f"将在行 {start_line}-{end_line} 外层包裹 AUTO-GEN 标记",
            fix_hint="加 --write 落盘",
        )

    # 真正包裹
    changed, err = autogen_block.wrap_lines_in_file(
        loc.file,
        section_id=loc.section_id,
        start_line=start_line,
        end_line=end_line,
        source=loc.source_label,
        dry_run=False,
    )
    if err:
        return RenderOutcome(
            loc.section_id, "error", paths.to_relative(loc.file),
            f"wrap 失败：{err}",
        )
    return RenderOutcome(
        loc.section_id, "wrapped", paths.to_relative(loc.file),
        f"已在行 {start_line}-{end_line} 包裹 AUTO-GEN 标记",
    )


def re_render_existing_block(loc: TableLocation) -> RenderOutcome:
    """对已存在的 AUTO-GEN 区段重新计算 hash 并写回（修复 hash 失配 / 缺失）。"""
    text = loc.file.read_text(encoding="utf-8")
    try:
        blocks = autogen_block.find_blocks(text)
    except ValueError as e:
        return RenderOutcome(loc.section_id, "error", paths.to_relative(loc.file), str(e))
    target = next((b for b in blocks if b.section_id == loc.section_id), None)
    if target is None:
        return RenderOutcome(
            loc.section_id, "not-wrapped", paths.to_relative(loc.file),
            "区段不存在；请先用 --write 首次区段化",
        )
    # body 内容保留现状，仅重算 hash 写回
    body_text = target.body_text
    changed, err = autogen_block.replace_block_in_file(
        loc.file,
        section_id=loc.section_id,
        new_body=body_text,
        source=loc.source_label,
    )
    if err:
        return RenderOutcome(loc.section_id, "error", paths.to_relative(loc.file), err)
    return RenderOutcome(
        loc.section_id, "rerendered", paths.to_relative(loc.file),
        "已重算 hash 写回",
    )


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def build_report(outcomes: list[RenderOutcome]) -> Report:
    report = Report(title="AUTO-GEN 区段渲染报告（Phase 1：保护模式）")

    sev_map = {
        "wrapped": Severity.PASS,
        "rerendered": Severity.PASS,
        "already-wrapped": Severity.PASS,
        "wrap-pending": Severity.WARN,
        "not-wrapped": Severity.WARN,
        "hash-mismatch": Severity.FAIL,
        "hash-missing": Severity.WARN,
        "not-found": Severity.FAIL,
        "error": Severity.ERROR,
    }

    grouped: dict[str, CheckResult] = {}
    for o in outcomes:
        check_id = "render"
        check = grouped.setdefault(check_id, CheckResult(
            check_id=check_id,
            description="所有目标区段的状态",
        ))
        sev = sev_map.get(o.status, Severity.INFO)
        check.findings.append(Finding(
            check_id=o.section_id,
            severity=sev,
            title=f"[{o.status}] {o.section_id}",
            file=o.file,
            message=o.message,
            fix_hint=o.fix_hint,
        ))

    for c in grouped.values():
        report.checks.append(c)

    counts = {s.value: 0 for s in Severity}
    for o in outcomes:
        counts[sev_map.get(o.status, Severity.INFO).value] += 1
    report.summary = {
        "tables": len(outcomes),
        **{f"status:{k}": sum(1 for o in outcomes if o.status == k) for k in
           ("wrapped", "rerendered", "already-wrapped", "wrap-pending",
            "not-wrapped", "hash-mismatch", "hash-missing", "not-found", "error")
           if any(o.status == k for o in outcomes)},
    }
    return report


# ---------------------------------------------------------------------------
# Phase 2.5：--write-json 模式（DSL → JSON 编译器）
# ---------------------------------------------------------------------------

def _canonical_json_dumps(data) -> str:
    """JSON 序列化的 canonical 形式：indent=2 / 保序 / 中文不转义 / 末尾换行。"""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _run_write_json_mode(do_write: bool, fmt: str) -> int:
    """从 meta/*.yaml DSL 编译产出 state-schema.json + phase-transitions.json 双平台 4 份文件。

    步骤：
        1. 加载 meta/phases.yaml + meta/state-schema.yaml
        2. 调用 validate_meta.compile_phases_to_transitions / compile_state_schema 编译
        3. canonical JSON 序列化
        4. 写入 .claude/skills/.../references/ + .codebuddy/skills/.../references/ 共 4 个文件
        5. 默认 dry-run（do_write=False），输出 diff 摘要

    退出码：
        0 — 全部成功（或 dry-run 显示无变化）
        1 — dry-run 显示有待写入差异
        2 — 编译失败 / 写入失败
        3 — DSL 文件缺失
    """
    try:
        import validate_meta
        from lib import meta_loader
    except ImportError as e:
        print(f"[ERROR] 模块导入失败：{e}", file=sys.stderr)
        return 3

    phases_meta = meta_loader.load_phases_meta()
    state_meta = meta_loader.load_state_schema_meta()

    if phases_meta is None:
        print(f"[ERROR] meta/phases.yaml 不存在", file=sys.stderr)
        return 3
    if state_meta is None:
        print(f"[ERROR] meta/state-schema.yaml 不存在", file=sys.stderr)
        return 3

    # 编译 DSL → JSON 对象（含 $generatedFrom / $doNotEdit sentinel）
    try:
        compiled_phases = validate_meta.compile_phases_to_transitions(phases_meta)
        compiled_state = validate_meta.compile_state_schema(state_meta)
    except Exception as e:
        print(f"[ERROR] 编译失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 2

    # 序列化为 canonical JSON
    phases_json_text = _canonical_json_dumps(compiled_phases)
    state_json_text = _canonical_json_dumps(compiled_state)

    # 4 个目标文件
    wf_rel = "skills/workflow-orchestrator/references"
    targets = [
        ("phase-transitions.json", paths.CLAUDE_ROOT / wf_rel / "phase-transitions.json", phases_json_text),
        ("phase-transitions.json", paths.CODEBUDDY_ROOT / wf_rel / "phase-transitions.json", phases_json_text),
        ("state-schema.json",      paths.CLAUDE_ROOT / wf_rel / "state-schema.json",      state_json_text),
        ("state-schema.json",      paths.CODEBUDDY_ROOT / wf_rel / "state-schema.json",   state_json_text),
    ]

    changes: list[dict] = []
    for label, path, new_text in targets:
        rel = paths.to_relative(path)
        if not path.parent.is_dir():
            changes.append({"file": str(rel), "status": "skip-no-parent",
                            "message": f"父目录不存在：{path.parent}"})
            continue
        if path.is_file():
            current = path.read_text(encoding="utf-8")
            if current == new_text:
                changes.append({"file": str(rel), "status": "unchanged"})
                continue
            # 计算 size 差作为简易 diff 摘要
            changes.append({"file": str(rel), "status": "needs-update",
                            "message": f"size: {len(current)} → {len(new_text)} bytes"})
        else:
            changes.append({"file": str(rel), "status": "needs-create",
                            "message": f"将创建新文件，{len(new_text)} bytes"})

        if do_write:
            try:
                path.write_text(new_text, encoding="utf-8")
                changes[-1]["status"] = "written"
            except Exception as e:
                changes[-1]["status"] = "write-error"
                changes[-1]["message"] = f"{type(e).__name__}: {e}"

    # 输出报告
    if fmt == "json":
        print(json.dumps({"mode": "write-json", "do_write": do_write, "changes": changes},
                         indent=2, ensure_ascii=False))
    else:
        header = "✓ 写入完成" if do_write else "ℹ Dry-run（加 --write 落盘）"
        print(f"━━━ render_artifacts --write-json（Phase 2.5） ━━━\n")
        print(f"  {header}\n")
        for c in changes:
            print(f"  [{c['status']:14s}] {c['file']}"
                  + (f"   {c.get('message','')}" if c.get("message") else ""))
        print()

    # 退出码
    has_pending = any(c["status"] in ("needs-update", "needs-create") for c in changes)
    has_error = any(c["status"] in ("write-error", "skip-no-parent") for c in changes)
    if has_error:
        return 2
    if has_pending and not do_write:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="render_artifacts",
        description="AUTO-GEN 区段渲染器（Phase 1：保护模式）+ DSL→JSON 编译器（Phase 2.5：--write-json）",
    )
    ap.add_argument("--section",
                    help=f"仅处理指定区段（{', '.join(t.section_id for t in TABLES)}）")
    ap.add_argument("--write", action="store_true",
                    help="真正落盘（默认 dry-run，仅预览）")
    ap.add_argument("--check", action="store_true",
                    help="仅校验 hash + 区段存在性（不修改文件）")
    ap.add_argument("--rerender", action="store_true",
                    help="对已存在但 hash 失配的区段重新计算 hash 写回（需 --write）")
    ap.add_argument("--write-json", action="store_true", dest="write_json",
                    help="Phase 2.5：从 meta/*.yaml DSL 编译产出 state-schema.json + phase-transitions.json，"
                         "注入 $generatedFrom + $doNotEdit sentinel 并同步到双平台。"
                         "默认 dry-run，加 --write 才落盘。")
    ap.add_argument("--format", default="console", choices=["console", "md", "json"])
    args = ap.parse_args(argv)

    # ---- 分支 1：--write-json（Phase 2.5 引入，与 AUTO-GEN 区段渲染独立） ----
    if args.write_json:
        return _run_write_json_mode(do_write=args.write, fmt=args.format)

    # ---- 分支 2：AUTO-GEN 区段渲染（原 Phase 1 逻辑） ----
    targets = TABLES
    if args.section:
        targets = [t for t in TABLES if t.section_id == args.section]
        if not targets:
            print(f"未知区段：{args.section}", file=sys.stderr)
            return 3

    # 双平台镜像扩展：每个 TableLocation 自动展开为 .claude/ + .codebuddy/ 两份
    expanded: list[TableLocation] = []
    for t in targets:
        expanded.extend(_expand_targets(t))
    targets = expanded

    outcomes: list[RenderOutcome] = []
    for loc in targets:
        if args.rerender:
            if not args.write:
                outcomes.append(RenderOutcome(
                    loc.section_id, "wrap-pending", paths.to_relative(loc.file),
                    message="--rerender 需要配合 --write 使用",
                ))
                continue
            outcomes.append(re_render_existing_block(loc))
        else:
            outcomes.append(process_table(
                loc,
                dry_run=not args.write,
                check_only=args.check,
            ))

    report = build_report(outcomes)
    return reporters.emit(report, fmt=args.format)


if __name__ == "__main__":
    sys.exit(main())
