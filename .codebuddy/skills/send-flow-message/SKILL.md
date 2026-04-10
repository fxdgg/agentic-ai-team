---
resource_id: send-flow-message
name: send-flow-message
description: "向企业微信群发送消息的技能。当用户说 '发送企微消息'、'通知企微'、'send message'、'发消息到群'、'企微通知'、'flow message' 或任何表达想要向企微群发送通知/消息的意图时，触发此技能。该技能通过 HTTP 推送服务投递消息，支持 Markdown 和卡片两种格式。"
---

# Send Flow Message

通过 HTTP 推送服务，向企业微信群发送消息。支持 **Markdown** 和 **卡片** 两种消息格式。

## 触发条件

匹配以下任一模式时激活：

- `发送企微消息` / `通知企微` / `企微通知`
- `send message` / `send flow message`
- `发消息到群` / `群消息` / `通知一下` / `发个通知`
- 任何明确表达想要向企微群发送消息/通知的意图

## 消息类型

### 1. Markdown 消息（默认）

适用于：通知、报告、日志等文本消息。内容支持 Markdown 格式。

### 2. 卡片消息

适用于：告警、状态变更等结构化消息。包含标题、描述和来源三个字段。

## 输入

- **Markdown 消息**：用户需提供消息内容（纯文本或 Markdown 格式）。
- **卡片消息**：用户需提供标题和描述，来源为可选项。

如果用户没有明确提供消息内容，请询问："请告诉我您要发送的消息内容。"

根据消息的结构特征自动选择类型：
- 如果内容是结构化的（有明确的标题 + 描述 + 来源），使用**卡片**格式。
- 其他情况，默认使用 **Markdown** 格式。

## 工作流程

### Step 1: 确认消息内容

从用户输入中提取要发送的消息文本或卡片字段。未提供时询问后再继续。

### Step 2: 调用 send.py 发送

**脚本路径**：`.codebuddy/skills/send-flow-message/send.py`

#### 发送 Markdown 消息（三种方式）：

```bash
# 方式 A：短消息 — 直接传文本
python3 .codebuddy/skills/send-flow-message/send.py --text "消息内容"

# 方式 B：长消息（推荐）— 通过管道传入
echo '消息内容' | python3 .codebuddy/skills/send-flow-message/send.py --tag <tag>

# 方式 C：带标签的短消息
python3 .codebuddy/skills/send-flow-message/send.py --tag evolve --text "消息内容"
```

#### 发送卡片消息：

```bash
python3 .codebuddy/skills/send-flow-message/send.py --type card \
  --title "标题" \
  --desc "描述内容" \
  --source "来源描述"
```

#### 健康检查：

```bash
python3 .codebuddy/skills/send-flow-message/send.py --health
```

**参数说明**：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--type` | 消息类型：`markdown` 或 `card` | `markdown` |
| `--tag` | 消息标签，用于日志标识（英文、无空格） | `msg` |
| `--text` | 直接传入 Markdown 消息文本（与 stdin 互斥） | — |
| `--title` | 卡片标题（`--type card` 时必需） | — |
| `--desc` | 卡片描述（`--type card` 时必需） | — |
| `--source` | 卡片来源描述 | 空 |
| `--health` | 仅执行健康检查，不发送消息 | — |

**长消息处理**：当消息超过 200 字符时，优先用管道方式避免命令行过长。

### Step 3: 报告结果

**成功时**（脚本退出码 0，stdout 输出 JSON）：

```
✅ 企微消息已发送！
📨 类型: <markdown|card>
```

**失败时**（脚本退出码 1，stderr 输出错误）：

```
❌ 消息发送失败！
🔍 错误信息: <stderr 内容>
💡 建议: <根据错误类型给出建议>
```

## 错误处理

- **连接失败 / URLError**: 推送服务可能未启动或网络不可达，建议先用 `--health` 检查服务状态。
- **HTTP 401 / 403**: API Token 认证失败，检查 send.py 中的 `API_TOKEN` 是否与服务端一致。
- **HTTP 400**: 请求参数错误，检查卡片消息是否缺少 `--title` 或 `--desc`。
- **HTTP 5xx**: 推送服务内部错误，稍后重试或检查服务端日志。
- **超时**: 请求超过 10 秒无响应，检查网络连接或服务负载。

## 安全规则

- **NEVER** 在对话输出中展示 API Token。
- **NEVER** 将 Token 写入项目业务代码文件中（仅存在于 send.py）。
- **ALWAYS** 在发送前向用户确认消息内容（除非上游明确要求自动发送）。
