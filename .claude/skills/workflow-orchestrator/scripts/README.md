# Skill 路径处理脚本

## 概述

本目录包含用于处理 Agent 文档中 Skill 内部文件相对路径的 Python 脚本。这些脚本实现了方案 B 的核心功能，支持编排器在调用 Agent 时正确处理相对路径。

## 脚本清单

### 1. `path_resolver.py` - 相对路径解析器

**功能**：解析 Agent 文档中的 Skill 内部相对路径，转换为绝对路径。

**输入**：
- `--agent-file` (required): Agent 文档的绝对路径
- `--project-root` (required): 项目根目录的绝对路径
- `--output` (optional): 输出格式，可选 `json` 或 `text`（默认: json）

**输出**：JSON 格式的路径映射表

**使用示例**：
```bash
python path_resolver.py \
  --agent-file /path/to/.claude/skills/.../agents/common-developer.md \
  --project-root /path/to/project \
  --output json
```

**输出示例**：
```json
{
  "../../rules/java-backend/meta-rule.md": "/path/to/project/.claude/skills/.../rules/java-backend/meta-rule.md",
  "../../rules/java-backend/package-structure.md": "/path/to/project/.claude/skills/.../rules/java-backend/package-structure.md"
}
```

### 2. `path_validator.py` - 路径验证器

**功能**：验证相对路径是否符合规范，检查文件存在性和安全性。

**输入**：
- `--paths` (required): JSON 格式的路径映射（来自 path_resolver）
- `--project-root` (required): 项目根目录的绝对路径
- `--strict` (optional): 严格模式（任何警告都视为失败）

**输出**：JSON 格式的验证结果

**验证内容**：
- ✅ 文件是否存在
- ✅ 是否指向 Skill 外部（禁止）
- ✅ 相对路径格式是否有效
- ✅ 是否指向允许的内部目录（rules、templates）

**使用示例**：
```bash
python path_validator.py \
  --paths '{"../../rules/java-backend/meta-rule.md": "/path/to/..."}' \
  --project-root /path/to/project \
  --strict
```

**输出示例**：
```json
{
  "passed": true,
  "total": 2,
  "valid": 2,
  "invalid": 0,
  "errors": []
}
```

### 3. `context_injector.py` - 上下文注入器

**功能**：将转换后的路径信息生成为可注入 Agent 上下文的文本。

**输入**：
- `--paths` (required): JSON 格式的路径映射
- `--format` (optional): 输出格式，可选 `markdown`、`json` 或 `plain`（默认: markdown）

**输出**：格式化的上下文文本

**使用示例**：
```bash
python context_injector.py \
  --paths '{"../../rules/java-backend/meta-rule.md": "/path/to/..."}' \
  --format markdown
```

**输出示例**（Markdown 格式）：
```markdown
---
## 【Skill 内部文件映射】

你的规则文件和模板文件存放在以下位置：

- **../../rules/java-backend/meta-rule.md**
  → .../.claude/skills/.../rules/java-backend/meta-rule.md

- **../../rules/java-backend/package-structure.md**
  → .../.claude/skills/.../rules/java-backend/package-structure.md

---
```

### 4. `resolve_agent_paths.py` - 主脚本（一站式调用）

**功能**：协调调用上述三个脚本，一站式处理 Agent 文档的路径解析、验证和上下文注入。

**输入**：
- `--agent-file` (required): Agent 文档的绝对路径
- `--project-root` (required): 项目根目录的绝对路径
- `--format` (optional): 上下文输出格式（默认: markdown）
- `--strict` (optional): 严格模式
- `--output` (optional): 最终输出内容，可选 `json` 或 `context`（默认: json）

**输出**：完整的解析结果（包含已解析路径、验证结果、生成的上下文）

**使用示例**：
```bash
# 完整流程（推荐）
python resolve_agent_paths.py \
  --agent-file /path/to/agents/common-developer.md \
  --project-root /path/to/project \
  --format markdown \
  --output json

# 只输出上下文文本
python resolve_agent_paths.py \
  --agent-file /path/to/agents/common-developer.md \
  --project-root /path/to/project \
  --output context
```

