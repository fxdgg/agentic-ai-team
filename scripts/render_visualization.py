#!/usr/bin/env python3
"""工作流可视化主脚本。

从 meta/*.yaml + .codebuddy/skills/workflow-orchestrator/{phases,agents,rules,templates,
references} + SKILL.md + consistency_check 快照编译为单文件 HTML（docs/workflow-visualization.html）。

CLI 风格对齐 scripts/render_artifacts.py：
    python scripts/render_visualization.py            # dry-run（不写盘，输出统计）
    python scripts/render_visualization.py --write    # 写盘到 docs/workflow-visualization.html
    python scripts/render_visualization.py --check    # 校验现有产物（不写盘）
    python scripts/render_visualization.py --format=json   # JSON 输出（reporters 协议）

退出码：
    0 — PASS / 全部已同步
    1 — WARN（可生成但有 INFO/WARN，如无 commit / 体检快照不可用）
    2 — FAIL（dry-run 检测到产物落后或 --check 校验失败）
    3 — ERROR（脚本内部异常）

承诺三段式声明（见 plan.md 实施要点）：
    硬承诺：
        - 单文件 HTML / 零外部依赖 / 数据 inline / 7 Tab 锚点齐全
        - CLI 退出码协议与 render_artifacts.py 对齐
        - --write 幂等：相同输入产生相同输出（除生成时间戳）
    软承诺：
        - 生成耗时 < 3s（< 100 个文件全量加载）
        - --check 模式仅做产物存在性 + 关键锚点校验，不重新加载数据源对比
    不承诺：
        - 不增量生成 / 不缓存中间结果（每次全量）
        - 不集成 git LFS / 不优化 HTML 大小（gzip 后 ~ 200KB 已可接受）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import paths, visualization_data, html_renderer
from lib.reporters import (
    Severity, Finding, CheckResult, Report, emit,
)


OUTPUT_PATH = paths.REPO_ROOT / "docs" / "workflow-visualization.html"


# ============================================================================
# 主流程
# ============================================================================

def _required_anchors(html: str) -> list[str]:
    """已生成 HTML 必须含的关键锚点（用于 --check 校验）。"""
    required = [
        '<!DOCTYPE html>',
        'id="__DATA__"',
    ]
    for tab in ["phases", "agents", "rules", "templates", "references", "skill", "health"]:
        required.append(f'data-tab="{tab}"')
    missing = [a for a in required if a not in html]
    return missing


def build_report(action: str, write_result: dict | None = None) -> Report:
    """构造报告：
       action ∈ {"dry-run", "write", "check"}
       write_result 含：{"target_path", "size", "phases_n", "agents_n", "rules_n",
                          "templates_n", "references_n", "phase_rules_n", "consistency",
                          "issues"}
    """
    report = Report(title="workflow-visualization")

    # 1) 数据加载情况
    data_check = CheckResult(check_id="data-load",
                             description="meta/ + .codebuddy/.../{phases,agents,rules,...} 全量加载")
    if write_result:
        wr = write_result
        if wr["phases_n"] == 0:
            data_check.findings.append(Finding(
                check_id="data-load.no-phases",
                severity=Severity.FAIL,
                title="未加载到任何 phases",
                fix_hint="检查 meta/phases.yaml 是否存在且格式正确",
            ))
        else:
            data_check.findings.append(Finding(
                check_id="data-load.phases",
                severity=Severity.PASS,
                title=f"phases={wr['phases_n']} / agents={wr['agents_n']} / "
                      f"rules={wr['rules_n']} / templates={wr['templates_n']} / "
                      f"references={wr['references_n']} / phase_rules={wr['phase_rules_n']}",
            ))
        for issue in wr.get("issues") or []:
            data_check.findings.append(Finding(
                check_id="data-load.issue",
                severity=Severity.WARN,
                title=issue,
            ))
        cs = wr.get("consistency", {})
        if cs.get("available"):
            counts = cs.get("counts", {})
            data_check.findings.append(Finding(
                check_id="data-load.consistency",
                severity=Severity.PASS if counts.get("FAIL", 0) == 0 else Severity.INFO,
                title=f"体检快照已嵌入：PASS={counts.get('PASS', 0)} "
                      f"WARN={counts.get('WARN', 0)} FAIL={counts.get('FAIL', 0)}",
            ))
        else:
            data_check.findings.append(Finding(
                check_id="data-load.consistency",
                severity=Severity.WARN,
                title=f"体检快照不可用：{cs.get('reason', 'unknown')}",
            ))
    report.checks.append(data_check)

    # 2) 产物状态
    artifact_check = CheckResult(check_id="artifact",
                                 description=f"产物 {paths.to_relative(OUTPUT_PATH)} 状态")
    if action == "dry-run":
        if OUTPUT_PATH.is_file():
            artifact_check.findings.append(Finding(
                check_id="artifact.exists",
                severity=Severity.INFO,
                title=f"产物已存在 ({OUTPUT_PATH.stat().st_size // 1024} KB)，"
                      f"未重新写盘（使用 --write 强制重新生成）",
            ))
        else:
            artifact_check.findings.append(Finding(
                check_id="artifact.missing",
                severity=Severity.INFO,
                title="产物尚未生成（dry-run 不写盘）",
                fix_hint="python3 scripts/render_visualization.py --write",
            ))
    elif action == "write":
        if write_result and write_result.get("target_path"):
            artifact_check.findings.append(Finding(
                check_id="artifact.written",
                severity=Severity.PASS,
                title=f"产物已写入 ({write_result['size'] // 1024} KB)",
                file=paths.to_relative(write_result["target_path"]),
            ))
        else:
            artifact_check.findings.append(Finding(
                check_id="artifact.write-failed",
                severity=Severity.ERROR,
                title="写盘异常",
            ))
    elif action == "check":
        if not OUTPUT_PATH.is_file():
            artifact_check.findings.append(Finding(
                check_id="artifact.missing",
                severity=Severity.FAIL,
                title="产物不存在，无法校验",
                fix_hint="python3 scripts/render_visualization.py --write",
            ))
        else:
            html_text = OUTPUT_PATH.read_text(encoding="utf-8")
            missing = _required_anchors(html_text)
            if missing:
                for a in missing:
                    artifact_check.findings.append(Finding(
                        check_id="artifact.missing-anchor",
                        severity=Severity.FAIL,
                        title=f"缺少锚点：{a}",
                        fix_hint="重新生成：python3 scripts/render_visualization.py --write",
                    ))
            else:
                artifact_check.findings.append(Finding(
                    check_id="artifact.anchors-ok",
                    severity=Severity.PASS,
                    title=f"产物 {len(html_text) // 1024} KB，所有关键锚点齐全",
                ))
    report.checks.append(artifact_check)

    # 摘要
    if write_result:
        report.summary = {
            "phases": write_result["phases_n"],
            "agents": write_result["agents_n"],
            "rules": write_result["rules_n"],
            "templates": write_result["templates_n"],
            "references": write_result["references_n"],
            "phase_rules": write_result["phase_rules_n"],
            "output": paths.to_relative(OUTPUT_PATH),
            "action": action,
        }
    else:
        report.summary = {"action": action, "output": paths.to_relative(OUTPUT_PATH)}

    return report


def do_render(write: bool, include_consistency: bool = True) -> dict:
    """核心：加载数据 → 渲染 HTML → 写盘（可选）。"""
    data = visualization_data.load_visualization_data(
        paths.REPO_ROOT,
        include_consistency=include_consistency,
    )
    html = html_renderer.render_html(data)

    result = {
        "phases_n": len(data["phases"]),
        "agents_n": len(data["agents"]),
        "rules_n": len(data["rules"]),
        "templates_n": len(data["templates"]),
        "references_n": len(data["references"]),
        "phase_rules_n": len(data["phase_rules"]),
        "consistency": data["consistency"],
        "issues": data["meta"].get("issues", []),
        "size": len(html.encode("utf-8")),
    }

    if write:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(html, encoding="utf-8")
        result["target_path"] = OUTPUT_PATH

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="生成工作流可视化 HTML")
    ap.add_argument("--write", action="store_true", help="写盘到 docs/workflow-visualization.html")
    ap.add_argument("--check", action="store_true", help="仅校验现有产物，不写盘")
    ap.add_argument("--no-consistency", action="store_true",
                    help="跳过 consistency_check 子进程调用（加速 / CI 用）")
    ap.add_argument("--format", default="console", choices=["console", "md", "json"],
                    help="报告输出格式")
    args = ap.parse_args()

    if args.write and args.check:
        print("error: --write 与 --check 互斥", file=sys.stderr)
        return 3

    try:
        if args.check:
            report = build_report("check")
        elif args.write:
            wr = do_render(write=True, include_consistency=not args.no_consistency)
            report = build_report("write", wr)
        else:
            wr = do_render(write=False, include_consistency=not args.no_consistency)
            report = build_report("dry-run", wr)
    except Exception as e:
        # 未预期异常：ERROR 级
        report = Report(title="workflow-visualization")
        check = CheckResult(check_id="exception", description="脚本异常")
        check.findings.append(Finding(
            check_id="exception.unhandled",
            severity=Severity.ERROR,
            title=f"{type(e).__name__}: {e}",
        ))
        report.checks.append(check)
        return emit(report, fmt=args.format) or 3

    return emit(report, fmt=args.format)


if __name__ == "__main__":
    sys.exit(main())
