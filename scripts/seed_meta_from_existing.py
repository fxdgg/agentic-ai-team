#!/usr/bin/env python3
"""反向生成 DSL：从现有 JSON Schema → meta/*.yaml DSL 草稿。

Phase 2 引入器：
    1. 读取 .claude/skills/workflow-orchestrator/references/phase-transitions.json
       → 写入 meta/phases.yaml（含 16 阶段流转 + rules 段）

    2. 读取 .claude/skills/workflow-orchestrator/references/state-schema.json
       → 写入 meta/state-schema.yaml（保留所有 31 顶层字段 + definitions）

    3. 读取 .claude/commands/*.md frontmatter
       → 写入 meta/commands.yaml（9 个命令）

设计目标：
    - 只在 meta/ 目录不存在或显式 --force 时生成（避免覆盖已手工编辑的 DSL）
    - 生成的 YAML 必须包含足够元数据，使 render_dsl_to_json.py 能编译产出
      与原 JSON byte-equal 的文件
    - 保留所有 description / examples / enum / pattern 等 JSON Schema 元数据

CLI:
    python scripts/seed_meta_from_existing.py --dry-run       # 预览
    python scripts/seed_meta_from_existing.py --write         # 写入 meta/
    python scripts/seed_meta_from_existing.py --write --force # 覆盖已存在的 meta/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import yaml
except ImportError as e:
    print("需要 PyYAML：pip install -r scripts/requirements.txt", file=sys.stderr)
    sys.exit(3)

from lib import paths


# ----------------------------------------------------------------------------
# 自定义 YAML dumper：保序 + 中文不转义 + 双引号优先
# ----------------------------------------------------------------------------

class StableDumper(yaml.SafeDumper):
    """保序 + 中文友好的 YAML dumper。"""
    pass


def _str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """字符串表示：含换行用 |- 块标量，否则用普通形式（不强制引号）。"""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


StableDumper.add_representer(str, _str_representer)
# 让 dict 按插入顺序输出（Python 3.7+ 默认保序）
StableDumper.add_representer(
    dict,
    lambda d, data: d.represent_dict(data.items()),
)


def dump_yaml(obj: object) -> str:
    return yaml.dump(
        obj,
        Dumper=StableDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )


# ----------------------------------------------------------------------------
# Seed phases.yaml
# ----------------------------------------------------------------------------

# 阶段中文名映射（来自 SKILL.md §2.1）— Phase 2 反向生成的种子
PHASE_CN_NAMES: dict[str, str] = {
    "INIT": "初始化",
    "ANALYSE_PRODUCT": "产品需求分析",
    "CLARIFY_PRODUCT": "产品需求澄清",
    "ANALYSE_TECH": "技术需求分析",
    "CLARIFY_TECH": "技术需求澄清",
    "ARCHITECT_BACKEND": "后端架构设计",
    "CLARIFY_ARCH_BACKEND": "后端架构澄清",
    "ARCHITECT_FRONTEND": "前端架构设计",
    "CLARIFY_ARCH_FRONTEND": "前端架构澄清",
    "IMPLEMENT": "代码实现",
    "BUILD_VERIFY": "编译验证",
    "VISUAL_REVIEW": "视觉验收",
    "E2E_VERIFY": "端到端链路验证",
    "TEST": "测试验证",
    "ARCHIVE": "完成归档",
    "DONE": "已完成",
}


def seed_phases_meta() -> dict:
    """从 phase-transitions.json + state-schema.json#PhaseId 反向生成 phases.yaml。"""
    pt = json.loads(paths.PHASE_TRANSITIONS.read_text(encoding="utf-8"))
    ss = json.loads(paths.STATE_SCHEMA.read_text(encoding="utf-8"))
    phase_ids = ss["definitions"]["PhaseId"]["enum"]

    transitions = pt["transitions"]
    rules = pt["rules"]

    phases_list = []
    for order, pid in enumerate(phase_ids):
        rule = transitions.get(pid, {})
        phase_entry = {
            "id": pid,
            "name": PHASE_CN_NAMES.get(pid, pid),
            "order": order,
            "next": rule.get("next"),
            "canSkipTo": rule.get("canSkipTo"),
        }
        # 三步模式标志（仅 INIT / DONE 为 false，其余 true）
        if pid in ("INIT", "DONE"):
            phase_entry["autoFlow"] = True
            phase_entry["threeStepMode"] = False
        else:
            phase_entry["autoFlow"] = False
            phase_entry["threeStepMode"] = True
        phases_list.append(phase_entry)

    return {
        "version": 1,
        "$comment": "由 scripts/seed_meta_from_existing.py 从 phase-transitions.json + state-schema.json#PhaseId 反向生成。"
                    "DSL 是 Phase 2 引入的单一真相源；编译产出的 phase-transitions.json 必须与原文件 byte-equal。",
        "phases": phases_list,
        "rules": {
            "forward": rules.get("forward", ""),
            "skipCondition": rules.get("skipCondition", ""),
            "rollback": rules.get("rollback", ""),
            "termination": rules.get("termination", ""),
        },
    }


