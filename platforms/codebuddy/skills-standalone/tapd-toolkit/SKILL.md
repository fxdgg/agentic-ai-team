---
name: tapd-toolkit
description: TAPD 扩展技能集，补充 MCP 原生工具不支持的本地操作。上传图片到 TAPD 获取可嵌入描述的 img 标签，上传附件到 TAPD 需求/缺陷/任务，查询和下载附件。当用户需要在 TAPD 中上传图片、上传附件、查询附件或下载附件时使用。
---

# TAPD Toolkit

本技能提供 TAPD 平台的扩展操作能力，补充 MCP 原生工具不支持的场景（如需要本地文件系统操作）。

## 前置条件

- Python 3.10+
- 依赖（见项目根目录 `requirement.txt`）：
  - `tapd-python-sdk==1.65.0`
  - `pydantic-settings>=2.0.0`
- 认证配置：凭证文件 `~/.tapd/credentials`（首次使用执行 `make init-credentials` 创建），格式如下：
  ```
  access_token=<你的TAPD访问令牌>
  env=OA
  ```

若 `~/.tapd/credentials` 凭证文件不存在或未包含 `access_token`，脚本会抛出 `ValueError` 并提示执行 `make init-credentials`。

## 功能列表

| 功能 | 适用场景 | 参考文档 |
|------|----------|----------|
| 图片上传 | 上传本地图片，获取 img 标签嵌入需求/缺陷/Wiki 描述 | `references/upload-image.md` |
| 附件上传 | 上传本地文件到需求/缺陷/任务 | `references/upload-attachment.md` |
| 附件查询与下载 | 查询附件列表、获取下载链接（通过 MCP 工具） | `references/upload-attachment.md` |

## 使用指引

根据用户意图选择对应功能，读取对应 reference 文档获取完整参数说明与示例。

### 图片上传

当用户需要在 TAPD 需求、缺陷、Wiki 等描述中插入图片时使用。读取 `references/upload-image.md` 获取详细用法。

核心命令：

```bash
python scripts/upload-image.py --workspace_id <项目ID> --file <图片路径>
```

支持格式：`.png`、`.jpg`/`.jpeg`、`.gif`、`.bmp`，大小上限 5MB。

上传成功后拿到 `html_code`，再通过 MCP 工具（`stories_update` / `bugs_update` / `wikis_update`）将其嵌入目标描述。

### 附件上传

当用户需要将本地文件作为附件上传到 TAPD 需求/缺陷/任务时使用。读取 `references/upload-attachment.md` 获取详细用法。

核心命令：

```bash
python scripts/upload-attachment.py \
  --workspace_id <项目ID> --file <文件路径> \
  --type <story|bug|task> --entry_id <业务对象ID>
```

文件大小上限 250MB。

### 附件查询与下载

直接使用 TAPD MCP 工具，无需执行本地脚本。详见 `references/upload-attachment.md` 中的"附件查询与下载"章节。

- 查询附件：MCP 工具 `get_attachment_info`
- 下载附件：MCP 工具 `get_attachment_download_url`

## 通用注意事项

- 脚本路径相对于 skill 目录（即 `tapd-toolkit/`），各平台导入后的实际路径可能不同（如 `.cursor/skills/tapd-toolkit/`、`.codebuddy/skills/tapd-toolkit/` 等），请以平台实际路径为准
- 每次只允许上传一个文件，多个文件需分多次执行
- 上传失败时检查网络连接和 Access Token 有效性
