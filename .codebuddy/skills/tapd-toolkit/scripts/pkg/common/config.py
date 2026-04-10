"""Skills 全局配置，从 ~/.tapd/credentials 凭证文件加载。

首次使用前需执行 `make init-credentials` 创建凭证文件。
"""

from typing import Literal

from pydantic import BaseModel, Field

from .utils import get_required_config


class TapdSkillConfig(BaseModel):
    """TAPD Skill 运行时配置，从 ~/.tapd/credentials 读取。"""

    tapd_access_token: str = Field(
        description="TAPD 访问令牌",
        default_factory=lambda: get_required_config("TAPD_ACCESS_TOKEN"),
    )
    env: Literal["OA", "IDC"] = Field(
        description="运行环境，OA（办公网/ODC）或 IDC",
        default_factory=lambda: get_required_config("ENV", "OA"),
    )
