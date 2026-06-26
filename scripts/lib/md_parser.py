"""Markdown 解析工具。

本仓库内的 markdown 文档不使用标准 YAML frontmatter（`---` 包裹），而是采用
"quote-block frontmatter"——即用 `> **键**: 值` 形式的引文行作为元数据。本模块
同时提供这种 quote-block frontmatter 的解析以及 GFM 表格解析。

约定：
    1. quote-block frontmatter 必须出现在 H1 标题之后、正文之前的连续引文区
    2. 标准表格识别为 `| ... |` 起始且第二行为 `| ---- | ---- |` 分隔的连续区块
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ----------------------------------------------------------------------------
# quote-block frontmatter
# ----------------------------------------------------------------------------

QUOTE_KV_RE = re.compile(
    r"""^>\s*
        (?:\*\*|__)?       # 可选加粗起
        (?P<key>[^*:`>]+?)
        (?:\*\*|__)?       # 可选加粗止
        \s*[:：]\s*
        (?P<val>.+?)\s*$
    """,
    re.VERBOSE,
)


@dataclass
class QuoteFrontmatter:
    """quote-block frontmatter 的解析结果。"""
    title: str = ""                                  # H1 标题（去掉 `# `）
    fields: dict[str, str] = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)


def parse_quote_frontmatter(text: str) -> QuoteFrontmatter:
    """解析 quote-block frontmatter。

    扫描规则：
        1. 跳过文件开头的空行
        2. 第一行非空行若为 `# Title`，记录 title 并继续
        3. 继续扫描直到遇到第一个 `> **键**: 值` 行，进入 quote-block
        4. quote-block 内允许 `> ` 续行、空行（视为结束）；其他行（含 `---`）也视为结束
    """
    lines = text.splitlines()
    fm = QuoteFrontmatter()

    i = 0
    n = len(lines)

    # 1. 跳过开头空行
    while i < n and lines[i].strip() == "":
        i += 1

    # 2. H1 标题
    if i < n and lines[i].startswith("# "):
        fm.title = lines[i][2:].strip()
        i += 1

    # 3. 跳到第一个 `>` 引文行（容忍中间的空行 / `---` 分隔）
    in_block = False
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith(">"):
            in_block = True
            fm.raw_lines.append(line)
            m = QUOTE_KV_RE.match(line)
            if m:
                key = m.group("key").strip().lower()
                # 归一化常用键名（"调用阶段" / "状态" / "职责" / "Parallel Agent 成员名"）
                key_norm = (
                    key.replace(" ", "-")
                    .replace("_", "-")
                )
                fm.fields[key_norm] = m.group("val").strip()
            i += 1
            continue

        if in_block:
            # 已进入 quote-block 后，遇到非引文行即结束
            break

        # 未进入引文块前，遇到 `---` 分隔线视为正文开始，停止扫描
        if stripped == "---":
            break

        # 普通正文，未找到 frontmatter（容忍 Agent 文档无 frontmatter）
        if stripped and not stripped.startswith(">"):
            break

        i += 1

    return fm


# ----------------------------------------------------------------------------
# GFM 表格解析
# ----------------------------------------------------------------------------

@dataclass
class MarkdownTable:
    """一个 GFM 表格。"""
    headers: list[str]
    rows: list[list[str]]
    start_line: int                                  # 表头行号（1-based）
    end_line: int                                    # 最后一行行号（1-based）

    def column(self, header: str) -> list[str]:
        """按表头名取一列。表头匹配忽略大小写与首尾空格。"""
        target = header.strip().lower()
        for idx, h in enumerate(self.headers):
            if h.strip().lower() == target:
                return [row[idx] if idx < len(row) else "" for row in self.rows]
        raise KeyError(f"表格中找不到列：{header}（实际列：{self.headers}）")

    def has_column(self, header: str) -> bool:
        target = header.strip().lower()
        return any(h.strip().lower() == target for h in self.headers)


_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _split_table_row(line: str) -> list[str]:
    """将表格一行拆分为单元格。处理首尾管道与转义。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    # 简易拆分（不考虑 `\|` 转义，足够本仓库使用）
    return [cell.strip() for cell in s.split("|")]


def parse_tables(text: str) -> list[MarkdownTable]:
    """扫描所有 GFM 表格。代码块 ``` 内的表格会被忽略。"""
    lines = text.splitlines()
    tables: list[MarkdownTable] = []
    in_code = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        if _TABLE_LINE_RE.match(line) and i + 1 < n and _TABLE_DIVIDER_RE.match(lines[i + 1]):
            headers = _split_table_row(line)
            rows: list[list[str]] = []
            j = i + 2
            while j < n and _TABLE_LINE_RE.match(lines[j]):
                rows.append(_split_table_row(lines[j]))
                j += 1
            tables.append(MarkdownTable(
                headers=headers,
                rows=rows,
                start_line=i + 1,
                end_line=j,
            ))
            i = j
            continue
        i += 1
    return tables


def find_table_under_heading(text: str, heading_pattern: str) -> MarkdownTable | None:
    """在某个 H 标题（正则）下方查找紧邻的第一个表格。

    `heading_pattern` 应包含完整的标题前缀，如 r"^##\\s+2\\.1\\s+阶段定义" 或
    r"^##\\s+3\\.\\s+子\\s*Agent\\s*注册表"。

    实现：找到匹配的 heading 行号 → 调用 parse_tables 后筛选 start_line > heading_line
    的第一个，但要求中间没有更高级别的 heading 阻断。
    """
    lines = text.splitlines()
    pat = re.compile(heading_pattern)
    heading_line = -1
    heading_level = 0
    for idx, line in enumerate(lines):
        if pat.search(line):
            heading_line = idx + 1
            m = re.match(r"^(#+)\s+", line)
            heading_level = len(m.group(1)) if m else 6
            break
    if heading_line < 0:
        return None

    tables = parse_tables(text)
    # 找下一个同级或更高级标题
    next_heading_line = len(lines) + 1
    for idx in range(heading_line, len(lines)):
        line = lines[idx]
        m = re.match(r"^(#+)\s+", line)
        if m and len(m.group(1)) <= heading_level:
            next_heading_line = idx + 1
            break

    for t in tables:
        if heading_line < t.start_line < next_heading_line:
            return t
    return None


# ----------------------------------------------------------------------------
# 文件级辅助
# ----------------------------------------------------------------------------

def read_text(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_file_quote_frontmatter(path: Path | str) -> QuoteFrontmatter:
    return parse_quote_frontmatter(read_text(path))


def find_h1_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""
