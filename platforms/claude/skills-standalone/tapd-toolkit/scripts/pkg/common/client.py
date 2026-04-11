"""TAPD API 客户端工厂，根据配置构建带鉴权和链路追踪的 SDK 客户端。"""

from tapdsdk.sdk import TapdAPIClient

from .config import TapdSkillConfig
from .utils import generate_nginx_request_id

TAPD_REQUEST_ID_NAME = "X-Tapd-Request-Id"

ENV_ADDR_MAP: dict[str, str] = {
    "IDC": "http://oss.apiv2.tapd.woa.com",
    "OA": "http://apiv2.tapd.woa.com",
}

DEFAULT_TIMEOUT = 30


def build_tapd_client(
    cfg: TapdSkillConfig,
    timeout: int = DEFAULT_TIMEOUT,
) -> TapdAPIClient | None:
    """根据配置创建 TAPD API 客户端。

    自动设置 Access Token 鉴权、MCP 链路追踪请求头和超时。
    当 token 为空或 env 不合法时返回 None。

    Args:
        cfg: 包含 tapd_access_token 和 env 的配置对象
        timeout: 请求超时秒数，默认 30s
    """
    if not cfg.tapd_access_token:
        return None

    address = ENV_ADDR_MAP.get(cfg.env)
    if address is None:
        return None

    client = TapdAPIClient(address=address)
    client.set_headers({"Via": "skills", TAPD_REQUEST_ID_NAME: generate_nginx_request_id()})
    client.set_auth_access_token(cfg.tapd_access_token)

    if hasattr(client, "set_timeout"):
        client.set_timeout(timeout)

    return client
