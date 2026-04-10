# Figma D2C Skill

将 Figma 设计稿自动转换为可直接运行的前端代码。基于 CodeBuddy Skill 机制，通过 Figma MCP 获取设计数据，结合项目级配置文件实现**精确还原、稳定复现、可追溯验证**的 Design-to-Code 工作流。

## 核心能力

### 设计稿精确还原

- **像素级视觉还原**：颜色、字号、行高、圆角、阴影等数值属性从 Figma 精确提取，禁止近似替代
- **坐标驱动布局**：基于设计稿坐标系统分析元素排列关系，自动选择 flex/grid/absolute 布局方案
- **复合视觉效果处理**：自动识别多层渐变、图片叠加等复杂效果，直接导出为图片而非用 CSS 模拟
- **自适应响应式输出**：固定宽度设计稿自动转换为 max-width + 居中的弹性布局，适配不同屏幕

### 智能组件识别与映射

- **组件库映射**：自动将 Figma 中的 Button、Tag、Avatar 等组件映射到项目实际使用的组件库（TDesign、Ant Design 等）
- **项目组件复用**：优先匹配项目中已有的自定义组件，避免重复开发
- **Design Token 对齐**：自动对齐 Figma Variables 与项目 Token 体系，保持命名一致性

### 稳定复现

- **确定性输出**：节点遍历顺序、Import 排序、类名排序、资源命名均有固定规则，同输入多次执行结果一致
- **项目画像锁定**：通过配置文件固定技术栈、目录结构、命名规范和生成策略
- **显式映射优先**：组件映射和 Token 别名通过配置文件显式定义，消除 AI 猜测带来的不确定性

### 全流程质量保障

- **设计稿预检**：代码生成前自动检测复合视觉效果、结构不规范项和数据完整性
- **逐节点数据回查**：输出前逐一核对每个 UI 元素的 Figma 原始数据与代码实际值
- **即时截图对比**：代码输出后立即截图与设计稿对比，发现问题当场修复
- **回归验证闭环**：9+ 维度定量评分，综合还原度 ≥ 90% 才算通过

## 前置准备

### 1. 连接 Figma MCP

本 Skill 依赖 **Framelink Figma MCP** 获取设计稿数据，需要在 CodeBuddy 中连接：

- MCP Server：`FramelinkFigmaMCP`
- 提供两个工具：`get_figma_data`（获取节点数据）、`download_figma_images`（下载图片资源）

### 2. 配置项目画像（推荐）

Skill 目录下提供了以下配置文件模板：

| 文件 | 作用 |
|------|------|
| `project-profile.json` | 锁定技术栈、目录结构、命名规范、生成策略 |
| `component-map.json` | 定义 Figma 组件到代码组件的映射关系 |
| `token-aliases.json` | 定义 Figma 色值/间距到项目 Token 的映射 |
| `request-template.json` | 统一请求格式，减少自然语言歧义 |

推荐流程：
1. 根据项目实际情况调整 `project-profile.json`（技术栈、目录结构等）
2. 补充 `component-map.json`（已有的自定义组件和组件库映射）
3. 补充 `token-aliases.json`（项目的 Design Token 体系）
4. 以上文件均非必需，缺失时 Skill 会使用内置默认值并自动检测项目技术栈

## 快速开始

### 方式一：自然语言（最简单）

直接发送设计稿链接即可：

```text
帮我把这个设计稿转成代码
https://www.figma.com/design/abc123/MyPage?node-id=1-234
```

也支持其他触发方式：
- "D2C"
- "设计稿转代码"
- "帮我还原这个设计稿"
- 直接粘贴 Figma 链接

### 方式二：标准请求（团队协作推荐）

```json
{
  "action": "create",
  "figmaUrl": "https://www.figma.com/design/abc123/MyPage?node-id=1-234",
  "nodeId": "1:234",
  "mode": "page",
  "outputPath": "src/pages/MyPage/index.tsx"
}
```

使用标准请求可以精确控制输出路径、生成模式等参数，团队成员之间结果更一致。

## 支持的操作

| 操作 | 触发方式 | 说明 |
|------|---------|------|
| **新建页面/组件** | "D2C"、"设计稿转代码"、粘贴 Figma 链接 | 完整的设计稿到代码转换流程 |
| **更新已有组件** | "更新设计稿"、"同步最新设计" | 仅修改变化部分，保留手写业务逻辑 |
| **回归验证** | "检查还原度"、"回归验证" | 对已生成代码进行多维度还原度评估 |
| **下载图片** | "下载图片"、"处理图片资源" | 单独处理设计稿中的图片资源 |
| **下载图标** | "下载图标"、"SVG" | 单独处理设计稿中的 SVG 图标 |

## 执行流程

完整的新建流程包含 4 个阶段、16 个步骤：

**P1 准备** → 输入归一化 → 加载配置 → 解析 URL

**P2 分析** → 获取 Figma 数据 → 质量预检 → 结构摘要 → 坐标系统建立 → 行聚类与间距精算

**P3 生成** → 节点解析与组件映射 → 布局验证 → 逐节点数据回查 → 代码输出

