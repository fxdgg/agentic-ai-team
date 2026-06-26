"""lib/platform_mirror.py 单元测试。

覆盖：
    - DEFAULT_DIVERGENCE 结构正确
    - _is_only_on_platform_waived（命中文件 / 命中目录前缀 / 未命中）
    - _is_content_diff_waived（配对清单命中）
    - collect_mirror_report（双平台对账，monkeypatch CLAUDE_ROOT/CODEBUDDY_ROOT 到 tmp）
    - get_active_divergence（DSL 优先 / fallback）
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib import paths, platform_mirror


# ---------------------------------------------------------------------------
# 豁免清单结构
# ---------------------------------------------------------------------------


def test_default_divergence_has_required_keys():
    """DEFAULT_DIVERGENCE 应含 4 个标准 key。"""
    div = platform_mirror.DEFAULT_DIVERGENCE
    assert "claude_only" in div
    assert "codebuddy_only" in div
    assert "codebuddy_only_dirs" in div
    assert "content_allowed_differ_pairs" in div


# ---------------------------------------------------------------------------
# 豁免命中
# ---------------------------------------------------------------------------


def test_is_only_on_platform_waived_file_hit():
    """exact 文件命中 codebuddy_only。"""
    div = {"codebuddy_only": {"skills/iwiki-operation/SKILL.md"}}
    assert platform_mirror._is_only_on_platform_waived(
        "skills/iwiki-operation/SKILL.md", "codebuddy_only", div
    )


def test_is_only_on_platform_waived_dir_prefix():
    """目录前缀（codebuddy_only_dirs）命中其下所有文件。"""
    div = {"codebuddy_only_dirs": {"plans"}}
    assert platform_mirror._is_only_on_platform_waived(
        "plans/some-draft.md", "codebuddy_only", div
    )


def test_is_only_on_platform_waived_file_prefix_match():
    """文件级豁免支持目录前缀匹配（如 'skills/iwiki-operation' 命中其下所有）。"""
    div = {"codebuddy_only": {"skills/iwiki-operation"}}
    assert platform_mirror._is_only_on_platform_waived(
        "skills/iwiki-operation/SKILL.md", "codebuddy_only", div
    )


def test_is_only_on_platform_waived_miss():
    """未在豁免清单的文件返回 False。"""
    div = {"codebuddy_only": set(), "codebuddy_only_dirs": set()}
    assert not platform_mirror._is_only_on_platform_waived(
        "skills/foo.md", "codebuddy_only", div
    )


def test_is_content_diff_waived_pair_match():
    """配对豁免清单（如 tcb/CLAUDE.md ↔ tcb/CODEBUDDY.md）命中任一边。"""
    div = {
        "content_allowed_differ_pairs": [
            ("rules/tcb/CLAUDE.md", "rules/tcb/CODEBUDDY.md"),
        ]
    }
    assert platform_mirror._is_content_diff_waived("rules/tcb/CLAUDE.md", div)
    assert platform_mirror._is_content_diff_waived("rules/tcb/CODEBUDDY.md", div)
    assert not platform_mirror._is_content_diff_waived("rules/tcb/other.md", div)


# ---------------------------------------------------------------------------
# collect_mirror_report
# ---------------------------------------------------------------------------


def test_collect_mirror_report_detects_diff_categories(tmp_path, monkeypatch):
    """对账能正确分类 only-claude / only-codebuddy / content-diff / 同步。"""
    claude = tmp_path / ".claude"
    cb = tmp_path / ".codebuddy"
    claude.mkdir()
    cb.mkdir()

    # 同步文件（hash 一致）
    (claude / "same.md").write_text("hello", encoding="utf-8")
    (cb / "same.md").write_text("hello", encoding="utf-8")

    # 内容差异
    (claude / "diff.md").write_text("claude version", encoding="utf-8")
    (cb / "diff.md").write_text("codebuddy version", encoding="utf-8")

    # 仅 claude
    (claude / "only-claude.md").write_text("a", encoding="utf-8")

    # 仅 codebuddy
    (cb / "only-cb.md").write_text("b", encoding="utf-8")

    monkeypatch.setattr(paths, "CLAUDE_ROOT", claude)
    monkeypatch.setattr(paths, "CODEBUDDY_ROOT", cb)

    # 用空豁免清单确保所有差异都暴露
    empty_div = {
        "claude_only": set(),
        "codebuddy_only": set(),
        "claude_only_dirs": set(),
        "codebuddy_only_dirs": set(),
        "content_allowed_differ_pairs": [],
    }
    report = platform_mirror.collect_mirror_report(divergence=empty_div)

    assert "only-claude.md" in report.only_claude
    assert "only-cb.md" in report.only_codebuddy
    assert "diff.md" in report.content_diff
    # same.md 既不在 only_*，也不在 content_diff
    assert "same.md" not in report.only_claude
    assert "same.md" not in report.only_codebuddy
    assert "same.md" not in report.content_diff


def test_collect_mirror_report_respects_waivers(tmp_path, monkeypatch):
    """命中豁免清单的差异进入 report.waived，不进入 only_* / content_diff。"""
    claude = tmp_path / ".claude"
    cb = tmp_path / ".codebuddy"
    claude.mkdir()
    cb.mkdir()
    (cb / "plans" / "draft.md").parent.mkdir()
    (cb / "plans" / "draft.md").write_text("draft", encoding="utf-8")

    monkeypatch.setattr(paths, "CLAUDE_ROOT", claude)
    monkeypatch.setattr(paths, "CODEBUDDY_ROOT", cb)

    div = {
        "claude_only": set(),
        "codebuddy_only": set(),
        "claude_only_dirs": set(),
        "codebuddy_only_dirs": {"plans"},
        "content_allowed_differ_pairs": [],
    }
    report = platform_mirror.collect_mirror_report(divergence=div)

    # plans/draft.md 应在 waived 而非 only_codebuddy
    assert any("plans/draft.md" in w for w in report.waived)
    assert "plans/draft.md" not in report.only_codebuddy


# ---------------------------------------------------------------------------
# get_active_divergence
# ---------------------------------------------------------------------------


def test_get_active_divergence_falls_back_when_dsl_missing(monkeypatch, tmp_path):
    """DSL 文件缺失时，get_active_divergence 应 fallback 到 DEFAULT_DIVERGENCE。"""
    monkeypatch.setattr(paths, "META_DIVERGENCE", tmp_path / "absent.yaml")
    div = platform_mirror.get_active_divergence()
    assert div is platform_mirror.DEFAULT_DIVERGENCE
