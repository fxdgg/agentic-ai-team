"""工作流可视化数据采集层。

职责：扫描 .codebuddy/skills/workflow-orchestrator/{phases,agents,rules,templates,references}
+ SKILL.md + meta/*.yaml + 调用 consistency_check.py 子进程，编译为标准化数据字典供
html_renderer.render_html() 消费。

设计原则：
    - **codebuddy-first**：v2 修正后的双平台方向，仅读 .codebuddy/（前线）
    - **缺失容忍**：单个 .md 解析失败不阻断全量加载；记录到 issues 列表
    - **graceful degrade**：consistency_check 子进程失败 → snapshot.available=False
    - **零依赖**：仅用 stdlib + lib.* 已有模块（不引 markdown 包等新依赖）

承诺三段式声明（见 plan.md 实施要点）：
    硬承诺：
        - 19 phases / ≥25 agents / ≥18 rules / ≥12 templates / 9 references / 13 phase_rules 全量加载
        - 调用阶段字段归一化处理 5 种变体（裸 ID / 反引号 / 括号修饰 / 描述长句 / 逗号分隔）
        - phase ↔ agents / phase ↔ rules_files 反查映射建立
    软承诺：
        - 启发式 phase-rules → phase id 映射尽力而为；命中率 ≥ 80%
        - JSON references 的 schema 解读尽量结构化（不深入解析 $ref）
    不承诺：
        - 不解析 SKILL.md 主体超过 H3 的标题（TOC 仅取 H1/H2/H3）
        - 不缓存 / 不增量；每次全量加载（19+29+19+13+9 ~ 100 个文件，<1s）
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from . import md_parser, meta_loader, paths


# ============================================================================
# 调用阶段字段归一化
# ============================================================================

# 合法的 phase id 形态：全大写字母 + 下划线 + 数字（不少于 2 字符）
_PHASE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")


def normalize_phase_field(value: str) -> list[str]:
    """将 quote-block frontmatter 中"调用阶段"字段的字符串值归一化为 phase id 列表。

    支持的输入形态（基于 .codebuddy/.../agents/*.md 的实际 5 种变体）：
        "ANALYSE_PRODUCT"                                  → ["ANALYSE_PRODUCT"]
        "`ANALYSE_TECH`"                                   → ["ANALYSE_TECH"]
        "IMPLEMENT（web）" / "IMPLEMENT(web)"              → ["IMPLEMENT"]
        "ANALYSE_PRODUCT（Agent Teams 模式下，仅迭代需求）" → ["ANALYSE_PRODUCT"]
            （括号内含中文逗号但本质仍是单 phase + 描述性后缀）
        "ANALYSE_PRODUCT, ANALYSE_TECH"                    → ["ANALYSE_PRODUCT", "ANALYSE_TECH"]
        "由 archiver §17.5 在 ARCHIVE 阶段末尾委派调用"  → []  （描述长句拒绝）

    规则（顺序很重要）：
        1. 优先剥离括号修饰（贪婪到字符串尾，处理括号未闭合的情况）
        2. 用逗号 / 顿号 / 中英文分号分割多 phase
        3. 剥离反引号 / 前后空白
        4. 仅保留通过 _PHASE_ID_RE 校验的 token
        5. 单 token 长度超 40 视为描述句残骸
    """
    if not value:
        return []

    # 长度 + 关键词阈值：纯描述句直接拒绝
    if any(zh in value for zh in ["由 ", "委派", "末尾", "Task 子 Agent"]) and "," not in value and "，" not in value:
        # 必须满足两条：包含描述性关键词 + 没有顶层逗号
        return []

    # 1) 剥离括号（贪婪到结尾，处理未闭合）
    cleaned = re.sub(r"[（(][^）)]*[）)]?$", "", value).strip()

    # 2) 分隔符：英文逗号/中文逗号/英文分号/中文分号/顿号
    parts = re.split(r"[,，;；、]", cleaned)
    out: list[str] = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        # 剥离反引号
        token = token.strip("`")
        # 二次括号剥离（应对中段也含括号的情况）
        token = re.sub(r"[（(][^）)]*[）)]?", "", token).strip()
        # 长度限制（剥完仍超长 → 描述句残骸）
        if len(token) > 40:
            continue
        # 必须匹配 phase id 形态
        if _PHASE_ID_RE.match(token):
            out.append(token)
    return out


# ============================================================================
# 极简 markdown → HTML 渲染（被 loader 用来预编译 .md 为 HTML 字符串）
# ----------------------------------------------------------------------------
# 注：完整渲染器在 html_renderer.md_to_html，此处导入避免循环。
# ============================================================================

def _md_render(text: str) -> str:
    """统一通过 html_renderer.md_to_html 渲染（延迟导入避免循环）。"""
    from . import html_renderer
    return html_renderer.md_to_html(text)


# ============================================================================
# 文件级 loader 辅助
# ============================================================================

def _file_id(path: Path, base: Path) -> str:
    """生成文件 id（相对于 base 的 POSIX 路径，去除 .md 后缀）。"""
    rel = path.relative_to(base).as_posix()
    if rel.endswith(".md"):
        rel = rel[:-3]
    elif rel.endswith(".json"):
        rel = rel[:-5]
    return rel


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _file_size(path: Path) -> int:
    return path.stat().st_size


# ============================================================================
# Agents loader
# ============================================================================

def _load_agent_file(path: Path, agents_root: Path) -> dict | None:
    """加载单个 Agent 文件。README.md 返回 None。

    返回 dict schema：
        {
          "id": "test-engineer" | "build-verifiers/backend-build-verifier",
          "title": H1 标题,
          "phases": [phase_id, ...],   # 由 normalize_phase_field 处理
          "role": frontmatter.fields["职责"] (若有),
          "permissions": frontmatter.fields["权限"] (若有),
          "team": frontmatter.fields["agent-teams-成员名"] (若有),
          "html": markdown 渲染后 HTML,
          "raw": 原始 markdown 文本,
          "file": 相对仓库根的 POSIX 路径,
          "size": 字节数
        }
    """
    name = path.name
    if name.lower() == "readme.md":
        return None
    text = _read_text(path)
    fm = md_parser.parse_quote_frontmatter(text)
    title = fm.title or path.stem
    phases_raw = fm.fields.get("调用阶段") or fm.fields.get("调用-阶段") or ""
    phases = normalize_phase_field(phases_raw)
    return {
        "id": _file_id(path, agents_root),
        "title": title,
        "phases": phases,
        "role": fm.fields.get("职责", ""),
        "permissions": fm.fields.get("权限", ""),
        "team": fm.fields.get("agent-teams-成员名", "") or fm.fields.get("agent-teams-成员名", ""),
        "raw_phase_field": phases_raw,
        "html": _md_render(text),
        "raw": text,
        "file": paths.to_relative(path),
        "size": _file_size(path),
    }


def _load_agents(skill_root: Path) -> list[dict]:
    """递归加载 agents/ 目录下所有 .md（含子目录）。"""
    agents_dir = skill_root / "agents"
    if not agents_dir.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(agents_dir.rglob("*.md")):
        agent = _load_agent_file(f, agents_dir)
        if agent is not None:
            out.append(agent)
    return out


# ============================================================================
# Rules / Templates loader（结构相近）
# ============================================================================

def _load_md_collection(root: Path, kind: str) -> list[dict]:
    """加载 rules/ 或 templates/ 目录下的 .md 文件（递归）。"""
    out: list[dict] = []
    if not root.is_dir():
        return out
    for f in sorted(root.rglob("*.md")):
        # 跳过子目录的 README.md（如有）
        if f.name.lower() == "readme.md" and f.parent != root:
            continue
        text = _read_text(f)
        title = md_parser.find_h1_title(text) or f.stem
        out.append({
            "id": _file_id(f, root),
            "title": title,
            "html": _md_render(text),
            "raw": text,
            "file": paths.to_relative(f),
            "size": _file_size(f),
            "kind": kind,
        })
    return out


# ============================================================================
# References loader（JSON 文件）
# ============================================================================

def _load_references(skill_root: Path) -> list[dict]:
    """加载 references/*.json，以代码块呈现。"""
    refs_dir = skill_root / "references"
    if not refs_dir.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(refs_dir.glob("*.json")):
        text = _read_text(f)
        # 尝试解析以提取 title / description（schema draft-07 通常含）
        title = f.stem
        description = ""
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                title = data.get("title", title)
                description = data.get("description", "")
        except json.JSONDecodeError:
            pass
        out.append({
            "id": _file_id(f, refs_dir),
            "title": title,
            "description": description,
            "json_text": text,           # 原始 JSON 文本（用于代码块呈现）
            "file": paths.to_relative(f),
            "size": _file_size(f),
        })
    return out


# ============================================================================
# Phase rules loader + phase 启发式映射
# ============================================================================

# phase id 到关键词的反向映射（用于启发式匹配 phase-rules 文件名）
_PHASE_KEYWORDS: dict[str, list[str]] = {
    "ANALYSE_PRODUCT": ["analyse-product", "product-analyse"],
    "CLARIFY_PRODUCT": ["clarify-product"],
    "ANALYSE_TECH": ["analyse-tech", "tech-analyse"],
    "CLARIFY_TECH": ["clarify-tech"],
    "ARCHITECT_BACKEND": ["architect-backend"],
    "CLARIFY_ARCH_BACKEND": ["clarify-arch-backend"],
    "ARCHITECT_FRONTEND": ["architect-frontend"],
    "CLARIFY_ARCH_FRONTEND": ["clarify-arch-frontend"],
    "IMPLEMENT": ["implement"],
    "TEST": ["test"],
    "BUILD_VERIFY": ["build-verify"],
    "VISUAL_REVIEW": ["visual-review"],
    "ARCHIVE": ["archive"],
    "IMPORT": ["import"],
    "ROLLBACK": ["rollback"],
    "INIT": ["init"],
    "DONE": ["done"],
}


def map_phase_rules_to_phase_ids(file_name: str, all_phase_ids: list[str]) -> list[str]:
    """启发式：根据 phase-rules 文件名匹配到 1 或多个 phase id。

    规则：
        1. 先用 _PHASE_KEYWORDS 反向查（精确）：每个 phase 的关键词若是 file 的 prefix，命中
        2. 通配 clarify-rules.md → 所有 CLARIFY_* phases
        3. 文件名命中多个关键词时，取最长 prefix 优先（避免 implement 误匹配 implement-foo）
    """
    name = file_name.lower()
    if name.endswith(".md"):
        name = name[:-3]

    matched: list[tuple[str, int]] = []  # (phase_id, prefix_len)
    for pid in all_phase_ids:
        for kw in _PHASE_KEYWORDS.get(pid, [pid.lower().replace("_", "-")]):
            if name.startswith(kw):
                matched.append((pid, len(kw)))
                break  # 该 phase 已命中，下一个

    # 通配规则：clarify-rules.md → 所有 CLARIFY_* phases
    if name == "clarify-rules" or name.startswith("clarify-rules-"):
        for pid in all_phase_ids:
            if pid.startswith("CLARIFY_") and pid not in [m[0] for m in matched]:
                matched.append((pid, 0))

    if not matched:
        return []

    # 取所有命中的 phase id（多对多映射允许）
    return [m[0] for m in matched]


def _load_phase_rules(skill_root: Path, all_phase_ids: list[str]) -> list[dict]:
    """加载 phases/ 目录下的 phase-rules .md 文件。"""
    phases_dir = skill_root / "phases"
    if not phases_dir.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(phases_dir.glob("*.md")):
        text = _read_text(f)
        title = md_parser.find_h1_title(text) or f.stem
        phase_ids = map_phase_rules_to_phase_ids(f.name, all_phase_ids)
        out.append({
            "id": _file_id(f, phases_dir),
            "title": title,
            "phase_ids": phase_ids,
            "html": _md_render(text),
            "raw": text,
            "file": paths.to_relative(f),
            "size": _file_size(f),
        })
    return out


# ============================================================================
# SKILL.md 主文档 loader（含 TOC 提取）
# ============================================================================

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


def _extract_toc(text: str) -> list[dict]:
    """提取 H1/H2/H3 标题作为 TOC。
    返回：[{"level": 1|2|3, "text": "...", "anchor": "slug"}]
    代码块 ``` 内的 # 不视为标题。
    """
    out: list[dict] = []
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            txt = m.group(2).strip()
            anchor = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", txt).strip("-").lower()
            out.append({"level": level, "text": txt, "anchor": anchor})
    return out


def _load_skill_main(skill_root: Path) -> dict:
    """加载 SKILL.md 主文档。"""
    skill_md = skill_root / "SKILL.md"
    if not skill_md.is_file():
        return {"toc": [], "html": "", "raw": "", "file": "", "size": 0}
    text = _read_text(skill_md)
    return {
        "toc": _extract_toc(text),
        "html": _md_render(text),
        "raw": text,
        "file": paths.to_relative(skill_md),
        "size": _file_size(skill_md),
    }


# ============================================================================
# Consistency check 快照（子进程调用）
# ============================================================================

def _load_consistency_snapshot(repo_root: Path) -> dict:
    """子进程调用 consistency_check.py --format=json，失败时 graceful degrade。"""
    script = repo_root / "scripts" / "consistency_check.py"
    if not script.is_file():
        return {"available": False, "reason": "consistency_check.py not found"}
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--format=json"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        payload = json.loads(result.stdout)
        return {
            "available": True,
            "exit_code": payload.get("exit_code"),
            "counts": payload.get("counts", {}),
            "summary": payload.get("summary", {}),
            "checks": payload.get("checks", []),
            "title": payload.get("title", ""),
        }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


# ============================================================================
# 主入口：load_visualization_data
# ============================================================================

def _git_short_sha(repo_root: Path) -> str | None:
    """优雅获取当前 commit 短 SHA；非 git 仓库 / git 不可用时返回 None。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _codebuddy_skill_root(repo_root: Path) -> Path:
    """codebuddy-first：返回 .codebuddy/skills/workflow-orchestrator/。"""
    return repo_root / ".codebuddy" / "skills" / "workflow-orchestrator"


def _load_phase_io(repo_root: Path) -> dict:
    """加载 meta/phase-io.yaml（可视化专用补充：分组 + 输入/输出产物）。

    该文件不属于 DSL 真相源，缺失或解析失败时 graceful degrade（返回空结构，
    可视化降级为不展示分组与输入输出区块，不报错）。

    返回 schema::
        {
          "groups": [{"id", "name", "color", "bg"}, ...],
          "phase_io": {phase_id: {"group", "inputs": [...], "outputs": [...]}}
        }
    """
    path = repo_root / "meta" / "phase-io.yaml"
    try:
        data = meta_loader._load_yaml(path)
    except Exception:
        data = None
    if not isinstance(data, dict):
        return {"groups": [], "phase_io": {}}
    groups = data.get("groups") or []
    phase_io = data.get("phase_io") or {}
    if not isinstance(groups, list):
        groups = []
    if not isinstance(phase_io, dict):
        phase_io = {}
    return {"groups": groups, "phase_io": phase_io}


def load_visualization_data(
    repo_root: Path | None = None,
    *,
    include_consistency: bool = True,
) -> dict[str, Any]:
    """加载完整可视化数据字典。

    参数：
        repo_root: 仓库根；None 时自动定位
        include_consistency: 是否调用 consistency_check 子进程获取快照

    返回 schema：
        {
          "meta": {"generated_at": ISO8601, "commit": short_sha or None,
                   "issues": [...]},
          "phases": [{id, name, order, next, canSkipTo, autoFlow, threeStepMode,
                      agent_ids, rules_file_ids}],
          "agents": [{id, title, phases, role, permissions, team, html, raw,
                      file, size, raw_phase_field}],
          "rules":  [{id, title, html, raw, file, size, kind}],
          "templates": [...],
          "references": [{id, title, description, json_text, file, size}],
          "phase_rules": [{id, title, phase_ids, html, raw, file, size}],
          "skill_main": {toc, html, raw, file, size},
          "consistency": {available, exit_code, counts, checks, ...}
        }
    """
    if repo_root is None:
        repo_root = paths.REPO_ROOT
    repo_root = Path(repo_root).resolve()
    skill_root = _codebuddy_skill_root(repo_root)

    issues: list[str] = []

    # 1) DSL phases
    phases_meta = meta_loader.load_phases_meta()
    if phases_meta is None or "phases" not in phases_meta:
        issues.append("meta/phases.yaml 缺失或格式异常")
        phases_list: list[dict] = []
    else:
        phases_list = list(phases_meta["phases"])

    all_phase_ids = [p["id"] for p in phases_list]

    # 2) 各 .md 集合
    agents = _load_agents(skill_root)
    rules = _load_md_collection(skill_root / "rules", kind="rules")
    templates = _load_md_collection(skill_root / "templates", kind="templates")
    references = _load_references(skill_root)
    phase_rules = _load_phase_rules(skill_root, all_phase_ids)
    skill_main = _load_skill_main(skill_root)

    # 3) 反查映射：phase → agents / phase → rules_files
    phase_to_agents: dict[str, list[str]] = {pid: [] for pid in all_phase_ids}
    for ag in agents:
        for pid in ag["phases"]:
            if pid in phase_to_agents:
                phase_to_agents[pid].append(ag["id"])

    phase_to_rules_files: dict[str, list[str]] = {pid: [] for pid in all_phase_ids}
    for pr in phase_rules:
        for pid in pr["phase_ids"]:
            if pid in phase_to_rules_files:
                phase_to_rules_files[pid].append(pr["id"])

    # phase-io.yaml：分组 + 输入/输出产物（可视化专用补充，缺失则降级）
    phase_io_data = _load_phase_io(repo_root)
    groups = phase_io_data["groups"]
    phase_io = phase_io_data["phase_io"]
    group_by_id = {g.get("id"): g for g in groups if isinstance(g, dict)}

    enriched_phases: list[dict] = []
    for p in phases_list:
        pid = p["id"]
        enriched = dict(p)
        enriched["agent_ids"] = phase_to_agents.get(pid, [])
        enriched["rules_file_ids"] = phase_to_rules_files.get(pid, [])
        # enrich phase-io（缺失则空）
        io = phase_io.get(pid, {}) if isinstance(phase_io, dict) else {}
        group_id = io.get("group", "")
        grp = group_by_id.get(group_id, {})
        enriched["group"] = group_id
        enriched["group_name"] = grp.get("name", "")
        enriched["group_color"] = grp.get("color", "#57606A")
        enriched["group_bg"] = grp.get("bg", "#F0F1F3")
        enriched["inputs"] = list(io.get("inputs") or [])
        enriched["outputs"] = list(io.get("outputs") or [])
        enriched_phases.append(enriched)

    # 4) consistency snapshot
    if include_consistency:
        consistency = _load_consistency_snapshot(repo_root)
    else:
        consistency = {"available": False, "reason": "skipped by caller"}

    return {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "commit": _git_short_sha(repo_root),
            "issues": issues,
            "repo_root": paths.to_relative(repo_root),
        },
        "groups": groups,
        "phases": enriched_phases,
        "agents": agents,
        "rules": rules,
        "templates": templates,
        "references": references,
        "phase_rules": phase_rules,
        "skill_main": skill_main,
        "consistency": consistency,
    }
