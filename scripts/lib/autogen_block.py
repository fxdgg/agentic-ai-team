"""AUTO-GEN 区段读写 + sha256 hash 校验。

区段格式（HTML 注释包裹，正文为纯 markdown，可以是表格 / 列表 / 段落）：

    <!-- BEGIN AUTO-GEN: section-id hash=<sha256> source=<file:section> -->

    实际渲染内容...

    <!-- END AUTO-GEN: section-id -->

约束：
    1. `section-id` 与 BEGIN/END 必须一一对应，且全文件内唯一
    2. `hash` 必须等于区段内容（不含 BEGIN/END 注释行本身）经 normalize 后的 sha256
       normalize 规则：
           - 行尾去空白
           - 文件级末尾换行不计
           - BEGIN/END 之间紧邻的空行不计入 hash 但保留在文件中（可读性）
    3. `source` 字段为可选元数据，记录此区段的渲染来源
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


# 注释行匹配（hash / source 字段顺序不限，全部可选）
BEGIN_RE = re.compile(
    r"<!--\s*BEGIN\s+AUTO-GEN\s*:\s*"
    r"(?P<sid>[a-zA-Z0-9._\-:/]+)"
    r"(?P<attrs>[^>]*?)"
    r"-->"
)
END_RE = re.compile(
    r"<!--\s*END\s+AUTO-GEN\s*:\s*(?P<sid>[a-zA-Z0-9._\-:/]+)\s*-->"
)
ATTR_RE = re.compile(r"(?P<key>[a-zA-Z_][a-zA-Z0-9_\-]*)\s*=\s*(?P<val>\S+)")


@dataclass
class AutogenBlock:
    """一个 AUTO-GEN 区段。

    所有行号为 1-based。begin_line 指 BEGIN 注释所在行，end_line 指 END 注释所在行。
    body_lines 为不含 BEGIN/END 注释行本身的中间内容（可能含前后空行）。
    """
    section_id: str
    begin_line: int
    end_line: int
    body_lines: list[str]
    declared_hash: str | None = None                 # BEGIN 注释中声明的 hash
    declared_source: str | None = None
    extra_attrs: dict[str, str] = field(default_factory=dict)

    @property
    def body_text(self) -> str:
        return "\n".join(self.body_lines)

    def computed_hash(self) -> str:
        return compute_block_hash(self.body_lines)

    def is_hash_valid(self) -> bool | None:
        """如果 declared_hash 缺失返回 None；否则返回 bool。"""
        if not self.declared_hash:
            return None
        return self.declared_hash == self.computed_hash()


def compute_block_hash(body_lines: list[str]) -> str:
    """计算区段内容的 sha256。

    normalize 规则：
        1. 每行去掉尾部空白
        2. 删除前后空行（仅区段内部首尾）
        3. 用 `\\n` 连接，末尾不加 `\\n`
    """
    # 1. 去尾空白
    stripped = [ln.rstrip() for ln in body_lines]
    # 2. 删除前后空行
    while stripped and stripped[0] == "":
        stripped.pop(0)
    while stripped and stripped[-1] == "":
        stripped.pop()
    payload = "\n".join(stripped)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _parse_attrs(attr_str: str) -> dict[str, str]:
    return {m.group("key"): m.group("val") for m in ATTR_RE.finditer(attr_str)}


def find_blocks(text: str) -> list[AutogenBlock]:
    """扫描文本中所有 AUTO-GEN 区段。

    校验：
        - BEGIN/END 嵌套不允许（同一 section_id 必须紧邻闭合）
        - section_id 在文件内必须唯一
    出现错误时直接抛 ValueError，由调用方包装为 Finding。
    """
    lines = text.splitlines()
    blocks: list[AutogenBlock] = []
    open_stack: list[tuple[str, int, dict[str, str]]] = []
    body_buffer: list[str] = []
    seen_ids: set[str] = set()

    for idx, line in enumerate(lines, start=1):
        bm = BEGIN_RE.search(line)
        em = END_RE.search(line)

        if bm and em:
            raise ValueError(f"行 {idx}：同一行包含 BEGIN 和 END，不允许")

        if bm:
            sid = bm.group("sid")
            if open_stack:
                raise ValueError(
                    f"行 {idx}：区段 '{sid}' 在 '{open_stack[-1][0]}' 未闭合时开启"
                )
            if sid in seen_ids:
                raise ValueError(f"行 {idx}：区段 ID '{sid}' 在文件内重复")
            attrs = _parse_attrs(bm.group("attrs"))
            open_stack.append((sid, idx, attrs))
            body_buffer = []
            seen_ids.add(sid)
            continue

        if em:
            sid = em.group("sid")
            if not open_stack:
                raise ValueError(f"行 {idx}：发现 END 但无对应 BEGIN（id={sid}）")
            open_sid, begin_line, attrs = open_stack[-1]
            if open_sid != sid:
                raise ValueError(
                    f"行 {idx}：END 区段 '{sid}' 与开启的 '{open_sid}' 不匹配"
                )
            open_stack.pop()
            blocks.append(AutogenBlock(
                section_id=sid,
                begin_line=begin_line,
                end_line=idx,
                body_lines=list(body_buffer),
                declared_hash=attrs.get("hash"),
                declared_source=attrs.get("source"),
                extra_attrs={k: v for k, v in attrs.items() if k not in {"hash", "source"}},
            ))
            body_buffer = []
            continue

        if open_stack:
            body_buffer.append(line)

    if open_stack:
        sid, begin_line, _ = open_stack[-1]
        raise ValueError(f"区段 '{sid}' 在行 {begin_line} 开启后未闭合")

    return blocks


def render_block_comments(
    section_id: str,
    body_text: str,
    source: str | None = None,
    extra_attrs: dict[str, str] | None = None,
) -> str:
    """生成完整的 AUTO-GEN 注释包裹后的文本。

    返回值不含尾部换行，调用方负责拼接到目标文件。
    """
    body_lines = body_text.splitlines()
    h = compute_block_hash(body_lines)
    attrs = [f"hash={h}"]
    if source:
        attrs.append(f"source={source}")
    if extra_attrs:
        for k, v in extra_attrs.items():
            attrs.append(f"{k}={v}")
    attrs_str = " " + " ".join(attrs)
    begin = f"<!-- BEGIN AUTO-GEN: {section_id}{attrs_str} -->"
    end = f"<!-- END AUTO-GEN: {section_id} -->"
    return "\n".join([begin, "", body_text.rstrip("\n"), "", end])


def replace_block_in_file(
    path: Path | str,
    section_id: str,
    new_body: str,
    source: str | None = None,
    dry_run: bool = False,
) -> tuple[bool, str | None]:
    """替换文件中指定区段的内容。

    返回 `(changed, error)`：
        - changed: True 表示文件有改动；False 表示原内容已与新内容一致
        - error: 失败时的错误信息（如未找到 section_id），成功为 None

    `dry_run=True` 时仅计算结果，不写回。
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        blocks = find_blocks(text)
    except ValueError as e:
        return False, str(e)
    target = next((b for b in blocks if b.section_id == section_id), None)
    if target is None:
        return False, f"未找到区段 ID：{section_id}"

    lines = text.splitlines()
    # 重新生成包含 BEGIN/END 的完整片段
    rendered = render_block_comments(section_id, new_body, source=source)
    rendered_lines = rendered.splitlines()

    new_lines = lines[: target.begin_line - 1] + rendered_lines + lines[target.end_line:]
    new_text = "\n".join(new_lines)
    if text.endswith("\n"):
        new_text += "\n"

    if new_text == text:
        return False, None

    if not dry_run:
        p.write_text(new_text, encoding="utf-8")
    return True, None


