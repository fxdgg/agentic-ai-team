"""仓库根目录与关键路径定位。

所有脚本统一从此模块获取路径，避免硬编码相对路径导致的"在不同目录跑结果不一致"问题。
"""

from __future__ import annotations

from pathlib import Path


# ----------------------------------------------------------------------------
# 仓库根定位
# ----------------------------------------------------------------------------

def find_repo_root(start: Path | None = None) -> Path:
    """从 `start`（默认本文件所在位置）向上查找仓库根。

    判定标志（按优先级）：
        1. 存在 `.git/` 目录
        2. 同时存在 `ARCHITECTURE.md` 与 `CLAUDE.md`
        3. 同时存在 `.claude/` 与 `.codebuddy/`
    """
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / ".git").exists():
            return candidate
        if (candidate / "ARCHITECTURE.md").exists() and (candidate / "CLAUDE.md").exists():
            return candidate
        if (candidate / ".claude").is_dir() and (candidate / ".codebuddy").is_dir():
            return candidate
    raise RuntimeError(f"未能从 {here} 向上定位 ai-team 引擎仓库根")


REPO_ROOT: Path = find_repo_root()


# ----------------------------------------------------------------------------
# 关键路径常量
# ----------------------------------------------------------------------------

# 顶层文档
ARCHITECTURE_MD = REPO_ROOT / "ARCHITECTURE.md"
README_MD = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CODEBUDDY_MD = REPO_ROOT / "CODEBUDDY.md"

# 双平台根
CLAUDE_ROOT = REPO_ROOT / ".claude"
CODEBUDDY_ROOT = REPO_ROOT / ".codebuddy"

# workflow-orchestrator Skill
WF_RELATIVE = Path("skills") / "workflow-orchestrator"
WF_CLAUDE = CLAUDE_ROOT / WF_RELATIVE
WF_CODEBUDDY = CODEBUDDY_ROOT / WF_RELATIVE

# workflow-orchestrator 关键文件（以 .claude/ 为准）
WF_SKILL_MD = WF_CLAUDE / "SKILL.md"
WF_REFERENCES = WF_CLAUDE / "references"
WF_AGENTS = WF_CLAUDE / "agents"
WF_PHASES = WF_CLAUDE / "phases"
WF_RULES = WF_CLAUDE / "rules"
WF_TEMPLATES = WF_CLAUDE / "templates"

# 关键 JSON Schema
STATE_SCHEMA = WF_REFERENCES / "state-schema.json"
PHASE_TRANSITIONS = WF_REFERENCES / "phase-transitions.json"

# 用户命令
CLAUDE_COMMANDS = CLAUDE_ROOT / "commands"
CODEBUDDY_COMMANDS = CODEBUDDY_ROOT / "commands"

# Skills 根
CLAUDE_SKILLS = CLAUDE_ROOT / "skills"
CODEBUDDY_SKILLS = CODEBUDDY_ROOT / "skills"

# DSL（Phase 2 引入，目前不存在）
META_DIR = REPO_ROOT / "meta"
META_PHASES = META_DIR / "phases.yaml"
META_AGENTS = META_DIR / "agents.yaml"
META_STATE_SCHEMA = META_DIR / "state-schema.yaml"
META_COMMANDS = META_DIR / "commands.yaml"
META_SKILLS = META_DIR / "skills.yaml"
META_DIVERGENCE = META_DIR / "platform-divergence.yaml"


# ----------------------------------------------------------------------------
# 路径工具
# ----------------------------------------------------------------------------

def to_relative(path: Path | str) -> str:
    """转换为相对仓库根的 POSIX 路径，便于报告输出。"""
    p = Path(path).resolve()
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def claude_to_codebuddy(claude_path: Path | str) -> Path:
    """`.claude/...` 路径 → 对应 `.codebuddy/...` 路径。"""
    p = Path(claude_path).resolve()
    try:
        rel = p.relative_to(CLAUDE_ROOT)
    except ValueError as e:
        raise ValueError(f"路径 {p} 不在 .claude/ 下") from e
    return CODEBUDDY_ROOT / rel


def codebuddy_to_claude(codebuddy_path: Path | str) -> Path:
    """`.codebuddy/...` 路径 → 对应 `.claude/...` 路径。"""
    p = Path(codebuddy_path).resolve()
    try:
        rel = p.relative_to(CODEBUDDY_ROOT)
    except ValueError as e:
        raise ValueError(f"路径 {p} 不在 .codebuddy/ 下") from e
    return CLAUDE_ROOT / rel


def is_in_platform(path: Path | str) -> str | None:
    """判定路径所属平台。返回 'claude' / 'codebuddy' / None。"""
    p = Path(path).resolve()
    try:
        p.relative_to(CLAUDE_ROOT)
        return "claude"
    except ValueError:
        pass
    try:
        p.relative_to(CODEBUDDY_ROOT)
        return "codebuddy"
    except ValueError:
        pass
    return None
