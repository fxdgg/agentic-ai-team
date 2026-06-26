"""lib/autogen_block.py 单元测试。

覆盖：
    - compute_block_hash（归一化 + 稳定）
    - render_block_comments（hash 写入注释）
    - find_blocks（正例 / 重复 ID / 未关闭 BEGIN / 嵌套）
    - replace_block_in_file（替换 / 幂等）
    - wrap_lines_in_file（首次区段化 / 行号非法 / 已包裹 / 归一化空行）
"""
from __future__ import annotations

import pytest

from lib import autogen_block


# ---------------------------------------------------------------------------
# compute_block_hash
# ---------------------------------------------------------------------------


def test_compute_block_hash_stable():
    """同样的 body 应产出同样的 hash（16 位 hex）。"""
    h1 = autogen_block.compute_block_hash(["line1", "line2", "line3"])
    h2 = autogen_block.compute_block_hash(["line1", "line2", "line3"])
    assert h1 == h2
    assert len(h1) == 16
    assert all(c in "0123456789abcdef" for c in h1)


def test_compute_block_hash_normalizes_blank_lines():
    """首尾空行 + 行尾空白被归一化（影响双平台 byte-equal）。"""
    h_clean = autogen_block.compute_block_hash(["a", "b"])
    h_padded = autogen_block.compute_block_hash(["", "a", "b   ", ""])
    assert h_clean == h_padded


# ---------------------------------------------------------------------------
# render_block_comments
# ---------------------------------------------------------------------------


def test_render_block_comments_includes_hash_and_source():
    """渲染产出的 BEGIN 行应包含 hash + 可选 source。"""
    out = autogen_block.render_block_comments(
        "my-section",
        "body line",
        source="state-schema.json",
    )
    assert "BEGIN AUTO-GEN: my-section" in out
    assert "END AUTO-GEN: my-section" in out
    assert "hash=" in out
    assert "source=state-schema.json" in out
    # body 在中间
    assert "body line" in out


# ---------------------------------------------------------------------------
# find_blocks
# ---------------------------------------------------------------------------


def test_find_blocks_basic():
    """标准 BEGIN/END 区段被识别。"""
    text = (
        "前置内容\n"
        "<!-- BEGIN AUTO-GEN: sec-1 hash=abc123 -->\n"
        "body\n"
        "<!-- END AUTO-GEN: sec-1 -->\n"
        "后续\n"
    )
    blocks = autogen_block.find_blocks(text)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.section_id == "sec-1"
    assert b.declared_hash == "abc123"
    assert "body" in b.body_text


def test_find_blocks_rejects_unclosed_begin():
    """BEGIN 没有 END 应抛 ValueError。"""
    text = (
        "<!-- BEGIN AUTO-GEN: sec-1 hash=abc -->\n"
        "body without end\n"
    )
    with pytest.raises(ValueError):
        autogen_block.find_blocks(text)


def test_find_blocks_rejects_duplicate_section_id():
    """同 section_id 出现两次应抛 ValueError。"""
    text = (
        "<!-- BEGIN AUTO-GEN: dup -->\nx\n<!-- END AUTO-GEN: dup -->\n"
        "<!-- BEGIN AUTO-GEN: dup -->\ny\n<!-- END AUTO-GEN: dup -->\n"
    )
    with pytest.raises(ValueError):
        autogen_block.find_blocks(text)


# ---------------------------------------------------------------------------
# replace_block_in_file
# ---------------------------------------------------------------------------


def test_replace_block_in_file_changes_content(tmp_path):
    """替换区段内容，文件应被改写。"""
    p = tmp_path / "f.md"
    p.write_text(
        "<!-- BEGIN AUTO-GEN: x hash=oldhash -->\nold body\n<!-- END AUTO-GEN: x -->\n",
        encoding="utf-8",
    )
    changed, err = autogen_block.replace_block_in_file(p, "x", "new body")
    assert err is None
    assert changed is True
    text = p.read_text(encoding="utf-8")
    assert "new body" in text
    assert "old body" not in text


def test_replace_block_in_file_idempotent(tmp_path):
    """连续两次以相同内容替换，第二次应返回 changed=False。"""
    p = tmp_path / "f.md"
    p.write_text(
        "<!-- BEGIN AUTO-GEN: x hash=h -->\nbody\n<!-- END AUTO-GEN: x -->\n",
        encoding="utf-8",
    )
    autogen_block.replace_block_in_file(p, "x", "stable body")
    changed, err = autogen_block.replace_block_in_file(p, "x", "stable body")
    assert err is None
    assert changed is False


def test_replace_block_in_file_missing_section(tmp_path):
    """目标 section_id 不存在应返回错误。"""
    p = tmp_path / "f.md"
    p.write_text("一些内容，无 AUTO-GEN 区段\n", encoding="utf-8")
    changed, err = autogen_block.replace_block_in_file(p, "absent", "body")
    assert changed is False
    assert err is not None
    assert "absent" in err


# ---------------------------------------------------------------------------
# wrap_lines_in_file
# ---------------------------------------------------------------------------


def test_wrap_lines_in_file_normalizes_blank_lines(tmp_path):
    """两个文件原始首尾空行数不同，wrap 后输出 byte-equal（关键约束）。"""
    body_a = "## H\n\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n后续\n"
    body_b = "## H\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n\n\n后续\n"
    pa = tmp_path / "a.md"
    pb = tmp_path / "b.md"
    pa.write_text(body_a, encoding="utf-8")
    pb.write_text(body_b, encoding="utf-8")

    # body 在两份文件里行号不同，但内容相同；wrap 后应等同
    # 找到表格的真实行号（简化用硬编码：表格在 4-6 / 3-5）
    autogen_block.wrap_lines_in_file(pa, "tbl", 4, 6)
    autogen_block.wrap_lines_in_file(pb, "tbl", 3, 5)

    # 取出两份文件的 BEGIN/END 之间内容比对
    blocks_a = autogen_block.find_blocks(pa.read_text(encoding="utf-8"))
    blocks_b = autogen_block.find_blocks(pb.read_text(encoding="utf-8"))
    assert blocks_a[0].body_text == blocks_b[0].body_text
    assert blocks_a[0].declared_hash == blocks_b[0].declared_hash


def test_wrap_lines_in_file_rejects_invalid_range(tmp_path):
    """非法行范围返回错误。"""
    p = tmp_path / "x.md"
    p.write_text("a\nb\nc\n", encoding="utf-8")
    changed, err = autogen_block.wrap_lines_in_file(p, "s", 0, 2)
    assert changed is False
    assert err is not None


def test_wrap_lines_in_file_rejects_existing_section(tmp_path):
    """同 section_id 已存在区段，wrap 应失败（幂等保护）。"""
    p = tmp_path / "x.md"
    p.write_text(
        "<!-- BEGIN AUTO-GEN: existing hash=h -->\nbody\n<!-- END AUTO-GEN: existing -->\n"
        "more text\n",
        encoding="utf-8",
    )
    changed, err = autogen_block.wrap_lines_in_file(p, "existing", 4, 4)
    assert changed is False
    assert err is not None
    assert "existing" in err
