"""html_renderer 单元测试。

覆盖：
  - 极简 markdown → HTML 转换（标题/段落/列表/代码块/行内 code/粗体斜体/链接/表格）
  - HTML 转义（XSS 防御）
  - JSON 安全嵌入（</script> 注入防御）
  - SVG 流程图节点 + 边数量正确
  - 完整 render_html 输出含必要锚点
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ============================================================================
# 极简 markdown 渲染
# ============================================================================

class TestMarkdownRender:
    def test_h1_h2_h3(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("# T1\n\n## T2\n\n### T3\n")
        assert "<h1" in html and ">T1<" in html
        assert "<h2" in html and ">T2<" in html
        assert "<h3" in html and ">T3<" in html

    def test_paragraph(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("第一段。\n\n第二段。\n")
        assert html.count("<p>") == 2

    def test_unordered_list(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("- a\n- b\n- c\n")
        assert "<ul>" in html
        assert html.count("<li>") == 3

    def test_ordered_list(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("1. one\n2. two\n")
        assert "<ol>" in html
        assert html.count("<li>") == 2

    def test_fenced_code_block(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("```python\nprint('hi')\n```\n")
        assert "<pre" in html and "<code" in html
        # 内部内容应被 HTML 转义
        assert "print('hi')" in html or "print(&#x27;hi&#x27;)" in html or "print(&apos;hi&apos;)" in html

    def test_inline_code(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("用 `os.path` 模块。\n")
        assert "<code>os.path</code>" in html

    def test_bold_italic(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("**粗体** 和 *斜体*。\n")
        assert "<strong>粗体</strong>" in html
        assert "<em>斜体</em>" in html

    def test_link(self):
        from lib.html_renderer import md_to_html
        html = md_to_html("点 [这里](https://example.com) 看。\n")
        assert 'href="https://example.com"' in html
        assert ">这里</a>" in html

    def test_html_escape_in_text(self):
        """正文里的 < > & 应被转义。"""
        from lib.html_renderer import md_to_html
        html = md_to_html("a < b & c > d\n")
        assert "&lt;" in html
        assert "&gt;" in html
        assert "&amp;" in html

    def test_xss_in_link_url_blocked(self):
        """javascript: 链接应被剥离/拒绝。"""
        from lib.html_renderer import md_to_html
        html = md_to_html("[click](javascript:alert(1))\n")
        # href 中不应出现 javascript:
        assert "javascript:" not in html.lower()

    def test_table(self):
        from lib.html_renderer import md_to_html
        html = md_to_html(
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
            "| 3 | 4 |\n"
        )
        assert "<table" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html


# ============================================================================
# JSON 安全嵌入
# ============================================================================

class TestSafeJSONEmbed:
    def test_normal_dict(self):
        from lib.html_renderer import safe_json_for_script
        out = safe_json_for_script({"a": 1, "b": "hi"})
        assert '"a"' in out
        assert '"hi"' in out

    def test_script_close_tag_escaped(self):
        """JSON 中含 </script> 必须被转义，否则会过早关闭 script 标签。"""
        from lib.html_renderer import safe_json_for_script
        out = safe_json_for_script({"x": "hello </script><script>alert(1)</script>"})
        assert "</script>" not in out
        # 一种常见做法：转为 <\/script>
        assert "<\\/script>" in out or "\\u003c/script\\u003e" in out.lower()

    def test_unicode_chinese(self):
        from lib.html_renderer import safe_json_for_script
        out = safe_json_for_script({"name": "测试"})
        # 中文应保留可读（ensure_ascii=False）或被 \u 转义皆可
        loaded = json.loads(out)
        assert loaded["name"] == "测试"


# ============================================================================
# SVG 流程图渲染
# ============================================================================

class TestSVGFlowchart:
    def test_node_count_matches(self):
        """节点数与传入 phases 数一致。"""
        from lib.html_renderer import render_phases_svg
        phases = [
            {"id": "INIT", "name": "初始化", "order": 0, "next": "A", "canSkipTo": None,
             "autoFlow": True, "threeStepMode": False},
            {"id": "A", "name": "A", "order": 1, "next": "B", "canSkipTo": None,
             "autoFlow": False, "threeStepMode": True},
            {"id": "B", "name": "B", "order": 2, "next": None, "canSkipTo": None,
             "autoFlow": False, "threeStepMode": False},
        ]
        svg = render_phases_svg(phases)
        # 每个节点应有对应的 data-phase-id 属性
        ids_in_svg = set(re.findall(r'data-phase-id="([^"]+)"', svg))
        assert {"INIT", "A", "B"}.issubset(ids_in_svg)

    def test_edges_for_next_and_skip(self):
        """next 边 + canSkipTo 边都应渲染。"""
        from lib.html_renderer import render_phases_svg
        phases = [
            {"id": "A", "name": "A", "order": 0, "next": "B", "canSkipTo": "C",
             "autoFlow": False, "threeStepMode": False},
            {"id": "B", "name": "B", "order": 1, "next": "C", "canSkipTo": None,
             "autoFlow": False, "threeStepMode": False},
            {"id": "C", "name": "C", "order": 2, "next": None, "canSkipTo": None,
             "autoFlow": False, "threeStepMode": False},
        ]
        svg = render_phases_svg(phases)
        # 边用 data-edge-from / data-edge-to / data-edge-kind 标注
        edges = re.findall(
            r'data-edge-from="([^"]+)"\s+data-edge-to="([^"]+)"\s+data-edge-kind="([^"]+)"',
            svg,
        )
        edge_set = {(f, t, k) for f, t, k in edges}
        assert ("A", "B", "next") in edge_set
        assert ("A", "C", "skip") in edge_set
        assert ("B", "C", "next") in edge_set


# ============================================================================
# 完整 HTML 渲染
# ============================================================================

class TestRenderHTML:
    def _minimal_data(self):
        return {
            "meta": {"generated_at": "2026-05-29T16:00:00", "commit": "abc1234"},
            "phases": [
                {"id": "INIT", "name": "初始化", "order": 0, "next": "DONE",
                 "canSkipTo": None, "autoFlow": True, "threeStepMode": False,
                 "agent_ids": [], "rules_file_ids": []},
                {"id": "DONE", "name": "完成", "order": 1, "next": None,
                 "canSkipTo": None, "autoFlow": False, "threeStepMode": False,
                 "agent_ids": [], "rules_file_ids": []},
            ],
            "agents": [
                {"id": "test-agent", "title": "测试 Agent", "phases": ["DONE"],
                 "role": "测试", "permissions": "只读",
                 "html": "<p>正文</p>", "raw": "# x\n", "file": "agents/test-agent.md"},
            ],
            "rules": [],
            "templates": [],
            "references": [],
            "phase_rules": [],
            "skill_main": {"toc": [], "html": "<p>SKILL</p>"},
            "consistency": {"available": False},
        }

    def test_html_has_doctype_and_meta_charset(self):
        from lib.html_renderer import render_html
        out = render_html(self._minimal_data())
        assert out.startswith("<!DOCTYPE html>") or out.startswith("<!doctype html>")
        assert 'charset="utf-8"' in out.lower() or "charset='utf-8'" in out.lower()

    def test_html_embeds_data_script(self):
        """所有数据通过 <script id="__DATA__"> 内联。"""
        from lib.html_renderer import render_html
        out = render_html(self._minimal_data())
        assert 'id="__DATA__"' in out
        # 数据 JSON 中应找到我们的 agent id
        assert "test-agent" in out

    def test_html_has_all_tabs(self):
        """7 个 Tab 锚点：phases / agents / rules / templates / references / skill / health"""
        from lib.html_renderer import render_html
        out = render_html(self._minimal_data())
        for tab in ["phases", "agents", "rules", "templates", "references", "skill", "health"]:
            assert f'data-tab="{tab}"' in out, f"缺少 Tab {tab}"

    def test_html_has_phase_node_anchors(self):
        from lib.html_renderer import render_html
        out = render_html(self._minimal_data())
        assert 'data-phase-id="INIT"' in out
        assert 'data-phase-id="DONE"' in out

    def test_html_no_external_dependencies(self):
        """单文件零依赖：不应含 CDN / 外部脚本 / 外部样式表引用。"""
        from lib.html_renderer import render_html
        out = render_html(self._minimal_data())
        # 不允许 src=http/https 的外部脚本（图片例外，但本项目不引图）
        assert 'src="http' not in out, "HTML 不应引用外部脚本"
        assert 'href="http' not in out.replace('href="https://example', ''), \
            "HTML 不应引用外部样式表（example 等正文链接除外）"
        # 严格：不应出现 cdn.jsdelivr / unpkg 等关键字
        assert "cdn.jsdelivr" not in out.lower()
        assert "unpkg.com" not in out.lower()

    def test_html_size_reasonable(self):
        """最小数据集 HTML 应 < 200KB（仅含模板 + 极少数据）。"""
        from lib.html_renderer import render_html
        out = render_html(self._minimal_data())
        assert len(out) < 200_000, f"最小数据集 HTML 体积 {len(out)} 异常偏大"
