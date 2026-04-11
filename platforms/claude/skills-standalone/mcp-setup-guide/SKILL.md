---
name: mcp-setup-guide
description: MCP 服务配置引导。当用户需要配置 MCP 服务（如 TAPD、iWiki、Figma）、MCP 未连接需要引导配置、或工作流检测到 MCP 配置缺失时触发此技能。引导用户完成 MCP 配置文件创建、个人 Token 申请、Token 回填和连通性验证的完整流程。
---

# MCP 服务配置引导

本技能引导用户完成 Claude Code MCP 服务的配置，包括全局配置文件生成、Token 申请和连通性验证。

## 适用场景

- 工作流（如 `/flow-import`）检测到 MCP 配置缺失，需要引导用户完成配置
- 用户主动要求配置 MCP 服务
- MCP 工具调用失败，怀疑配置问题

## 配置流程

### Step 1：检测当前 MCP 配置状态

读取全局 MCP 配置文件，判断当前状态：

```
检查项:
  1. Claude MCP 设置中是否已配置目标服务（tapd_mcp_http / iWiki / FramelinkFigmaMCP）
  2. 对应服务的 headers 或 args 中是否包含有效 Token（非占位符）
```

根据检测结果，跳转到对应步骤：
- 文件不存在 → Step 2（创建配置文件）
- 文件存在但缺少目标服务 → Step 2（补充服务配置）
- 文件存在、服务存在但 Token 是占位符 → Step 3（引导申请和回填 Token）
- 文件存在、服务和 Token 都正常 → Step 4（验证连通性）

### Step 2：生成全局 MCP 配置文件

在 Claude MCP 设置中添加或更新以下服务配置，使用占位符替代真实 Token：

```json
{
    "mcpServers": {
        "iWiki": {
            "url": "https://prod.mcp.it.woa.com/app_iwiki_mcp/mcp3",
            "headers": {
                "Authorization": "Bearer YOUR_TAI_PAT_TOKEN"
            }
        },
        "tapd_mcp_http": {
            "url": "https://mcpgw.knot.woa.com/tapd/",
            "timeout": 20000,
            "headers": {
                "X-Tapd-Access-Token": "YOUR_TAPD_ACCESS_TOKEN"
            },
            "transportType": "streamable-http"
        },
        "FramelinkFigmaMCP": {
            "command": "npx",
            "args": [
                "-y",
                "figma-developer-mcp",
                "--figma-api-key=YOUR_FIGMA_PERSONAL_ACCESS_TOKEN",
                "--stdio"
            ]
        }
    }
}
```

**重要说明**：
- 三个服务使用**不同的** Token，需要分别申请：
  - `iWiki` 使用 **TAI PAT Token**（格式 `tai_pat_xxx.xxx`）
  - `tapd_mcp_http` 使用 **TAPD 个人访问令牌**
  - `FramelinkFigmaMCP` 使用 **Figma Personal Access Token**（格式 `figd_xxxx`）
- `iWiki` 的认证头字段名为 `Authorization`，Token 格式为 `Bearer tai_pat_xxx.xxx`
- `tapd_mcp_http` 的认证头字段名为 `X-Tapd-Access-Token`，Token 格式为 `{TAPD个人令牌}`
- `FramelinkFigmaMCP` 是本地 stdio 类型 MCP，Token 通过 `--figma-api-key` 参数传递，无需 `Bearer` 前缀

如果全局配置文件已存在，使用 `replace_in_file` 工具将新服务追加到 `mcpServers` 中，保留已有的其他服务配置不受影响。

生成完成后告知用户：

```
✅ MCP 服务配置已添加到 Claude MCP 设置

目前 Token 使用的是占位符，接下来需要申请你的个人 Token 并回填。
```

### Step 3：引导用户申请个人 Token

三个 MCP 服务使用**不同来源**的 Token，需要分别引导用户申请。

#### 3a. iWiki Token（TAI PAT Token）

使用 `AskUserQuestion` 工具引导用户申请 iWiki 所需的 TAI PAT Token：

```
标题: 🔑 申请 iWiki 个人访问令牌 (TAI PAT Token)

问题: iWiki MCP 服务需要 TAI PAT Token 来认证。请按以下步骤操作：

1️⃣ 打开浏览器访问: https://tai.it.woa.com/user/pat
2️⃣ 登录后创建一个新的 Personal Access Token
3️⃣ 复制生成的 Token（格式如 tai_pat_xxx.xxx）
4️⃣ 将 Token 粘贴到下方

选项:
  - "我已获取 iWiki Token，准备粘贴"
  - "帮我打开 TAI PAT Token 申请页面"
  - "我已有 iWiki Token，直接配置"
  - "跳过 iWiki 配置，稍后再做"
```

