#!/bin/bash
set -euo pipefail

PLATFORM=""
TARGET=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --platform) PLATFORM="$2"; shift 2 ;;
    --target)   TARGET="$2";   shift 2 ;;
    -h|--help)  echo "用法: $0 --platform {codebuddy|claude} [--target /path/to/project]"; exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [[ -z "$PLATFORM" ]]; then echo "❌ 请指定平台: --platform {codebuddy|claude}"; exit 1; fi
if [[ "$PLATFORM" != "codebuddy" && "$PLATFORM" != "claude" ]]; then echo "❌ 不支持的平台: $PLATFORM"; exit 1; fi

TARGET="${TARGET:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case $PLATFORM in
  codebuddy) DEPLOY_DIR="$TARGET/.codebuddy" ;;
  claude)    DEPLOY_DIR="$TARGET/.claude" ;;
esac

echo "📦 安装 AI Team 工作流（$PLATFORM 版）→ $DEPLOY_DIR"

mkdir -p "$DEPLOY_DIR/skills/workflow-orchestrator"

# Step 1: 共享核心
echo "1️⃣  复制共享核心..."
cp -r "$SCRIPT_DIR/shared/skills/workflow-orchestrator/agents"     "$DEPLOY_DIR/skills/workflow-orchestrator/"
cp -r "$SCRIPT_DIR/shared/skills/workflow-orchestrator/templates"   "$DEPLOY_DIR/skills/workflow-orchestrator/"
cp -r "$SCRIPT_DIR/shared/skills/workflow-orchestrator/references"  "$DEPLOY_DIR/skills/workflow-orchestrator/"
cp -r "$SCRIPT_DIR/shared/skills/workflow-orchestrator/scripts"     "$DEPLOY_DIR/skills/workflow-orchestrator/"
mkdir -p "$DEPLOY_DIR/skills/workflow-orchestrator/phases"
cp -r "$SCRIPT_DIR/shared/skills/workflow-orchestrator/phases/output-formats" "$DEPLOY_DIR/skills/workflow-orchestrator/phases/"
cp -r "$SCRIPT_DIR/shared/skills/workflow-orchestrator/rules"       "$DEPLOY_DIR/skills/workflow-orchestrator/"

for skill_dir in "$SCRIPT_DIR/shared/skills"/*/; do
  skill_name="$(basename "$skill_dir")"
  [[ "$skill_name" != "workflow-orchestrator" ]] && cp -r "$skill_dir" "$DEPLOY_DIR/skills/$skill_name"
done

# Step 2: 平台特定层
echo "2️⃣  叠加 $PLATFORM 平台适配层..."
PLATFORM_DIR="$SCRIPT_DIR/platforms/$PLATFORM"
cp "$PLATFORM_DIR/SKILL.md" "$DEPLOY_DIR/skills/workflow-orchestrator/"
mkdir -p "$DEPLOY_DIR/commands"
cp -r "$PLATFORM_DIR/commands/"* "$DEPLOY_DIR/commands/"
cp "$PLATFORM_DIR/phases/"*.md "$DEPLOY_DIR/skills/workflow-orchestrator/phases/" 2>/dev/null || true
if [[ -d "$PLATFORM_DIR/rules" ]] && ls "$PLATFORM_DIR/rules/"* >/dev/null 2>&1; then
  mkdir -p "$DEPLOY_DIR/rules"; cp -r "$PLATFORM_DIR/rules/"* "$DEPLOY_DIR/rules/"
fi
if [[ -d "$PLATFORM_DIR/skills-standalone" ]]; then
  for skill_dir in "$PLATFORM_DIR/skills-standalone"/*/; do
    [[ -d "$skill_dir" ]] && cp -r "$skill_dir" "$DEPLOY_DIR/skills/$(basename "$skill_dir")"
  done
fi

# Step 3: 平台额外文件
if [[ "$PLATFORM" == "claude" && -f "$PLATFORM_DIR/CLAUDE.md" ]]; then
  cp "$PLATFORM_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
  echo "   → CLAUDE.md 已写入项目根目录"
fi

# Step 4: 版本信息
COMMIT_HASH="$(cd "$SCRIPT_DIR" && git rev-parse HEAD 2>/dev/null || echo 'unknown')"
echo "{\"commit\":\"$COMMIT_HASH\",\"date\":\"$(date -Iseconds)\",\"platform\":\"$PLATFORM\"}" > "$DEPLOY_DIR/.ai-team-version"

FILE_COUNT=$(find "$DEPLOY_DIR" -type f | wc -l)
echo "✅ 安装完成！共 $FILE_COUNT 个文件 → $DEPLOY_DIR"
