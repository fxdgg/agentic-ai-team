# 图片上传

将本地图片上传到 TAPD，获取图片 HTML img 标签后嵌入到需求/缺陷/Wiki 的描述中。

## 执行命令

在本 skill 所在目录下执行：

```bash
python scripts/upload-image.py \
  --workspace_id <项目ID> \
  --file <图片文件路径>
```

> 脚本路径相对于 skill 目录（即 `tapd-toolkit/`），各平台导入后的实际路径可能不同（如 `.cursor/skills/tapd-toolkit/`、`.codebuddy/skills/tapd-toolkit/` 等），请以平台实际路径为准。

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--workspace_id` | 是 | TAPD 项目 ID |
| `--file` | 是 | 本地图片文件路径 |

支持的图片格式：`.png`、`.jpg`/`.jpeg`、`.gif`、`.bmp`，大小上限 5MB。

如果图片是通过 GenerateImage 工具生成的，使用生成后返回的文件路径。

## 返回结果

### 成功返回

```
[success] 图片上传成功
image_src: /tfl/pictures/202008/api_755_15982838491369683433.png
html_code: <img src="/tfl/pictures/202008/api_755_15982838491369683433.png"/>
filename: uploaded_image.png
```

成功时进程退出码为 `0`。使用 `html_code` 值嵌入到 TAPD 描述中。

### 失败返回

```
[error] 错误描述 (错误码)
补充信息key: value
```

失败时进程退出码为 `1`。可能的错误码：

| 错误码 | 含义 |
|--------|------|
| `FILE_NOT_FOUND` | 文件不存在 |
| `INVALID_FORMAT` | 不支持的图片格式 |
| `FILE_TOO_LARGE` | 文件超过 5MB 大小限制 |
| `CLIENT_INIT_FAILED` | TAPD 客户端初始化失败（检查 `TAPD_ACCESS_TOKEN` 和 `ENV`） |
| `UPLOAD_FAILED` | TAPD API 上传接口返回失败 |

## 将图片嵌入 TAPD 描述

拿到 `html_code` 后，使用 TAPD MCP 工具将图片插入到目标对象的描述中。

**插入到需求描述：**

使用 `proxy_execute_tool` 调用 `stories_update`，在 `description` 字段中直接使用返回的 `html_code`。

**插入到缺陷描述：**

使用 `proxy_execute_tool` 调用 `bugs_update`，方式同上。

**插入到 Wiki：**

使用 `proxy_execute_tool` 调用 `wikis_update`，方式同上。

## 完整工作流示例

用户说："帮我把这张截图上传到 TAPD 需求 #12345 的描述里"

1. 确认图片路径和项目 ID（workspace_id）
2. 执行上传脚本，解析返回的 `html_code`
3. 使用 `lookup_tool_param_schema` 获取 `stories_update` 的参数结构
4. 先通过 `proxy_execute_tool` 调用 `stories_view` 获取需求当前 description
5. 将 `html_code` 追加到原有 description 末尾
6. 使用 `proxy_execute_tool` 调用 `stories_update` 更新 description

## 注意事项

- 每次只允许上传一张图片，多张图片需分多次上传
- 脚本会自动校验：文件是否存在、格式是否支持、大小是否超过 5MB
- 上传失败时检查网络连接和 Access Token 有效性
- 上传后的图片仅限在 TAPD 平台上使用，不允许外链引用
- 更新描述时，必须先获取原有描述内容，将图片追加到末尾，避免覆盖已有内容