如果用户选择"帮我打开 TAI PAT Token 申请页面"，执行：
```bash
open "https://tai.it.woa.com/user/pat"
```

当用户提供 iWiki Token 后（格式通常为 `tai_pat_xxx.xxx`），将全局配置文件中的 iWiki 占位符替换为真实 Token：

```
将 Claude MCP 设置中 iWiki 服务的 YOUR_TAI_PAT_TOKEN 替换为用户提供的实际 Token
  - iWiki 的 Authorization 值: "Bearer {token}"
```

#### 3b. TAPD Token（TAPD 个人访问令牌）

使用 `AskUserQuestion` 工具引导用户申请 TAPD 所需的个人访问令牌：

```
标题: 🔑 申请 TAPD 个人访问令牌

问题: TAPD MCP 服务需要 TAPD 个人访问令牌来认证。请按以下步骤操作：

1️⃣ 打开浏览器访问: https://tapd.woa.com/platform/myhome?not_direct=1&from=mcp#tab=tab-mytoken
2️⃣ 点击「创建个人访问令牌」
3️⃣ 复制生成的令牌（⚠️ 令牌只显示一次，请注意保存）
4️⃣ 将令牌粘贴到下方

选项:
  - "我已获取 TAPD Token，准备粘贴"
  - "帮我打开 TAPD 令牌申请页面"
  - "我已有 TAPD Token，直接配置"
  - "跳过 TAPD 配置，稍后再做"
```

如果用户选择"帮我打开 TAPD 令牌申请页面"，执行：
```bash
open "https://tapd.woa.com/platform/myhome?not_direct=1&from=mcp#tab=tab-mytoken"
```

当用户提供 TAPD Token 后，将全局配置文件中的 TAPD 占位符替换为真实 Token：

```
将 Claude MCP 设置中 TAPD 服务的 YOUR_TAPD_ACCESS_TOKEN 替换为用户提供的实际 Token
  - TAPD 的 X-Tapd-Access-Token 值: "Bearer {token}"
```

#### 3c. Figma Token（Figma Personal Access Token）

使用 `AskUserQuestion` 工具引导用户申请 Figma 所需的个人访问令牌：

```
标题: 🔑 申请 Figma Personal Access Token

问题: Figma MCP 服务需要 Figma Personal Access Token 来认证。请按以下步骤操作：

1️⃣ 打开浏览器访问 Figma 官网并登录你的账号
2️⃣ 点击左上角头像 → 进入「Settings」（个人设置）页面
3️⃣ 切换到「Security」标签页
4️⃣ 在「Personal access tokens」区域，点击「Generate new token」
5️⃣ 输入 Token 描述（如 "Claude Code MCP"），设置权限和过期时间后确认生成
6️⃣ 复制生成的 Token（格式如 figd_xxxx，⚠️ 只显示一次，请注意保存）
7️⃣ 将 Token 粘贴到下方

选项:
  - "我已获取 Figma Token，准备粘贴"
  - "帮我打开 Figma 个人设置页面"
  - "我已有 Figma Token，直接配置"
  - "跳过 Figma 配置，稍后再做"
```

如果用户选择"帮我打开 Figma 个人设置页面"，执行：
```bash
open "https://www.figma.com/settings"
```

当用户提供 Figma Token 后（格式通常为 `figd_xxxx`），将全局配置文件中的 Figma 占位符替换为真实 Token：

```
将 Claude MCP 设置中 FramelinkFigmaMCP 服务 args 中的 YOUR_FIGMA_PERSONAL_ACCESS_TOKEN 替换为用户提供的实际 Token
  - 替换 args 中 "--figma-api-key=YOUR_FIGMA_PERSONAL_ACCESS_TOKEN" 为 "--figma-api-key={token}"
  - 注意：Figma Token 不需要 Bearer 前缀，直接拼接在 --figma-api-key= 后面
```

#### Token 替换约束

