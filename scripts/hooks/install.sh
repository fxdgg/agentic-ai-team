#!/usr/bin/env bash
# 安装 ai-team 引擎仓库的 pre-commit hook
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SRC="$REPO_ROOT/scripts/hooks/pre-commit"
DST="$HOOKS_DIR/pre-commit"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "✗ $HOOKS_DIR 不存在，确认仓库已 git init"
    exit 1
fi

if [ -e "$DST" ] && [ ! -L "$DST" ]; then
    echo "⚠ $DST 已存在且不是软链接，备份为 $DST.bak"
    mv "$DST" "$DST.bak"
fi

ln -sfn "$SRC" "$DST"
chmod +x "$SRC"
echo "✓ 已安装 pre-commit hook：$DST -> $SRC"
echo "  跳过 hook 提交：git commit --no-verify"
