#!/usr/bin/env python3
"""
send.py — 企业微信消息发送脚本（通过 HTTP 推送服务）

用法:
  # 发送 Markdown 消息
  echo "消息内容" | python3 send.py --tag evolve
  python3 send.py --tag evolve --text "短消息"

  # 发送卡片消息
  python3 send.py --type card --title "告警" --desc "服务异常" --source "监控系统"

  # 健康检查
  python3 send.py --health

退出码:
  0  发送成功
  1  发送失败
"""

import argparse
import json
import subprocess
import sys


# ── 配置 ──────────────────────────────────────────────
API_BASE_URL = "https://workspaceatz10fmdcqvoiznt6k-8765.gz.cloudide.woa.com"
API_TOKEN = "changeme-token-123"
REQUEST_TIMEOUT = 10


def _curl_get(url: str) -> dict:
    """通过 curl 发送 GET 请求，返回响应 dict。"""
    cmd = [
        "curl", "-s", "-k",
        "--max-time", str(REQUEST_TIMEOUT),
        "-w", "\n%{http_code}",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT + 5)
    if proc.returncode != 0:
        raise RuntimeError(f"curl 失败 (exit {proc.returncode}): {proc.stderr.strip()}")

    lines = proc.stdout.rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    status_code = int(lines[-1]) if lines[-1].strip().isdigit() else 0

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"HTTP {status_code}: {body.strip()}")

    return json.loads(body) if body.strip() else {"status": "ok"}


def _curl_post(endpoint: str, payload: dict) -> dict:
    """通过 curl 发送 POST 请求到推送服务，返回响应 dict。"""
    url = f"{API_BASE_URL}{endpoint}"
    data = json.dumps(payload, ensure_ascii=False)

    cmd = [
        "curl", "-s", "-k",
        "--max-time", str(REQUEST_TIMEOUT),
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", f"X-API-Token: {API_TOKEN}",
        "-w", "\n%{http_code}",
        "-d", data,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT + 5)
    if proc.returncode != 0:
        raise RuntimeError(f"curl 失败 (exit {proc.returncode}): {proc.stderr.strip()}")

    lines = proc.stdout.rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    status_code = int(lines[-1]) if lines[-1].strip().isdigit() else 0

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"HTTP {status_code}: {body.strip()}")

    return json.loads(body) if body.strip() else {"status": "ok"}


def health_check() -> dict:
    """检查推送服务健康状态。"""
    return _curl_get(f"{API_BASE_URL}/health")


def send_markdown(content: str) -> dict:
    """发送 Markdown 格式消息。"""
    return _curl_post("/send/markdown", {"content": content})


def send_card(title: str, description: str, source_desc: str = "") -> dict:
    """发送卡片格式消息。"""
    payload = {"title": title, "description": description}
    if source_desc:
        payload["source_desc"] = source_desc
    return _curl_post("/send/card", payload)


def main():
    parser = argparse.ArgumentParser(description="发送企微群消息（HTTP 推送服务）")
    parser.add_argument("--tag", default="msg", help="消息标签 (默认: msg，仅用于日志标识)")
    parser.add_argument(
        "--type",
        choices=["markdown", "card"],
        default="markdown",
        help="消息类型: markdown (默认) 或 card",
    )

    # Markdown 消息参数
    md_group = parser.add_mutually_exclusive_group()
    md_group.add_argument("--text", help="直接传入 Markdown 消息文本")
    md_group.add_argument(
        "--stdin",
        action="store_true",
        default=True,
        help="从 stdin 读取消息 (默认)",
    )

    # Card 消息参数
    parser.add_argument("--title", help="卡片标题 (--type card 时必需)")
    parser.add_argument("--desc", help="卡片描述 (--type card 时必需)")
    parser.add_argument("--source", default="", help="卡片来源描述 (可选)")

    # 健康检查
    parser.add_argument(
        "--health", action="store_true", help="仅执行健康检查，不发送消息"
    )

    args = parser.parse_args()

    # 健康检查模式
    if args.health:
        try:
            result = health_check()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        if args.type == "card":
            # 卡片消息
            if not args.title or not args.desc:
                print(
                    "ERROR: 卡片消息需要 --title 和 --desc 参数。",
                    file=sys.stderr,
                )
                sys.exit(1)
            result = send_card(args.title, args.desc, args.source)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # Markdown 消息
            if args.text:
                text = args.text
            else:
                if sys.stdin.isatty():
                    print(
                        "ERROR: 未提供消息内容。用 --text 或通过管道传入。",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                text = sys.stdin.read().strip()

            if not text:
                print("ERROR: 消息内容为空。", file=sys.stderr)
                sys.exit(1)

            result = send_markdown(text)
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
