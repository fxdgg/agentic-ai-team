# VISUAL_REVIEW 视觉验收阶段规则（按需加载）

> **加载时机**: 编排器进入 VISUAL_REVIEW 阶段时加载本文件，包括前置条件检查、Agent 调度、对比验收流程和回退策略。
> **前置阶段**: BUILD_VERIFY（编译验证通过后进入本阶段）
> **后继阶段**: E2E_VERIFY

---

## 0. 阶段概述

VISUAL_REVIEW（视觉验收）是 BUILD_VERIFY 之后、E2E_VERIFY 之前的**可选质量门禁**阶段。

**核心目标**: 验证前端代码实现与设计稿之间的视觉还原度，确保"页面长得像设计稿"。

### 0.1 阶段触发条件

| 条件 | 行为 |
|------|------|
| `_visual-analysis.json` 存在且 `visualReviewReady = true` | **执行**视觉验收 |
| `_visual-analysis.json` 存在但 `visualReviewReady = false` | **跳过**视觉验收，自动流转到 E2E_VERIFY |
| `_visual-analysis.json` 不存在 | **跳过**视觉验收，自动流转到 E2E_VERIFY |
| Web 端未启用（`platforms.web.enabled = false`） | **跳过**视觉验收 |
| 仅小程序端启用（无 Web 端） | **跳过**视觉验收（当前仅支持 Web 端视觉验收） |
| 纯后端需求 | **跳过**视觉验收 |

> **当前限制**: 视觉验收依赖本地预览服务 + Playwright 截图，**当前仅支持 Web 端**。小程序端的视觉验收能力后续版本规划中。

> **跳过时**: 在 `phaseHistory` 中记录 `{ "phase": "VISUAL_REVIEW", "status": "skipped", "skipReason": "{原因}" }`，然后自动流转到 E2E_VERIFY。

### 0.2 与 BUILD_VERIFY 的关系

```
BUILD_VERIFY (PASS) 
    ↓ 
查阅 phase-transitions.json：下一阶段 = VISUAL_REVIEW
    ↓
检查 VISUAL_REVIEW 触发条件
    ├─ 满足条件 → 进入 VISUAL_REVIEW 三步模式
    └─ 不满足条件 → 跳过 VISUAL_REVIEW → 进入 E2E_VERIFY
```

---

## 1. 前置条件检查

编排器进入 VISUAL_REVIEW 阶段时，按以下顺序检查：

```
1. 检查 state.json：currentPhase 应为 VISUAL_REVIEW
2. 定位 _visual-analysis.json：
   a) 优先检查 docs/workflows/{需求ID}/analysis/_visual-analysis.json
   b) 备选检查 docs/prd/_visual-analysis.json
3. 读取 _visual-analysis.json：
   a) 检查 visualReviewReady 字段
   b) 检查 designScreenshotsDir 字段
   c) 统计 images[].savedPath 非 null 的数量
4. 检查 designScreenshotsDir 目录是否存在且非空
5. 检查 Web 端项目可用性：
   a) platforms.web.enabled = true
   b) projectConfig.webProject 路径有效
6. 所有检查通过 → 进入执行阶段
   任一检查失败 → 跳过本阶段
```

---

## 2. Agent 调度策略

VISUAL_REVIEW 阶段固定使用**单 Agent 直接调度**（不使用 Parallel Agent），因为：
- 视觉对比需要逐页串行执行（启动预览 → 访问页面 → 对比截图）
- 对比过程依赖本地预览服务的状态连续性
- 视觉验收通常涉及的页面数量不多（3-10 页）

### 2.1 调度方式选择

| 方式 | 条件 | 说明 |
|------|------|------|
| **Task 调度**（默认） | 始终优先 | 使用 Task 工具调用 visual-reviewer Agent |
| **编排器直接执行**（兜底） | Task 失败时 | 编排器自身参考 Agent 规范执行视觉验收 |

### 2.2 Task Prompt 模板

