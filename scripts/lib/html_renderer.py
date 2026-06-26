"""单文件零依赖 HTML 渲染器。

包含：
    1. 极简 markdown → HTML（覆盖 95% 工作流文档常见语法，无第三方依赖）
    2. JSON 安全嵌入（防 </script> 注入）
    3. SVG 流程图（按 phases.order 横向时间线 + 自动换行）
    4. 完整 HTML 模板（HTML5 + 内嵌 CSS + 内嵌 vanilla JS）

承诺三段式声明（见 plan.md）：
    硬承诺：单文件零依赖 / 7 Tab / 抽屉交互 / data-* 锚点齐全
    软承诺：极简 md 覆盖 95% 常见语法（嵌套表格 / HTML 内联 / 数学公式不保证）
    不承诺：响应式 < 768px / 移动端体验 / 多主题切换
"""
from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any


# ============================================================================
# 极简 Markdown → HTML
# ============================================================================

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
_OL_RE = re.compile(r"^(\s*)(\d+)\.\s+(.+)$")
_UL_RE = re.compile(r"^(\s*)[-*+]\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_HR_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")


def _safe_url(url: str) -> str:
    """剥离 javascript:/vbscript:/data: 等危险协议。"""
    u = url.strip()
    low = u.lower()
    for bad in ("javascript:", "vbscript:", "data:text/html"):
        if low.startswith(bad):
            return "#"
    return u


def _render_inline(text: str) -> str:
    """渲染行内元素：转义 → 行内代码 → 链接 → 粗体 → 斜体。

    顺序很重要：先抽出 inline code 占位（避免后续替换误伤），最后再回填。
    """
    # 1) 抽出 `inline code`，先 escape 再用占位符
    code_holders: list[str] = []

    def _stash_code(m: re.Match) -> str:
        idx = len(code_holders)
        code_holders.append(html_lib.escape(m.group(1)))
        return f"\x00CODE{idx}\x00"

    text = _INLINE_CODE_RE.sub(_stash_code, text)

    # 2) 抽出 [link](url)
    link_holders: list[str] = []

    def _stash_link(m: re.Match) -> str:
        idx = len(link_holders)
        label = m.group(1)
        url = _safe_url(m.group(2))
        link_holders.append(
            f'<a href="{html_lib.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            + html_lib.escape(label)
            + "</a>"
        )
        return f"\x00LINK{idx}\x00"

    text = _LINK_RE.sub(_stash_link, text)

    # 3) HTML 转义剩余文本
    text = html_lib.escape(text, quote=False)

    # 4) 粗体 / 斜体（在转义后的文本上做，不影响占位符）
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)

    # 5) 回填占位符
    for i, code in enumerate(code_holders):
        text = text.replace(f"\x00CODE{i}\x00", f"<code>{code}</code>")
    for i, link in enumerate(link_holders):
        text = text.replace(f"\x00LINK{i}\x00", link)

    return text


def _slug(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text).strip("-").lower()


