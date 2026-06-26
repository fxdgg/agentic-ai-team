#!/usr/bin/env python3
"""L4 影响分析：输入改动文件列表，输出待同步目标 + 已同步状态。

用法：
    python scripts/impact_analyzer.py --changed=<file1>,<file2>
    python scripts/impact_analyzer.py --git-staged
    python scripts/impact_analyzer.py --git-diff=HEAD~1

退出码：
    0 — 所有目标已同步 / 无影响
    1 — 存在待同步目标
    2 — 改动文件无法分类
    3 — 脚本错误
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths, dependency_graph, reporters, platform_mirror
from lib.reporters import Severity, Finding, CheckResult, Report
from lib.dependency_graph import FileImpact, TargetSpec, ChangeType


# ----------------------------------------------------------------------------
# 改动来源
# ----------------------------------------------------------------------------

def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(paths.REPO_ROOT), *args],
            capture_output=True, text=True, check=True,
        )
        return out.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git 调用失败: {e.stderr}") from e


def collect_changed_from_git_staged() -> list[str]:
    out = _git("diff", "--cached", "--name-only")
    return [l.strip() for l in out.splitlines() if l.strip()]


def collect_changed_from_git_diff(ref: str) -> list[str]:
    out = _git("diff", "--name-only", ref)
    return [l.strip() for l in out.splitlines() if l.strip()]


def collect_changed_from_git_status() -> list[str]:
    """从 git status --porcelain 收集（含 untracked）。"""
    out = _git("status", "--porcelain")
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # 形如 " M path" 或 "?? path" 或 "R  old -> new"
        status = line[:2]
        rest = line[3:].strip()
        if status.strip() == "R":
            # rename，取新名
            if "->" in rest:
                rest = rest.split("->", 1)[1].strip()
        files.append(rest)
    return files


# ----------------------------------------------------------------------------
# 同步状态判定
# ----------------------------------------------------------------------------

def _file_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    import hashlib
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def check_platform_mirror_sync(impact: FileImpact) -> Severity:
    """判定双平台镜像目标是否已同步。"""
    if impact.platform_mirror is None:
        return Severity.PASS

    src_rel = impact.file
    dst_rel = impact.platform_mirror.path

    src_abs = paths.REPO_ROOT / src_rel
    dst_abs = paths.REPO_ROOT / dst_rel

    sha_src = _file_sha(src_abs)
    sha_dst = _file_sha(dst_abs)

    if sha_src is None and sha_dst is None:
        return Severity.PASS
    if sha_src != sha_dst:
        return Severity.WARN
    return Severity.PASS


def build_report(impacts: list[FileImpact]) -> Report:
    report = Report(title="影响范围分析报告")

    overall_check = CheckResult(
        check_id="impact-summary",
        description="本次改动的影响范围与同步状态",
    )

    if not impacts:
        overall_check.findings.append(Finding(
            check_id=overall_check.check_id, severity=Severity.INFO,
            title="无改动文件，无需同步",
        ))
        report.checks.append(overall_check)
        report.summary = {"changed_files": 0}
        return report

    # 改动文件列表
    overall_check.findings.append(Finding(
        check_id=overall_check.check_id, severity=Severity.INFO,
        title=f"改动文件 {len(impacts)} 个",
        message="\n".join(f"- {i.file}  [{i.change_type}]" for i in impacts),
    ))

    # 双平台镜像同步状态
    mirror_check = CheckResult(
        check_id="platform-mirror",
        description="双平台镜像同步状态",
    )
    mirror_pairs = 0
    for impact in impacts:
        if impact.platform_mirror is None:
            continue
        mirror_pairs += 1
        sev = check_platform_mirror_sync(impact)
        if sev == Severity.PASS:
            mirror_check.findings.append(Finding(
                check_id=mirror_check.check_id, severity=Severity.PASS,
                title=f"已同步：{impact.file} ↔ {impact.platform_mirror.path}",
            ))
        else:
            mirror_check.findings.append(Finding(
                check_id=mirror_check.check_id, severity=sev,
                title=f"待同步：{impact.file} → {impact.platform_mirror.path}",
                fix_hint=(
                    f"cp {paths.REPO_ROOT / impact.file} "
                    f"{paths.REPO_ROOT / impact.platform_mirror.path}"
                    if not impact.file.endswith(".md") or "CLAUDE" in impact.file or "CODEBUDDY" in impact.file
                    else f"diff {impact.file} {impact.platform_mirror.path}  # 然后人工同步"
                ),
            ))
    if mirror_pairs == 0:
        mirror_check.findings.append(Finding(
            check_id=mirror_check.check_id, severity=Severity.INFO,
            title="本次改动不涉及双平台镜像",
        ))

    # 文档 / 章节同步目标
    doc_check = CheckResult(
        check_id="doc-sync",
        description="文档章节同步目标",
    )
    has_doc_target = False
    appendix_a_needed = False
    for impact in impacts:
        for tgt in impact.targets:
            has_doc_target = True
            if tgt.kind == "appendix-a":
                appendix_a_needed = True
                continue
            sev = Severity.WARN  # 文档目标无法机器判定是否已同步，统一标 WARN
            section_part = f" — {tgt.section}" if tgt.section else ""
            doc_check.findings.append(Finding(
                check_id=doc_check.check_id, severity=sev,
                title=f"需同步：{tgt.path}{section_part}",
                message=f"触发来源：{impact.file}（{impact.change_type}）",
                fix_hint=tgt.note or "对照变更内容更新该章节",
            ))

    if appendix_a_needed:
        doc_check.findings.append(Finding(
            check_id=doc_check.check_id, severity=Severity.WARN,
            title="必须追加 ARCHITECTURE.md 附录 A 更新日志",
            file="ARCHITECTURE.md",
            fix_hint="追加 ### YYYY-MM-DD — 主题，含背景 / 变更 / 影响面 / 关联文件",
        ))

    if not has_doc_target and not appendix_a_needed:
        doc_check.findings.append(Finding(
            check_id=doc_check.check_id, severity=Severity.INFO,
            title="本次改动无需更新 ARCHITECTURE / README",
        ))

    # 无法分类的改动
    unclassified = [i.file for i in impacts if i.change_type == ChangeType.OTHER]
    if unclassified:
        overall_check.findings.append(Finding(
            check_id=overall_check.check_id, severity=Severity.WARN,
            title=f"{len(unclassified)} 个文件无法分类为已知变更类型",
            message="\n".join(f"- {f}" for f in unclassified),
            fix_hint="如属于已知类型请扩展 lib/dependency_graph.py 的 PATH_PATTERNS",
        ))

    report.checks.append(overall_check)
    report.checks.append(mirror_check)
    report.checks.append(doc_check)

    report.summary = {
        "changed_files": len(impacts),
        "mirror_pairs": mirror_pairs,
        "doc_sync_targets": sum(
            1 for i in impacts for _ in i.targets
        ),
    }

    return report


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="impact_analyzer",
        description="ai-team 引擎仓库影响范围分析",
    )
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--changed",
                     help="逗号分隔的改动文件相对路径列表")
    grp.add_argument("--git-staged", action="store_true",
                     help="使用 git diff --cached 获取改动")
    grp.add_argument("--git-diff", metavar="REF",
                     help="使用 git diff <REF> 获取改动")
    grp.add_argument("--git-status", action="store_true",
                     help="使用 git status --porcelain 获取改动（含未跟踪）")
    ap.add_argument("--format", default="console", choices=["console", "md", "json"])

    args = ap.parse_args(argv)

    try:
        if args.changed:
            files = [f.strip() for f in args.changed.split(",") if f.strip()]
        elif args.git_staged:
            files = collect_changed_from_git_staged()
        elif args.git_diff:
            files = collect_changed_from_git_diff(args.git_diff)
        elif args.git_status:
            files = collect_changed_from_git_status()
        else:
            # 默认 git status
            files = collect_changed_from_git_status()
    except RuntimeError as e:
        print(f"获取改动失败：{e}", file=sys.stderr)
        return 3

    impacts = dependency_graph.analyze_changes(files)
    report = build_report(impacts)
    exit_code = reporters.emit(report, fmt=args.format)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
