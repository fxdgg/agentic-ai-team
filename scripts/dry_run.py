#!/usr/bin/env python3
"""L5 dry-run：**仅校验状态机骨架**（图遍历），不模拟业务路径。

⚠️ **明确不做的**（plan v2 显式声明）：
    - 不模拟 IntentGate 5 类意图分支
    - 不模拟 D2C 双模式（PRD 优先 / 设计优先）
    - 不模拟三级降级（Agent Teams / Task Pipeline / Single Agent）
    业务路径模拟登记在 ARCHITECTURE 附录 C 「Phase 4 候选项清单」，按需启动。

✅ **本脚本实际做的**（图遍历级自检）：
    1. 从 INIT 出发遍历所有合法流转路径（含 canSkipTo），输出每条路径经过的阶段
    2. 检查每个阶段的 "调用阶段为 X 的 Agent" 是否存在文件
    3. 检查 state-schema.json 中所有 $ref 引用是否可解析
    4. 报告未被任何流转涉及的"孤儿阶段"
    5. 检查图无环、可达 DONE

价值定位：状态机骨架自洽性快速回归（< 100ms）。业务路径正确性靠真实跑 `/flow-run` 验证。

用法：
    python scripts/dry_run.py [--format=console|md|json] [--max-paths=N]

退出码：
    0 — 全部通过
    1 — 有 WARN
    2 — 存在 FAIL
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths, md_parser, reporters
from lib.reporters import Severity, Finding, CheckResult, Report


def _load_phase_transitions() -> tuple[dict, list[str]]:
    pt = json.loads(paths.PHASE_TRANSITIONS.read_text(encoding="utf-8"))
    ss = json.loads(paths.STATE_SCHEMA.read_text(encoding="utf-8"))
    phase_ids = ss["definitions"]["PhaseId"]["enum"]
    return pt, phase_ids


# ----------------------------------------------------------------------------
# 路径枚举
# ----------------------------------------------------------------------------

def enumerate_paths(transitions: dict, start: str = "INIT", max_paths: int = 50) -> list[list[str]]:
    """枚举从 start 出发的所有简单路径（不重复访问阶段）。

    包含 next 与 canSkipTo 两条分支。返回的每条路径是阶段 ID 列表。
    """
    paths_out: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        if len(paths_out) >= max_paths:
            return
        rule = transitions["transitions"].get(node, {})
        nxt = rule.get("next")
        skip = rule.get("canSkipTo")
        children = [c for c in (nxt, skip) if c]
        if not children:
            paths_out.append(list(path))
            return
        for c in children:
            if c in path:
                # 检测到环，记录当前路径并终止
                paths_out.append(list(path) + [f"<cycle:{c}>"])
                continue
            dfs(c, path + [c])

    dfs(start, [start])
    return paths_out


# ----------------------------------------------------------------------------
# Agent ↔ 阶段对账
# ----------------------------------------------------------------------------

def _collect_agent_phase_map() -> dict:
    """读取所有 agents/*.md 的 quote-block frontmatter「调用阶段」，返回 阶段 → [agent 文件] 映射。

    鲁棒识别：在原文中匹配所有 PhaseId 枚举值（精确大写边界匹配），允许描述性句子。
    """
    # 懒加载 PhaseId 枚举
    ss = json.loads(paths.STATE_SCHEMA.read_text(encoding="utf-8"))
    phase_ids = ss["definitions"]["PhaseId"]["enum"]

    mp: dict = {}
    if not paths.WF_AGENTS.is_dir():
        return mp
    for p in paths.WF_AGENTS.rglob("*.md"):
        rel = p.relative_to(paths.WF_AGENTS).as_posix()
        try:
            fm = md_parser.parse_file_quote_frontmatter(p)
        except Exception:
            continue
        phase_val = fm.fields.get("调用阶段") or fm.fields.get("调用-阶段")
        if not phase_val:
            continue
        for pid in phase_ids:
            if re.search(rf"\b{pid}\b", phase_val):
                mp.setdefault(pid, []).append(rel)
    return mp


# ----------------------------------------------------------------------------
# $ref 解析校验
# ----------------------------------------------------------------------------

def check_state_schema_refs(schema: dict) -> list[Finding]:
    """检查 state-schema.json 中所有 $ref 引用是否可解析。"""
    findings: list[Finding] = []

    def resolve(ref: str) -> bool:
        # 仅支持本文件内部 #/definitions/X 形式
        if not ref.startswith("#/"):
            return False
        node: object = schema
        for part in ref[2:].split("/"):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return False
        return True

    def walk(obj, path: str = "$") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "$ref" and isinstance(v, str):
                    if not resolve(v):
                        findings.append(Finding(
                            check_id="dry-run.schema-refs",
                            severity=Severity.FAIL,
                            title=f"无法解析 $ref: '{v}'",
                            file=str(paths.to_relative(paths.STATE_SCHEMA)),
                            message=f"位置：{path}",
                        ))
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(schema)
    return findings


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------

def run(max_paths: int = 50) -> Report:
    report = Report(title="ai-team 工作流 dry-run 报告")

    try:
        transitions, phase_ids = _load_phase_transitions()
    except Exception as e:
        c = CheckResult(check_id="dry-run.load", description="加载 schema")
        c.findings.append(Finding(
            check_id=c.check_id, severity=Severity.ERROR,
            title=f"加载失败：{e}",
        ))
        report.checks.append(c)
        return report

    # 1. 流转路径枚举
    path_check = CheckResult(
        check_id="dry-run.paths",
        description=f"从 INIT 出发的合法流转路径（最多展示 {max_paths} 条）",
    )
    paths_enum = enumerate_paths(transitions, max_paths=max_paths)
    reached_done = [p for p in paths_enum if p and p[-1] == "DONE"]
    cyclic = [p for p in paths_enum if any(s.startswith("<cycle:") for s in p)]
    dead_end = [p for p in paths_enum if p and not p[-1].startswith("<cycle:") and p[-1] != "DONE"]

    for p in paths_enum[:10]:
        path_check.findings.append(Finding(
            check_id=path_check.check_id, severity=Severity.INFO,
            title=" → ".join(p),
        ))
    if len(paths_enum) > 10:
        path_check.findings.append(Finding(
            check_id=path_check.check_id, severity=Severity.INFO,
            title=f"...省略 {len(paths_enum) - 10} 条",
        ))
    if cyclic:
        for cp in cyclic:
            path_check.findings.append(Finding(
                check_id=path_check.check_id, severity=Severity.FAIL,
                title="检测到流转环",
                message=" → ".join(cp),
            ))
    if dead_end:
        for de in dead_end:
            path_check.findings.append(Finding(
                check_id=path_check.check_id, severity=Severity.FAIL,
                title=f"流转路径在 '{de[-1]}' 处终止但不是 DONE",
                message=" → ".join(de),
            ))
    if not reached_done:
        path_check.findings.append(Finding(
            check_id=path_check.check_id, severity=Severity.FAIL,
            title="所有枚举路径均未到达 DONE",
        ))
    report.checks.append(path_check)

    # 2. 孤儿阶段
    orphan_check = CheckResult(
        check_id="dry-run.orphan-phases",
        description="孤儿阶段（PhaseId 中存在但任何路径都不经过）",
    )
    reachable: set[str] = set()
    for p in paths_enum:
        for s in p:
            if not s.startswith("<cycle:"):
                reachable.add(s)
    orphans = [pid for pid in phase_ids if pid not in reachable]
    for o in orphans:
        orphan_check.findings.append(Finding(
            check_id=orphan_check.check_id, severity=Severity.FAIL,
            title=f"孤儿阶段：'{o}'",
            file=str(paths.to_relative(paths.PHASE_TRANSITIONS)),
            fix_hint="检查 transitions 是否漏配 next 指向该阶段",
        ))
    if not orphans:
        orphan_check.findings.append(Finding(
            check_id=orphan_check.check_id, severity=Severity.PASS,
            title=f"所有 {len(phase_ids)} 个阶段均可被流转覆盖",
        ))
    report.checks.append(orphan_check)

    # 3. 每个阶段至少绑定一个 Agent（INIT / CLARIFY_* / DONE 除外）
    agent_check = CheckResult(
        check_id="dry-run.agent-binding",
        description="每个阶段至少绑定一个 Agent 实现（不含 CLARIFY_* / INIT / DONE）",
    )
    NO_AGENT_PHASES = {"INIT", "DONE"}
    phase_agent = _collect_agent_phase_map()
    for pid in phase_ids:
        if pid in NO_AGENT_PHASES or pid.startswith("CLARIFY_"):
            continue
        agents = phase_agent.get(pid, [])
        if not agents:
            agent_check.findings.append(Finding(
                check_id=agent_check.check_id, severity=Severity.WARN,
                title=f"阶段 '{pid}' 未找到声明「调用阶段: {pid}」的 Agent 文件",
                fix_hint="在 agents/*.md 的 frontmatter 声明该阶段，或确认通过团队成员声明",
            ))
        else:
            agent_check.findings.append(Finding(
                check_id=agent_check.check_id, severity=Severity.PASS,
                title=f"阶段 '{pid}' 绑定 {len(agents)} 个 Agent",
                message="\n".join(f"- {a}" for a in agents),
            ))
    report.checks.append(agent_check)

    # 4. state-schema $ref 解析
    schema_obj = json.loads(paths.STATE_SCHEMA.read_text(encoding="utf-8"))
    ref_check = CheckResult(
        check_id="dry-run.schema-refs",
        description="state-schema.json 内部 $ref 引用解析",
    )
    ref_findings = check_state_schema_refs(schema_obj)
    if ref_findings:
        ref_check.findings.extend(ref_findings)
    else:
        ref_check.findings.append(Finding(
            check_id=ref_check.check_id, severity=Severity.PASS,
            title="所有 $ref 引用均可解析",
        ))
    report.checks.append(ref_check)

    report.summary = {
        "phase_count": len(phase_ids),
        "enumerated_paths": len(paths_enum),
        "paths_to_done": len(reached_done),
        "cyclic_paths": len(cyclic),
        "dead_end_paths": len(dead_end),
        "orphan_phases": len(orphans),
    }

    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="dry_run",
        description="ai-team 工作流 dry-run（Phase 0 基础版）",
    )
    ap.add_argument("--format", default="console", choices=["console", "md", "json"])
    ap.add_argument("--max-paths", type=int, default=50,
                    help="路径枚举上限（防止指数爆炸）")
    args = ap.parse_args(argv)
    report = run(max_paths=args.max_paths)
    return reporters.emit(report, fmt=args.format)


if __name__ == "__main__":
    sys.exit(main())