def md_to_html(text: str) -> str:
    """极简 markdown → HTML。

    支持：H1-H6 / 段落 / 无序列表 / 有序列表 / 围栏代码块 / 行内代码 /
          粗体 / 斜体 / 链接 / 表格 / 引用块 / 水平线
    不支持：嵌套列表深度 > 2 / HTML 原生标签（会被转义） / 数学公式 / 图片
    """
    if not text:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    def _flush_para(buf: list[str]):
        if not buf:
            return
        para = " ".join(buf).strip()
        if para:
            out.append(f"<p>{_render_inline(para)}</p>")
        buf.clear()

    para_buf: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.rstrip()

        # 围栏代码块
        m_fence = _FENCE_RE.match(stripped)
        if m_fence:
            _flush_para(para_buf)
            lang = m_fence.group(1)
            code_lines: list[str] = []
            i += 1
            while i < n and not _FENCE_RE.match(lines[i].rstrip()):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = html_lib.escape("\n".join(code_lines))
            cls = f' class="lang-{html_lib.escape(lang, quote=True)}"' if lang else ""
            out.append(f'<pre><code{cls}>{code}</code></pre>')
            continue

        # 标题
        m_h = _HEADING_RE.match(stripped)
        if m_h:
            _flush_para(para_buf)
            level = len(m_h.group(1))
            txt = m_h.group(2).strip()
            anchor = _slug(txt)
            out.append(f'<h{level} id="{anchor}">{_render_inline(txt)}</h{level}>')
            i += 1
            continue

        # 水平线
        if _HR_RE.match(stripped):
            _flush_para(para_buf)
            out.append("<hr/>")
            i += 1
            continue

        # 表格
        if _TABLE_LINE_RE.match(stripped) and i + 1 < n and _TABLE_DIVIDER_RE.match(lines[i + 1]):
            _flush_para(para_buf)
            headers = [c.strip() for c in stripped.strip().strip("|").split("|")]
            i += 2  # skip header + divider
            rows: list[list[str]] = []
            while i < n and _TABLE_LINE_RE.match(lines[i].rstrip()):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            thead = "".join(f"<th>{_render_inline(h)}</th>" for h in headers)
            tbody = "".join(
                "<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            out.append(f'<table class="md-table"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>')
            continue

        # 无序列表
        if _UL_RE.match(line):
            _flush_para(para_buf)
            items: list[str] = []
            while i < n and _UL_RE.match(lines[i]):
                m = _UL_RE.match(lines[i])
                items.append(f"<li>{_render_inline(m.group(2))}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # 有序列表
        if _OL_RE.match(line):
            _flush_para(para_buf)
            items = []
            while i < n and _OL_RE.match(lines[i]):
                m = _OL_RE.match(lines[i])
                items.append(f"<li>{_render_inline(m.group(3))}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # 引用块（简单版：连续 > 行合并为一段）
        if _BLOCKQUOTE_RE.match(line):
            _flush_para(para_buf)
            block: list[str] = []
            while i < n and _BLOCKQUOTE_RE.match(lines[i]):
                m = _BLOCKQUOTE_RE.match(lines[i])
                block.append(m.group(1))
                i += 1
            content = " ".join(block).strip()
            out.append(f"<blockquote>{_render_inline(content)}</blockquote>")
            continue

        # 空行
        if not stripped:
            _flush_para(para_buf)
            i += 1
            continue

        # 普通段落（连续非空行合并）
        para_buf.append(stripped)
        i += 1

    _flush_para(para_buf)
    return "\n".join(out)


# ============================================================================
# JSON 安全嵌入
# ============================================================================

def safe_json_for_script(data: Any) -> str:
    """将 Python 对象序列化为可安全嵌入 <script> 的 JSON 字符串。

    防御：
        - </script> 转为 <\\/script>（最常见的 script tag 注入）
        - U+2028 / U+2029 转为 \\u2028 / \\u2029（避免 JS 字符串字面量解析错误）
    """
    js = json.dumps(data, ensure_ascii=False)
    js = js.replace("</", "<\\/")
    js = js.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return js


# ============================================================================
# SVG 流程图
# ============================================================================

# 布局常量
_NODE_W = 160
_NODE_H = 56
_HGAP = 40       # 节点水平间距
_VGAP = 80       # 行间距
_PER_ROW = 5     # 每行最多 5 个节点（19 phases → 4 行）
_PADDING = 32    # SVG 内边距
_FONT = "PingFang SC, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def _node_color(p: dict) -> str:
    """按 autoFlow / threeStepMode 决定节点填充色。"""
    if p.get("autoFlow"):
        return "#DCEFFF"  # 浅蓝
    if p.get("threeStepMode"):
        return "#FFE7CE"  # 浅橙
    return "#EAEEF2"      # 浅灰


def _node_stroke(p: dict) -> str:
    if p.get("autoFlow"):
        return "#0969DA"
    if p.get("threeStepMode"):
        return "#9A6700"
    return "#57606A"


def render_phases_svg(phases: list[dict]) -> str:
    """渲染 SVG 流程图。

    布局：按 order 横向排列，每行 _PER_ROW 个节点；折返时下一行起始更靠右
    （蛇形布局），简化箭头折线。
    边：
      - next: 实线箭头
      - canSkipTo: 虚线箭头
    """
    if not phases:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20"></svg>'

    # 按 order 排序
    ordered = sorted(phases, key=lambda x: x.get("order", 0))
    pos: dict[str, tuple[int, int]] = {}  # phase_id -> (cx, cy) 节点中心

    rows = (len(ordered) + _PER_ROW - 1) // _PER_ROW
    for idx, p in enumerate(ordered):
        row = idx // _PER_ROW
        col = idx % _PER_ROW
        # 蛇形：奇数行倒序，使 next 箭头折返自然
        if row % 2 == 1:
            col = _PER_ROW - 1 - col
        cx = _PADDING + col * (_NODE_W + _HGAP) + _NODE_W // 2
        cy = _PADDING + row * (_NODE_H + _VGAP) + _NODE_H // 2
        pos[p["id"]] = (cx, cy)

    width = _PADDING * 2 + _PER_ROW * _NODE_W + (_PER_ROW - 1) * _HGAP
    height = _PADDING * 2 + rows * _NODE_H + max(0, rows - 1) * _VGAP

    svg_parts: list[str] = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" class="phases-svg">'
    )
    # 箭头 marker 定义
    svg_parts.append(
        '<defs>'
        '<marker id="arrow-next" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#0969DA"/></marker>'
        '<marker id="arrow-skip" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#9A6700"/></marker>'
        '</defs>'
    )

    # 边（先画边，后画节点，节点遮挡边端点）
    for p in ordered:
        pid = p["id"]
        if pid not in pos:
            continue
        sx, sy = pos[pid]
        # next 边
        nxt = p.get("next")
        if nxt and nxt in pos:
            tx, ty = pos[nxt]
            path = _edge_path(sx, sy, tx, ty)
            svg_parts.append(
                f'<path d="{path}" fill="none" stroke="#0969DA" stroke-width="1.6" '
                f'marker-end="url(#arrow-next)" '
                f'data-edge-from="{html_lib.escape(pid, quote=True)}" '
                f'data-edge-to="{html_lib.escape(nxt, quote=True)}" '
                f'data-edge-kind="next" />'
            )
        # canSkipTo 边
        skip = p.get("canSkipTo")
        if skip and skip in pos:
            tx, ty = pos[skip]
            path = _edge_path(sx, sy, tx, ty)
            svg_parts.append(
                f'<path d="{path}" fill="none" stroke="#9A6700" stroke-width="1.4" '
                f'stroke-dasharray="6 4" marker-end="url(#arrow-skip)" '
                f'data-edge-from="{html_lib.escape(pid, quote=True)}" '
                f'data-edge-to="{html_lib.escape(skip, quote=True)}" '
                f'data-edge-kind="skip" />'
            )

    # 节点
    for p in ordered:
        pid = p["id"]
        if pid not in pos:
            continue
        cx, cy = pos[pid]
        x = cx - _NODE_W // 2
        y = cy - _NODE_H // 2
        fill = _node_color(p)
        stroke = _node_stroke(p)
        name = html_lib.escape(p.get("name", pid))
        order = p.get("order", "")
        svg_parts.append(
            f'<g class="phase-node" data-phase-id="{html_lib.escape(pid, quote=True)}" '
            f'tabindex="0" role="button" aria-label="{html_lib.escape(pid, quote=True)}">'
            f'<rect x="{x}" y="{y}" width="{_NODE_W}" height="{_NODE_H}" rx="8" ry="8" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-family="{_FONT}" '
            f'font-size="13" font-weight="600" fill="#1F2328">{html_lib.escape(pid)}</text>'
            f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-family="{_FONT}" '
            f'font-size="11" fill="#57606A">#{order} · {name}</text>'
            f'</g>'
        )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def _edge_path(sx: int, sy: int, tx: int, ty: int) -> str:
    """两点之间的 cubic Bezier 折线（避免直线穿越节点）。"""
    if abs(sx - tx) < 4 and abs(sy - ty) < 4:
        # 同位置，画一个小回环
        return f"M{sx},{sy + _NODE_H // 2} q40,40 0,80"
    # 起点从节点底部出发，终点到节点顶部
    sy_out = sy + _NODE_H // 2
    ty_in = ty - _NODE_H // 2
    if sy == ty:
        # 同行：横向曲线
        sx_out = sx + _NODE_W // 2 if tx > sx else sx - _NODE_W // 2
        tx_in = tx - _NODE_W // 2 if tx > sx else tx + _NODE_W // 2
        mid = (sx_out + tx_in) // 2
        return f"M{sx_out},{sy} C{mid},{sy} {mid},{ty} {tx_in},{ty}"
    # 跨行：从下方出发到上方进入
    cy1 = sy_out + 30
    cy2 = ty_in - 30
    return f"M{sx},{sy_out} C{sx},{cy1} {tx},{cy2} {tx},{ty_in}"


# ============================================================================
# 垂直分组卡片式流程图（主视图）
# ============================================================================

def render_phases_minimap(phases: list[dict]) -> str:
    """服务端渲染左侧全览（minimap）：紧凑列出全部阶段，分组着色。

    - 每个阶段一个紧凑条目（order + 名称），data-mini-phase 与主流程对应
    - 分组变化时插入分组小标题
    - 顶部含一个 viewport 指示框（.minimap-viewport），由 JS 随主区滚动定位
    """
    if not phases:
        return '<div class="minimap minimap-empty">—</div>'

    ordered = sorted(phases, key=lambda x: x.get("order", 0))
    parts: list[str] = ['<div class="minimap" id="minimap">']
    parts.append(f'<div class="minimap-title">全览 · {len(ordered)} 步</div>')
    parts.append('<div class="minimap-track" id="minimap-track">')
    parts.append('<div class="minimap-viewport" id="minimap-viewport"></div>')
    last_group = object()
    for p in ordered:
        pid = p.get("id", "")
        gid = p.get("group", "")
        gcolor = p.get("group_color") or "#57606A"
        gname = p.get("group_name") or gid or "其他"
        order = p.get("order", "")
        name = html_lib.escape(p.get("name", pid))

        if gid != last_group:
            parts.append(
                f'<div class="minimap-group" style="color:{gcolor};">'
                f'<span class="minimap-group-dot" style="background:{gcolor};"></span>'
                f'{html_lib.escape(gname)}</div>'
            )
            last_group = gid

        parts.append(
            f'<a class="minimap-node" href="#" '
            f'data-mini-phase="{html_lib.escape(pid, quote=True)}" '
            f'style="border-left-color:{gcolor};" title="{html_lib.escape(pid, quote=True)}">'
            f'<span class="minimap-order" style="background:{gcolor};">{order}</span>'
            f'<span class="minimap-name">{name}</span>'
            f'</a>'
        )
    parts.append("</div>")  # minimap-track
    parts.append("</div>")  # minimap
    return "".join(parts)


def render_phases_flow(phases: list[dict], groups: list[dict]) -> str:
    """服务端渲染垂直分组卡片式流程图（从上至下铺开）。

    - 按 group 用彩色区块区分（group label 横幅 + 节点左边框着色）
    - 每个节点卡片内展示：order / id / 名称 / 标签 / 关联 Agent /
      输入依赖 / 输出产物 / 流转关系（next / canSkipTo）
    - 节点之间用向下箭头连接
    - 含 data-phase-id 锚点（被测试与 JS 点击交互依赖）
    """
    if not phases:
        return '<div class="flow flow-empty">暂无阶段数据</div>'

    ordered = sorted(phases, key=lambda x: x.get("order", 0))
    parts: list[str] = ['<div class="flow">']
    last_group = object()  # 哨兵，确保首个分组一定输出 label
    n = len(ordered)

    for idx, p in enumerate(ordered):
        pid = p.get("id", "")
        gid = p.get("group", "")
        gcolor = p.get("group_color") or "#57606A"
        gbg = p.get("group_bg") or "#F0F1F3"
        gname = p.get("group_name") or gid or "其他"

        # 分组变化时输出彩色区块标签
        if gid != last_group:
            parts.append(
                f'<div class="flow-group-label" data-group="{html_lib.escape(gid, quote=True)}" '
                f'style="background:{gbg};color:{gcolor};border-color:{gcolor};">'
                f'<span class="flow-group-dot" style="background:{gcolor};"></span>'
                f'{html_lib.escape(gname)}</div>'
            )
            last_group = gid

        order = p.get("order", "")
        name = html_lib.escape(p.get("name", pid))

        tags: list[str] = []
        if p.get("autoFlow"):
            tags.append('<span class="fn-tag auto">autoFlow</span>')
        if p.get("threeStepMode"):
            tags.append('<span class="fn-tag three">三步确认</span>')
        tags_html = "".join(tags)

        # 关联 Agent
        agent_ids = p.get("agent_ids") or []
        if agent_ids:
            chips = "".join(
                f'<span class="fn-chip" data-agent="{html_lib.escape(a, quote=True)}">'
                f'{html_lib.escape(a)}</span>'
                for a in agent_ids
            )
        else:
            chips = '<span class="fn-muted">编排器处理（无子 Agent）</span>'

        # 输入依赖
        inputs = p.get("inputs") or []
        if inputs:
            in_items = "".join(f"<li>{_render_inline(str(x))}</li>" for x in inputs)
            inputs_html = f'<ul class="fn-io-list">{in_items}</ul>'
        else:
            inputs_html = '<div class="fn-muted">—</div>'

        # 输出产物
        outputs = p.get("outputs") or []
        if outputs:
            out_items = "".join(
                f'<li><code class="fn-file">{html_lib.escape(str(o.get("file", "")))}</code>'
                f'<span class="fn-io-desc">{html_lib.escape(str(o.get("desc", "")))}</span></li>'
                for o in outputs
            )
            outputs_html = f'<ul class="fn-io-list">{out_items}</ul>'
        else:
            outputs_html = '<div class="fn-muted">无产物（终态）</div>'

        # 流转关系
        flow_tags: list[str] = []
        nxt = p.get("next")
        if nxt:
            flow_tags.append(f'<span class="fn-flow next">next → {html_lib.escape(str(nxt))}</span>')
        skip = p.get("canSkipTo")
        if skip:
            flow_tags.append(f'<span class="fn-flow skip">canSkipTo ⇢ {html_lib.escape(str(skip))}</span>')
        flow_html = "".join(flow_tags) or '<span class="fn-muted">终态</span>'

        parts.append(
            f'<article class="flow-node" data-phase-id="{html_lib.escape(pid, quote=True)}" '
            f'data-group="{html_lib.escape(gid, quote=True)}" tabindex="0" role="button" '
            f'aria-label="{html_lib.escape(pid, quote=True)}" '
            f'style="border-left-color:{gcolor};">'
            f'<header class="fn-head">'
            f'<span class="fn-order" style="background:{gcolor};">{order}</span>'
            f'<div class="fn-titles"><span class="fn-id">{html_lib.escape(pid)}</span>'
            f'<span class="fn-name">{name}</span></div>'
            f'<div class="fn-tags">{tags_html}</div>'
            f'</header>'
            f'<div class="fn-body">'
            f'<div class="fn-section"><span class="fn-label">关联 Agent</span>'
            f'<div class="fn-chips">{chips}</div></div>'
            f'<div class="fn-io">'
            f'<div class="fn-section fn-in"><span class="fn-label">⤵ 输入依赖</span>{inputs_html}</div>'
            f'<div class="fn-section fn-out"><span class="fn-label">⤴ 输出产物</span>{outputs_html}</div>'
            f'</div>'
            f'</div>'
            f'<footer class="fn-foot"><div class="fn-flows">{flow_html}</div>'
            f'<span class="fn-hint">点击查看详情</span></footer>'
            f'</article>'
        )

        if idx < n - 1:
            parts.append('<div class="flow-arrow" aria-hidden="true">↓</div>')

    parts.append("</div>")
    return "".join(parts)


# ============================================================================
# 完整 HTML 渲染
# ============================================================================

def render_html(data: dict) -> str:
    """编译数据字典为完整单文件 HTML。"""
    # 预先准备内嵌数据（防 </script> 注入）
    embedded = safe_json_for_script(data)
    flow = render_phases_flow(data.get("phases", []), data.get("groups", []))
    minimap = render_phases_minimap(data.get("phases", []))

    css = _CSS_TEMPLATE
    js = _JS_TEMPLATE
    title = "ai-team workflow visualization"

    meta = data.get("meta", {})
    generated_at = html_lib.escape(meta.get("generated_at") or "")
    commit = html_lib.escape(meta.get("commit") or "")

    counts_phases = len(data.get("phases", []))
    counts_agents = len(data.get("agents", []))
    counts_rules = len(data.get("rules", []))
    counts_templates = len(data.get("templates", []))
    counts_references = len(data.get("references", []))

    health = data.get("consistency", {})
    health_badge = ""
    if health.get("available"):
        c = health.get("counts", {})
        health_badge = (
            f'<span class="health-badge">'
            f'<span class="b pass">{c.get("PASS", 0)} PASS</span>'
            f'<span class="b warn">{c.get("WARN", 0)} WARN</span>'
            f'<span class="b fail">{c.get("FAIL", 0)} FAIL</span>'
            f'</span>'
        )

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8"/>')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>')
    parts.append(f"<title>{html_lib.escape(title)}</title>")
    parts.append("<style>" + css + "</style>")
    parts.append("</head>")
    parts.append("<body>")

    # Header
    parts.append('<header class="topbar">')
    parts.append(f'<div class="brand"><span class="logo">▣</span><span>{html_lib.escape(title)}</span></div>')
    parts.append('<nav class="tabs" role="tablist">')
    for tab_id, tab_label in [
        ("phases", "Phases"),
        ("agents", "Agents"),
        ("rules", "Rules"),
        ("templates", "Templates"),
        ("references", "References"),
        ("skill", "SKILL"),
        ("health", "Health"),
    ]:
        parts.append(
            f'<button class="tab" data-tab="{tab_id}" role="tab" aria-selected="false">'
            f'{tab_label}</button>'
        )
    parts.append("</nav>")
    parts.append('<div class="meta-block">')
    parts.append(f'<input id="search" type="search" placeholder="搜索 (按 / 聚焦)" aria-label="搜索"/>')
    parts.append(health_badge)
    if commit:
        parts.append(f'<span class="commit" title="HEAD short SHA">{commit}</span>')
    if generated_at:
        parts.append(f'<span class="time">{generated_at}</span>')
    parts.append("</div>")
    parts.append("</header>")

    # Main
    parts.append('<main class="main">')

    # Phases tab
    parts.append('<section class="panel" data-panel="phases">')
    parts.append('<div class="legend">')
    parts.append('<span class="lg lg-auto">autoFlow</span>')
    parts.append('<span class="lg lg-three">threeStepMode</span>')
    parts.append('<span class="lg-edge"><span class="line solid"></span> next</span>')
    parts.append('<span class="lg-edge"><span class="line dashed"></span> canSkipTo</span>')
    parts.append("</div>")
    parts.append(f'<p class="hint">共 {counts_phases} 个阶段，按工作流大阶段分组从上至下铺开。左侧全览可点击跳转，方框随页面滚动同步；点击任意节点查看该阶段的规则文档与 Agent 详情。</p>')
    parts.append('<div class="phases-layout">')
    parts.append('<aside class="minimap-wrap">' + minimap + "</aside>")
    parts.append('<div class="phases-flow" id="phases-flow">' + flow + "</div>")
    parts.append("</div>")
    parts.append("</section>")

    # Agents tab
    parts.append('<section class="panel" data-panel="agents" hidden>')
    parts.append(f'<p class="hint">共 {counts_agents} 个 Agent，按调用阶段分组。点击卡片查看 prompt 全文。</p>')
    parts.append('<div class="agent-groups" id="agent-groups"></div>')
    parts.append("</section>")

    # Rules tab
    parts.append('<section class="panel" data-panel="rules" hidden>')
    parts.append(f'<p class="hint">共 {counts_rules} 条 Rules。</p>')
    parts.append('<div class="md-list" data-collection="rules"></div>')
    parts.append("</section>")

    # Templates tab
    parts.append('<section class="panel" data-panel="templates" hidden>')
    parts.append(f'<p class="hint">共 {counts_templates} 个模板。</p>')
    parts.append('<div class="md-list" data-collection="templates"></div>')
    parts.append("</section>")

    # References tab
    parts.append('<section class="panel" data-panel="references" hidden>')
    parts.append(f'<p class="hint">共 {counts_references} 个 JSON 引用。</p>')
    parts.append('<div class="ref-list" id="ref-list"></div>')
    parts.append("</section>")

    # SKILL tab
    parts.append('<section class="panel" data-panel="skill" hidden>')
    parts.append('<div class="skill-layout">')
    parts.append('<aside class="skill-toc" id="skill-toc"></aside>')
    parts.append('<article class="skill-body" id="skill-body"></article>')
    parts.append("</div>")
    parts.append("</section>")

    # Health tab
    parts.append('<section class="panel" data-panel="health" hidden>')
    parts.append('<div id="health-block"></div>')
    parts.append("</section>")

    parts.append("</main>")

    # Modal（居中浮层 + 遮罩；点击遮罩 / 关闭按钮 / Esc 关闭）
    parts.append('<div class="modal-overlay" id="modal-overlay" aria-hidden="true">')
    parts.append('<div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">')
    parts.append('<div class="modal-head">')
    parts.append('<div class="modal-title" id="modal-title">详情</div>')
    parts.append('<button class="modal-close" id="modal-close" aria-label="关闭">×</button>')
    parts.append("</div>")
    parts.append('<div class="modal-meta" id="modal-meta"></div>')
    parts.append('<div class="modal-body" id="modal-body"></div>')
    parts.append("</div>")
    parts.append("</div>")

    # Embedded data + JS
    parts.append(f'<script id="__DATA__" type="application/json">{embedded}</script>')
    parts.append("<script>" + js + "</script>")

    parts.append("</body></html>")
    return "\n".join(parts)


# ============================================================================
# 内嵌 CSS / JS 模板
# ============================================================================

_CSS_TEMPLATE = r"""
:root {
  --color-primary: #0969DA;
  --color-primary-deep: #0550AE;
  --color-bg: #FFFFFF;
  --color-bg-soft: #F6F8FA;
  --color-bg-mute: #EAEEF2;
  --color-text: #1F2328;
  --color-text-soft: #57606A;
  --color-text-inv: #FFFFFF;
  --color-border: #D0D7DE;
  --color-success: #1A7F37;
  --color-warn: #9A6700;
  --color-fail: #CF222E;
  --color-info: #0969DA;
  --shadow-sm: 0 1px 2px rgba(31,35,40,.06);
  --shadow-md: 0 4px 12px rgba(31,35,40,.08);
  --radius: 8px;
  --font-sans: "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "SFMono-Regular", "Menlo", "Consolas", monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: var(--font-sans); color: var(--color-text); background: var(--color-bg-soft); font-size: 14px; line-height: 1.55; }
button { font-family: inherit; cursor: pointer; }
a { color: var(--color-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

/* topbar */
.topbar {
  position: sticky; top: 0; z-index: 50;
  display: flex; align-items: center; gap: 16px;
  height: 64px; padding: 0 24px;
  background: var(--color-bg); border-bottom: 1px solid var(--color-border);
}
.brand { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 16px; min-width: 240px; }
.brand .logo { color: var(--color-primary); font-size: 22px; }
.tabs { flex: 1; display: flex; gap: 4px; }
.tab {
  border: 0; background: transparent; padding: 8px 14px; border-radius: 6px;
  color: var(--color-text-soft); font-size: 14px; font-weight: 500;
  transition: all .15s;
}
.tab:hover { background: var(--color-bg-soft); color: var(--color-text); }
.tab[aria-selected="true"] { background: var(--color-bg-mute); color: var(--color-primary); font-weight: 600; }
.meta-block { display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--color-text-soft); }
#search {
  padding: 6px 10px; border: 1px solid var(--color-border); border-radius: 6px;
  background: var(--color-bg); color: var(--color-text); font: inherit;
  width: 220px; outline: none; transition: border .15s;
}
#search:focus { border-color: var(--color-primary); }
.commit { font-family: var(--font-mono); padding: 2px 8px; border-radius: 4px; background: var(--color-bg-mute); }
.health-badge { display: inline-flex; gap: 6px; align-items: center; }
.health-badge .b { padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; }
.health-badge .pass { background: #DAFBE1; color: var(--color-success); }
.health-badge .warn { background: #FFF8C5; color: var(--color-warn); }
.health-badge .fail { background: #FFEBE9; color: var(--color-fail); }

/* main */
.main { padding: 24px; max-width: 100%; }
.panel { animation: fadeIn .2s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px);} to { opacity: 1; transform: none;} }

.hint { color: var(--color-text-soft); margin: 0 0 16px; }

/* phases */
.legend { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; font-size: 12px; color: var(--color-text-soft); }
.lg { padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.lg-auto { background: #DCEFFF; color: var(--color-primary); }
.lg-three { background: #FFE7CE; color: var(--color-warn); }
.lg-other { background: var(--color-bg-mute); color: var(--color-text-soft); }
.lg-edge { display: inline-flex; align-items: center; gap: 4px; }
.lg-edge .line { display: inline-block; width: 24px; height: 0; border-top: 2px solid var(--color-primary); }
.lg-edge .line.dashed { border-top-style: dashed; border-color: var(--color-warn); }

.phases-canvas {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  padding: 16px; box-shadow: var(--shadow-sm); overflow: auto;
}
.phases-svg { display: block; max-width: 100%; }
.phase-node { cursor: pointer; transition: transform .15s; }
.phase-node:hover rect { stroke-width: 2.4; filter: drop-shadow(0 2px 6px rgba(31,35,40,.15)); }
.phase-node:focus { outline: none; }
.phase-node:focus rect { stroke-width: 2.4; }

/* agent groups */
.agent-groups { display: flex; flex-direction: column; gap: 24px; }
.agent-group h3 { margin: 0 0 12px; font-size: 14px; color: var(--color-text-soft); font-weight: 600; }
.agent-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.agent-card {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  padding: 14px 16px; cursor: pointer; transition: all .15s; box-shadow: var(--shadow-sm);
}
.agent-card:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); border-color: var(--color-primary); }
.agent-card .name { font-weight: 600; margin-bottom: 6px; color: var(--color-text); }
.agent-card .role { font-size: 12px; color: var(--color-text-soft); display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.agent-card .badges { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 8px; }
.agent-card .badge { font-size: 10px; padding: 1px 6px; border-radius: 3px; background: var(--color-bg-mute); color: var(--color-text-soft); }

/* md-list / ref-list */
.md-list, .ref-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.md-item, .ref-item {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  padding: 12px 14px; cursor: pointer; transition: all .15s;
}
.md-item:hover, .ref-item:hover { border-color: var(--color-primary); box-shadow: var(--shadow-sm); }
.md-item .title, .ref-item .title { font-weight: 600; margin-bottom: 4px; }
.md-item .file, .ref-item .file { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-soft); }

/* SKILL */
.skill-layout { display: grid; grid-template-columns: 240px 1fr; gap: 24px; }
.skill-toc {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  padding: 12px; max-height: calc(100vh - 140px); overflow: auto; position: sticky; top: 88px;
}
.skill-toc a { display: block; padding: 4px 8px; border-radius: 4px; color: var(--color-text); font-size: 13px; }
.skill-toc a:hover { background: var(--color-bg-soft); text-decoration: none; }
.skill-toc .lvl-2 { padding-left: 18px; color: var(--color-text-soft); }
.skill-toc .lvl-3 { padding-left: 32px; color: var(--color-text-soft); font-size: 12px; }
.skill-body {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  padding: 24px 32px; line-height: 1.7;
}

/* health */
.health-table {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  width: 100%; border-collapse: collapse; overflow: hidden;
}
.health-table th, .health-table td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--color-border); }
.health-table th { background: var(--color-bg-soft); font-weight: 600; font-size: 12px; color: var(--color-text-soft); }
.sev-pass { color: var(--color-success); font-weight: 600; }
.sev-warn { color: var(--color-warn); font-weight: 600; }
.sev-fail { color: var(--color-fail); font-weight: 600; }
.sev-info { color: var(--color-info); font-weight: 600; }
.findings-list { margin: 8px 0 0; padding-left: 18px; font-size: 12px; color: var(--color-text-soft); }

/* ── 垂直分组流程图（Phases tab） ── */
.flow { display: flex; flex-direction: column; align-items: stretch; max-width: 960px; margin: 0 auto; }
.flow-empty { color: var(--color-text-soft); text-align: center; padding: 40px; }
.flow-group-label {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 8px;
  padding: 5px 14px; border-radius: 999px; border: 1px solid; font-weight: 700;
  font-size: 12px; letter-spacing: .02em; margin: 18px 0 10px;
}
.flow-group-label:first-child { margin-top: 0; }
.flow-group-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.flow-node {
  position: relative; background: var(--color-bg);
  border: 1px solid var(--color-border); border-left: 5px solid var(--color-text-soft);
  border-radius: var(--radius); padding: 0; cursor: pointer; overflow: hidden;
  box-shadow: var(--shadow-sm); transition: box-shadow .15s, transform .15s, border-color .15s;
  text-align: left; width: 100%; display: block;
}
.flow-node:hover, .flow-node:focus-visible {
  transform: translateY(-2px); box-shadow: 0 6px 18px rgba(31,35,40,.12);
  outline: none;
}
.fn-head { display: flex; align-items: center; gap: 12px; padding: 14px 18px 10px; }
.fn-order {
  flex: 0 0 auto; width: 30px; height: 30px; border-radius: 8px; color: #fff;
  font-weight: 700; font-size: 14px; display: flex; align-items: center; justify-content: center;
}
.fn-titles { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
.fn-id { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-soft); letter-spacing: .03em; }
.fn-name { font-weight: 700; font-size: 15px; color: var(--color-text); }
.fn-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.fn-tag { font-size: 10px; padding: 2px 8px; border-radius: 999px; font-weight: 700; }
.fn-tag.auto { background: #DCEFFF; color: var(--color-primary); }
.fn-tag.three { background: #FFE7CE; color: var(--color-warn); }
.fn-body { padding: 0 18px 12px; display: flex; flex-direction: column; gap: 12px; }
.fn-section { display: flex; flex-direction: column; gap: 6px; }
.fn-label { font-size: 11px; font-weight: 700; color: var(--color-text-soft); text-transform: uppercase; letter-spacing: .04em; }
.fn-chips { display: flex; gap: 6px; flex-wrap: wrap; }
.fn-chip {
  font-family: var(--font-mono); font-size: 11px; padding: 3px 9px; border-radius: 6px;
  background: var(--color-bg-mute); color: var(--color-text); border: 1px solid var(--color-border);
}
.fn-muted { color: var(--color-text-soft); font-size: 12px; }
.fn-io { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.fn-in, .fn-out { background: var(--color-bg-soft); border: 1px solid var(--color-border); border-radius: 6px; padding: 10px 12px; }
.fn-in { border-left: 3px solid var(--color-info); }
.fn-out { border-left: 3px solid var(--color-success); }
.fn-io-list { margin: 0; padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.fn-io-list li { font-size: 12px; line-height: 1.5; display: flex; flex-direction: column; gap: 1px; }
.fn-file { font-family: var(--font-mono); font-size: 11px; background: var(--color-bg-mute); padding: 1px 6px; border-radius: 4px; color: var(--color-text); align-self: flex-start; }
.fn-io-desc { color: var(--color-text-soft); font-size: 11.5px; }
.fn-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 18px; border-top: 1px solid var(--color-border); background: var(--color-bg-soft); flex-wrap: wrap; }
.fn-flows { display: flex; gap: 8px; flex-wrap: wrap; }
.fn-flow { font-size: 11px; font-family: var(--font-mono); padding: 2px 8px; border-radius: 4px; }
.fn-flow.next { background: #DDF4E4; color: var(--color-success); }
.fn-flow.skip { background: #FFF1D6; color: var(--color-warn); }
.fn-hint { font-size: 11px; color: var(--color-text-soft); }
.flow-arrow { text-align: center; color: var(--color-text-soft); font-size: 20px; line-height: 1; margin: 4px 0; }

/* ── 两栏布局：左 minimap 全览 + 右流程 ── */
.phases-layout { display: grid; grid-template-columns: 232px 1fr; gap: 24px; align-items: start; }
.minimap-wrap { position: sticky; top: 88px; align-self: start; }
.phases-flow .flow { margin: 0; max-width: none; }
.minimap {
  background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius);
  box-shadow: var(--shadow-sm); padding: 12px; max-height: calc(100vh - 112px); display: flex; flex-direction: column;
}
.minimap-title { font-size: 11px; font-weight: 700; color: var(--color-text-soft); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 10px; flex: 0 0 auto; }
.minimap-track { position: relative; overflow-y: auto; padding-right: 2px; display: flex; flex-direction: column; gap: 3px; }
.minimap-viewport {
  position: absolute; left: 0; right: 0; top: 0; height: 0;
  background: rgba(9,105,218,.10); border: 1.5px solid var(--color-primary); border-radius: 6px;
  pointer-events: none; transition: transform .08s linear; z-index: 1;
}
.minimap-group { font-size: 10px; font-weight: 700; display: flex; align-items: center; gap: 5px; margin: 8px 0 2px; letter-spacing: .02em; }
.minimap-group:first-of-type { margin-top: 0; }
.minimap-group-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.minimap-node {
  position: relative; z-index: 2; display: flex; align-items: center; gap: 7px;
  padding: 4px 6px; border-radius: 5px; border-left: 3px solid var(--color-text-soft);
  background: var(--color-bg-soft); color: var(--color-text); font-size: 11.5px;
  text-decoration: none; transition: background .12s;
}
.minimap-node:hover { background: var(--color-bg-mute); text-decoration: none; }
.minimap-node.active { background: #DCEFFF; box-shadow: inset 0 0 0 1px var(--color-primary); }
.minimap-order { flex: 0 0 auto; width: 16px; height: 16px; border-radius: 4px; color: #fff; font-size: 9px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.minimap-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 920px) {
  .phases-layout { grid-template-columns: 1fr; }
  .minimap-wrap { display: none; }
}
@media (max-width: 720px) {
  .fn-io { grid-template-columns: 1fr; }
}

/* ── 居中浮层 Modal ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(31,35,40,.55);
  display: none; align-items: flex-start; justify-content: center;
  padding: 48px 20px; z-index: 200; overflow-y: auto;
}
.modal-overlay.open { display: flex; }
.modal {
  background: var(--color-bg); border-radius: 12px; width: 860px; max-width: 100%;
  max-height: calc(100vh - 96px); display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(31,35,40,.28); overflow: hidden;
  animation: modalIn .18s ease;
}
@keyframes modalIn { from { transform: translateY(12px) scale(.98); opacity: 0; } to { transform: none; opacity: 1; } }
.modal-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 24px; border-bottom: 1px solid var(--color-border); }
.modal-title { font-weight: 700; font-size: 18px; }
.modal-close { border: 0; background: var(--color-bg-mute); font-size: 22px; line-height: 1; color: var(--color-text-soft); width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
.modal-close:hover { background: var(--color-fail); color: #fff; }
.modal-meta { padding: 10px 24px; border-bottom: 1px solid var(--color-border); font-family: var(--font-mono); font-size: 11px; color: var(--color-text-soft); display: flex; gap: 12px; flex-wrap: wrap; }
.modal-meta:empty { display: none; }
.modal-body { flex: 1; overflow: auto; padding: 22px 28px; line-height: 1.7; }
.modal-body h1, .modal-body h2, .modal-body h3 { margin-top: 1.4em; }
.modal-body h1 { font-size: 21px; }
.modal-body h2 { font-size: 18px; }
.modal-body h3 { font-size: 15px; }
.modal-body code { background: var(--color-bg-mute); padding: 1px 5px; border-radius: 3px; font-family: var(--font-mono); font-size: 12.5px; }
.modal-body pre { background: #0D1117; color: #E6EDF3; padding: 12px; border-radius: 6px; overflow: auto; }
.modal-body pre code { background: transparent; color: inherit; padding: 0; }
.modal-body table { border-collapse: collapse; width: 100%; }
.modal-body table th, .modal-body table td { border: 1px solid var(--color-border); padding: 6px 10px; }
.modal-body table th { background: var(--color-bg-soft); }
.modal-body blockquote { border-left: 3px solid var(--color-primary); padding-left: 12px; color: var(--color-text-soft); margin: 0; }
.modal-section { margin-bottom: 18px; }
.modal-section h4 { margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--color-text-soft); }

@media (max-width: 1080px) {
  .skill-layout { grid-template-columns: 1fr; }
  .skill-toc { position: static; max-height: none; }
}
"""


_JS_TEMPLATE = r"""
(function() {
  const dataEl = document.getElementById('__DATA__');
  const DATA = JSON.parse(dataEl.textContent);

  // ---------- Tabs ----------
  const tabs = Array.from(document.querySelectorAll('.tab'));
  const panels = Array.from(document.querySelectorAll('.panel'));
  function activateTab(id) {
    tabs.forEach(t => t.setAttribute('aria-selected', t.dataset.tab === id ? 'true' : 'false'));
    panels.forEach(p => { p.hidden = p.dataset.panel !== id; });
  }
  tabs.forEach(t => t.addEventListener('click', () => activateTab(t.dataset.tab)));
  activateTab('phases');

  // ---------- Modal（居中浮层；遮罩 / 关闭按钮 / Esc 关闭） ----------
  const overlay = document.getElementById('modal-overlay');
  const drawerTitle = document.getElementById('modal-title');
  const drawerMeta = document.getElementById('modal-meta');
  const drawerBody = document.getElementById('modal-body');
  document.getElementById('modal-close').addEventListener('click', () => closeDrawer());
  // 点击遮罩空白区域（modal 本体之外）关闭
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeDrawer(); });
  function openDrawer(title, meta, html) {
    drawerTitle.textContent = title;
    drawerMeta.innerHTML = meta;
    drawerBody.innerHTML = html;
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    drawerBody.scrollTop = 0;
  }
  function closeDrawer() {
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDrawer();
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
      e.preventDefault();
      document.getElementById('search').focus();
    }
    if (/^[1-7]$/.test(e.key) && document.activeElement.tagName !== 'INPUT') {
      const idx = parseInt(e.key, 10) - 1;
      if (tabs[idx]) tabs[idx].click();
    }
  });

  // ---------- Phase node click ----------
  const phaseById = {};
  (DATA.phases || []).forEach(p => phaseById[p.id] = p);
  const agentById = {};
  (DATA.agents || []).forEach(a => agentById[a.id] = a);
  const phaseRulesById = {};
  (DATA.phase_rules || []).forEach(r => phaseRulesById[r.id] = r);

  document.querySelectorAll('.flow-node').forEach(node => {
    node.addEventListener('click', () => {
      const pid = node.dataset.phaseId;
      const p = phaseById[pid];
      if (!p) return;
      const meta = `<span>id=${escapeHtml(p.id)}</span><span>order=${p.order}</span>` +
        (p.next ? `<span>next=${escapeHtml(p.next)}</span>` : '') +
        (p.canSkipTo ? `<span>skip=${escapeHtml(p.canSkipTo)}</span>` : '') +
        `<span>autoFlow=${p.autoFlow}</span><span>threeStepMode=${p.threeStepMode}</span>`;
      let body = `<h2>${escapeHtml(p.name || p.id)} <small style="color:#57606A;">(${escapeHtml(p.id)})</small></h2>`;
      // 关联 agents
      if ((p.agent_ids || []).length) {
        body += '<h3>关联 Agents</h3><ul>';
        p.agent_ids.forEach(aid => {
          const a = agentById[aid];
          if (a) body += `<li><a href="#" data-link-agent="${escapeAttr(aid)}">${escapeHtml(a.title)}</a> — <small>${escapeHtml(a.role || '')}</small></li>`;
        });
        body += '</ul>';
      }
      // 关联 phase-rules 文档
      if ((p.rules_file_ids || []).length) {
        body += '<h3>阶段规则文档</h3><ul>';
        p.rules_file_ids.forEach(rid => {
          const r = phaseRulesById[rid];
          if (r) body += `<li><a href="#" data-link-phaserule="${escapeAttr(rid)}">${escapeHtml(r.title)}</a></li>`;
        });
        body += '</ul>';
      }
      if (!(p.agent_ids || []).length && !(p.rules_file_ids || []).length) {
        body += '<p style="color:#57606A;">该阶段暂无关联 Agent / 规则文档。</p>';
      }
      openDrawer(p.name || p.id, meta, body);
    });
  });

  // ---------- Minimap 全览 + 视口同步 ----------
  (function initMinimap() {
    const flowWrap = document.getElementById('phases-flow');
    const track = document.getElementById('minimap-track');
    const viewport = document.getElementById('minimap-viewport');
    if (!flowWrap || !track || !viewport) return;

    const miniNodes = Array.from(track.querySelectorAll('.minimap-node'));
    const TOPBAR = 72; // 顶栏遮挡高度补偿

    // 点击全览节点 → 平滑滚动到主流程对应节点
    miniNodes.forEach(mn => {
      mn.addEventListener('click', (e) => {
        e.preventDefault();
        const pid = mn.dataset.miniPhase;
        const target = flowWrap.querySelector('.flow-node[data-phase-id="' + cssEsc(pid) + '"]');
        if (target) {
          const y = target.getBoundingClientRect().top + window.scrollY - TOPBAR - 12;
          window.scrollTo({ top: y, behavior: 'smooth' });
        }
      });
    });

    function cssEsc(s) { return (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/"/g, '\\"'); }

    function sync() {
      const flowTop = flowWrap.getBoundingClientRect().top + window.scrollY;
      const flowH = flowWrap.offsetHeight || 1;
      const viewTop = window.scrollY + TOPBAR;
      const viewBottom = window.scrollY + window.innerHeight;
      let startFrac = (viewTop - flowTop) / flowH;
      let endFrac = (viewBottom - flowTop) / flowH;
      startFrac = Math.max(0, Math.min(1, startFrac));
      endFrac = Math.max(0, Math.min(1, endFrac));
      const trackH = track.scrollHeight;
      const boxTop = startFrac * trackH;
      const boxH = Math.max(18, (endFrac - startFrac) * trackH);
      viewport.style.transform = 'translateY(' + boxTop + 'px)';
      viewport.style.height = boxH + 'px';

      // 高亮当前可见的主节点
      let activeIdx = 0;
      const nodes = flowWrap.querySelectorAll('.flow-node');
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].getBoundingClientRect().top <= TOPBAR + 80) activeIdx = i;
      }
      miniNodes.forEach((mn, i) => mn.classList.toggle('active', i === activeIdx));
      // 让激活项在 minimap 可视范围内
      const am = miniNodes[activeIdx];
      if (am) {
        const at = am.offsetTop, ab = at + am.offsetHeight;
        if (at < track.scrollTop) track.scrollTop = at - 8;
        else if (ab > track.scrollTop + track.clientHeight) track.scrollTop = ab - track.clientHeight + 8;
      }
    }

    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => { sync(); ticking = false; });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    // Tab 切回 phases 或首次渲染时校准
    document.querySelectorAll('.tab').forEach(t => {
      if (t.dataset.tab === 'phases') t.addEventListener('click', () => setTimeout(sync, 30));
    });
    sync();
  })();

  // 抽屉内的二级跳转
  drawerBody.addEventListener('click', (e) => {
    const aAgent = e.target.closest('[data-link-agent]');
    if (aAgent) {
      e.preventDefault();
      const id = aAgent.dataset.linkAgent;
      const a = agentById[id];
      if (a) showAgent(a);
      return;
    }
    const aRule = e.target.closest('[data-link-phaserule]');
    if (aRule) {
      e.preventDefault();
      const id = aRule.dataset.linkPhaserule;
      const r = phaseRulesById[id];
      if (r) showPhaseRule(r);
      return;
    }
  });

  function showAgent(a) {
    const meta = `<span>${escapeHtml(a.file)}</span><span>${(a.size/1024).toFixed(1)} KB</span>` +
      ((a.phases || []).length ? `<span>phases=${a.phases.map(escapeHtml).join(',')}</span>` : '') +
      (a.permissions ? `<span>权限=${escapeHtml(a.permissions)}</span>` : '');
    openDrawer(a.title, meta, a.html);
  }
  function showPhaseRule(r) {
    const meta = `<span>${escapeHtml(r.file)}</span><span>${(r.size/1024).toFixed(1)} KB</span>` +
      ((r.phase_ids || []).length ? `<span>phases=${r.phase_ids.map(escapeHtml).join(',')}</span>` : '');
    openDrawer(r.title, meta, r.html);
  }

  // ---------- Agents tab ----------
  const groupsEl = document.getElementById('agent-groups');
  const phaseOrder = (DATA.phases || []).map(p => p.id);
  function renderAgentGroups(filter) {
    groupsEl.innerHTML = '';
    const groups = {};
    const orphan = [];
    (DATA.agents || []).forEach(a => {
      if (filter && !matchAgent(a, filter)) return;
      if ((a.phases || []).length === 0) {
        orphan.push(a);
      } else {
        a.phases.forEach(pid => {
          (groups[pid] = groups[pid] || []).push(a);
        });
      }
    });
    phaseOrder.forEach(pid => {
      if (!groups[pid]) return;
      const grp = document.createElement('div');
      grp.className = 'agent-group';
      const phaseName = (phaseById[pid] || {}).name || pid;
      grp.innerHTML = `<h3>${escapeHtml(pid)} · ${escapeHtml(phaseName)}</h3><div class="agent-cards"></div>`;
      const cardsEl = grp.querySelector('.agent-cards');
      groups[pid].forEach(a => cardsEl.appendChild(buildAgentCard(a)));
      groupsEl.appendChild(grp);
    });
    if (orphan.length) {
      const grp = document.createElement('div');
      grp.className = 'agent-group';
      grp.innerHTML = `<h3>未关联阶段（${orphan.length}）</h3><div class="agent-cards"></div>`;
      const cardsEl = grp.querySelector('.agent-cards');
      orphan.forEach(a => cardsEl.appendChild(buildAgentCard(a)));
      groupsEl.appendChild(grp);
    }
  }
  function buildAgentCard(a) {
    const div = document.createElement('div');
    div.className = 'agent-card';
    const badges = [];
    (a.phases || []).forEach(p => badges.push(`<span class="badge">${escapeHtml(p)}</span>`));
    if (a.permissions) badges.push(`<span class="badge">权限</span>`);
    div.innerHTML = `<div class="name">${escapeHtml(a.title)}</div>` +
      `<div class="role">${escapeHtml(a.role || '—')}</div>` +
      `<div class="badges">${badges.join('')}</div>`;
    div.addEventListener('click', () => showAgent(a));
    return div;
  }
  function matchAgent(a, q) {
    q = q.toLowerCase();
    return (a.title || '').toLowerCase().includes(q) ||
           (a.role || '').toLowerCase().includes(q) ||
           (a.id || '').toLowerCase().includes(q) ||
           (a.phases || []).some(p => p.toLowerCase().includes(q));
  }
  renderAgentGroups('');

  // ---------- Md collections (rules / templates) ----------
  function renderMdList(coll, filter) {
    const list = DATA[coll] || [];
    const container = document.querySelector(`.md-list[data-collection="${coll}"]`);
    if (!container) return;
    container.innerHTML = '';
    list.forEach(it => {
      if (filter && !matchMd(it, filter)) return;
      const div = document.createElement('div');
      div.className = 'md-item';
      div.innerHTML = `<div class="title">${escapeHtml(it.title)}</div>` +
        `<div class="file">${escapeHtml(it.file)} · ${(it.size/1024).toFixed(1)} KB</div>`;
      div.addEventListener('click', () => {
        const meta = `<span>${escapeHtml(it.file)}</span><span>${(it.size/1024).toFixed(1)} KB</span>`;
        openDrawer(it.title, meta, it.html);
      });
      container.appendChild(div);
    });
  }
  function matchMd(it, q) {
    q = q.toLowerCase();
    return (it.title || '').toLowerCase().includes(q) ||
           (it.id || '').toLowerCase().includes(q);
  }
  renderMdList('rules', '');
  renderMdList('templates', '');

  // ---------- References ----------
  const refsEl = document.getElementById('ref-list');
  function renderRefs(filter) {
    refsEl.innerHTML = '';
    (DATA.references || []).forEach(r => {
      if (filter && !((r.title || '').toLowerCase().includes(filter.toLowerCase()) ||
                      (r.id || '').toLowerCase().includes(filter.toLowerCase()))) return;
      const div = document.createElement('div');
      div.className = 'ref-item';
      div.innerHTML = `<div class="title">${escapeHtml(r.title)}</div>` +
        `<div class="file">${escapeHtml(r.file)} · ${(r.size/1024).toFixed(1)} KB</div>` +
        (r.description ? `<div style="margin-top:6px;color:#57606A;font-size:12px;">${escapeHtml(r.description)}</div>` : '');
      div.addEventListener('click', () => {
        const meta = `<span>${escapeHtml(r.file)}</span><span>${(r.size/1024).toFixed(1)} KB</span>`;
        const body = `<pre><code class="lang-json">${escapeHtml(r.json_text)}</code></pre>`;
        openDrawer(r.title, meta, body);
      });
      refsEl.appendChild(div);
    });
  }
  renderRefs('');

  // ---------- SKILL ----------
  const tocEl = document.getElementById('skill-toc');
  const skillBody = document.getElementById('skill-body');
  if (DATA.skill_main) {
    skillBody.innerHTML = DATA.skill_main.html || '';
    (DATA.skill_main.toc || []).forEach(item => {
      const a = document.createElement('a');
      a.href = '#' + item.anchor;
      a.className = 'lvl-' + item.level;
      a.textContent = item.text;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const target = skillBody.querySelector('#' + CSS.escape(item.anchor));
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      tocEl.appendChild(a);
    });
  }

  // ---------- Health ----------
  const healthEl = document.getElementById('health-block');
  const cs = DATA.consistency || {};
  if (cs.available) {
    const counts = cs.counts || {};
    const summary = `<p class="hint">体检快照：` +
      `PASS <span class="sev-pass">${counts.PASS||0}</span> · ` +
      `WARN <span class="sev-warn">${counts.WARN||0}</span> · ` +
      `FAIL <span class="sev-fail">${counts.FAIL||0}</span> · ` +
      `INFO <span class="sev-info">${counts.INFO||0}</span> · ` +
      `exit_code=${cs.exit_code}</p>`;
    let table = '<table class="health-table"><thead><tr><th>维度</th><th>说明</th><th>聚合状态</th><th>Findings</th></tr></thead><tbody>';
    (cs.checks || []).forEach(c => {
      const sev = c.severity;
      const cls = 'sev-' + sev.toLowerCase();
      const findingsCount = (c.findings || []).filter(f => f.severity !== 'PASS').length;
      let findingsHtml = '';
      if (findingsCount) {
        findingsHtml = '<ul class="findings-list">' +
          (c.findings || []).filter(f => f.severity !== 'PASS').slice(0, 5).map(f =>
            `<li><span class="sev-${f.severity.toLowerCase()}">[${f.severity}]</span> ${escapeHtml(f.title)}</li>`
          ).join('') +
          (findingsCount > 5 ? `<li>...还有 ${findingsCount - 5} 项</li>` : '') +
          '</ul>';
      }
      table += `<tr><td><code>${escapeHtml(c.check_id)}</code></td>` +
        `<td>${escapeHtml(c.description || '')}</td>` +
        `<td class="${cls}">${sev}</td>` +
        `<td>${findingsCount} ${findingsHtml}</td></tr>`;
    });
    table += '</tbody></table>';
    healthEl.innerHTML = summary + table;
  } else {
    healthEl.innerHTML = `<p class="hint">体检快照不可用：${escapeHtml(cs.reason || '未知原因')}。可执行 <code>python3 scripts/consistency_check.py</code> 后重新生成可视化。</p>`;
  }

  // ---------- Search ----------
  const searchEl = document.getElementById('search');
  searchEl.addEventListener('input', () => {
    const q = searchEl.value.trim();
    renderAgentGroups(q);
    renderMdList('rules', q);
    renderMdList('templates', q);
    renderRefs(q);
  });

  // ---------- Utils ----------
  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
  function escapeAttr(s) { return escapeHtml(s); }
})();
"""
