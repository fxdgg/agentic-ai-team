"""标准化纯文本输出函数，供 Skills 脚本向 stdout 打印结构化信息。

采用 key: value 纯文本格式而非 JSON，最大限度减少无效 token
（引号、括号、逗号等结构符号），节省模型上下文窗口。

输出类型：
    - success : [success] message + key: value 数据行
    - error   : [error] message (CODE) + 补充信息行，进程以退出码 1 终止
    - warning : [warning] message + 可选附加数据
    - progress: [progress] step (current/total)
"""

import sys
from typing import Any


def _format_pairs(data: dict[str, Any]) -> list[str]:
    """将字典格式化为 key: value 行列表，跳过空值，展平嵌套结构。"""
    lines: list[str] = []
    for k, v in data.items():
        if v is None or v == "" or v == [] or v == {}:
            continue
        if isinstance(v, list):
            lines.append(f"{k}: {', '.join(str(i) for i in v)}")
        elif isinstance(v, dict):
            for dk, dv in v.items():
                if dv is not None and dv != "" and dv != [] and dv != {}:
                    lines.append(f"{k}.{dk}: {dv}")
        else:
            lines.append(f"{k}: {v}")
    return lines


def echo_success(data: dict[str, Any], message: str = "") -> None:
    """输出成功结果。

    Args:
        data: 业务数据字典（仅输出非空字段）
        message: 可选的人类可读描述
    """
    header = f"[success] {message}" if message else "[success]"
    lines = [header, *_format_pairs(data)]
    print("\n".join(lines))


def echo_error(message: str, code: str = "", details: dict[str, Any] | None = None) -> None:
    """输出错误信息并以退出码 1 终止进程。

    Args:
        message: 错误描述
        code: 机器可读的错误码（如 FILE_NOT_FOUND）
        details: 补充调试信息
    """
    header = f"[error] {message} ({code})" if code else f"[error] {message}"
    lines = [header]
    if details:
        lines.extend(_format_pairs(details))
    print("\n".join(lines))
    sys.exit(1)


def echo_warning(message: str, data: dict[str, Any] | None = None) -> None:
    """输出警告信息，脚本继续执行。

    Args:
        message: 警告描述
        data: 可选的附加数据
    """
    lines = [f"[warning] {message}"]
    if data:
        lines.extend(_format_pairs(data))
    print("\n".join(lines))


def echo_progress(step: str, current: int, total: int) -> None:
    """输出进度信息，用于多步骤任务。

    Args:
        step: 当前步骤描述
        current: 当前进度（第几步）
        total: 总步骤数
    """
    print(f"[progress] {step} ({current}/{total})")


def echo_list(items: list[dict[str, Any]], message: str = "", total: int | None = None) -> None:
    """输出列表类结果。

    Args:
        items: 数据列表
        message: 可选的人类可读描述
        total: 总数，默认取 items 长度
    """
    count = total if total is not None else len(items)
    header = f"[success] {message} (total: {count})" if message else f"[success] (total: {count})"
    lines = [header]
    for item in items:
        lines.append("---")
        lines.extend(_format_pairs(item))
    print("\n".join(lines))
