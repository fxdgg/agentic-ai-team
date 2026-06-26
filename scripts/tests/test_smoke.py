"""冒烟测试：验证 pytest 骨架可运行，lib/ 可被导入。"""
from __future__ import annotations


def test_pytest_runs():
    """最简单的 pass 测试。"""
    assert 1 + 1 == 2


def test_lib_importable():
    """conftest 应已把 scripts/ 加入 sys.path，lib/ 可直接导入。"""
    from lib import paths  # noqa: F401
    from lib import md_parser  # noqa: F401
    from lib import autogen_block  # noqa: F401
    from lib import meta_loader  # noqa: F401
    from lib import platform_mirror  # noqa: F401


def test_fixture_tmp_repo(tmp_repo):
    """tmp_repo fixture 构造的双平台目录存在。"""
    assert (tmp_repo / ".claude" / "skills" / "workflow-orchestrator").is_dir()
    assert (tmp_repo / ".codebuddy" / "skills" / "workflow-orchestrator").is_dir()
