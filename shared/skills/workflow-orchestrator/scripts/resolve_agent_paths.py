#!/usr/bin/env python3
"""
Agent 路径解析主脚本

功能：
  - 协调调用 path_resolver、path_validator、context_injector
  - 一站式处理 Agent 文档中的相对路径
  - 输出完整的上下文信息

使用方式：
  python resolve_agent_paths.py --agent-file <path> --project-root <path> [--format markdown|json]

返回：
  0: 成功
  1: 失败（路径验证不通过或其他错误）
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Dict


class AgentPathResolver:
    """Agent 路径解析器（主协调器）"""

    def __init__(self, agent_file: str, project_root: str, scripts_dir: str):
        """
        初始化

        参数：
          agent_file: Agent 文档的绝对路径
          project_root: 项目根目录的绝对路径
          scripts_dir: 脚本目录的绝对路径
        """
        self.agent_file = agent_file
        self.project_root = project_root
        self.scripts_dir = scripts_dir

    def replace(self) -> Dict:
        """
        执行路径替换流程（方案 A：直接替换相对路径为绝对路径）

        返回：
          Dict: 替换结果
            {
              "success": bool,
              "modified_content": str,
              "replacements": {...},
              "temp_file": str,
              "message": str,
              "errors": [...]
            }
        """
        result = {
            "success": False,
            "modified_content": "",
            "replacements": {},
            "temp_file": "",
            "message": "",
            "errors": []
        }

        try:
            # 调用 replace_agent_paths.py
            replacer_script = Path(self.scripts_dir) / 'replace_agent_paths.py'

            cmd = [
                'python3',
                str(replacer_script),
                '--agent-file', self.agent_file,
                '--project-root', self.project_root,
                '--format', 'file'
            ]

            replace_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if replace_result.returncode != 0:
                result["errors"].append(f"路径替换失败: {replace_result.stderr}")
                return result

            replace_data = json.loads(replace_result.stdout)

            if not replace_data.get("success"):
                result["errors"].append(f"路径替换失败: {replace_data.get('error')}")
                return result

            # 读取修改后的内容
            temp_file = replace_data.get("file")
            try:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    modified_content = f.read()
            except Exception as e:
                result["errors"].append(f"无法读取临时文件: {e}")
                return result

            result["success"] = True
            result["modified_content"] = modified_content
            result["replacements"] = replace_data.get("replacements", {})
            result["temp_file"] = temp_file
            result["message"] = f"成功替换 {len(result['replacements'])} 个路径"

            return result

        except Exception as e:
            result["errors"].append(f"路径替换异常: {e}")
            return result

    def resolve(self, strict: bool = False, format: str = 'markdown') -> Dict:
        """
        执行完整的路径解析流程

        参数：
          strict: 严格模式（任何警告都视为失败）
          format: 上下文输出格式

        返回：
          Dict: 解析结果
            {
              "success": bool,
              "resolved_paths": {...},
              "validation": {...},
              "context": str,
              "errors": [...]
            }
        """
        result = {
            "success": False,
            "resolved_paths": {},
            "validation": {},
            "context": "",
            "errors": []
        }

        # Step 1: 解析相对路径
        try:
            resolved_paths = self._run_path_resolver()
            result["resolved_paths"] = resolved_paths
        except Exception as e:
            result["errors"].append(f"路径解析失败: {e}")
            return result

        # Step 2: 验证路径
        try:
            validation_result = self._run_path_validator(resolved_paths, strict)
            result["validation"] = validation_result

            if not validation_result.get("passed", False):
                result["errors"].append("路径验证失败")
                for error in validation_result.get("errors", []):
                    result["errors"].append(f"  - {error['relative_path']}: {error['error']}")
                return result

        except Exception as e:
            result["errors"].append(f"路径验证异常: {e}")
            return result

        # Step 3: 生成上下文
        try:
            context = self._run_context_injector(resolved_paths, format)
            result["context"] = context
        except Exception as e:
            result["errors"].append(f"上下文生成失败: {e}")
            return result

        result["success"] = True
        return result

    def _run_path_resolver(self) -> Dict[str, str]:
        """
        运行 path_resolver.py

        返回：
          Dict: 相对路径 -> 绝对路径的映射
        """
        resolver_script = Path(self.scripts_dir) / 'path_resolver.py'

        cmd = [
            'python3',
            str(resolver_script),
            '--agent-file', self.agent_file,
            '--project-root', self.project_root,
            '--output', 'json'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(f"path_resolver 执行失败: {result.stderr}")

        return json.loads(result.stdout)

    def _run_path_validator(self, path_mappings: Dict[str, str], strict: bool = False) -> Dict:
        """
        运行 path_validator.py

        参数：
          path_mappings: 相对路径 -> 绝对路径的映射
          strict: 严格模式

        返回：
          Dict: 验证结果
        """
        validator_script = Path(self.scripts_dir) / 'path_validator.py'

        cmd = [
            'python3',
            str(validator_script),
            '--paths', json.dumps(path_mappings),
            '--project-root', self.project_root
        ]

        if strict:
            cmd.append('--strict')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(f"path_validator 执行失败: {result.stderr}")

        return json.loads(result.stdout)

    def _run_context_injector(self, path_mappings: Dict[str, str], format: str = 'markdown') -> str:
        """
        运行 context_injector.py

        参数：
          path_mappings: 相对路径 -> 绝对路径的映射
          format: 输出格式

        返回：
          str: 生成的上下文文本
        """
        injector_script = Path(self.scripts_dir) / 'context_injector.py'

        cmd = [
            'python3',
            str(injector_script),
            '--paths', json.dumps(path_mappings),
            '--format', format
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(f"context_injector 执行失败: {result.stderr}")

        return result.stdout


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='解析 Agent 文档中的相对路径并生成上下文'
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
        default='markdown',
        choices=['markdown', 'json', 'plain'],
        help='上下文输出格式（默认: markdown）'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='严格模式（任何警告都视为失败）'
    )
    parser.add_argument(
        '--output',
        default='json',
        choices=['json', 'context'],
        help='最终输出内容（默认: json）'
    )
    parser.add_argument(
        '--mode',
        default='resolve',
        choices=['resolve', 'replace'],
        help='处理模式：resolve（生成上下文）或 replace（直接替换路径，推荐用于 Task 调用）'
    )

    args = parser.parse_args()

    # 获取脚本目录
    scripts_dir = Path(__file__).parent.absolute()

    try:
        resolver = AgentPathResolver(args.agent_file, args.project_root, str(scripts_dir))

        if args.mode == 'replace':
            # 方案 A：直接替换模式（推荐）
            result = resolver.replace()

            if args.output == 'json':
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                # 只输出修改后的内容
                if result["success"]:
                    print(result["modified_content"])
                else:
                    print(f"错误: {result['errors']}", file=sys.stderr)

            return 0 if result["success"] else 1
        else:
            # 原始模式：生成上下文
            result = resolver.resolve(strict=args.strict, format=args.format)

            if args.output == 'json':
                # 输出完整的 JSON 结果
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                # 只输出生成的上下文
                print(result["context"])

            return 0 if result["success"] else 1

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
