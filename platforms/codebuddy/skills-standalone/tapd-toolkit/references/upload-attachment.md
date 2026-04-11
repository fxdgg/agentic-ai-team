# 附件上传

将本地文件作为附件上传到 TAPD 的需求、缺陷或任务。

> **附件查询与下载** 不需要本脚本，请直接使用 TAPD MCP 工具（见下方"附件查询与下载"章节）。

## 执行命令

在本 skill 所在目录下执行：

```bash
python scripts/upload-attachment.py \
  --workspace_id <项目ID> \
  --file <文件路径> \
  --type <story|bug|task> \
  --entry_id <需求/缺陷/任务ID> \
  [--owner <创建人>] \
  [--overwrite <0|1>] \
  [--custom_field <字段英文名>]
```

> 脚本路径相对于 skill 目录（即 `tapd-toolkit/`），各平台导入后的实际路径可能不同（如 `.cursor/skills/tapd-toolkit/`、`.codebuddy/skills/tapd-toolkit/` 等），请以平台实际路径为准。

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--workspace_id` | 是 | TAPD 项目 ID |
| `--file` | 是 | 本地文件路径 |
| `--type` | 是 | 业务对象类型：`story`（需求）、`bug`（缺陷）、`task`（任务） |
| `--entry_id` | 是 | 需求/缺陷/任务的 ID |
| `--owner` | 否 | 附件创建人 |
| `--overwrite` | 否 | 是否同名覆盖：`0` 不覆盖，`1` 覆盖 |
| `--custom_field` | 否 | 字段英文名（仅用于轻量项目，且为必填） |

文件大小上限 250MB，每次只能上传一个文件。

## 返回结果

### 成功返回

```
[success] 附件上传成功
id: 1000000755503455439
type: task
entry_id: 1000000755859140551
filename: uu.jpg
content_type: image/jpeg
created: 2021-09-07 21:36:08
workspace_id: 755
```

成功时进程退出码为 `0`，空值字段自动省略。

### 失败返回

```
[error] 错误描述 (错误码)
补充信息key: value
```

失败时进程退出码为 `1`。可能的错误码：

| 错误码 | 含义 |
|--------|------|
| `FILE_NOT_FOUND` | 文件不存在 |
| `FILE_TOO_LARGE` | 文件超过 250MB 大小限制 |
| `INVALID_TYPE` | 不支持的业务类型（仅支持 story/bug/task） |
| `CLIENT_INIT_FAILED` | TAPD 客户端初始化失败（检查 `TAPD_ACCESS_TOKEN` 和 `ENV`） |
| `UPLOAD_FAILED` | TAPD API 上传接口返回失败 |

## 附件查询与下载（通过 TAPD MCP 工具）

附件的查询和下载已由 TAPD MCP 提供，无需使用本 skill 的脚本，直接调用 MCP 工具即可。

### 查询附件信息

使用 MCP 工具 `get_attachment_info` 获取指定业务对象下的附件列表。

**操作步骤：**

1. 调用 `lookup_tool_param_schema` 获取 `get_attachment_info` 的参数结构：

```
CallMcpTool: user-tapd_mcp_http / lookup_tool_param_schema
参数: { "tool_name": "get_attachment_info" }
```

2. 根据返回的参数 schema，调用 `proxy_execute_tool` 执行查询：

```
CallMcpTool: user-tapd_mcp_http / proxy_execute_tool
参数: { "tool_name": "get_attachment_info", "tool_args": { "workspace_id": "<项目ID>", ... } }
```

### 获取附件下载链接

使用 MCP 工具 `get_attachment_download_url` 获取附件的下载地址。

**操作步骤：**

1. 调用 `lookup_tool_param_schema` 获取 `get_attachment_download_url` 的参数结构：

```
CallMcpTool: user-tapd_mcp_http / lookup_tool_param_schema
参数: { "tool_name": "get_attachment_download_url" }
```

2. 根据返回的参数 schema，调用 `proxy_execute_tool` 执行：

```
CallMcpTool: user-tapd_mcp_http / proxy_execute_tool
参数: { "tool_name": "get_attachment_download_url", "tool_args": { "workspace_id": "<项目ID>", "attachment_id": "<附件ID>" } }
```

3. 拿到下载链接后，可使用 `curl` 或 `wget` 将文件下载到本地。

## 完整工作流示例

### 示例 1：上传附件到需求

用户说："帮我把设计稿 design.pdf 上传到项目 20088921 的需求 1120088921001025214 上"

1. 确认文件路径、项目 ID（workspace_id）、业务类型（story）和需求 ID（entry_id）
2. 执行上传命令：

```bash
python scripts/upload-attachment.py \
  --workspace_id 20088921 \
  --file /path/to/design.pdf \
  --type story \
  --entry_id 1120088921001025214
```

3. 解析返回结果，确认附件 `id` 和 `filename`，向用户反馈上传结果

### 示例 2：查询并下载缺陷附件

用户说："帮我下载项目 20088921 缺陷 1120088921001038888 的附件"

1. 调用 MCP 工具 `get_attachment_info` 查询该缺陷下的附件列表
2. 从返回结果中获取目标附件的 `attachment_id`
3. 调用 MCP 工具 `get_attachment_download_url` 获取下载链接
4. 使用 `curl -o <文件名> <下载链接>` 将附件下载到本地

## 注意事项

- 每次只允许上传一个文件，多个文件需分多次执行
- 附件大小上限 250MB，脚本会自动校验
- 上传仅支持 `story`（需求）、`bug`（缺陷）、`task`（任务）三种业务类型
- 轻量项目上传附件时，`--custom_field` 参数为必填
- 附件查询与下载直接通过 TAPD MCP 工具完成，不需要执行本地脚本
