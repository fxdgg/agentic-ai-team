"""DSL 加载器：读取 meta/*.yaml 单一真相源，构建内存模型。

Phase 2 引入。设计原则：
    1. **只读加载** — 不修改 YAML 文件本身
    2. **保序加载** — Python 3.7+ dict 自然保序；列表自然保序
    3. **延迟校验** — 加载阶段只做语法检查，语义校验交给 validate_meta.py
    4. **缺失容忍** — 文件不存在时返回 None，调用方决定是否失败

模块导出：
    load_phases_meta()       — 加载 meta/phases.yaml
    load_state_schema_meta() — 加载 meta/state-schema.yaml
    load_commands_meta()     — 加载 meta/commands.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:
    raise ImportError(
        "需要安装 PyYAML：pip install -r scripts/requirements.txt"
    ) from e

from . import paths


def _load_yaml(path: Path) -> dict | None:
    """加载 YAML 文件。文件不存在返回 None。"""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层必须是 mapping，实际是 {type(data).__name__}")
    return data


def load_phases_meta() -> dict | None:
    """加载阶段流转 DSL（meta/phases.yaml）。

    期望结构（参考 meta/README.md）::
        version: 1
        phases:
          - id: INIT
            name: 初始化
            order: 0
            next: ANALYSE_PRODUCT
            canSkipTo: null
            autoFlow: true
            threeStepMode: false
            agents: ...
        rules:
          forward: ...
          skipCondition: ...
          rollback: ...
          termination: ...
    """
    return _load_yaml(paths.META_PHASES)


def load_state_schema_meta() -> dict | None:
    """加载 state.json schema DSL（meta/state-schema.yaml）。"""
    return _load_yaml(paths.META_STATE_SCHEMA)


def load_commands_meta() -> dict | None:
    """加载命令 DSL（meta/commands.yaml）。"""
    return _load_yaml(paths.META_COMMANDS)


def load_platform_divergence() -> dict | None:
    """加载双平台偏差豁免清单（meta/platform-divergence.yaml）。"""
    return _load_yaml(paths.META_DIVERGENCE)


def load_all() -> dict[str, Any]:
    """一次性加载所有 DSL 文件。返回 {phases, state_schema, commands, platform_divergence} 字典，缺失文件键值为 None。"""
    return {
        "phases": load_phases_meta(),
        "state_schema": load_state_schema_meta(),
        "commands": load_commands_meta(),
        "platform_divergence": load_platform_divergence(),
    }
