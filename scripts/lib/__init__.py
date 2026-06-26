"""ai-team 引擎工具链共享库。

模块导出：
    paths            — 仓库根目录与关键路径定位
    md_parser        — Markdown 解析（quote-block frontmatter / 表格 / AUTO-GEN）
    autogen_block    — AUTO-GEN 区段读写 + sha256 hash
    dependency_graph — 文件依赖图（基于 ARCHITECTURE.md §2 + 命名约定）
    platform_mirror  — 双平台对账
    reporters        — 报告格式化（console / md / json）
"""

__version__ = "0.1.0"
