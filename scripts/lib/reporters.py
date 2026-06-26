"""统一的报告格式化输出。

支持三种格式：
    console — 彩色 ANSI 终端输出（默认）
    md      — Markdown 报告，便于贴到 PR 评论
    json    — 结构化输出，便于 CI 与进一步处理

退出码约定（由调用脚本汇总后传给 sys.exit）：
    0 — PASS
    1 — WARN
    2 — FAIL
    3 — ERROR（脚本内部异常）
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """检查项严重级别（值即字面量，便于 JSON 序列化）。"""
    PASS = "PASS"
    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"
    ERROR = "ERROR"

    @property
    def color(self) -> str:
        return {
            "PASS": "\033[32m",   # green
            "INFO": "\033[36m",   # cyan
            "WARN": "\033[33m",   # yellow
            "FAIL": "\033[31m",   # red
            "ERROR": "\033[35m",  # magenta
        }[self.value]

    @property
    def icon(self) -> str:
        return {
            "PASS": "✓",
            "INFO": "·",
            "WARN": "⚠",
            "FAIL": "✗",
            "ERROR": "✖",
        }[self.value]


@dataclass
class Finding:
    """单个检查发现项。"""
    check_id: str                       # 检查项 ID，如 "phase-transition-closure"
    severity: Severity
    title: str                          # 一句话标题
    message: str = ""                   # 详细说明
    file: str | None = None             # 关联文件（相对仓库根）
    line: int | None = None             # 关联行号
    fix_hint: str | None = None         # 修复建议（可包含命令）


@dataclass
class CheckResult:
    """单个检查维度的结果（包含多个 Finding）。"""
    check_id: str
    description: str                    # 维度描述
    findings: list[Finding] = field(default_factory=list)

    @property
    def severity(self) -> Severity:
        """聚合严重级别（取最高）。"""
        if any(f.severity == Severity.ERROR for f in self.findings):
            return Severity.ERROR
        if any(f.severity == Severity.FAIL for f in self.findings):
            return Severity.FAIL
        if any(f.severity == Severity.WARN for f in self.findings):
            return Severity.WARN
        return Severity.PASS


@dataclass
class Report:
    """完整报告。"""
    title: str
    checks: list[CheckResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        for c in self.checks:
            if c.severity in (Severity.ERROR,):
                return 3
        for c in self.checks:
            if c.severity == Severity.FAIL:
                return 2
        for c in self.checks:
            if c.severity == Severity.WARN:
                return 1
        return 0

    def counts(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for c in self.checks:
            for f in c.findings:
                counts[f.severity.value] += 1
        return counts


# ----------------------------------------------------------------------------
# 渲染函数
# ----------------------------------------------------------------------------

def _reset() -> str:
    return "\033[0m"


def _bold() -> str:
    return "\033[1m"


def render_console(report: Report, use_color: bool = True) -> str:
    """彩色终端输出。"""
    def c(text: str, color: str = "") -> str:
        if not use_color:
            return text
        return f"{color}{text}{_reset()}"

    lines: list[str] = []
    lines.append(c(f"━━━ {report.title} ━━━", _bold()))
    lines.append("")

    counts = report.counts()
    summary_parts = []
    for sev in [Severity.PASS, Severity.WARN, Severity.FAIL, Severity.ERROR]:
        n = counts[sev.value]
        if n:
            summary_parts.append(c(f"{sev.icon} {sev.value}: {n}", sev.color))
    if not summary_parts:
        summary_parts.append(c("无检查项", Severity.INFO.color))
    lines.append("  " + "   ".join(summary_parts))
    lines.append("")

    for check in report.checks:
        sev = check.severity
        header = c(f"[{sev.value}]", sev.color) + f" {check.check_id} — {check.description}"
        lines.append(header)
        if check.severity == Severity.PASS and not check.findings:
            continue
        for f in check.findings:
            if f.severity == Severity.PASS:
                continue
            icon = c(f.severity.icon, f.severity.color)
            head = f"  {icon} {f.title}"
            if f.file:
                loc = f.file + (f":{f.line}" if f.line else "")
                head += c(f"  ({loc})", "\033[90m")
            lines.append(head)
            if f.message:
                for ml in f.message.splitlines():
                    lines.append(f"      {ml}")
            if f.fix_hint:
                lines.append(c(f"      → {f.fix_hint}", "\033[36m"))
        lines.append("")

    if report.summary:
        lines.append(c("摘要：", _bold()))
        for k, v in report.summary.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def render_markdown(report: Report) -> str:
    """Markdown 报告。"""
    lines: list[str] = []
    lines.append(f"# {report.title}")
    lines.append("")

    counts = report.counts()
    lines.append("## 摘要")
    lines.append("")
    lines.append("| 级别 | 数量 |")
    lines.append("|------|------|")
    for sev in [Severity.PASS, Severity.INFO, Severity.WARN, Severity.FAIL, Severity.ERROR]:
        n = counts[sev.value]
        if n:
            lines.append(f"| {sev.icon} {sev.value} | {n} |")
    lines.append("")

    if report.summary:
        for k, v in report.summary.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines.append("## 检查结果")
    lines.append("")
    for check in report.checks:
        sev = check.severity
        lines.append(f"### [{sev.icon} {sev.value}] `{check.check_id}` — {check.description}")
        lines.append("")
        if check.severity == Severity.PASS and not check.findings:
            lines.append("（通过，无发现项）")
            lines.append("")
            continue
        for f in check.findings:
            if f.severity == Severity.PASS:
                continue
            loc = ""
            if f.file:
                loc = f" — `{f.file}" + (f":{f.line}" if f.line else "") + "`"
            lines.append(f"- {f.severity.icon} **{f.title}**{loc}")
            if f.message:
                for ml in f.message.splitlines():
                    lines.append(f"  - {ml}" if ml.strip() else "")
            if f.fix_hint:
                lines.append(f"  - 修复建议：`{f.fix_hint}`")
        lines.append("")

    return "\n".join(lines)


def render_json(report: Report) -> str:
    """JSON 输出。"""
    payload = {
        "title": report.title,
        "exit_code": report.exit_code,
        "counts": report.counts(),
        "summary": report.summary,
        "checks": [
            {
                "check_id": c.check_id,
                "description": c.description,
                "severity": c.severity.value,
                "findings": [
                    {
                        "check_id": f.check_id,
                        "severity": f.severity.value,
                        "title": f.title,
                        "message": f.message,
                        "file": f.file,
                        "line": f.line,
                        "fix_hint": f.fix_hint,
                    }
                    for f in c.findings
                ],
            }
            for c in report.checks
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def emit(report: Report, fmt: str = "console") -> int:
    """渲染并打印报告，返回退出码（调用方负责 sys.exit）。"""
    fmt = (fmt or "console").lower()
    use_color = sys.stdout.isatty() and fmt == "console"
    if fmt == "md":
        print(render_markdown(report))
    elif fmt == "json":
        print(render_json(report))
    else:
        print(render_console(report, use_color=use_color))
    return report.exit_code
