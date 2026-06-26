# scripts/hooks/ — Git pre-commit hook（已端到端实测）

> **受众边界**：本目录仅引擎维护者使用，不部署到业务项目。

## 安装

```bash
bash scripts/hooks/install.sh
```

`install.sh` 在 `.git/hooks/pre-commit` 创建一个**软链接**指向 `scripts/hooks/pre-commit`，因此后续修改 hook 只需直接编辑源文件即可生效。

如果 `.git/hooks/pre-commit` 已存在且不是软链接，会备份为 `pre-commit.bak`。

## 卸载

```bash
rm .git/hooks/pre-commit
# 如有 .bak 备份，恢复：
# mv .git/hooks/pre-commit.bak .git/hooks/pre-commit
```

## 工作模式

每次 `git commit` 触发以下两个步骤：

1. **影响范围分析**（始终仅提示，不阻断）— 调用 `scripts/impact_analyzer.py --git-staged` 列出本次改动需要同步的 ARCHITECTURE 章节 / 双平台镜像目标
2. **一致性体检** — 调用 `scripts/consistency_check.py`，按以下规则处理退出码：

| consistency_check 退出码 | 含义 | 默认 (warn) 模式 | 严格 (`AI_TEAM_HOOK_STRICT=1`) 模式 |
|--------------------------|------|------------------|------------------------------------|
| `0` PASS | 全部维度通过 | ✅ 不阻断 | ✅ 不阻断 |
| `1` WARN | 仅有警告 | ⚠️ 不阻断（提示） | ⚠️ 不阻断（提示） |
| `2` FAIL | 至少一项硬性漂移 | ⚠️ **不阻断**（提示） | ✗ **阻断 commit** |
| `3` ERROR | 体检脚本自身崩溃 | ✗ **阻断 commit** | ✗ **阻断 commit** |

### 为什么默认是 warn 模式

仓库当前存在 **54 项已知双平台漂移**（多数为方言差异，将由 Phase 3-new 处理）。如果默认严格模式，任何 commit 都会被阻断（包括与漂移完全无关的改动），违反维护者日常体验。Warn 模式让维护者看到漂移信息但不阻塞工作；CI / 关键 commit 可显式开启严格模式。

### 跳过 hook

```bash
git commit --no-verify -m "..."
```

`--no-verify` 完全跳过所有 hook（不仅是 ai-team 的）。**仅在确实需要绕过时使用**。

## 端到端实测日志（2026-05-29）

### 实测 1：默认 warn 模式 — commit 应通过

```bash
$ echo "marker" > .test-hook.txt
$ git add .test-hook.txt
$ git commit -m "test warn"
[pre-commit] 使用 python3.8 执行 ai-team 静态校验
▼▼▼ 影响范围分析（仅提示）▼▼▼
... [影响分析输出]
▼▼▼ 一致性体检 ▼▼▼
... [11 维度体检输出，含 FAIL]
[pre-commit] ⚠ 体检 FAIL（warn 模式不阻断 commit）
             启用严格模式：AI_TEAM_HOOK_STRICT=1 git commit
[master abc1234] test warn
 1 file changed, 1 insertion(+)
$ echo "git exit=$?"
git exit=0
```

**结果**：HEAD 前进 ✅，体检 FAIL 输出 ✅，commit 未被阻断 ✅

### 实测 2：严格模式 — commit 应被阻断

```bash
$ echo "marker2" > .test-hook.txt
$ git add .test-hook.txt
$ AI_TEAM_HOOK_STRICT=1 git commit -m "test strict"
[pre-commit] 使用 python3.8 执行 ai-team 静态校验
... [体检输出，含 FAIL]
[pre-commit] ✗ 严格模式：体检 FAIL，阻断 commit
             如需强制提交：git commit --no-verify
$ echo "git exit=$?"
git exit=1
$ git rev-parse HEAD  # 与之前相同，HEAD 未前进
3d490b02ddbf33d154f721f4c8c8e21b88180a78
```

**结果**：git exit = 1 ✅，HEAD 未前进 ✅，commit 真的被阻止 ✅

### 实测 3：`--no-verify` 跳过

```bash
$ git commit --no-verify -m "test bypass"
[master def5678] test bypass
$ echo "git exit=$?"
git exit=0
```

**结果**：hook 不运行 ✅，commit 通过 ✅

## 已知边界 / 注意事项

1. **软链接 broken 时 git 静默跳过 hook**。如果你看到 `git commit` 没有 hook 输出但又通过了，跑 `file .git/hooks/pre-commit` 检查链接是否正常（`broken symbolic link` 表示需要重新 install）。这通常发生在 `git stash push -u` 把 `scripts/` 当 untracked 收走后。
2. **hook 不会捕获非 stage 改动的影响**。`impact_analyzer --git-staged` 只看 `git diff --cached`，未 stage 的改动不会被分析。
3. **Python 版本要求**：hook 自动寻找 python3.8+ 解释器，找不到时静默跳过（只打印一行警告，不阻断）。
4. **`set -u` 严格模式**：hook 启用了 `set -u`（未定义变量报错），但**没有** `set -e`（任一命令失败即退出）—— 因为我们要根据 `consistency_check` 的退出码区分 PASS/WARN/FAIL/ERROR，不能让 set -e 把 FAIL 直接吞成 hook 失败。

## CI 集成（候选，未启用）

未来如启用 CI（GitHub Actions / 工蜂 CI），推荐：

```yaml
- name: ai-team consistency check (strict)
  env:
    AI_TEAM_HOOK_STRICT: "1"
  run: bash scripts/hooks/pre-commit
```

具体见 ARCHITECTURE 附录 C "Phase 4 候选项清单"。
