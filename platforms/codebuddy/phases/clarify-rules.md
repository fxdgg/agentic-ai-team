# 澄清阶段规则（按需加载）

> **加载时机**: 编排器进入 CLARIFY_PRODUCT / CLARIFY_TECH / CLARIFY_ARCH_BACKEND / CLARIFY_ARCH_FRONTEND 阶段时加载本文件。

---

## 1. 澄清文件格式（*-clarify.json）

```json
{
  "questions": [
    {
      "id": "Q001",
      "category": "功能边界",
      "priority": "blocking",
      "question": "用户注册是否需要支持邮箱注册？",
      "context": "当前设计仅包含手机号注册",
      "suggestedAnswer": "建议仅支持手机号注册。理由：当前系统验证码服务仅对接了短信通道，新增邮箱注册需额外对接邮件服务，建议一期聚焦手机号。",
      "status": "pending",
      "answer": null,
      "answeredAt": null
    }
  ]
}
```

> **关键规则**: 
> - 分析 Agent 生成 clarify 问题时，`status` **必须**为 `pending`，**禁止**设为 `answered`
> - 每个问题**必须**提供 `suggestedAnswer`（Agent 的推断答案），供用户在澄清阶段参考
> - 最终确认权**始终在用户**，Agent 不能代替用户做决策

## 2. 优先级定义

| 优先级 | 含义 | 跳过后果 |
|--------|------|----------|
| `blocking` | 阻塞性问题 | 记录为 **high** 风险 |
| `important` | 重要问题 | 记录为 **medium** 风险 |
| `recommended` | 建议性问题 | 记录为 **low** 风险 |

## 3. 澄清执行流程

```
0. 【平台变更检查】读取前序阶段产出物的 front-matter：
   - 若包含 `platformChangeRequest` 字段 →
     a) 向用户展示平台变更建议及原因、证据
     b) 用户确认 → 编排器更新 state.json 中 platforms 对应字段，
        并动态创建新启用平台对应的 architecture/{platform}/ 和
        implementation/{platform}/ 目录
     c) 用户拒绝 → 在 risks.json 中记录"用户拒绝平台变更建议"
   - 若不包含 → 跳过此步骤

1. 读取对应阶段的 *-clarify.json
2. 检查是否有 status: "pending" 的问题
   - 无 pending 问题 → 自动跳过澄清阶段（直接执行步骤 7）
   - 有 pending 问题 → 进入澄清流程
3. 按优先级分组展示所有 pending 问题（blocking → important → recommended）
   - 每个问题同时展示 `suggestedAnswer`（Agent 的建议答案）
   - 展示格式见 phases/output-formats/common.md §3（澄清展示格式）
4. 用户逐个处理每个问题，有三种操作：
   a) 采纳建议答案 → 将 suggestedAnswer 填入 answer 字段、status 改为 "answered"、记录 answeredAt
   b) 修改 → 用户提供自定义答案、填入 answer 字段、status 改为 "answered"、记录 answeredAt
   c) 跳过 → status 改为 "skipped"、自动写入 risks.json
5. 【快速采纳】当问题较多时，编排器可提供"全部采纳"选项：
   - 用户选择"全部采纳" → 所有 pending 问题的 suggestedAnswer 批量填入 answer、status 批量改为 "answered"
   - 此选项仅在所有 pending 问题都有 suggestedAnswer 时可用
6. 所有问题处理完毕后，执行澄清回填（见下方 §4）
7. 更新原始文档的 front-matter，设置 `clarified: true`
8. 更新 state.json，流转到下一阶段
```

## 4. 澄清回填规范

### 4.1 回填执行者

**编排器自行执行回填**。回填是机械性文本操作（查找段落 → 就地修改 → 追加标签），不涉及分析判断，属于编排器"轻量文本操作"的职责范围。

> **例外声明**: 这是行为约束中「禁止编排器自己执行具体工作」的**唯一例外**。回填操作不涉及分析、设计或编码。

### 4.2 回填策略：就地修改

**核心原则**: 在原始文档中**就地修改**对应内容，不创建新文件、不在文档末尾另起章节。这样做的目的是减少下游 Agent 读取时的疑惑，保证其上下文加载的纯粹性。

**回填步骤**:

```
对每个 status: "answered" 的澄清问题：

1. 根据 clarify 问题的 category + context 定位原始文档中的相关段落
2. 就地修改该段落内容，将澄清答案融入原始表述中
3. 在修改后的内容末尾追加 `[已澄清]` 标签，格式：
   - 行内标记: `... 内容 ... [已澄清: Q001]`
   - 段落标记: 在段落末尾另起一行 `> [已澄清: Q001] 基于用户回答更新`
4. 确保修改后的文档语义连贯、上下文通顺
```

**回填示例**:

```markdown
# 修改前
### 1.2 目标用户
| 角色 | 核心诉求 | 使用频率 |
|------|----------|----------|
| 消费者 | 快速注册 | 高频 |

# 修改后（Q003 回答了"需要支持商家角色"）
### 1.2 目标用户
| 角色 | 核心诉求 | 使用频率 |
|------|----------|----------|
| 消费者 | 快速注册 | 高频 |
| 商家管理员 | 店铺信息管理、商品上架 | 中频 |
> [已澄清: Q003] 基于用户回答更新
```

### 4.3 front-matter 版本标记

回填完成后，更新原始文档的 YAML front-matter，增加 `clarified` 标记：

```yaml
---
qualityGate: pass
qualityScore: 3.8
qualityTimestamp: 2026-03-16T14:30:00Z
clarified: true                           # 新增：标记已完成澄清回填
clarifiedAt: 2026-03-16T15:30:00Z         # 新增：回填完成时间
---
```

**规则**:
- 当澄清阶段被跳过时（无 pending 问题），编排器仍需设置 `clarified: true`——原始文档即为"已澄清版本"
- 下游 Agent 读取文档时，无需关心 `clarified` 字段的值——它始终是最新可用版本

### 4.4 回填对象映射

| 澄清阶段 | 回填目标文档 |
|----------|-------------|
| `CLARIFY_PRODUCT` | `analysis/product-requirements.md` |
| `CLARIFY_TECH` | `analysis/tech-requirements.md`（总纲）+ `analysis/tech-requirements-backend.md` + `analysis/tech-requirements-web.md` + `analysis/tech-requirements-miniprogram.md`（按启用平台） |
| `CLARIFY_ARCH_BACKEND` | `architecture/backend/architecture.md` |
| `CLARIFY_ARCH_FRONTEND` | `architecture/web/architecture.md` + `architecture/miniprogram/architecture.md` |