```
你是一位资深视觉验收专家，负责对前端实现进行设计还原度验收。请按以下步骤执行：

1. 读取你的 Agent 行为规范文件（Read）：{agents/visual-reviewer.md 的绝对路径}
2. 读取工作流状态：{state.json 的绝对路径}
3. 读取视觉分析数据：{_visual-analysis.json 的绝对路径}
4. 读取 UI 视觉规范：{rules/ui-visual-spec.md 的绝对路径}
5. 条件读取 Web 端架构文档：{architecture/web/architecture.md 的绝对路径}（如存在）
6. 严格按照 Agent 规范（v2）执行完整流程：
   a) Phase 1: 创建 visual-review/ 目录结构（design/ + actual/fullpage/ + actual/viewport/）
   b) Phase 2: 启动本地预览服务（端口 3099）
   c) Phase 3: 截图采集（CRITICAL）
      - 复制设计稿到 visual-review/design/
      - 使用 Playwright 截取全页面长截图 → visual-review/actual/fullpage/
      - 滚动触发入场动画后逐屏截图 → visual-review/actual/viewport/
      - 验证截图非空
   d) Phase 4: 逐页对比设计稿和实际截图
   e) Phase 5: 生成结构化验收报告（含截图路径引用）
7. 将验收报告写入：{visual-review/visual-review-report.md 的绝对路径}
8. 将验收数据写入：{visual-review/visual-review-data.json 的绝对路径}
9. 关闭浏览器和预览服务

需求 ID：{id}
工作流路径：{docs/workflows/{需求ID}/ 的绝对路径}
项目根目录：{项目绝对路径}
Web 端项目目录：{webProject 绝对路径}
Playwright CLI 路径：~/.claude/plugins/marketplaces/codebuddy-plugins-official/plugins/playwright-cli/playwright-cli.js

⚠️ 重要：
- 你必须先 Read 读取 Agent 规范文件，再按规范执行
- 必须使用 Playwright 截取实际页面截图，不能仅凭代码分析
- 截图时必须先滚动到底部触发所有 Framer Motion / IntersectionObserver 入场动画
- 逐屏截图使用 80% 步进（20% 重叠）确保无遗漏
- 所有截图和设计稿副本必须保存到 visual-review/ 目录
- 在差异清单中引用具体的截图文件名（如 "见 viewport-08.png"）
- 完成后返回综合还原度评分、各页面分数和差异摘要
```

---

## 3. 回退策略

### 3.1 回退路由

| 验收结果 | 编排器行为 |
|---------|-----------|
| qualityGate = `pass` | 正常流转到 E2E_VERIFY |
| qualityGate = `warn` | 展示 🟡 警告，用户选择继续或回退 |
| qualityGate = `fail` | 展示 🔴 建议回退，但用户有最终决策权 |

### 3.2 回退目标

```
VISUAL_REVIEW 发现还原度不足
    ↓
按差异类型分类
    ↓
┌──────────────────────────────────────────────────────────┐
│ 场景 A：布局/组件缺失等代码层面问题                        │
│   → 回退到 IMPLEMENT 阶段                                │
│   → 注入视觉差异清单作为修复上下文                        │
│   → 仅重新调度 Web 端开发 Agent                           │
├──────────────────────────────────────────────────────────┤
│ 场景 B：间距/色彩等样式微调问题                           │
│   → 回退到 IMPLEMENT 阶段                                │
│   → 注入精确的 CSS 修复建议                              │
│   → 仅重新调度 Web 端开发 Agent                           │
├──────────────────────────────────────────────────────────┤
│ 场景 C：设计稿理解偏差（架构层面问题）                    │
│   → 仍回退到 IMPLEMENT 阶段（phase-transitions.json      │
│     仅允许 VISUAL_REVIEW → IMPLEMENT 回退）               │
│   → 在 rollbackLog 中注明"需先调整组件架构再实现"        │
│   → 注入架构层面的修改建议，由 Web 开发 Agent 综合处理    │
│   → 极少发生，需用户确认                                 │
└──────────────────────────────────────────────────────────┘
```

### 3.3 回退次数保护

| 规则 | 说明 |
|------|------|
| **最大回退次数**: 2 | 同一个 VISUAL_REVIEW → IMPLEMENT 的回退循环**不超过 2 次** |
| **第 2 次回退时** | 编排器展示 🔴 强警告：\"已连续 2 次视觉修复失败，建议人工介入。\" |
| **超过 2 次** | 编排器**不阻断**，但记录为 HIGH 风险到 `risks.json` |

### 3.4 回退执行流程

```
1. VISUAL_REVIEW 阶段总结确认 → 用户选择「回退修复」
2. 编排器执行回退：
   a) 在 state.json.rollbackLog 中记录回退信息
   b) 删除 visual-review/ 目录（验收报告）
   c) 更新 state.json：
      - currentPhase → IMPLEMENT
      - 仅将 Web 端的 platforms.web.status 改回 "pending"
      - 后端等其他平台保持不变
   d) phaseHistory 中 VISUAL_REVIEW 记录状态改为 "rolled_back"
3. 重新进入 IMPLEMENT 阶段（视觉修复模式）
4. 仅调度 Web 端开发 Agent，注入视觉差异上下文
5. IMPLEMENT 完成 → BUILD_VERIFY（二次验证）→ VISUAL_REVIEW（二次验收）
```

### 3.5 视觉修复模式上下文注入

回退到 IMPLEMENT 阶段时，编排器在 rollbackLog 中记录以下信息：

