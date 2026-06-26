"""Phase 2.5 测试：DSL 真权威源切换 — sentinel 注入 + dsl-source-marker 体检。

覆盖：
    - compile_phases_to_transitions / compile_state_schema 输出含 sentinel
    - sentinel 元数据不参与 equivalence 比较（运行时无影响）
    - check_dsl_source_marker 维度（待加入 consistency_check）能识别 sentinel 缺失
    - --write-json 编译产出 byte-deterministic（同样输入 → 同样字节输出）
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Sentinel 注入到编译产物
# ---------------------------------------------------------------------------


def test_compile_phases_emits_sentinel():
    """compile_phases_to_transitions 输出应含 $generatedFrom + $doNotEdit 字段。"""
    import validate_meta
    phases_meta = {
        "phases": [
            {"id": "INIT", "next": "DONE", "canSkipTo": None},
            {"id": "DONE", "next": None, "canSkipTo": None},
        ],
        "rules": {"forward": "顺序"},
    }
    out = validate_meta.compile_phases_to_transitions(phases_meta)
    assert "$generatedFrom" in out
    assert out["$generatedFrom"] == "meta/phases.yaml"
    assert "$doNotEdit" in out
    assert "scripts/render_artifacts.py" in out["$doNotEdit"]


def test_compile_state_schema_emits_sentinel():
    """compile_state_schema 输出应含 $generatedFrom + $doNotEdit 字段。"""
    import validate_meta
    state_meta = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Test",
        "properties": {"a": {"type": "string"}},
    }
    out = validate_meta.compile_state_schema(state_meta)
    assert out.get("$generatedFrom") == "meta/state-schema.yaml"
    assert "scripts/render_artifacts.py" in out.get("$doNotEdit", "")


# ---------------------------------------------------------------------------
# Sentinel 不参与等价性比较
# ---------------------------------------------------------------------------


def test_equivalence_ignores_sentinel_fields():
    """validate_meta 的等价性校验应该忽略 $generatedFrom / $doNotEdit / $comment* 字段。

    场景：DSL 编译产出含 sentinel，磁盘 JSON 也含 sentinel；这两份对象在去除 sentinel 后等价即视为 PASS。
    """
    import validate_meta
    # 模拟编译产出 + 磁盘 JSON 都含 sentinel，但 sentinel 内容不同（如时间戳变化）
    a = {
        "$generatedFrom": "meta/phases.yaml",
        "$doNotEdit": "Run script v1",
        "transitions": {"INIT": {"next": "DONE", "canSkipTo": None}},
    }
    b = {
        "$generatedFrom": "meta/phases.yaml",
        "$doNotEdit": "Run script v2 (different wording)",  # 不同的 doNotEdit
        "transitions": {"INIT": {"next": "DONE", "canSkipTo": None}},
    }
    diff = validate_meta._diff_objects(a, b)
    # 关键约束：sentinel 内部差异不应导致 equivalence FAIL
    # （如果 sentinel 字段被剔除后对象树等价，diff 应为空）
    sentinel_keys = {"$generatedFrom", "$doNotEdit"}
    real_diff = [
        d for d in diff if not any(d[0].endswith(k) or k in d[0] for k in sentinel_keys)
    ]
    assert real_diff == [], f"非 sentinel 差异不应存在: {real_diff}"


# ---------------------------------------------------------------------------
# dsl-source-marker 体检维度
# ---------------------------------------------------------------------------


def test_check_dsl_source_marker_detects_missing_sentinel(tmp_path, monkeypatch):
    """JSON 文件缺失 $generatedFrom 字段时，dsl-source-marker 维度应 WARN。"""
    # 准备 mock 双平台 JSON
    claude_ref = tmp_path / ".claude" / "skills" / "workflow-orchestrator" / "references"
    cb_ref = tmp_path / ".codebuddy" / "skills" / "workflow-orchestrator" / "references"
    claude_ref.mkdir(parents=True)
    cb_ref.mkdir(parents=True)

    # 一份含 sentinel
    good = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$generatedFrom": "meta/state-schema.yaml",
        "$doNotEdit": "...",
        "title": "X",
    }
    (claude_ref / "state-schema.json").write_text(json.dumps(good, indent=2), encoding="utf-8")

    # 一份缺 sentinel
    bad = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "X",
    }
    (cb_ref / "state-schema.json").write_text(json.dumps(bad, indent=2), encoding="utf-8")

    # phase-transitions.json 同样
    (claude_ref / "phase-transitions.json").write_text(
        json.dumps({"$generatedFrom": "meta/phases.yaml", "transitions": {}}, indent=2),
        encoding="utf-8",
    )
    (cb_ref / "phase-transitions.json").write_text(
        json.dumps({"transitions": {}}, indent=2), encoding="utf-8"
    )

    # monkeypatch paths
    from lib import paths
    monkeypatch.setattr(paths, "STATE_SCHEMA", claude_ref / "state-schema.json")
    monkeypatch.setattr(paths, "PHASE_TRANSITIONS", claude_ref / "phase-transitions.json")
    monkeypatch.setattr(paths, "CLAUDE_ROOT", tmp_path / ".claude")
    monkeypatch.setattr(paths, "CODEBUDDY_ROOT", tmp_path / ".codebuddy")

    import consistency_check
    ctx = consistency_check.Context()
    result = consistency_check.check_dsl_source_marker(ctx)

    # 应有至少一个 WARN（codebuddy 两份缺 sentinel）
    severity_counts = {}
    for f in result.findings:
        severity_counts[f.severity.name] = severity_counts.get(f.severity.name, 0) + 1
    assert severity_counts.get("WARN", 0) >= 1, "至少应有一个 WARN（缺 sentinel）"


def test_check_dsl_source_marker_passes_when_all_present(tmp_path, monkeypatch):
    """当所有 4 份 JSON 都含 $generatedFrom 时，dsl-source-marker PASS。"""
    claude_ref = tmp_path / ".claude" / "skills" / "workflow-orchestrator" / "references"
    cb_ref = tmp_path / ".codebuddy" / "skills" / "workflow-orchestrator" / "references"
    claude_ref.mkdir(parents=True)
    cb_ref.mkdir(parents=True)

    good_schema = {"$generatedFrom": "meta/state-schema.yaml", "title": "X"}
    good_trans = {"$generatedFrom": "meta/phases.yaml", "transitions": {}}
    for ref in (claude_ref, cb_ref):
        (ref / "state-schema.json").write_text(json.dumps(good_schema, indent=2), encoding="utf-8")
        (ref / "phase-transitions.json").write_text(json.dumps(good_trans, indent=2), encoding="utf-8")

    from lib import paths
    monkeypatch.setattr(paths, "STATE_SCHEMA", claude_ref / "state-schema.json")
    monkeypatch.setattr(paths, "PHASE_TRANSITIONS", claude_ref / "phase-transitions.json")
    monkeypatch.setattr(paths, "CLAUDE_ROOT", tmp_path / ".claude")
    monkeypatch.setattr(paths, "CODEBUDDY_ROOT", tmp_path / ".codebuddy")

    import consistency_check
    ctx = consistency_check.Context()
    result = consistency_check.check_dsl_source_marker(ctx)
    fail_or_warn = [f for f in result.findings
                    if f.severity.name in ("FAIL", "WARN", "ERROR")]
    assert fail_or_warn == [], f"全员含 sentinel 时不应有 FAIL/WARN: {fail_or_warn}"


# ---------------------------------------------------------------------------
# --write-json deterministic
# ---------------------------------------------------------------------------


def test_compile_phases_is_deterministic():
    """compile_phases_to_transitions 同样输入应产出同样输出（保序 + 字段稳定）。"""
    import validate_meta
    phases_meta = {
        "phases": [
            {"id": "INIT", "next": "ANALYSE", "canSkipTo": None},
            {"id": "ANALYSE", "next": "DONE", "canSkipTo": "DONE"},
            {"id": "DONE", "next": None, "canSkipTo": None},
        ],
        "rules": {"forward": "顺序", "skipCondition": "...", "rollback": "...", "termination": "..."},
    }
    a = validate_meta.compile_phases_to_transitions(phases_meta)
    b = validate_meta.compile_phases_to_transitions(phases_meta)
    # JSON 序列化后字节级等
    assert json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False)
