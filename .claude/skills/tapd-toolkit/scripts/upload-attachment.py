#!/usr/bin/env python3
"""上传附件到 TAPD 需求/缺陷/任务。

用法：
    python upload-attachment.py --workspace_id <项目ID> --file <文件路径> \\
        --type <story|bug|task> --entry_id <对象ID>

支持任意文件类型，大小限制 250MB。文件以 multipart/form-data 方式上传。
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, SCRIPT_DIR)

from pkg.common.client import build_tapd_client
from pkg.common.config import TapdSkillConfig
from pkg.common.echo import echo_error, echo_success
from pkg.common.retry import with_retry
from pkg.common.validate import validate_file

VALID_TYPES = {"story", "bug", "task"}
MAX_FILE_SIZE = 250 * 1024 * 1024  # 250MB


def upload_attachment(
    workspace_id: str,
    filepath: str,
    entry_type: str,
    entry_id: str,
    owner: str | None = None,
    overwrite: int | None = None,
    custom_field: str | None = None,
) -> None:
    """上传附件到指定的 TAPD 需求/缺陷/任务。

    每次重试都会重新打开文件句柄，确保流式上传不会因 seek 位置而失败。

    Args:
        workspace_id: TAPD 项目 ID
        filepath: 本地文件路径
        entry_type: 业务对象类型（story/bug/task）
        entry_id: 需求/缺陷/任务 ID
        owner: 附件创建人（可选）
        overwrite: 是否同名覆盖，0 不覆盖 / 1 覆盖（可选）
        custom_field: 轻量项目自定义字段英文名（可选）
    """
    if entry_type not in VALID_TYPES:
        echo_error(
            f"不支持的业务类型: {entry_type}",
            code="INVALID_TYPE",
            details={"allowed": sorted(VALID_TYPES)},
        )
        return

    if not validate_file(filepath, max_size=MAX_FILE_SIZE):
        return

    cfg = TapdSkillConfig()
    client = build_tapd_client(cfg)
    if client is None:
        echo_error(
            "无法创建 TAPD 客户端，请检查 TAPD_ACCESS_TOKEN 和 ENV 配置",
            code="CLIENT_INIT_FAILED",
        )
        return

    def _do_upload() -> dict:
        """每次重试都重新打开文件，避免文件指针问题。"""
        params: dict = {
            "workspace_id": workspace_id,
            "type": entry_type,
            "entry_id": entry_id,
        }
        if owner:
            params["owner"] = owner
        if overwrite is not None:
            params["overwrite"] = str(overwrite)
        if custom_field:
            params["custom_field"] = custom_field

        with open(filepath, "rb") as f:
            params["file"] = f
            return client.upload_attachment(params)

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

    attachment = result.get("data", {}).get("Attachment", {})
    echo_success(
        data={
            "id": attachment.get("id", ""),
            "type": attachment.get("type", ""),
            "entry_id": attachment.get("entry_id", ""),
            "filename": attachment.get("filename", ""),
            "content_type": attachment.get("content_type", ""),
            "created": attachment.get("created", ""),
            "workspace_id": attachment.get("workspace_id", ""),
            "owner": attachment.get("owner", ""),
        },
        message="附件上传成功",
    )


def main():
    parser = argparse.ArgumentParser(description="上传附件到 TAPD")
    parser.add_argument("--workspace_id", required=True, help="TAPD 项目 ID")
    parser.add_argument("--file", required=True, help="附件文件路径")
    parser.add_argument(
        "--type",
        required=True,
        choices=sorted(VALID_TYPES),
        help="业务对象类型: story/bug/task",
    )
    parser.add_argument("--entry_id", required=True, help="需求/缺陷/任务 ID")
    parser.add_argument("--owner", help="附件创建人")
    parser.add_argument(
        "--overwrite",
        type=int,
        choices=[0, 1],
        help="是否同名覆盖: 0 不覆盖, 1 覆盖",
    )
    parser.add_argument("--custom_field", help="字段英文名（仅用于轻量项目，为必填）")
    args = parser.parse_args()

    upload_attachment(
        workspace_id=args.workspace_id,
        filepath=args.file,
        entry_type=args.type,
        entry_id=args.entry_id,
        owner=args.owner,
        overwrite=args.overwrite,
        custom_field=args.custom_field,
    )


if __name__ == "__main__":
    main()
