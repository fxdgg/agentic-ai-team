"""pytest 共享 fixture。

设计原则：
    - 每个 fixture 用 tmp_path 隔离，避免跨用例污染
    - 不依赖真实仓库内容，所有 mock 数据由 fixture 现场构造
    - lib/ 模块导入需要 scripts/ 在 sys.path，conftest 自动加载（pytest 约定）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让 lib/ 可被导入：将 scripts/ 加入 sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# 跳过低于 3.8 的 Python（与 lib/ 代码使用的 PEP 604 / dataclass 一致）
if sys.version_info < (3, 8):
    pytest.skip("ai-team 工具链需要 Python 3.8+", allow_module_level=True)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """构造一个最小双平台仓库结构。"""
    (tmp_path / ".claude" / "skills" / "workflow-orchestrator").mkdir(parents=True)
    (tmp_path / ".codebuddy" / "skills" / "workflow-orchestrator").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_quote_frontmatter_md(tmp_path: Path) -> Path:
    """生成含 quote-block frontmatter 的 markdown 文件（agents/*.md 风格）。"""
    p = tmp_path / "agent.md"
    p.write_text(
        "# Sample Agent\n\n"
        "> **状态**: active\n"
        "> **调用阶段**: ANALYSE_PRODUCT, ANALYSE_TECH\n"
        "> **团队**: product-analysts\n"
        "\n正文内容\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def sample_descriptive_frontmatter_md(tmp_path: Path) -> Path:
    """生成 frontmatter 值为描述性句子的 markdown（fact-checker.md 风格）。"""
    p = tmp_path / "fact-checker.md"
    p.write_text(
        "# Fact Checker\n\n"
        "> **状态**: dynamic\n"
        "> **调用阶段**: 由 archiver §17.5 在 ARCHIVE 阶段末尾委派调用\n"
        "\n正文\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def sample_gfm_table_md(tmp_path: Path) -> Path:
    """生成含 GFM 表格的 markdown。"""
    p = tmp_path / "table.md"
    p.write_text(
        "# Title\n\n"
        "| 列A | 列B | 列C |\n"
        "|-----|-----|-----|\n"
        "| a1  | b1  | c1  |\n"
        "| a2  | b2  | c2  |\n"
        "\n后续段落\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def sample_autogen_md(tmp_path: Path) -> Path:
    """生成已包裹 AUTO-GEN 区段的 markdown。"""
    body = (
        "# Doc\n\n"
        "<!-- BEGIN AUTO-GEN: test-section source=test hash=PLACEHOLDER -->\n"
        "\n表格内容\n\n"
        "<!-- END AUTO-GEN: test-section -->\n"
    )
    p = tmp_path / "with-block.md"
    p.write_text(body, encoding="utf-8")
    return p


@pytest.fixture
def sample_dsl_phases(tmp_path: Path) -> Path:
    """最小 phases.yaml DSL 样例。"""
    p = tmp_path / "phases.yaml"
    p.write_text(
        "phases:\n"
        "  - id: INIT\n"
        "    name: 初始化\n"
        "    order: 0\n"
        "    next: ANALYSE_PRODUCT\n"
        "  - id: ANALYSE_PRODUCT\n"
        "    name: 产品分析\n"
        "    order: 1\n"
        "    next: DONE\n"
        "  - id: DONE\n"
        "    name: 完成\n"
        "    order: 2\n"
        "    next: null\n"
        "rules:\n"
        "  forward: 顺序流转\n",
        encoding="utf-8",
    )
    return p