```json
{
  "fromPhase": "VISUAL_REVIEW",
  "toPhase": "IMPLEMENT",
  "reason": "视觉还原度不足",
  "timestamp": "{ISO8601时间}",
  "deletedArtifacts": ["visual-review/"],
  "failedPlatforms": ["web"],
  "passedPlatforms": ["backend"],
  "visualReviewScore": 65,
  "visualIssues": [
    {
      "severity": "critical",
      "pageName": "首页",
      "dimension": "components",
      "description": "设计稿中的搜索筛选栏未实现",
      "suggestion": "在 HomePage 组件顶部添加 SearchFilter 组件"
    },
    {
      "severity": "major",
      "pageName": "用户列表",
      "dimension": "spacing",
      "description": "表格与搜索栏间距应为 16px，实际为 32px",
      "suggestion": "将 SearchFilter 的 margin-bottom 从 mb-8 改为 mb-4"
    }
  ]
}
```

编排器注入给 Web 开发 Agent 的上下文：

```
【视觉修复模式】上次 VISUAL_REVIEW 阶段发现以下视觉还原度问题（综合评分: {score}/100），
请在本次实现中修复。仅需修复以下视觉差异，不要修改其他代码：

{差异清单 + 修复建议}

参考设计稿: {design-screenshots/ 目录下对应的图片路径}
```

---

## 4. 编排器对接行为（VISUAL_REVIEW 三步模式）

### Step 1: 预览

```
** 📋 阶段预览: VISUAL_REVIEW **

📌 需求: [需求名称]
🔄 当前阶段: VISUAL_REVIEW (11/14)
🎨 验收模式: AI 视觉对比验收

📥 输入:
  - 设计稿: {designScreenshotsDir} ({N} 张设计稿)
  - 视觉分析: _visual-analysis.json (含组件树/样式指南)
  - UI 规范: ui-visual-spec.md

📤 预期输出:
  - visual-review/visual-review-report.md (视觉验收报告)
  - visual-review/visual-review-data.json (验收数据)

🔍 验收范围:
  | 页面 | 设计稿 | 路由 |
  |------|--------|------|
  | {页面名} | {设计稿文件名} | {路由路径} |
  | ... | ... | ... |

⚠️ 已知限制:
  - AI 视觉对比为近似评估，非像素级精确对比
  - 动态内容（动画、过渡效果）无法通过静态截图验证
  - 响应式断点仅在当前浏览器窗口尺寸下验证

请确认是否执行？[执行 / 跳过 / 取消]
```

### Step 2: 执行

- 使用 Task 工具调用 visual-reviewer Agent
- 实时监控执行进度

### Step 3: 总结确认

```
** ✅ 阶段完成: VISUAL_REVIEW **

🎨 综合还原度: {score}/100 (等级: {grade})
⏱️ 耗时: {时长}

📊 逐页验收结果:
  ┌─────────────┬───────┬───────┬──────────────────────────────┐
  │ 页面         │ 得分   │ 等级   │ 主要差异                      │
  ├─────────────┼───────┼───────┼──────────────────────────────┤
  │ 首页         │ 88/100 │ B     │ 通知 Badge 未实现             │
  │ 用户列表     │ 92/100 │ A     │ 无                           │
  │ 用户表单     │ 75/100 │ C     │ 间距偏差、底部操作栏缺失      │
  └─────────────┴───────┴───────┴──────────────────────────────┘

📸 截图清单:
  - 设计稿副本: visual-review/design/ ({N} 张)
  - 全页面截图: visual-review/actual/fullpage/ ({N} 张)
  - 逐屏截图:   visual-review/actual/viewport/ ({N} 张)
  - 总截图数:    {total} 张

📄 产出物:
  - visual-review/visual-review-report.md
  - visual-review/visual-review-data.json

{根据 qualityGate 展示不同级别提示}

⚠️ 差异摘要:
  - 🔴 严重差异: {N} 项
  - 🟡 明显差异: {N} 项
  - 🟢 微小差异: {N} 项

下一阶段: E2E_VERIFY
请选择: [确认进入下一阶段 / 回退修复视觉差异]
```

---

## 5. VISUAL_REVIEW PASS 后的流转指令（CRITICAL）

> **编排器必读**: VISUAL_REVIEW PASS 仅表示"视觉验收通过"，**不等于工作流完成**。

VISUAL_REVIEW 阶段 PASS 后，编排器的下一步操作：

| 步骤 | 操作 |
|------|------|
| 1 | 在"总结确认"中展示视觉验收结果 |
| 2 | 查阅 `references/phase-transitions.json`，确认下一阶段为 **E2E_VERIFY** |
| 3 | 更新 `state.json`: currentPhase → `E2E_VERIFY` |
| 4 | 进入 E2E_VERIFY 阶段的"预览"步骤 |

**严禁操作**:
- ❌ 不得将 `currentPhase` 直接设为 `DONE`、`TEST`、`ARCHIVE` 或其他非 `E2E_VERIFY` 的阶段
- ❌ 不得跳过 E2E_VERIFY、TEST、ARCHIVE 中的任何一个阶段

VISUAL_REVIEW PASS 后的完整剩余流程：
```
VISUAL_REVIEW (PASS) → E2E_VERIFY → TEST → ARCHIVE → DONE
                       ↑                              ↑
                       还有3个阶段                     终态
```
