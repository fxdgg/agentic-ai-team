"""lib/md_parser.py 单元测试。

覆盖：
    - parse_quote_frontmatter（正例 / 多字段 / 描述性句子值 / 缺 frontmatter / 中文 key 归一化）
    - parse_tables（GFM 标准表 / 代码块内忽略 / 多个表）
    - find_table_under_heading（命中 / 未命中）
    - parse_file_quote_frontmatter（从文件路径加载）
"""
from __future__ import annotations

import pytest

from lib import md_parser


# ---------------------------------------------------------------------------
# parse_quote_frontmatter
# ---------------------------------------------------------------------------


def test_parse_quote_frontmatter_basic():
    """标准 quote-block frontmatter 解析。"""
    text = (
        "# Agent X\n\n"
        "> **状态**: active\n"
        "> **调用阶段**: ANALYSE_PRODUCT\n"
        "\n正文\n"
    )
    fm = md_parser.parse_quote_frontmatter(text)
    assert fm.title == "Agent X"
    assert fm.fields["状态"] == "active"
    assert fm.fields["调用阶段"] == "ANALYSE_PRODUCT"


def test_parse_quote_frontmatter_descriptive_value():
    """frontmatter 值是描述性句子（fact-checker.md 风格），应保留完整字符串不切片。"""
    text = (
        "# Fact Checker\n\n"
        "> **调用阶段**: 由 archiver §17.5 在 ARCHIVE 阶段末尾委派调用\n"
    )
    fm = md_parser.parse_quote_frontmatter(text)
    assert "ARCHIVE" in fm.fields["调用阶段"]
    assert "委派调用" in fm.fields["调用阶段"]


def test_parse_quote_frontmatter_no_frontmatter():
    """无 frontmatter 的 markdown 应返回空 fields。"""
    text = "# Just a title\n\n这里全是正文，没有任何 quote block。\n"
    fm = md_parser.parse_quote_frontmatter(text)
    assert fm.title == "Just a title"
    assert fm.fields == {}


def test_parse_quote_frontmatter_key_normalization():
    """空格 / 下划线被归一为 dash。"""
    text = (
        "# X\n\n"
        "> **Parallel Agent 成员名**: foo\n"
        "> **knowledge_budget**: 5\n"
    )
    fm = md_parser.parse_quote_frontmatter(text)
    # 空格和下划线都归一为 dash，且 key 转小写
    assert "parallel-agent-成员名" in fm.fields
    assert "knowledge-budget" in fm.fields


def test_parse_quote_frontmatter_stops_at_blank_or_separator():
    """空行后即使再出现 `>` 引文行也不再算 frontmatter。"""
    text = (
        "# X\n\n"
        "> **状态**: active\n"
        "\n"
        "> 这是后面的引文，不应被视为 frontmatter\n"
    )
    fm = md_parser.parse_quote_frontmatter(text)
    assert fm.fields == {"状态": "active"}


# ---------------------------------------------------------------------------
# parse_tables
# ---------------------------------------------------------------------------


def test_parse_tables_basic(sample_gfm_table_md):
    """GFM 表格基本解析。"""
    text = sample_gfm_table_md.read_text(encoding="utf-8")
    tables = md_parser.parse_tables(text)
    assert len(tables) == 1
    t = tables[0]
    assert t.headers == ["列A", "列B", "列C"]
    assert t.rows == [["a1", "b1", "c1"], ["a2", "b2", "c2"]]
    assert t.start_line >= 1
    assert t.end_line >= t.start_line + 2


def test_parse_tables_skips_code_block():
    """代码块内的伪表格不应被识别。"""
    text = (
        "# Doc\n\n"
        "```\n"
        "| 不是表 | 因为 | 在代码块 |\n"
        "|-----|-----|-----|\n"
        "| a | b | c |\n"
        "```\n"
        "\n后续段落\n"
    )
    tables = md_parser.parse_tables(text)
    assert tables == []


def test_parse_tables_column_access(sample_gfm_table_md):
    """MarkdownTable.column / has_column 接口。"""
    text = sample_gfm_table_md.read_text(encoding="utf-8")
    t = md_parser.parse_tables(text)[0]
    assert t.has_column("列A")
    assert not t.has_column("不存在")
    assert t.column("列A") == ["a1", "a2"]
    with pytest.raises(KeyError):
        t.column("不存在")


# ---------------------------------------------------------------------------
# find_table_under_heading
# ---------------------------------------------------------------------------


def test_find_table_under_heading_hit():
    """在指定标题下找到紧邻的第一个表格。"""
    text = (
        "# Doc\n\n"
        "## §10. 阶段规则按需加载映射表\n\n"
        "| 阶段 | 文件 |\n"
        "|------|------|\n"
        "| INIT | init-rules.md |\n"
    )
    t = md_parser.find_table_under_heading(text, r"^##\s+§10\.\s+阶段规则按需加载映射表")
    assert t is not None
    assert t.headers == ["阶段", "文件"]
    assert t.rows == [["INIT", "init-rules.md"]]


def test_find_table_under_heading_miss():
    """未匹配的标题返回 None。"""
    text = "# Doc\n\n## 别的标题\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    t = md_parser.find_table_under_heading(text, r"^##\s+完全不存在的标题")
    assert t is None


# ---------------------------------------------------------------------------
# parse_file_quote_frontmatter
# ---------------------------------------------------------------------------


def test_parse_file_quote_frontmatter_loads_from_path(sample_quote_frontmatter_md):
    """从 Path 加载并解析。"""
    fm = md_parser.parse_file_quote_frontmatter(sample_quote_frontmatter_md)
    assert fm.title == "Sample Agent"
    assert fm.fields["状态"] == "active"
    assert "ANALYSE_PRODUCT" in fm.fields["调用阶段"]
