"""双平台对账：`.claude/` ↔ `.codebuddy/` 文件树差异 + 内容 hash 比对。

策略：
    1. 以 `.claude/` 为基准，列出所有文件
    2. 对每个文件查找 `.codebuddy/` 中的对应文件
    3. 比对内容 sha256
    4. 同时反向扫描 `.codebuddy/` 中独有的文件

豁免来源（按优先级）：
    1. meta/platform-divergence.yaml（Phase 3 起，DSL 单一真相源）
    2. DEFAULT_DIVERGENCE 硬编码（Phase 3 之前的兼容兜底）
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from . import paths


# Phase 3 之前的硬编码豁免（fallback）
# 路径相对 `.claude/` 或 `.codebuddy/`，POSIX 形式
DEFAULT_DIVERGENCE = {
    # iwiki-operation Skill 仅在 .codebuddy/（依赖 iwiki MCP）
    "codebuddy_only": {
        "skills/iwiki-operation",
    },
    # .codebuddy/plans/ 含临时草稿
    "codebuddy_only_dirs": {
        "plans",
    },
    "claude_only": set(),
    # 双方都存在但允许内容差异的文件（按平台命名约定，如 tcb/CLAUDE.md ↔ tcb/CODEBUDDY.md）
    "content_allowed_differ_pairs": [
        ("rules/tcb/CLAUDE.md", "rules/tcb/CODEBUDDY.md"),
    ],
}

# 应当从对账中完全忽略的路径前缀（不视为差异）
IGNORE_PREFIXES: set[str] = set()


def load_divergence_from_dsl() -> dict | None:
    """从 meta/platform-divergence.yaml 加载豁免清单。

    返回与 DEFAULT_DIVERGENCE 同结构的字典，并扩展两个新键：
        - ``paired_translation``: list[dict]  （Phase 3-new 引入）
                每条形如 ``{"kind": "tool_name", "claude": "Read", "codebuddy": "read_file"}``。
                供 ``collect_mirror_report`` 使用 ``normalize_text`` 静默方言-only 差异。

    DSL 文件不存在时返回 None（调用方可 fallback 到 DEFAULT_DIVERGENCE）。
    """
    try:
        from . import meta_loader
    except ImportError:
        return None
    raw = meta_loader.load_platform_divergence()
    if raw is None:
        return None

    result = {
        "claude_only": set(),
        "codebuddy_only": set(),
        "claude_only_dirs": set(),
        "codebuddy_only_dirs": set(),
        "content_allowed_differ_pairs": [],
        "paired_translation": [],
    }

    # only_on_platform: 文件 / 目录仅存在于某平台
    for entry in raw.get("only_on_platform", []) or []:
        path = entry.get("path")
        platform = entry.get("platform")
        if not path or not platform:
            continue
        # 判定 path 是文件还是目录：根据实际文件系统
        platform_root = paths.CLAUDE_ROOT if platform == "claude" else paths.CODEBUDDY_ROOT
        full = platform_root / path
        is_dir = full.is_dir()
        key_dirs = f"{platform}_only_dirs"
        key_files = f"{platform}_only"
        target_set = result[key_dirs] if is_dir else result[key_files]
        target_set.add(path)

    # content_allowed_differ: 双方都存在但允许差异
    for entry in raw.get("content_allowed_differ", []) or []:
        a = entry.get("path")
        b = entry.get("paired_with")
        if a and b:
            result["content_allowed_differ_pairs"].append((a, b))

    # directory_skip
    for entry in raw.get("directory_skip", []) or []:
        path = entry.get("path") if isinstance(entry, dict) else entry
        if path:
            # 双向加入，与 only_*_dirs 类似
            result.setdefault("ignore_dirs", set()).add(path)

    # paired_translation: 双平台方言映射对（Phase 3-new）
    for entry in raw.get("paired_translation", []) or []:
        if not isinstance(entry, dict):
            continue
        c = entry.get("claude")
        cb = entry.get("codebuddy")
        kind = entry.get("kind", "unknown")
        if c is None or cb is None:
            continue
        result["paired_translation"].append({
            "kind": kind,
            "claude": c,
            "codebuddy": cb,
        })

    return result


def get_active_divergence() -> dict:
    """返回当前生效的豁免清单（DSL 优先，fallback 到 DEFAULT_DIVERGENCE）。"""
    dsl = load_divergence_from_dsl()
    if dsl is not None:
        return dsl
    return DEFAULT_DIVERGENCE


@dataclass
class FileEntry:
    """单个文件的对账记录。"""
    rel_path: str                                    # 相对平台根的 POSIX 路径
    sha_claude: str | None = None
    sha_codebuddy: str | None = None
    size_claude: int | None = None
    size_codebuddy: int | None = None


@dataclass
class MirrorReport:
    """整体对账结果。"""
    entries: dict[str, FileEntry] = field(default_factory=dict)
    only_claude: list[str] = field(default_factory=list)
    only_codebuddy: list[str] = field(default_factory=list)
    content_diff: list[str] = field(default_factory=list)
    waived: list[str] = field(default_factory=list)


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_files(root: Path) -> set[str]:
    """递归收集 root 下所有文件的相对 POSIX 路径（仅文件，不含目录）。"""
    if not root.is_dir():
        return set()
    files: set[str] = set()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # 跳过隐藏文件 .DS_Store 等
        if p.name.startswith("."):
            continue
        rel = p.relative_to(root).as_posix()
        files.add(rel)
    return files


def _is_only_on_platform_waived(rel: str, side: str, divergence: dict) -> bool:
    """rel 是否被"仅平台 X 存在"豁免？side ∈ {'claude_only', 'codebuddy_only'}。"""
    waivers_files = divergence.get(side, set())
    if rel in waivers_files:
        return True
    # 目录前缀豁免
    waivers_dirs = divergence.get(side + "_dirs", set())
    for prefix in waivers_dirs:
        if rel == prefix or rel.startswith(prefix.rstrip("/") + "/"):
            return True
    # 文件级豁免：以前缀方式匹配（e.g. "skills/iwiki-operation" 命中其下所有文件）
    for prefix in waivers_files:
        if rel.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def _is_content_diff_waived(rel: str, divergence: dict) -> bool:
    """rel 是否在"双方都存在但允许内容差异"的配对清单中？

    既支持双方都引用同一相对路径的配对，也支持文件名不同的配对（如 tcb/CLAUDE.md ↔ tcb/CODEBUDDY.md，
    在双平台树下分别取对应路径）。
    """
    pairs = divergence.get("content_allowed_differ_pairs", [])
    for a, b in pairs:
        if rel == a or rel == b:
            return True
    return False


def normalize_text(text: str, pairs: list[dict]) -> str:
    """按 paired_translation 列表把文本中的 claude 方言替换为 codebuddy 形式（统一基线）。

    替换原则：
        - 双向归一到 codebuddy 形式（codebuddy 是前线，作为基线）
        - 长字符串优先替换（避免短词截断长短语，如 "Parallel Agent 调度" 应先于 "Parallel Agent"）
        - 简单字符串替换（无正则上下文判断），仅用于"normalize 后是否相等"的等价性比较
        - 不修改原文件，仅返回新字符串

    用途：体检静默 — 对每对 content-diff 文件，把 .claude/.codebuddy/ 双方都 normalize 后比较。
    若结果相等则视为方言-only 差异（豁免）。

    args:
        text: 原文本
        pairs: 形如 ``[{"kind": ..., "claude": "Read", "codebuddy": "read_file"}, ...]``

    returns:
        normalize 后的文本（所有 claude 形式被替换为 codebuddy 形式）
    """
    if not pairs:
        return text
    # 按 claude 字符串长度降序排序，长串先替换
    sorted_pairs = sorted(pairs, key=lambda p: -len(str(p.get("claude", ""))))
    out = text
    for p in sorted_pairs:
        c = p.get("claude")
        cb = p.get("codebuddy")
        if not c or cb is None:
            continue
        if c == cb:
            # 同名（如 Task ↔ Task）无需替换
            continue
        out = out.replace(c, cb)
    return out


def _is_paired_translation_only(rel: str, divergence: dict) -> bool:
    """检查双方文件 normalize 后是否完全相等（即差异仅来自方言映射）。

    返回 True 表示差异仅是"方言"，应被体检静默。
    """
    pairs = divergence.get("paired_translation", [])
    if not pairs:
        return False
    claude_path = paths.CLAUDE_ROOT / rel
    codebuddy_path = paths.CODEBUDDY_ROOT / rel
    if not claude_path.is_file() or not codebuddy_path.is_file():
        return False
    try:
        ct = claude_path.read_text(encoding="utf-8")
        bt = codebuddy_path.read_text(encoding="utf-8")
    except Exception:
        return False
    return normalize_text(ct, pairs) == normalize_text(bt, pairs)


def collect_mirror_report(
    divergence: dict | None = None,
) -> MirrorReport:
    """对账 `.claude/` 与 `.codebuddy/` 的全量文件。

    豁免来源：
        - 显式传入 `divergence` 参数
        - 否则使用 get_active_divergence()（DSL 优先，fallback 硬编码）
    """
    div = divergence if divergence is not None else get_active_divergence()
    report = MirrorReport()

    claude_files = _walk_files(paths.CLAUDE_ROOT)
    codebuddy_files = _walk_files(paths.CODEBUDDY_ROOT)

    all_files = claude_files | codebuddy_files

    for rel in sorted(all_files):
        # 跳过忽略前缀
        if any(rel.startswith(p) for p in IGNORE_PREFIXES):
            continue

        in_claude = rel in claude_files
        in_codebuddy = rel in codebuddy_files

        entry = FileEntry(rel_path=rel)

        if in_claude:
            cpath = paths.CLAUDE_ROOT / rel
            entry.sha_claude = _file_sha(cpath)
            entry.size_claude = cpath.stat().st_size
        if in_codebuddy:
            cbpath = paths.CODEBUDDY_ROOT / rel
            entry.sha_codebuddy = _file_sha(cbpath)
            entry.size_codebuddy = cbpath.stat().st_size

        report.entries[rel] = entry

        if in_claude and not in_codebuddy:
            if _is_only_on_platform_waived(rel, "claude_only", div):
                report.waived.append(f"[claude-only] {rel}")
            elif _is_content_diff_waived(rel, div):
                # 配对的另一文件名应该出现在 .codebuddy/，所以这里其实是 only-claude 的"按命名差异"
                report.waived.append(f"[paired-naming] {rel}")
            else:
                report.only_claude.append(rel)
        elif in_codebuddy and not in_claude:
            if _is_only_on_platform_waived(rel, "codebuddy_only", div):
                report.waived.append(f"[codebuddy-only] {rel}")
            elif _is_content_diff_waived(rel, div):
                report.waived.append(f"[paired-naming] {rel}")
            else:
                report.only_codebuddy.append(rel)
        else:
            # 双方都存在，比对内容
            if entry.sha_claude != entry.sha_codebuddy:
                if (_is_only_on_platform_waived(rel, "claude_only", div)
                        or _is_only_on_platform_waived(rel, "codebuddy_only", div)
                        or _is_content_diff_waived(rel, div)):
                    report.waived.append(f"[content-diff] {rel}")
                elif _is_paired_translation_only(rel, div):
                    # Phase 3-new：方言-only 差异（normalize 后双方相等）静默
                    report.waived.append(f"[paired-translation] {rel}")
                else:
                    report.content_diff.append(rel)

    return report
