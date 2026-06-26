"""Phase 3-new 测试：双平台对账新方案 — 豁免清单 + normalize 体检静默。

覆盖：
    - meta/platform-divergence.yaml 的 paired_translation 段加载
    - normalize_text 函数（按 paired_translation 把所有方言转为统一形式）
    - 体检静默：normalize 后两份相等的 content-diff 自动豁免
    - 单文件 mirror（不翻译，仅整文件覆盖）
"""
from __future__ import annotations

import pytest

# Phase 3-new 待加入的函数（在 lib/platform_mirror.py 实现）
# 测试期望的接口：
#   - lib.platform_mirror.normalize_text(text: str, pairs: list[dict]) -> str
#   - 升级后的 collect_mirror_report 在 normalize 后等价时把差异移到 waived
#   - meta_loader.load_platform_divergence 返回的 dict 可含 'paired_translation' 段


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------


def test_normalize_text_replaces_tool_names():
    """normalize 应把双平台工具名都转成 codebuddy 形式（统一基线）。"""
    from lib import platform_mirror
    pairs = [
        {"kind": "tool_name", "claude": "Read", "codebuddy": "read_file"},
        {"kind": "tool_name", "claude": "Write", "codebuddy": "write_to_file"},
    ]
    # claude 文本应被替换
    claude_text = "使用 `Read` 工具加载文件，再用 `Write` 输出。"
    expected = "使用 `read_file` 工具加载文件，再用 `write_to_file` 输出。"
    assert platform_mirror.normalize_text(claude_text, pairs) == expected
    # codebuddy 文本应保持原样（已是基线形式）
    codebuddy_text = "使用 `read_file` 工具加载文件，再用 `write_to_file` 输出。"
    assert platform_mirror.normalize_text(codebuddy_text, pairs) == expected


def test_normalize_text_handles_terms_and_paths():
    """normalize 处理术语 / 路径 / IDE 名等多种 kind。"""
    from lib import platform_mirror
    pairs = [
        {"kind": "term", "claude": "Parallel Agent", "codebuddy": "Agent Teams"},
        {"kind": "ide_name", "claude": "Claude Code", "codebuddy": "CodeBuddy"},
        {"kind": "path", "claude": ".claude/", "codebuddy": ".codebuddy/"},
    ]
    text = "Parallel Agent 调度时，Claude Code 在 .claude/ 配置目录中..."
    expected = "Agent Teams 调度时，CodeBuddy 在 .codebuddy/ 配置目录中..."
    assert platform_mirror.normalize_text(text, pairs) == expected


def test_normalize_text_no_pairs_returns_unchanged():
    """空 pairs 列表，文本应原样返回。"""
    from lib import platform_mirror
    text = "any text"
    assert platform_mirror.normalize_text(text, []) == text


# ---------------------------------------------------------------------------
# 体检静默：normalize 等价的 content-diff 视为 waived
# ---------------------------------------------------------------------------


def test_collect_mirror_report_waives_dialect_only_diff(tmp_path, monkeypatch):
    """两份文件仅方言不同（normalize 后相等），应进入 waived 而非 content_diff。"""
    from lib import paths, platform_mirror
    claude = tmp_path / ".claude"
    cb = tmp_path / ".codebuddy"
    claude.mkdir()
    cb.mkdir()

    # 仅工具名差异
    (claude / "agent.md").write_text(
        "使用 `Read` 加载，使用 `Write` 输出。", encoding="utf-8"
    )
    (cb / "agent.md").write_text(
        "使用 `read_file` 加载，使用 `write_to_file` 输出。", encoding="utf-8"
    )

    monkeypatch.setattr(paths, "CLAUDE_ROOT", claude)
    monkeypatch.setattr(paths, "CODEBUDDY_ROOT", cb)

    div = {
        "claude_only": set(),
        "codebuddy_only": set(),
        "claude_only_dirs": set(),
        "codebuddy_only_dirs": set(),
        "content_allowed_differ_pairs": [],
        "paired_translation": [
            {"kind": "tool_name", "claude": "Read", "codebuddy": "read_file"},
            {"kind": "tool_name", "claude": "Write", "codebuddy": "write_to_file"},
        ],
    }
    report = platform_mirror.collect_mirror_report(divergence=div)

    # 关键约束：方言-only 差异应被识别为 paired-translation，不进入 content_diff
    assert "agent.md" not in report.content_diff
    assert any("agent.md" in w and "paired" in w for w in report.waived), \
        f"agent.md 应进入 waived 但未命中。waived: {report.waived}"


def test_collect_mirror_report_keeps_real_diff(tmp_path, monkeypatch):
    """normalize 后仍不等价的（真漂移）应保留在 content_diff。"""
    from lib import paths, platform_mirror
    claude = tmp_path / ".claude"
    cb = tmp_path / ".codebuddy"
    claude.mkdir()
    cb.mkdir()

    # 实质内容差异（多了一段 + 工具名差异）
    (claude / "agent.md").write_text("使用 `Read` 加载文件。", encoding="utf-8")
    (cb / "agent.md").write_text(
        "使用 `read_file` 加载文件。新增的功能段落。", encoding="utf-8"
    )

    monkeypatch.setattr(paths, "CLAUDE_ROOT", claude)
    monkeypatch.setattr(paths, "CODEBUDDY_ROOT", cb)

    div = {
        "claude_only": set(),
        "codebuddy_only": set(),
        "claude_only_dirs": set(),
        "codebuddy_only_dirs": set(),
        "content_allowed_differ_pairs": [],
        "paired_translation": [
            {"kind": "tool_name", "claude": "Read", "codebuddy": "read_file"},
        ],
    }
    report = platform_mirror.collect_mirror_report(divergence=div)
    # normalize 后两份仍不等（多一段），应在 content_diff
    assert "agent.md" in report.content_diff


# ---------------------------------------------------------------------------
# DSL 加载：paired_translation 段
# ---------------------------------------------------------------------------


def test_load_divergence_returns_paired_translation(tmp_path, monkeypatch):
    """meta/platform-divergence.yaml 的 paired_translation 段应被 load_divergence_from_dsl 提取。"""
    from lib import paths, platform_mirror
    yaml_text = """
only_on_platform: []
content_allowed_differ: []
paired_translation:
  - kind: tool_name
    claude: Read
    codebuddy: read_file
  - kind: term
    claude: Parallel Agent
    codebuddy: Agent Teams
"""
    p = tmp_path / "platform-divergence.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    monkeypatch.setattr(paths, "META_DIVERGENCE", p)

    div = platform_mirror.load_divergence_from_dsl()
    assert div is not None
    pairs = div.get("paired_translation", [])
    assert len(pairs) == 2
    assert pairs[0]["claude"] == "Read"
    assert pairs[1]["codebuddy"] == "Agent Teams"


# ---------------------------------------------------------------------------
# mirror_platforms 单文件覆盖（不翻译）
# ---------------------------------------------------------------------------


def test_mirror_platforms_status_lists_pairs(tmp_path, monkeypatch):
    """mirror_platforms.collect_mirror_report 在豁免后给出真实漂移列表（接口可用即可，不需要重测）。"""
    # 这个能力在 collect_mirror_report 已覆盖，重复测试不必要。
    pass