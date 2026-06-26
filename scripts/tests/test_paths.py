"""lib/paths.py 单元测试。

覆盖：
    - REPO_ROOT 定位（含 ARCHITECTURE.md 锚点）
    - to_relative / claude_to_codebuddy / codebuddy_to_claude / is_in_platform
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib import paths


def test_repo_root_resolved_to_real_repo():
    """REPO_ROOT 应指向当前实际仓库根（含 ARCHITECTURE.md）。"""
    assert paths.REPO_ROOT.is_dir()
    assert (paths.REPO_ROOT / "ARCHITECTURE.md").is_file()
    assert (paths.REPO_ROOT / ".claude").is_dir()
    assert (paths.REPO_ROOT / ".codebuddy").is_dir()


def test_key_paths_constants_resolve():
    """所有关键路径常量应至少父目录存在（即使文件不存在也应在合理位置）。"""
    # 已存在的
    assert paths.WF_SKILL_MD.is_file()
    assert paths.STATE_SCHEMA.is_file()
    assert paths.PHASE_TRANSITIONS.is_file()
    # 顶层目录
    assert paths.WF_CLAUDE.is_dir()
    assert paths.WF_CODEBUDDY.is_dir()


def test_claude_to_codebuddy_swaps_platform_prefix():
    """claude → codebuddy 路径转换。"""
    src = paths.CLAUDE_ROOT / "skills" / "foo" / "SKILL.md"
    dst = paths.claude_to_codebuddy(src)
    assert dst == paths.CODEBUDDY_ROOT / "skills" / "foo" / "SKILL.md"


def test_codebuddy_to_claude_swaps_platform_prefix():
    """codebuddy → claude 路径转换。"""
    src = paths.CODEBUDDY_ROOT / "commands" / "flow-run.md"
    dst = paths.codebuddy_to_claude(src)
    assert dst == paths.CLAUDE_ROOT / "commands" / "flow-run.md"


def test_is_in_platform_recognizes_both_sides():
    """is_in_platform 应能识别 claude / codebuddy / 仓库根三种位置。"""
    in_claude = paths.CLAUDE_ROOT / "skills" / "x.md"
    in_codebuddy = paths.CODEBUDDY_ROOT / "skills" / "x.md"
    in_root = paths.REPO_ROOT / "ARCHITECTURE.md"

    assert paths.is_in_platform(in_claude) == "claude"
    assert paths.is_in_platform(in_codebuddy) == "codebuddy"
    assert paths.is_in_platform(in_root) is None


def test_to_relative_returns_repo_relative_string():
    """to_relative 把绝对路径转换为相对仓库根的 POSIX 字符串。"""
    rel = paths.to_relative(paths.WF_SKILL_MD)
    assert isinstance(rel, str)
    assert rel.startswith(".claude/skills/workflow-orchestrator/")
    assert rel.endswith("SKILL.md")
    # 保证使用 POSIX 分隔符
    assert "\\" not in rel
