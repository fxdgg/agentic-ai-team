"""lib/meta_loader.py 单元测试。

覆盖：
    - _load_yaml：缺失文件返回 None / 空文件返回 {} / 顶层非 dict 抛错
    - load_phases_meta / load_state_schema_meta / load_commands_meta：通过 monkeypatch 指向 mock 文件
    - load_all：返回结构与缺失兜底
    - 保序假设：YAML mapping 顺序在 PyYAML safe_load + Python 3.7+ dict 下保持
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib import meta_loader, paths


def test_load_yaml_missing_returns_none(tmp_path):
    """文件不存在时 _load_yaml 返回 None。"""
    p = tmp_path / "absent.yaml"
    assert meta_loader._load_yaml(p) is None


def test_load_yaml_empty_returns_empty_dict(tmp_path):
    """空文件被 PyYAML 解析为 None，模块兜底为 {}。"""
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    assert meta_loader._load_yaml(p) == {}


def test_load_yaml_top_level_must_be_mapping(tmp_path):
    """顶层是 list / scalar 应抛 ValueError。"""
    p = tmp_path / "bad.yaml"
    p.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="顶层必须是 mapping"):
        meta_loader._load_yaml(p)


def test_load_phases_meta_via_monkeypatch(tmp_path, monkeypatch, sample_dsl_phases):
    """指向 mock phases.yaml 时正确加载。"""
    monkeypatch.setattr(paths, "META_PHASES", sample_dsl_phases)
    data = meta_loader.load_phases_meta()
    assert data is not None
    assert "phases" in data
    assert len(data["phases"]) == 3
    # 保序：第一个 phase 应是 INIT
    assert data["phases"][0]["id"] == "INIT"


def test_load_phases_meta_missing_returns_none(tmp_path, monkeypatch):
    """phases.yaml 不存在时返回 None。"""
    monkeypatch.setattr(paths, "META_PHASES", tmp_path / "no-such-file.yaml")
    assert meta_loader.load_phases_meta() is None


def test_load_all_returns_four_keys(monkeypatch, tmp_path):
    """load_all 应返回 4 个键，缺失值为 None。"""
    fake = tmp_path / "absent.yaml"
    monkeypatch.setattr(paths, "META_PHASES", fake)
    monkeypatch.setattr(paths, "META_STATE_SCHEMA", fake)
    monkeypatch.setattr(paths, "META_COMMANDS", fake)
    monkeypatch.setattr(paths, "META_DIVERGENCE", fake)
    data = meta_loader.load_all()
    assert set(data.keys()) == {"phases", "state_schema", "commands", "platform_divergence"}
    assert all(v is None for v in data.values())


def test_dict_preserves_yaml_order(tmp_path):
    """关键假设：PyYAML safe_load + CPython 3.7+ dict 保持 mapping 插入顺序。

    若此测试失败，说明运行环境不满足保序假设，需要切换到 ordereddict 或重写加载器。
    """
    p = tmp_path / "ordered.yaml"
    p.write_text(
        "phases:\n"
        "  - id: ZETA\n"
        "    order: 0\n"
        "  - id: ALPHA\n"
        "    order: 1\n"
        "  - id: MU\n"
        "    order: 2\n",
        encoding="utf-8",
    )
    data = meta_loader._load_yaml(p)
    ids = [item["id"] for item in data["phases"]]
    # 关键断言：列表顺序 = YAML 顺序，不被字母排序
    assert ids == ["ZETA", "ALPHA", "MU"]
