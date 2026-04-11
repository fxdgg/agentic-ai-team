#!/usr/bin/env python3
"""
上下文注入器

功能：
  - 将转换后的路径信息注入 Task 上下文
  - 生成适合注入 Agent 的上下文文本
  - 支持多种格式输出

使用方式：
  python context_injector.py --paths <path_mappings_json> --format <format>

输出：
  格式化的上下文文本，可直接追加到 Task prompt 中
"""

import json
import sys
import argparse
from typing import Dict
from pathlib import Path


class ContextInjector:
    """上下文注入器"""

    def __init__(self, path_mappings: Dict[str, str]):
        """
        初始化注入器

        参数：
          path_mappings: 相对路径 -> 绝对路径的映射
        """
        self.path_mappings = path_mappings

    def generate_context(self, format: str = 'markdown') -> str:
        """
        生成上下文文本

        参数：
          format: 输出格式 ('markdown', 'json', 'plain')

        返回：
          str: 格式化的上下文文本
        """
        if format == 'markdown':
            return self._generate_markdown_context()
        elif format == 'json':
            return self._generate_json_context()
        elif format == 'plain':
            return self._generate_plain_context()
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _generate_markdown_context(self) -> str:
        """生成 Markdown 格式的上下文"""
        lines = []
        lines.append("---")
        lines.append("## 【Skill 内部文件映射】")
        lines.append("")
        lines.append("你的规则文件和模板文件存放在以下位置：")
        lines.append("")

        for relative_path, absolute_path in self.path_mappings.items():
            # 获取相对于项目根的路径
            display_path = self._shorten_path(absolute_path)
            lines.append(f"- **{relative_path}**")
            lines.append(f"  → {display_path}")
            lines.append("")

        lines.append("---")
        return "\n".join(lines)

    def _generate_json_context(self) -> str:
        """生成 JSON 格式的上下文"""
        context = {
            "skill_internal_files": self.path_mappings,
            "info": {
                "type": "Skill 内部文件映射",
                "description": "这些是你可以引用的规则文件和模板文件"
            }
        }
        return json.dumps(context, indent=2, ensure_ascii=False)

    def _generate_plain_context(self) -> str:
        """生成纯文本格式的上下文"""
        lines = []
        lines.append("=" * 80)
        lines.append("Skill 内部文件映射")
        lines.append("=" * 80)
        lines.append("")

        for relative_path, absolute_path in self.path_mappings.items():
            display_path = self._shorten_path(absolute_path)
            lines.append(f"{relative_path}")
            lines.append(f"  → {display_path}")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    @staticmethod
    def _shorten_path(absolute_path: str, max_length: int = 100) -> str:
        """
        缩短路径显示

        参数：
          absolute_path: 绝对路径
          max_length: 最大长度

        返回：
          str: 缩短后的路径
        """
        path = Path(absolute_path)

        # 如果路径太长，只显示最后几个部分
        if len(absolute_path) > max_length:
            parts = path.parts
            # 保留文件名和前几个目录
            if len(parts) > 3:
                shortened = '.../' + '/'.join(parts[-3:])
            else:
                shortened = '/'.join(parts)
            return shortened
        else:
            return absolute_path


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='生成 Skill 内部文件的上下文注入文本'
    )
    parser.add_argument(
        '--paths',
        required=True,
        help='JSON 格式的路径映射'
    )
    parser.add_argument(
        '--format',
        default='markdown',
        choices=['markdown', 'json', 'plain'],
        help='输出格式（默认: markdown）'
    )

    args = parser.parse_args()

    try:
        # 解析路径映射
        path_mappings = json.loads(args.paths)

        injector = ContextInjector(path_mappings)
        context = injector.generate_context(args.format)

        print(context)
        return 0

    except json.JSONDecodeError as e:
        print(f"错误: 无法解析 JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
