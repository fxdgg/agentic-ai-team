"""简单的重试工具，支持指数退避，用于网络请求等可恢复操作。"""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def with_retry(
    func: Callable[..., T],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retryable: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """带指数退避的重试执行器。

    Args:
        func: 要执行的可调用对象（无参数，用 lambda 包装）
        max_attempts: 最大尝试次数
        base_delay: 首次重试延迟（秒）
        max_delay: 最大延迟上限（秒）
        retryable: 可重试的异常类型元组

    Returns:
        func 的返回值

    Raises:
        最后一次尝试抛出的异常
    """
    last_exc: BaseException | None = None
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except retryable as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]