**输出示例**：
```json
{
  "success": true,
  "resolved_paths": {
    "../../rules/java-backend/meta-rule.md": "/path/to/...",
    "../../rules/java-backend/package-structure.md": "/path/to/..."
  },
  "validation": {
    "passed": true,
    "total": 2,
    "valid": 2,
    "invalid": 0,
    "errors": []
  },
  "context": "---\n## 【Skill 内部文件映射】\n...",
  "errors": []
}
```

## 工作流程

```
用户/编排器
    ↓
resolve_agent_paths.py
    ├─ 调用 path_resolver.py → 获取路径映射
    ├─ 调用 path_validator.py → 验证路径有效性
    ├─ 调用 context_injector.py → 生成上下文
    └─ 返回完整结果
    ↓
编排器将 context 注入 Task prompt
    ↓
Agent 接收完整的路径信息并执行
```

## 编排器集成指南

编排器在调用 Agent 工具执行 Agent 时，应该：

### Step 1: 解析 Agent 路径
```python
result = subprocess.run([
    'python3',
    'resolve_agent_paths.py',
    '--agent-file', agent_file_path,
    '--project-root', project_root,
    '--format', 'markdown',
    '--output', 'json'
], capture_output=True, text=True)

if result.returncode != 0:
    raise Exception("路径解析失败")

resolve_result = json.loads(result.stdout)
```

### Step 2: 检查是否成功
```python
if not resolve_result['success']:
    print(f"错误: {resolve_result['errors']}")
    raise Exception("无法继续执行 Agent")
```

### Step 3: 提取上下文并注入
```python
context = resolve_result['context']
agent_prompt = f"""
{agent_content}

{context}
"""
```

### Step 4: 调用 Agent 工具
```python
task_result = task_tool(
    subagent_type='general-purpose',
    description='执行 Agent',
    prompt=agent_prompt
)
```

## 错误处理

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|--------|
| `文件不存在` | 规则文件被移动或删除 | 检查 `.claude/skills/.../rules/` 目录 |
| `路径指向 Skill 外部` | 相对路径计算错误 | 检查 `../` 的数量是否匹配目录深度 |
| `相对路径必须以 ../ 开头` | 使用了不支持的路径格式 | 仅支持 `../rules/` 和 `../templates/` |
| `JSON 解析失败` | 传入的 JSON 格式不正确 | 确保路径映射是有效的 JSON |

### 调试建议

1. **单独运行各脚本进行测试**
   ```bash
   # 测试路径解析
   python path_resolver.py --agent-file ... --project-root ...

   # 测试路径验证
   python path_validator.py --paths '...' --project-root ...

   # 测试上下文注入
   python context_injector.py --paths '...' --format markdown
   ```

2. **查看详细日志**
   ```bash
   # 启用 Python 调试模式
   PYTHONVERBOSE=2 python resolve_agent_paths.py ...
   ```

3. **验证输入路径**
   ```bash
   # 确认 Agent 文件存在
   ls -la <agent-file>

   # 确认项目根目录正确
   ls -la <project-root>/.claude/
   ```

## 性能和限制

- **性能**：每个脚本的执行时间 < 100ms（在本地磁盘）
- **支持的路径数量**：单个 Agent 最多支持 100+ 个路径引用（实际上不会这么多）
- **路径长度限制**：相对路径和绝对路径长度均无特殊限制
- **并发安全**：脚本是无状态的，支持并发调用

## 开发指南

### 扩展脚本

如果需要添加新的功能（如不同的输出格式、新的验证规则等），可以：

1. 修改相应的脚本模块
2. 在 `resolve_agent_paths.py` 中添加新的调用
3. 更新本 README 文档

### 测试

创建单元测试：
```bash
python -m pytest scripts/ -v
```

## 许可

这些脚本是 workflow-orchestrator Skill 的一部分。

---

**最后更新**：2026-03-24
**版本**：1.1.0
