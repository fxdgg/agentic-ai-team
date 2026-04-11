#!/usr/bin/env python3
"""
相对路径解析器

功能：
  - 解析 Agent 文档中的 Skill 内部相对路径
  - 转换为绝对路径
  - 验证文件是否存在

使用方式：
  python path_resolver.py --agent-file <agent_file_path> --project-root <project_root>

输出：
  JSON 格式的路径映射表
"""

import os
import re
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class PathResolver:
    """Skill 内部相对路径解析器"""

    # 匹配 Skill 内部文件的正则模式
    SKILL_INTERNAL_PATTERNS = [
        r'`((?:\.\./)+rules/[^`]*)`',      # 匹配反引号内的 ../../rules/... 或 ../rules/...
        r'`((?:\.\./)+templates/[^`]*)`',  # 匹配反引号内的 ../../templates/... 或 ../templates/...
    ]

    # 定义 Skill 的基准目录（相对于项目根）
    SKILL_BASE_PATH = '.claude/skills/workflow-orchestrator'

    def __init__(self, project_root: str):
        """
        初始化解析器

        参数：
          project_root: 项目根目录的绝对路径
        """
        self.project_root = Path(project_root).resolve()
        self.skill_base = self.project_root / self.SKILL_BASE_PATH

        if not self.skill_base.exists():
            raise ValueError(f"Skill 基准目录不存在: {self.skill_base}")

    def resolve_agent_paths(self, agent_file_path: str) -> Dict[str, str]:
        """
        解析 Agent 文件中的所有相对路径

        参数：
          agent_file_path: Agent 文档的绝对路径

        返回：
          Dict: 相对路径 -> 绝对路径的映射
            {
              "../../rules/java-backend/meta-rule.md": "/abs/path/to/.../rules/java-backend/meta-rule.md",
              ...
            }

        异常：
          FileNotFoundError: Agent 文件不存在
          ValueError: 路径解析失败或文件不存在
        """
        agent_file = Path(agent_file_path).resolve()

        # 验证 Agent 文件存在
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent 文件不存在: {agent_file_path}")

        # 读取 Agent 文件内容
        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"无法读取 Agent 文件: {e}")

        # Agent 文件所在目录（作为相对路径的基准）
        agent_dir = agent_file.parent

        # 扫描并解析所有相对路径
        resolved_paths = {}
        all_matches = []

        for pattern in self.SKILL_INTERNAL_PATTERNS:
            for match in re.finditer(pattern, content):
                relative_path = match.group(1)
                all_matches.append(relative_path)

        # 去重
        unique_paths = list(set(all_matches))

        for relative_path in unique_paths:
            try:
                # 从 Agent 文件位置解析相对路径
                absolute_path = (agent_dir / relative_path).resolve()

                # 验证文件是否存在
                if not absolute_path.exists():
                    raise FileNotFoundError(f"Skill 内部文件不存在: {absolute_path}")

                # 验证文件是否在 Skill 内部
                if not self._is_within_skill(absolute_path):
                    raise ValueError(
                        f"相对路径指向 Skill 外部，禁止: {relative_path} → {absolute_path}"
                    )

                resolved_paths[relative_path] = str(absolute_path)

            except Exception as e:
                raise ValueError(f"无法解析路径 {relative_path}: {e}")

        return resolved_paths

    def _is_within_skill(self, file_path: Path) -> bool:
        """
        验证文件是否在 Skill 内部

        参数：
          file_path: 要验证的文件路径

        返回：
          bool: 是否在 Skill 内部
        """
        try:
            file_path.resolve().relative_to(self.skill_base)
            return True
        except ValueError:
            return False

    def get_relative_path_from_project_root(self, absolute_path: str) -> str:
        """
        获取文件相对于项目根的相对路径

        参数：
          absolute_path: 绝对路径

        返回：
          str: 相对于项目根的路径
        """
        file_path = Path(absolute_path).resolve()
        return str(file_path.relative_to(self.project_root))


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='解析 Agent 文档中的 Skill 内部相对路径'
    )
    parser.add_argument(
        '--agent-file',
        required=True,
        help='Agent 文档的绝对路径'
    )
    parser.add_argument(
        '--project-root',
        required=True,
        help='项目根目录的绝对路径'
    )
    parser.add_argument(
        '--output',
        default='json',
        choices=['json', 'text'],
        help='输出格式（默认: json）'
    )

    args = parser.parse_args()

    try:
        resolver = PathResolver(args.project_root)
        resolved = resolver.resolve_agent_paths(args.agent_file)

        if args.output == 'json':
            print(json.dumps(resolved, indent=2))
        else:
            print("相对路径 -> 绝对路径映射：")
            print("-" * 80)
            for rel_path, abs_path in resolved.items():
                print(f"{rel_path}")
                print(f"  → {abs_path}")
                print()

        return 0

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
