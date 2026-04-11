#!/usr/bin/env python3
"""
Agent 路径替换脚本（方案 A）

功能：
  - 直接替换 Agent 文档中的相对路径为绝对路径
  - 返回修改后的 Agent 内容，可直接作为 system prompt
  - 避免重复路径解析和信息冗余

使用方式：
  python replace_agent_paths.py --agent-file <path> --project-root <path> [--format file|content]

输出：
  - format=file: 返回修改后内容保存的临时文件路径
  - format=content: 直接返回修改后的内容
"""

import sys
import json
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional


class AgentPathReplacer:
    """Agent 路径直接替换器（方案 A）"""

    def __init__(self, agent_file: str, project_root: str, scripts_dir: str):
        """
        初始化替换器

        参数：
          agent_file: Agent 文档的绝对路径
          project_root: 项目根目录的绝对路径
          scripts_dir: 脚本目录的绝对路径
        """
        self.agent_file = Path(agent_file).resolve()
        self.project_root = Path(project_root).resolve()
        self.scripts_dir = Path(scripts_dir).resolve()

    def replace_paths(self) -> Tuple[str, Dict[str, str]]:
        """
        替换 Agent 文档中的所有相对路径为绝对路径

        返回：
          Tuple: (修改后的内容, 替换映射表)
        """
        # Step 1: 读取 Agent 文件
        try:
            with open(self.agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"无法读取 Agent 文件: {e}")

        # Step 2: 调用 path_resolver 获取路径映射
        path_mappings = self._get_path_mappings()

        if not path_mappings:
            # 无需替换，直接返回原始内容
            return content, {}

        # Step 3: 替换相对路径为绝对路径
        modified_content = content
        replacements = {}

        for rel_path, abs_path in sorted(path_mappings.items()):
            # 构造要替换的模式：`相对路径`
            old_pattern = f"`{rel_path}`"

            # 构造替换后的内容：`绝对路径`（保持反引号格式以便 Agent 识别为代码）
            new_pattern = f"`{abs_path}`"

            # 执行替换
            if old_pattern in modified_content:
                modified_content = modified_content.replace(old_pattern, new_pattern)
                replacements[rel_path] = abs_path
                print(f"✓ 已替换: {rel_path} → {abs_path}", file=sys.stderr)
            else:
                # 如果模式未找到，可能是 Markdown 表格中没有反引号或格式不同
                # 尝试不同的模式
                alt_patterns = [
                    (f"{rel_path}", f"{abs_path}"),  # 不带反引号
                ]

                for alt_old, alt_new in alt_patterns:
                    if alt_old in modified_content:
                        modified_content = modified_content.replace(alt_old, alt_new)
                        replacements[rel_path] = abs_path
                        print(f"✓ 已替换（无反引号）: {rel_path} → {abs_path}", file=sys.stderr)
                        break

        return modified_content, replacements

    def _get_path_mappings(self) -> Dict[str, str]:
        """
        调用 path_resolver.py 获取路径映射

        返回：
          Dict: 相对路径 -> 绝对路径的映射
        """
        resolver_script = self.scripts_dir / 'path_resolver.py'

        cmd = [
            'python3',
            str(resolver_script),
            '--agent-file', str(self.agent_file),
            '--project-root', str(self.project_root),
            '--output', 'json'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError(f"path_resolver 执行失败: {result.stderr}")

            return json.loads(result.stdout)

        except Exception as e:
            print(f"⚠️ 路径解析失败（将使用原始 Agent）: {e}", file=sys.stderr)
            return {}

    def save_to_temp_file(self, content: str) -> str:
        """
        将修改后的内容保存到临时文件

        参数：
          content: 要保存的内容

        返回：
          str: 临时文件路径
        """
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.md',
            encoding='utf-8',
            delete=False
        ) as f:
            f.write(content)
            return f.name


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='直接替换 Agent 文档中的相对路径为绝对路径'
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
        '--format',
        default='file',
        choices=['file', 'content'],
        help='输出格式：file（临时文件路径）或 content（直接内容）'
    )

    args = parser.parse_args()

    # 获取脚本目录
    scripts_dir = Path(__file__).parent.absolute()

    try:
        replacer = AgentPathReplacer(args.agent_file, args.project_root, str(scripts_dir))
        modified_content, replacements = replacer.replace_paths()

        if args.format == 'file':
            # 保存到临时文件并返回路径
            temp_file = replacer.save_to_temp_file(modified_content)
            output = {
                "success": True,
                "file": temp_file,
                "replacements": replacements,
                "message": f"已将修改后的 Agent 保存到: {temp_file}"
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            # 直接返回内容
            output = {
                "success": True,
                "content": modified_content,
                "replacements": replacements,
                "message": "已返回修改后的 Agent 内容"
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))

        return 0

    except Exception as e:
        error_output = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(error_output, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