```
🚨 CRITICAL 替换约束：
1. **必须逐个顺序替换**：对同一文件的多处修改，必须依次执行 replace_in_file（等前一个完成后再执行下一个），
   **严禁并行调用多个 replace_in_file 操作同一文件**，否则可能因竞态条件导致部分替换丢失
2. **替换后必须验证**：所有替换完成后，必须重新检查 Claude MCP 设置，
   检查配置中是否仍存在 "YOUR_TAI_PAT_TOKEN"、"YOUR_TAPD_ACCESS_TOKEN" 或 "YOUR_FIGMA_PERSONAL_ACCESS_TOKEN" 占位符。如仍存在，需再次替换直到全部消除
3. **三处都必须替换**：
   - iWiki 的 Authorization 值: "Bearer {iWiki TAI PAT Token}"
   - TAPD 的 X-Tapd-Access-Token 值: "Bearer {TAPD 个人访问令牌}"
   - FramelinkFigmaMCP 的 args 中: "--figma-api-key={Figma Personal Access Token}"
   - 三处使用不同的 Token，缺一不可
```

替换完成并验证无残留占位符后，提示用户：

```
✅ Token 已配置完成！
```

### Step 4：验证 MCP 连通性

使用 curl 命令通过 MCP 协议测试两个服务的连通性：

**TAPD 验证**（注意正确的请求方式）：
```bash
curl -s -X POST "https://mcpgw.knot.woa.com/tapd/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Tapd-Access-Token: Bearer {token}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  2>&1 | head -200
```

**iWiki 验证**（注意正确的请求方式）：
```bash
curl -s -X POST "https://prod.mcp.it.woa.com/app_iwiki_mcp/mcp3" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer {token}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  2>&1 | head -200
```

**关键要点**（避免常见错误）：
- 必须使用 `POST` 方法
- 必须设置 `Accept: application/json, text/event-stream` 头
- TAPD 认证头是 `X-Tapd-Access-Token`，不是 `Authorization`
- 两个服务都通过 `tools/list` 方法验证

根据验证结果反馈：

| 结果 | 处理方式 |
|------|---------|
| 返回工具列表 JSON | ✅ 配置成功，MCP 服务可用 |
| 返回 `missing_bearer_token` | ❌ Token 未生效或格式错误，检查是否带了 `Bearer ` 前缀 |
| 返回 `invalid_token` | ❌ Token 无效或已过期，引导用户重新申请 |
| 连接超时/网络错误 | ❌ 网络问题，确认是否在内网环境 |

### Step 5：配置完成确认

所有验证通过后，向用户展示最终结果：

```
🎉 MCP 服务配置完成！

✅ TAPD MCP — https://mcpgw.knot.woa.com/tapd/
   可用工具: lookup_tapd_tool, lookup_tool_param_schema, proxy_execute_tool
   底层支持 60+ 个 TAPD 操作

✅ iWiki MCP — https://prod.mcp.it.woa.com/app_iwiki_mcp/mcp3
   可用工具: metadata, aiSearch, getSpacePageTree 等

✅ Figma MCP (FramelinkFigmaMCP) — 本地 stdio 模式
   可用工具: get_figma_data, download_figma_images 等
   用于获取 Figma 设计稿数据和下载设计稿渲染图

请重新加载 MCP 配置后即可在对话中使用这些能力。
```

## 注意事项

1. MCP 配置通过 Claude MCP 设置维护
2. 修改全局配置时，必须**合并而非覆盖**，保留已有的其他服务配置不受影响
3. 三个 MCP 服务使用**不同的** Token，需要分别申请：
   - iWiki 使用 **TAI PAT Token**（在 https://tai.it.woa.com/user/pat 申请，格式 `tai_pat_xxx.xxx`）
   - TAPD 使用 **TAPD 个人访问令牌**（在 https://tapd.woa.com/platform/myhome?not_direct=1&from=mcp#tab=tab-mytoken 申请，令牌只显示一次需及时保存）
   - Figma 使用 **Figma Personal Access Token**（在 Figma 个人设置页 → Security 标签页 → Personal access tokens 区域生成，格式 `figd_xxxx`，只显示一次需及时保存）
4. iWiki 和 TAPD 的 Token 配置时需要加 `Bearer ` 前缀；Figma Token **不需要** `Bearer` 前缀，直接拼接在 `--figma-api-key=` 后面
5. 验证时必须使用 `POST` 方法 + `Accept: application/json, text/event-stream` 头（仅适用于 HTTP 类型的 iWiki 和 TAPD）
6. TAPD MCP 使用 `X-Tapd-Access-Token` 头，iWiki 使用 `Authorization` 头
7. FramelinkFigmaMCP 是本地 stdio 类型 MCP（通过 `npx figma-developer-mcp` 启动），不走 HTTP 协议，无需 curl 验证；重新加载 MCP 配置后 Claude Code 会自动启动并连接
8. 内网环境才能访问 iWiki 和 TAPD 服务；Figma MCP 需要外网访问 Figma API
