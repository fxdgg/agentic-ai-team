"""通用文件校验函数，供上传类 Skill 脚本复用。"""

import os

from .echo import echo_error


def validate_file(
    filepath: str,
    *,
    max_size: int,
    allowed_extensions: set[str] | None = None,
) -> bool:
    """校验文件：存在性、格式（可选）、大小。校验失败时通过 echo_error 输出错误并退出。

    Args:
        filepath: 文件路径
        max_size: 允许的最大文件字节数
        allowed_extensions: 允许的扩展名集合（含点号，如 {".png", ".jpg"}），None 表示不限制

    Returns:
        校验通过返回 True，失败时 echo_error 会终止进程（不会返回 False 到调用方）
    """
    if not os.path.isfile(filepath):
        echo_error(f"文件不存在: {filepath}", code="FILE_NOT_FOUND")
        return False

    if allowed_extensions is not None:
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in allowed_extensions:
            echo_error(
                f"不支持的文件格式: {ext}",
                code="INVALID_FORMAT",
                details={"allowed": sorted(allowed_extensions)},
            )
            return False

    size = os.path.getsize(filepath)
    if size > max_size:
        echo_error(
            f"文件大小 {size / 1024 / 1024:.1f}MB 超过限制 {max_size / 1024 / 1024:.0f}MB",
            code="FILE_TOO_LARGE",
            details={"size_bytes": size, "max_bytes": max_size},
        )
        return False

    return True