# ----------------------------------------------------------------------------
# Seed state-schema.yaml
# ----------------------------------------------------------------------------

def seed_state_schema_meta() -> dict:
    """从 state-schema.json 直接转 YAML（保持结构完全一致）。

    YAML 自然保序，编译时直接 json.dump 即可产出 byte-equal JSON。
    """
    schema = json.loads(paths.STATE_SCHEMA.read_text(encoding="utf-8"))
    # 加一个顶层注释字段（不影响编译，YAML/JSON 兼容）
    return {
        "$comment": "由 scripts/seed_meta_from_existing.py 从 state-schema.json 反向生成。"
                    "DSL 是 Phase 2 引入的单一真相源；render_dsl_to_json.py 编译产出 state-schema.json。"
                    "若需要新增字段，应仅在本 YAML 编辑，编译后写回 JSON。",
        **schema,
    }


# ----------------------------------------------------------------------------
# Seed commands.yaml
# ----------------------------------------------------------------------------

YAML_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_yaml_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = YAML_FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path} 缺少 YAML frontmatter")
    return yaml.safe_load(m.group(1)) or {}


def seed_commands_meta() -> dict:
    """从 .claude/commands/*.md frontmatter 反向生成 commands.yaml。"""
    cmd_dir = paths.CLAUDE_COMMANDS
    if not cmd_dir.is_dir():
        raise FileNotFoundError(f"未找到目录：{cmd_dir}")

    commands_list = []
    for f in sorted(cmd_dir.glob("*.md")):
        try:
            fm = _parse_yaml_frontmatter(f)
        except ValueError as e:
            print(f"  ⚠ 跳过：{e}", file=sys.stderr)
            continue
        commands_list.append({
            "name": fm.get("name", f.stem),
            "description": fm.get("description", ""),
            "file": f"commands/{f.name}",
        })

    return {
        "version": 1,
        "$comment": "由 scripts/seed_meta_from_existing.py 从 .claude/commands/*.md frontmatter 反向生成。",
        "commands": commands_list,
    }


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="seed_meta_from_existing",
        description="从现有 JSON Schema / Agent frontmatter 反向生成 meta/*.yaml DSL 草稿",
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="预览生成的内容（不写入）")
    ap.add_argument("--write", action="store_true",
                    help="真正写入 meta/")
    ap.add_argument("--force", action="store_true",
                    help="允许覆盖已存在的 meta/*.yaml（危险）")
    ap.add_argument("--target", choices=["all", "phases", "state-schema", "commands"],
                    default="all",
                    help="选择性生成")
    args = ap.parse_args(argv)

    if not args.dry_run and not args.write:
        ap.print_help()
        print("\n请指定 --dry-run 或 --write", file=sys.stderr)
        return 3

    paths.META_DIR.mkdir(exist_ok=True)

    targets = []
    if args.target in ("all", "phases"):
        targets.append(("phases", paths.META_PHASES, seed_phases_meta))
    if args.target in ("all", "state-schema"):
        targets.append(("state-schema", paths.META_STATE_SCHEMA, seed_state_schema_meta))
    if args.target in ("all", "commands"):
        targets.append(("commands", paths.META_COMMANDS, seed_commands_meta))

    for name, dst, seed_fn in targets:
        try:
            data = seed_fn()
        except Exception as e:
            print(f"✗ {name} 生成失败：{type(e).__name__}: {e}", file=sys.stderr)
            return 3

        text = dump_yaml(data)
        rel_dst = paths.to_relative(dst)

        if args.dry_run:
            print(f"━━━ {rel_dst}（{len(text.splitlines())} 行）━━━")
            # 仅展示前 30 行 + 末尾 10 行
            lines = text.splitlines()
            for line in lines[:30]:
                print(line)
            if len(lines) > 40:
                print(f"... (省略 {len(lines) - 40} 行) ...")
                for line in lines[-10:]:
                    print(line)
            print()
            continue

        if dst.exists() and not args.force:
            print(f"⚠ {rel_dst} 已存在，跳过（加 --force 覆盖）")
            continue

        dst.write_text(text, encoding="utf-8")
        print(f"✓ 写入 {rel_dst}（{len(text.splitlines())} 行）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
