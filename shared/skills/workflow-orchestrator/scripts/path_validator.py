#!/usr/bin/env python3
"""
路径验证器

功能：
  - 验证相对路径是否符合规范
  - 检查是否存在无效的 ../ 数量
  - 检查是否指向 Skill 外部（禁止）
  - 验证文件存在性

使用方式：
  python path_validator.py --paths <path_mappings_json> --project-root <project_root>

输出：
  验证结果（JSON 格式），包含是否通过和具体的错误信息
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class PathValidator:
    """路径验证器"""

    # Skill 的基准目录（相对于项目根）
    SKILL_BASE_PATH = '.codebuddy/skills/workflow-orchestrator'

    # 允许的 Skill 内部目录
    ALLOWED_INTERNAL_DIRS = ['rules', 'templates']

    def __init__(self, project_root: str):
        """
        初始化验证器

        参数：
          project_root: 项目根目录的绝对路径
        """
        self.project_root = Path(project_root).resolve()
        self.skill_base = self.project_root / self.SKILL_BASE_PATH

    def validate_paths(self, path_mappings: Dict[str, str]) -> Dict:
        """
        验证所有路径

        参数：
          path_mappings: 相对路径 -> 绝对路径的映射

        返回：
          Dict: 验证结果
            {
              "passed": bool,
              "total": int,
              "valid": int,
              "invalid": int,
              "errors": [
                {
                  "relative_path": "../../rules/...",
                  "absolute_path": "/abs/path/...",
                  "error": "错误信息",
                  "severity": "error|warning"
                }
              ]
            }
        """
        results = {
            "passed": True,
            "total": len(path_mappings),
            "valid": 0,
            "invalid": 0,
            "errors": []
        }

        for relative_path, absolute_path in path_mappings.items():
            error = self._validate_single_path(relative_path, absolute_path)

            if error:
                results["invalid"] += 1
                results["passed"] = False
                results["errors"].append({
                    "relative_path": relative_path,
                    "absolute_path": absolute_path,
                    "error": error["message"],
                    "severity": error["severity"]
                })
            else:
                results["valid"] += 1

        return results

    def _validate_single_path(self, relative_path: str, absolute_path: str) -> Optional[Dict]:
        """
        验证单个路径

        参数：
          relative_path: 相对路径（如 ../../rules/java-backend/meta-rule.md）
          absolute_path: 绝对路径

        返回：
          Dict 或 None: 如果验证失败，返回错误信息；否则返回 None
        """
        errors = []

        # 1. 检查文件是否存在
        abs_file = Path(absolute_path)
        if not abs_file.exists():
            errors.append({
                "message": f"文件不存在: {absolute_path}",
                "severity": "error"
            })

        # 2. 检查是否指向 Skill 外部
        if not self._is_within_skill(abs_file):
            errors.append({
                "message": f"路径指向 Skill 外部，禁止: {absolute_path}",
                "severity": "error"
            })

        # 3. 检查相对路径格式
        format_error = self._validate_path_format(relative_path)
        if format_error:
            errors.append({
                "message": format_error,
                "severity": "error"
            })

        # 4. 检查是否指向允许的目录
        dir_error = self._validate_internal_directory(relative_path)
        if dir_error:
            errors.append({
                "message": dir_error,
                "severity": "warning"
            })

        # 返回第一个错误（或 None 如果通过）
        return errors[0] if errors else None

    def _is_within_skill(self, file_path: Path) -> bool:
        """检查文件是否在 Skill 内部"""
        try:
            file_path.resolve().relative_to(self.skill_base)
            return True
        except ValueError:
            return False

    def _validate_path_format(self, relative_path: str) -> Optional[str]:
        """
        验证相对路径的格式

        返回：
          错误信息或 None
        """
        # 检查是否以 ../ 开头
        if not relative_path.startswith('..'):
            return f"相对路径必须以 ../ 开头: {relative_path}"

        # 检查是否包含不安全的字符
        unsafe_patterns = ['..\\', '~/', '${', '`']
        for pattern in unsafe_patterns:
            if pattern in relative_path:
                return f"相对路径包含不安全字符: {pattern}"

        return None

    def _validate_internal_directory(self, relative_path: str) -> Optional[str]:
        """
        检查相对路径是否指向允许的内部目录

        返回：
          错误信息或 None
        """
        # 提取目录名（第一个 ../ 后面的部分）
        parts = relative_path.split('/')

        # 查找第一个不是 .. 的部分
        for part in parts:
            if part and part != '..':
                if part not in self.ALLOWED_INTERNAL_DIRS:
                    return f"只允许引用 {self.ALLOWED_INTERNAL_DIRS} 目录，不允许: {part}/"
                break

        return None


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='验证相对路径的有效性'
    )
    parser.add_argument(
        '--paths',
        required=True,
        help='JSON 格式的路径映射 (相对路径 -> 绝对路径)'
    )
    parser.add_argument(
        '--project-root',
        required=True,
        help='项目根目录的绝对路径'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='严格模式：任何警告都视为失败'
    )

    args = parser.parse_args()

    try:
        # 解析路径映射
        path_mappings = json.loads(args.paths)

        validator = PathValidator(args.project_root)
        result = validator.validate_paths(path_mappings)

        # 严格模式检查
        if args.strict and result["errors"]:
            result["passed"] = False

        print(json.dumps(result, indent=2))

        return 0 if result["passed"] else 1

    except json.JSONDecodeError as e:
        print(f"错误: 无法解析 JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
