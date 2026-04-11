"""通用工具函数，提供凭证文件读取、请求 ID 生成等基础能力。"""

import os
import uuid
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".tapd" / "credentials"

_KEY_MAP: dict[str, str] = {
    "access_token": "TAPD_ACCESS_TOKEN",
    "tapd_access_token": "TAPD_ACCESS_TOKEN",
    "env": "ENV",
}


def read_credentials_file(path: Path | None = None) -> dict[str, str]:
    """读取 ~/.tapd/credentials 凭证文件，返回 {配置名: 值} 字典。

    文件格式为每行 key=value，支持 # 注释和空行。
    key 会按 _KEY_MAP 映射为标准配置名（如 access_token -> TAPD_ACCESS_TOKEN）。

    Args:
        path: 凭证文件路径，默认 ~/.tapd/credentials
    """
    if path is None:
        path = CREDENTIALS_PATH
    result: dict[str, str] = {}
    if not path.is_file():
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"无法读取凭证文件 {path}: {exc}") from exc

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().lower()
        value = value.strip()
        env_name = _KEY_MAP.get(key, key.upper())
        result[env_name] = value

    return result


def get_required_config(var_name: str, default: str | None = None) -> str:
    """获取配置值，优先从凭证文件读取，凭证文件不存在时回退到环境变量。

    查找顺序：~/.tapd/credentials 凭证文件 → 环境变量 → 默认值。

    Args:
        var_name: 配置名称（如 TAPD_ACCESS_TOKEN、ENV）
        default: 默认值，为 None 时表示该配置必须存在

    Returns:
        配置值

    Raises:
        ValueError: 当所有来源均未找到值且无默认值时
    """
    creds = read_credentials_file()
    value = creds.get(var_name)
    if value:
        return value

    value = os.getenv(var_name)
    if value:
        return value

    if default is not None:
        return default

    raise ValueError(
        f"{var_name} 未设置。请通过以下任一方式配置：\n"
        f"  1. 执行 make init-credentials 创建凭证文件\n"
        f"  2. 设置环境变量: export {var_name}=<值>"
    )


def generate_nginx_request_id() -> str:
    """生成 32 位十六进制请求 ID，用于 TAPD API 链路追踪。"""
    return uuid.uuid4().hex