**P4 验证** → 即时截图对比 → 背景图验证 → 回归验证 → 生成 Manifest

每个步骤都有结构化检查点（Checkpoint），确保不跳过关键环节。

## 生成产物

以一个典型页面为例：

```text
src/
├── pages/PageName/
│   ├── index.tsx          # 页面入口（纯组装层）
│   ├── HeroBanner.tsx     # 子组件
│   ├── ContentArea.tsx    # 子组件
│   └── mock/
│       ├── types.ts       # TypeScript 类型定义
│       ├── pageData.ts    # Mock 数据（标注 @source）
│       └── index.ts       # 统一导出
├── services/
│   └── pageService.ts     # API 预留层
└── assets/
    └── images/            # 设计稿图片资源
```

### 代码特点

- **可直接运行**：Import 完整、类型定义完备、零 `any` / 零 `@ts-ignore`
- **单文件 ≤ 300 行**：超过自动拆分为子组件
- **数据分离**：UI 组件通过 Service/Hook 获取数据，不直接引用 Mock 常量
- **语义化标记**：`data-figmanode` 属性关联 Figma 节点 ID，`@d2c-start/@d2c-end` 标记生成区域
- **自适应布局**：页面根容器使用 `w-full`，内容区使用 `max-width + 居中`

## 支持的技术栈

| 类别 | 支持项 |
|------|--------|
| 框架 | React、Vue 3 |
| 语言 | TypeScript、JavaScript |
| 样式 | Tailwind CSS、CSS Modules、SCSS、Less、CSS-in-JS |
| 组件库 | TDesign、Ant Design、Element Plus 等 |
| 图标库 | tdesign-icons-react、@ant-design/icons、lucide-react 等 |
| 构建工具 | Vite、Next.js、Webpack |

Skill 会自动检测项目技术栈，也可以通过 `project-profile.json` 显式指定。

## 工具脚本

`scripts/` 目录提供了可独立使用的辅助工具：

```bash
# 图片批量压缩与 WebP 转换
node .codebuddy/skills/figma-d2c/scripts/process-images.cjs --dir src/assets/images --webp --quality 85

# 视觉回归对比
node .codebuddy/skills/figma-d2c/scripts/vrt-check.cjs --figma-image design.png --local-image screenshot.png

# 资源上传 CDN
export D2C_CDN_DOMAIN="cdn.example.com"
node .codebuddy/skills/figma-d2c/scripts/upload-figma-images.cjs --dir src/assets/images
```

## 目录结构

```text
.codebuddy/skills/figma-d2c/
├── skill.json                          # Skill 元信息
├── SKILL.md                            # 主入口调度逻辑
├── README.md                           # 本文件
├── request-template.json               # 标准请求模板
├── project-profile.json                # 项目画像配置
├── component-map.json                  # 组件映射表
├── token-aliases.json                  # Token 别名表
├── generation-manifest.template.json   # 生成清单模板
├── references/                         # 详细参考文档
│   ├── create-workflow.md              # 新建流程
│   ├── update-workflow.md              # 变更流程
│   ├── design-quality-precheck.md      # 设计稿预检
│   ├── code-standards.md               # 代码规范
│   ├── image-workflow.md               # 图片处理
│   ├── svg-icons.md                    # SVG 图标处理
│   ├── regression-check.md             # 回归验证
│   ├── mock-data.md                    # Mock 数据规范
│   ├── design-tokens.md                # Design Token
│   ├── reuse-check.md                  # 组件复用检测
│   ├── interaction-logic.md            # 交互逻辑
│   ├── error-handler.md                # 异常处理
│   └── a11y-guidelines.md              # 无障碍指南
└── scripts/                            # 辅助工具脚本
    ├── config.cjs
    ├── process-images.cjs
    ├── upload-figma-images.cjs
    └── vrt-check.cjs
```

## 常见问题

**Q: 必须配置 `project-profile.json` 等文件吗？**
不是必须的。Skill 在缺少配置文件时会自动检测项目技术栈并使用内置默认值。但配置后可以显著提升结果的稳定性和准确度，特别是团队多人使用时。

**Q: 支持哪些 Figma 链接格式？**
支持 `figma.com/file/...` 和 `figma.com/design/...` 两种格式，会自动解析 `fileKey` 和 `node-id`。

**Q: 复杂渐变和视觉效果怎么处理？**
Skill 在预检阶段会自动识别复合视觉效果节点（多层渐变叠加、图片+渐变混合等），直接导出为图片而非用 CSS 模拟，避免反复调试渐变参数。

**Q: 生成的代码如何接入真实 API？**
Mock 数据通过 Service 层封装，替换时只需修改 Service 文件中的数据源，UI 组件无需改动。每个 Mock 常量都标注了 `@source`（数据来源）和 `@todo`（替换提示）。

**Q: 如何更新已有的设计稿代码？**
使用"更新设计稿"指令触发增量更新流程，Skill 会对比新旧设计稿差异，仅修改变化部分，保留 `@user-zone` 标记内的手写代码。
