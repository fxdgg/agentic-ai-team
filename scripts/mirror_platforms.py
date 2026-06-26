#!/usr/bin/env python3
"""L2 双平台镜像：`.claude/` ↔ `.codebuddy/` 的差异列表 + 单文件镜像工具。

Phase 3 设计原则（基于用户选择的方案 B）：
    - **不做全量自动镜像**（54 处真实差异中可能含正当独有内容，盲覆盖会丢失）
    - 工具到位 + 报告优先 + 单文件按需镜像 + 维护者控制方向
    - 豁免清单读取自 `meta/platform-divergence.yaml`

CLI:
    # 模式 1：列出所有差异 + 给出建议同步方向
    python scripts/mirror_platforms.py --status

    # 模式 2：单文件镜像（明确方向）
    python scripts/mirror_platforms.py --mirror=<rel-path> --from=claude --write
    python scripts/mirror_platforms.py --mirror=<rel-path> --from=codebuddy --write
    （rel-path 是相对 .claude/ 或 .codebuddy/ 的相对路径，如 commands/flow-run.md）

    # 模式 3：批量镜像（从清单文件读取）
    python scripts/mirror_platforms.py --batch=<file> --write
    （清单文件每行格式：`<from>:<rel-path>`，如 `claude:commands/flow-run.md`）

退出码：
    0 PASS（无未豁免差异，或镜像成功）
    1 WARN（dry-run 模式下存在差异）
    2 FAIL（写入失败）
    3 ERROR
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths, platform_mirror, reporters
from lib.reporters import Severity, Finding, CheckResult, Report


# ----------------------------------------------------------------------------
# 建议同步方向启发式判断
# ----------------------------------------------------------------------------

def _suggest_direction(rel: str) -> tuple[str, str]:
    """对一个 content-diff 文件给出建议同步方向。

    返回 (suggested_from, reason)。

    启发式（按优先级）：
        1. 比较 mtime — 较新的一边作为权威
        2. 比较 size — 较大的一边可能含更多内容（建议保留）
        3. 默认 .claude/ 优先（plan 中确定的默认权威源）
    """
    a = paths.CLAUDE_ROOT / rel
    b = paths.CODEBUDDY_ROOT / rel
    if not a.exists() or not b.exists():
        return ("claude" if a.exists() else "codebuddy", "仅一侧存在")

    sa = a.stat()
    sb = b.stat()

    # 1. mtime 差距 > 60 秒，取较新者
    if abs(sa.st_mtime - sb.st_mtime) > 60:
        if sa.st_mtime > sb.st_mtime:
            return ("claude", f".claude/ 较新（mtime 差 {int(sa.st_mtime - sb.st_mtime)}s）")
        return ("codebuddy", f".codebuddy/ 较新（mtime 差 {int(sb.st_mtime - sa.st_mtime)}s）")

    # 2. size 差距 > 200 字节，取较大者（可能含更多内容）
    size_diff = sa.st_size - sb.st_size
    if abs(size_diff) > 200:
        if size_diff > 0:
            return ("claude", f".claude/ 体量更大（多 {size_diff} 字节）")
        return ("codebuddy", f".codebuddy/ 体量更大（多 {-size_diff} 字节）")

    # 3. 默认 .claude/
    return ("claude", "默认权威方向（其他启发式无明显差异）")


# ----------------------------------------------------------------------------
# --status 模式：列差异 + 建议
# ----------------------------------------------------------------------------

def cmd_status(format_: str) -> int:
    mirror = platform_mirror.collect_mirror_report()
    report = Report(title="双平台镜像状态报告（Phase 3）")

    summary_check = CheckResult(
        check_id="mirror-summary",
        description="双平台对账总览（仅展示未豁免的差异）",
    )
    summary_check.findings.append(Finding(
        check_id=summary_check.check_id, severity=Severity.INFO,
        title=(
            f"豁免 {len(mirror.waived)} 项；"
            f"only-claude {len(mirror.only_claude)}，"
            f"only-codebuddy {len(mirror.only_codebuddy)}，"
            f"内容差异 {len(mirror.content_diff)}"
        ),
    ))
    report.checks.append(summary_check)

    # only-claude / only-codebuddy
    if mirror.only_claude or mirror.only_codebuddy:
        only_check = CheckResult(
            check_id="mirror-only-side",
            description="仅存在于一侧的文件（建议复制到另一侧 / 或登记到豁免清单）",
        )
        for rel in mirror.only_claude:
            only_check.findings.append(Finding(
                check_id=only_check.check_id, severity=Severity.WARN,
                title=f"仅 .claude/：{rel}",
                fix_hint=f"python3 scripts/mirror_platforms.py --mirror={rel} --from=claude --write",
            ))
        for rel in mirror.only_codebuddy:
            only_check.findings.append(Finding(
                check_id=only_check.check_id, severity=Severity.WARN,
                title=f"仅 .codebuddy/：{rel}",
                fix_hint=f"python3 scripts/mirror_platforms.py --mirror={rel} --from=codebuddy --write",
            ))
        report.checks.append(only_check)

    # 内容差异 + 建议方向
    if mirror.content_diff:
        diff_check = CheckResult(
            check_id="mirror-content-diff",
            description="双方都存在但内容不一致（带建议同步方向）",
        )
        for rel in mirror.content_diff:
            suggested, reason = _suggest_direction(rel)
            diff_check.findings.append(Finding(
                check_id=diff_check.check_id, severity=Severity.WARN,
                title=f"内容不一致：{rel}",
                message=f"建议方向：{suggested}（{reason}）",
                fix_hint=f"python3 scripts/mirror_platforms.py --mirror={rel} --from={suggested} --write",
            ))
        report.checks.append(diff_check)

    if not (mirror.only_claude or mirror.only_codebuddy or mirror.content_diff):
        summary_check.findings.append(Finding(
            check_id=summary_check.check_id, severity=Severity.PASS,
            title="✓ 双平台完全同步（不计豁免项）",
        ))

    report.summary = {
        "claude_only": len(mirror.only_claude),
        "codebuddy_only": len(mirror.only_codebuddy),
        "content_diff": len(mirror.content_diff),
        "waived": len(mirror.waived),
    }
    return reporters.emit(report, fmt=format_)


# ----------------------------------------------------------------------------
# --mirror 模式：单文件镜像
# ----------------------------------------------------------------------------

def cmd_mirror_one(rel: str, from_side: str, dry_run: bool, format_: str) -> int:
    if from_side not in ("claude", "codebuddy"):
        print(f"--from 必须是 claude 或 codebuddy，收到：{from_side}", file=sys.stderr)
        return 3

    src_root = paths.CLAUDE_ROOT if from_side == "claude" else paths.CODEBUDDY_ROOT
    dst_root = paths.CODEBUDDY_ROOT if from_side == "claude" else paths.CLAUDE_ROOT
    src = src_root / rel
    dst = dst_root / rel

    report = Report(title=f"镜像 {rel}（from {from_side}）")
    check = CheckResult(check_id="mirror-one", description=f"{from_side} → {'codebuddy' if from_side == 'claude' else 'claude'}")

    if not src.is_file():
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.FAIL,
            title=f"源文件不存在：{paths.to_relative(src)}",
        ))
        report.checks.append(check)
        return reporters.emit(report, fmt=format_)

    # 比较内容
    src_bytes = src.read_bytes()
    dst_exists = dst.is_file()
    dst_bytes = dst.read_bytes() if dst_exists else b""

    if src_bytes == dst_bytes:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.PASS,
            title="已同步，无需操作",
            file=f"{paths.to_relative(src)} ↔ {paths.to_relative(dst)}",
        ))
        report.checks.append(check)
        return reporters.emit(report, fmt=format_)

    # 摘要 diff
    src_size = len(src_bytes)
    dst_size = len(dst_bytes)
    delta = src_size - dst_size
    delta_str = f"+{delta}" if delta >= 0 else str(delta)

    if dry_run:
        check.findings.append(Finding(
            check_id=check.check_id, severity=Severity.WARN,
            title="[dry-run] 将覆盖目标",
            file=f"{paths.to_relative(src)}({src_size}) → {paths.to_relative(dst)}({dst_size})  Δ {delta_str}",
            fix_hint="加 --write 真正落盘",
        ))
        report.checks.append(check)
        return reporters.emit(report, fmt=format_)

    # 真正写入
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    check.findings.append(Finding(
        check_id=check.check_id, severity=Severity.PASS,
        title="已镜像写入",
        file=f"{paths.to_relative(src)} → {paths.to_relative(dst)}",
        message=f"源 {src_size} 字节，目标 {dst_size} → {src_size}（Δ {delta_str}）",
    ))
    report.checks.append(check)
    return reporters.emit(report, fmt=format_)


# ----------------------------------------------------------------------------
# --batch 模式：批量镜像
# ----------------------------------------------------------------------------

def cmd_batch(batch_file: Path, dry_run: bool, format_: str) -> int:
    if not batch_file.is_file():
        print(f"清单文件不存在：{batch_file}", file=sys.stderr)
        return 3

    report = Report(title=f"批量镜像：{paths.to_relative(batch_file)}")
    check = CheckResult(
        check_id="mirror-batch",
        description=f"按清单逐文件镜像（{'dry-run' if dry_run else 'write'}）",
    )

    for lineno, raw in enumerate(batch_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.WARN,
                title=f"清单第 {lineno} 行格式错误（应为 from:rel-path）：{line}",
            ))
            continue
        from_side, rel = line.split(":", 1)
        from_side = from_side.strip()
        rel = rel.strip()
        if from_side not in ("claude", "codebuddy"):
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.WARN,
                title=f"清单第 {lineno} 行 from 非法（应为 claude/codebuddy）：{from_side}",
            ))
            continue

        src_root = paths.CLAUDE_ROOT if from_side == "claude" else paths.CODEBUDDY_ROOT
        dst_root = paths.CODEBUDDY_ROOT if from_side == "claude" else paths.CLAUDE_ROOT
        src = src_root / rel
        dst = dst_root / rel

        if not src.is_file():
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.FAIL,
                title=f"源文件不存在：{paths.to_relative(src)}",
            ))
            continue

        src_bytes = src.read_bytes()
        dst_bytes = dst.read_bytes() if dst.is_file() else b""
        if src_bytes == dst_bytes:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.PASS,
                title=f"已同步：{rel}",
            ))
            continue

        if dry_run:
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.WARN,
                title=f"[dry-run] 待镜像：{rel} (from {from_side})",
            ))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            check.findings.append(Finding(
                check_id=check.check_id, severity=Severity.PASS,
                title=f"✓ 镜像：{rel} (from {from_side})",
            ))

    report.checks.append(check)
    return reporters.emit(report, fmt=format_)


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="mirror_platforms",
        description="双平台镜像工具（Phase 3）",
    )
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--status", action="store_true",
                     help="列出所有未豁免差异 + 建议同步方向")
    grp.add_argument("--mirror", metavar="REL-PATH",
                     help="单文件镜像（必须配合 --from）")
    grp.add_argument("--batch", metavar="FILE",
                     help="批量镜像（清单文件每行 from:rel-path）")
    ap.add_argument("--from", dest="from_side", choices=["claude", "codebuddy"],
                    help="--mirror 时指定权威源")
    ap.add_argument("--write", action="store_true",
                    help="真正落盘（默认 dry-run）")
    ap.add_argument("--format", default="console", choices=["console", "md", "json"])
    args = ap.parse_args(argv)

    if args.status:
        return cmd_status(args.format)
    if args.mirror:
        if not args.from_side:
            print("--mirror 必须配合 --from=claude|codebuddy", file=sys.stderr)
            return 3
        return cmd_mirror_one(args.mirror, args.from_side, dry_run=not args.write, format_=args.format)
    if args.batch:
        return cmd_batch(Path(args.batch).resolve(), dry_run=not args.write, format_=args.format)

    return 3


if __name__ == "__main__":
    sys.exit(main())