def wrap_lines_in_file(
    path: Path | str,
    section_id: str,
    start_line: int,
    end_line: int,
    source: str | None = None,
    dry_run: bool = False,
) -> tuple[bool, str | None]:
    """**首次区段化**：在文件指定行范围 [start_line, end_line]（1-based, 闭区间）外层
    包裹 AUTO-GEN BEGIN/END 注释，原内容**byte-equal 保留**为 body。

    返回 `(changed, error)`。

    用途：第一次给一个已有的表格 / 段落加 AUTO-GEN 标记时使用，确保不改动正文。
    后续修改这个区段应使用 `replace_block_in_file`。

    幂等性：如果该范围已经被相同 section_id 的 BEGIN/END 包裹则不操作。
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    n = len(lines)

    if start_line < 1 or end_line > n or start_line > end_line:
        return False, f"行范围非法：[{start_line}, {end_line}]，文件共 {n} 行"

    # 幂等检查：若 start_line - 1 已是同 ID 的 BEGIN 且 end_line + 1 是同 ID 的 END，则跳过
    try:
        existing = find_blocks(text)
    except ValueError as e:
        return False, str(e)
    for b in existing:
        if b.section_id == section_id:
            return False, f"区段 ID '{section_id}' 已存在（行 {b.begin_line}-{b.end_line}）"

    body_lines = lines[start_line - 1:end_line]  # inclusive
    # 归一化：剥离 body 首尾空行，确保 wrap 输出结构稳定（双平台 byte-equal）
    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    body_text = "\n".join(body_lines)
    rendered = render_block_comments(section_id, body_text, source=source)
    rendered_lines = rendered.splitlines()

    # 在原范围替换为 wrapped 版本
    new_lines = lines[: start_line - 1] + rendered_lines + lines[end_line:]
    new_text = "\n".join(new_lines)
    if text.endswith("\n"):
        new_text += "\n"

    if not dry_run:
        p.write_text(new_text, encoding="utf-8")
    return True, None
