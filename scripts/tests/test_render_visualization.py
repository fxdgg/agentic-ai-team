"""scripts/render_visualization.py 主脚本端到端测试。

测试 CLI：
  - 默认 dry-run 不写盘
  - --write 写到 docs/workflow-visualization.html
  - --check 仅校验产物存在性 + 语法
  - --format=json 输出 JSON
  - 退出码 0/1/2/3 协议
  - 产物 HTML 含必要锚点 + 不含外部依赖
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent
SCRIPT = SCRIPTS_DIR / "render_visualization.py"


def _run(*args, cwd=REPO_ROOT) -> subprocess.CompletedProcess:
    """运行 render_visualization.py 子进程。"""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


class TestCLI:
    def test_script_exists(self):
        assert SCRIPT.is_file(), f"主脚本应存在：{SCRIPT}"

    def test_dry_run_default(self):
        """默认 dry-run，stdout 含统计且不应写产物（如已存在则不修改）。"""
        result = _run()
        # dry-run 退出码：0（默认数据齐全）/ 1（有 INFO/WARN）；不是 ERROR
        assert result.returncode in (0, 1), \
            f"dry-run 退出码异常：{result.returncode}\nstderr: {result.stderr}"
        # 输出含统计
        out = result.stdout + result.stderr
        assert any(kw in out for kw in ["phases", "Phases", "节点", "阶段"]), \
            f"dry-run 输出缺少统计信息: {out[:500]}"

    def test_write_creates_html(self, tmp_path: Path):
        """--write 应在仓库 docs/ 下生成 HTML 文件。"""
        target = REPO_ROOT / "docs" / "workflow-visualization.html"
        # 记录原始大小（如有）
        original_existed = target.is_file()

        result = _run("--write")
        assert result.returncode in (0, 1), \
            f"--write 退出码异常：{result.returncode}\nstderr: {result.stderr}"
        assert target.is_file(), "docs/workflow-visualization.html 应被创建"
        size = target.stat().st_size
        assert size > 50_000, f"产物 HTML 体积过小（{size} bytes），数据未嵌入"

    def test_html_artifact_has_anchors(self):
        """已生成产物应含必要锚点。"""
        target = REPO_ROOT / "docs" / "workflow-visualization.html"
        if not target.is_file():
            pytest.skip("产物不存在，跳过；先跑 test_write_creates_html")
        content = target.read_text(encoding="utf-8")
        # 双平台都不引入这条
        assert content.startswith("<!DOCTYPE html>") or content.startswith("<!doctype html>")
        assert 'id="__DATA__"' in content
        # 7 个 Tab
        for tab in ["phases", "agents", "rules", "templates", "references", "skill", "health"]:
            assert f'data-tab="{tab}"' in content, f"缺少 Tab {tab}"
        # 19 个 phase 锚点抽样
        assert 'data-phase-id="INIT"' in content
        assert 'data-phase-id="ANALYSE_PRODUCT"' in content
        assert 'data-phase-id="DONE"' in content

    def test_html_artifact_no_external_deps(self):
        target = REPO_ROOT / "docs" / "workflow-visualization.html"
        if not target.is_file():
            pytest.skip("产物不存在")
        content = target.read_text(encoding="utf-8")
        # 不引外部 CDN/库
        assert "cdn.jsdelivr" not in content.lower()
        assert "unpkg.com" not in content.lower()
        assert "cdnjs.cloudflare" not in content.lower()
        # 不引 mermaid / marked / cytoscape 关键字
        for forbidden in ["mermaid.min.js", "marked.min.js", "cytoscape.min.js"]:
            assert forbidden not in content.lower(), f"产物含外部依赖 {forbidden}"

    def test_format_json_output(self):
        """--format=json 应输出 reporters Report JSON。"""
        result = _run("--format=json")
        assert result.returncode in (0, 1), \
            f"--format=json 退出码异常：{result.returncode}\nstderr: {result.stderr}"
        # stdout 应为合法 JSON
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"--format=json stdout 非 JSON: {result.stdout[:300]}")
        assert "exit_code" in payload
        assert "counts" in payload
        assert "checks" in payload

    def test_check_mode_no_write(self):
        """--check 模式不写产物，仅校验现有产物（若存在）。"""
        target = REPO_ROOT / "docs" / "workflow-visualization.html"
        # 先跑 --write 确保产物存在
        _run("--write")
        before_mtime = target.stat().st_mtime if target.is_file() else None

        # --check 模式
        result = _run("--check")
        assert result.returncode in (0, 1, 2), \
            f"--check 退出码异常：{result.returncode}"

        # mtime 不应变化（--check 不写盘）
        if before_mtime is not None:
            after_mtime = target.stat().st_mtime
            assert before_mtime == after_mtime, "--check 不应修改产物"
