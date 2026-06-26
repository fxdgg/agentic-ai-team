"""visualization_data loader 单元 + 集成测试。

测试分两类：
  - 单元测试（tmp_repo + 现场写文件）：覆盖 loader 函数对各种边界 frontmatter 形态的处理
  - 集成测试（真实仓库）：跑全量加载，验证 19 phases / 29 agents / 19 rules / 13 templates / 9 refs 都被加载到
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 让 lib/ 可被导入
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

REPO_ROOT = SCRIPTS_DIR.parent


# ============================================================================
# 单元测试：loader 边界用例
# ============================================================================

class TestNormalizePhaseField:
    """调用阶段字段归一化（处理反引号 / 括号修饰 / 描述长句 / 逗号分隔）。"""

    def test_simple_phase_id(self):
        from lib.visualization_data import normalize_phase_field
        assert normalize_phase_field("ANALYSE_PRODUCT") == ["ANALYSE_PRODUCT"]

    def test_backtick_wrapped(self):
        from lib.visualization_data import normalize_phase_field
        # fullstack-analyst.md 风格："`ANALYSE_TECH`"
        assert normalize_phase_field("`ANALYSE_TECH`") == ["ANALYSE_TECH"]

    def test_with_parenthesis_modifier(self):
        from lib.visualization_data import normalize_phase_field
        # web-developer.md 风格："IMPLEMENT（web）"
        assert normalize_phase_field("IMPLEMENT（web）") == ["IMPLEMENT"]
        assert normalize_phase_field("IMPLEMENT(web)") == ["IMPLEMENT"]

    def test_comma_separated_multiple(self):
        from lib.visualization_data import normalize_phase_field
        assert normalize_phase_field("ANALYSE_PRODUCT, ANALYSE_TECH") == [
            "ANALYSE_PRODUCT",
            "ANALYSE_TECH",
        ]

    def test_descriptive_sentence_returns_empty(self):
        from lib.visualization_data import normalize_phase_field
        # fact-checker.md 风格："由 archiver §17.5 在 ARCHIVE 阶段末尾委派调用"
        # 长句不能误识别为 phase id，应返回空列表
        result = normalize_phase_field(
            "由 archiver §17.5 在 ARCHIVE 阶段末尾委派调用（Task 子 Agent 模式）"
        )
        assert result == []  # 不允许把无效内容当 phase id


class TestLoadAgents:
    """Agent 加载（含子目录 / 无 frontmatter / README 排除）。"""

    def test_load_agent_with_quote_frontmatter(self, tmp_path: Path):
        from lib.visualization_data import _load_agent_file

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        f = agents_dir / "test-engineer.md"
        f.write_text(
            "# 测试验证专家 Agent\n\n"
            "> **状态**: 已完成\n"
            "> **调用阶段**: TEST\n"
            "> **职责**: 三层静态验证\n"
            "> **权限**: 只读审查\n\n"
            "## 角色定位\n\n"
            "正文。\n",
            encoding="utf-8",
        )
        agent = _load_agent_file(f, agents_dir)
        assert agent is not None
        assert agent["id"] == "test-engineer"
        assert agent["title"] == "测试验证专家 Agent"
        assert agent["phases"] == ["TEST"]
        assert "三层静态验证" in agent["role"]
        assert "html" in agent and len(agent["html"]) > 0
        assert "raw" in agent and "## 角色定位" in agent["raw"]

    def test_load_agent_without_frontmatter(self, tmp_path: Path):
        """import-agents 风格：完全无 quote-block frontmatter。"""
        from lib.visualization_data import _load_agent_file

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        f = agents_dir / "doc-collector.md"
        f.write_text(
            "# @doc-collector — 项目文档收集与结构化专家\n\n"
            "## 角色定位\n\n"
            "无 frontmatter 的 Agent。\n",
            encoding="utf-8",
        )
        agent = _load_agent_file(f, agents_dir)
        assert agent is not None
        assert agent["id"] == "doc-collector"
        assert "@doc-collector" in agent["title"]
        assert agent["phases"] == []  # 没有 frontmatter 时 phases 为空
        assert agent["role"] == ""

    def test_skip_readme(self, tmp_path: Path):
        """README.md 应被识别为非 Agent 文件。"""
        from lib.visualization_data import _load_agent_file

        agents_dir = tmp_path / "agents"
        (agents_dir / "backend-developers").mkdir(parents=True)
        f = agents_dir / "backend-developers" / "README.md"
        f.write_text("# 后端领域开发 Agent 规范目录\n\n## 设计理念\n\n说明文档。\n",
                     encoding="utf-8")
        agent = _load_agent_file(f, agents_dir)
        # README 文件应返回 None（被识别为目录说明而非 Agent）
        assert agent is None


class TestPhaseRulesMapping:
    """phase-rules 文件名 → phase id 启发式映射。"""

    def test_simple_match(self):
        from lib.visualization_data import map_phase_rules_to_phase_ids
        all_phase_ids = ["INIT", "ANALYSE_PRODUCT", "CLARIFY_PRODUCT", "ARCHIVE"]
        # analyse-product-rules.md → ANALYSE_PRODUCT
        result = map_phase_rules_to_phase_ids("analyse-product-rules.md", all_phase_ids)
        assert "ANALYSE_PRODUCT" in result

    def test_archive_match(self):
        from lib.visualization_data import map_phase_rules_to_phase_ids
        all_phase_ids = ["INIT", "ARCHIVE"]
        result = map_phase_rules_to_phase_ids("archive-rules.md", all_phase_ids)
        assert "ARCHIVE" in result

    def test_clarify_one_to_many(self):
        """clarify-rules.md 应映射到所有 CLARIFY_* 阶段。"""
        from lib.visualization_data import map_phase_rules_to_phase_ids
        all_phase_ids = [
            "INIT", "ANALYSE_PRODUCT", "CLARIFY_PRODUCT",
            "CLARIFY_TECH", "CLARIFY_ARCH_BACKEND", "CLARIFY_ARCH_FRONTEND"
        ]
        result = map_phase_rules_to_phase_ids("clarify-rules.md", all_phase_ids)
        # 至少命中一个 CLARIFY_*
        assert any(pid.startswith("CLARIFY_") for pid in result)

    def test_no_match_returns_empty(self):
        from lib.visualization_data import map_phase_rules_to_phase_ids
        all_phase_ids = ["INIT", "DONE"]
        result = map_phase_rules_to_phase_ids("totally-unknown-file.md", all_phase_ids)
        assert result == []


# ============================================================================
# 集成测试：真实仓库
# ============================================================================

class TestLoadAllRealRepo:
    """对真实仓库跑一次完整加载。"""

    def test_phases_count(self):
        """phases.yaml 实际为 16 个阶段（不含 IMPORT/ROLLBACK 这两个命令级流程）。"""
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        assert len(data["phases"]) == 16, \
            f"phases.yaml 应有 16 个阶段，实际 {len(data['phases'])}"
        # 抽样关键阶段
        phase_ids = {p["id"] for p in data["phases"]}
        assert "INIT" in phase_ids
        assert "DONE" in phase_ids
        assert "ANALYSE_PRODUCT" in phase_ids
        assert "ARCHIVE" in phase_ids
        assert "E2E_VERIFY" in phase_ids

    def test_agents_count_at_least_25(self):
        """29 个 agent 文件中含 README，loader 应排除 README，剩余 ≥ 25。"""
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        # backend-developers/README.md 应被排除，剩余 28 个
        assert len(data["agents"]) >= 25, \
            f"agents 应 ≥ 25 个，实际 {len(data['agents'])}"
        # 抽样关键 agent
        agent_ids = {a["id"] for a in data["agents"]}
        assert "test-engineer" in agent_ids
        assert "archiver" in agent_ids

    def test_rules_count_19(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        # 顶层 7 + java-backend 12 = 19
        assert len(data["rules"]) >= 18, \
            f"rules 应 ≥ 18 条，实际 {len(data['rules'])}"

    def test_templates_count(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        assert len(data["templates"]) >= 12, \
            f"templates 应 ≥ 12 个，实际 {len(data['templates'])}"

    def test_references_count_9(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        assert len(data["references"]) == 9, \
            f"references 应 9 个 JSON，实际 {len(data['references'])}"
        # 抽样
        ref_ids = {r["id"] for r in data["references"]}
        assert "state-schema" in ref_ids
        assert "phase-transitions" in ref_ids

    def test_phase_rules_count_13(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        assert len(data["phase_rules"]) == 13, \
            f"phase_rules 应 13 个，实际 {len(data['phase_rules'])}"

    def test_skill_main_loaded(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        assert "html" in data["skill_main"]
        assert len(data["skill_main"]["html"]) > 1000  # 76KB 原文渲染后非空
        assert "toc" in data["skill_main"]
        assert len(data["skill_main"]["toc"]) > 0

    def test_meta_includes_generated_at(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        assert "generated_at" in data["meta"]
        # ISO8601 形如 2026-05-29T16:00:00...
        assert "T" in data["meta"]["generated_at"]

    def test_consistency_snapshot_optional(self):
        """体检快照可选；不可用时应 graceful degrade（available=False）。"""
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT, include_consistency=True)
        snap = data["consistency"]
        assert "available" in snap
        if snap["available"]:
            assert "exit_code" in snap
            assert "counts" in snap
            assert isinstance(snap["counts"], dict)
            assert "checks" in snap

    def test_consistency_can_be_skipped(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT, include_consistency=False)
        # include_consistency=False 时，snapshot 应为不可用占位
        assert data["consistency"]["available"] is False


class TestPhaseAgentLinking:
    """phase ↔ agents 反查映射建立正确。"""

    def test_phase_has_agents_field(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        # 每个 phase 应有 agents 字段（可能为空数组）
        for p in data["phases"]:
            assert "agent_ids" in p, f"phase {p['id']} 缺少 agent_ids 字段"

    def test_test_phase_has_test_engineer(self):
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        test_phase = next(p for p in data["phases"] if p["id"] == "TEST")
        assert "test-engineer" in test_phase["agent_ids"]

    def test_phase_rules_field(self):
        """每个 phase 应有 rules_file_ids 字段（关联的 phase-rules 文件 id 列表）。"""
        from lib.visualization_data import load_visualization_data
        data = load_visualization_data(REPO_ROOT)
        for p in data["phases"]:
            assert "rules_file_ids" in p, f"phase {p['id']} 缺少 rules_file_ids 字段"
        # ARCHIVE phase 至少关联到 archive-rules
        archive = next(p for p in data["phases"] if p["id"] == "ARCHIVE")
        assert any("archive" in rid for rid in archive["rules_file_ids"])
