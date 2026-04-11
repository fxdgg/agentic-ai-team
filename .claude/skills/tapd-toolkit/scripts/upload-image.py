#!/usr/bin/env python3
"""上传图片到 TAPD，返回可嵌入需求/缺陷/Wiki 描述的 HTML img 标签。

用法：
    python upload-image.py --workspace_id <项目ID> --file <图片路径>

支持格式：.png, .jpg/.jpeg, .gif, .bmp，大小限制 5MB。
"""

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, SCRIPT_DIR)

from pkg.common.client import build_tapd_client
from pkg.common.config import TapdSkillConfig
from pkg.common.echo import echo_error, echo_success
from pkg.common.retry import with_retry
from pkg.common.validate import validate_file

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def upload_image(workspace_id: str, filepath: str) -> None:
    """上传图片到 TAPD 并输出包含 image_src 和 html_code 的 JSON 结果。

    Args:
        workspace_id: TAPD 项目 ID
        filepath: 本地图片文件路径
    """
    if not validate_file(filepath, max_size=MAX_FILE_SIZE, allowed_extensions=ALLOWED_EXTENSIONS):
        return

    cfg = TapdSkillConfig()
    client = build_tapd_client(cfg)
    if client is None:
        echo_error("无法创建 TAPD 客户端，请检查 TAPD_ACCESS_TOKEN 和 ENV 配置", code="CLIENT_INIT_FAILED")
        return

    def _do_upload() -> dict:
        """每次重试都重新打开文件，避免文件指针问题。"""
        with open(filepath, "rb") as f:
            return client.upload_image({"workspace_id": workspace_id, "image": f})

    try:
        result = with_retry(_do_upload, max_attempts=3, base_delay=1.0)
    except Exception as exc:
        echo_error(
            f"上传失败（已重试）: {exc}",
            code="UPLOAD_FAILED",
            details={"exception": str(exc)},
        )
        return

    if result.get("status") != 1:
        echo_error(
            f"上传失败: {result.get('info', '未知错误')}",
            code="UPLOAD_FAILED",
            details={"api_response": result},
        )
        return

    data = result.get("data", {})
    echo_success(
        data={
            "image_src": data.get("image_src", ""),
            "html_code": data.get("html_code", ""),
            "filename": os.path.basename(filepath),
        },
        message="图片上传成功",
    )


def main():
    parser = argparse.ArgumentParser(description="上传图片到 TAPD")
    parser.add_argument("--workspace_id", required=True, help="TAPD 项目 ID")
    parser.add_argument("--file", required=True, help="图片文件路径")
    args = parser.parse_args()

    upload_image(args.workspace_id, args.file)


if __name__ == "__main__":
    main()
