# 图片处理（Image Workflow）

处理 Figma 设计稿中的位图资源（PNG、JPG、WebP）。

---

## 一、图片识别规则（强制下载策略）

**为确保不同人执行 Skill 时图片下载结果一致，以下规则为硬性约束：**

### 1.1 必须下载的节点（强制，无 AI 自由度）

以下条件满足**任意一条**即必须加入下载队列：

1. **fills 中包含 IMAGE 类型**：`fills[].type === 'IMAGE'` → **必须下载**
2. **节点含 imageRef 属性**：不论节点类型 → **必须下载**
3. **节点名称包含以下关键词（不区分大小写）**：`image`、`img`、`photo`、`banner`、`hero`、`bg`、`background`、`thumbnail`、`cover`、`logo`、`avatar`、`icon`（仅当是位图不是矢量时）、`illustration`、`pic`、`picture` → **必须下载**

### 1.2 不应下载的节点（排除规则）

以下节点即使匹配上述关键词也**不下载**：

1. 纯色填充的 RECTANGLE（`fills[].type === 'SOLID'` 且无 IMAGE fill）
2. 纯 VECTOR 节点（矢量图标走 SVG 流程，参见 `svg-icons.md`）
3. 节点 `visible === false`

### 1.3 图片清单输出（必须步骤）

**在调用 `download_figma_images` 之前，必须先输出完整图片清单供核对：**

```
📋 图片下载清单（共 N 张）：
  序号 | 节点ID    | 节点名称         | 尺寸      | 文件名
  1    | 1:234    | hero-banner     | 1200×600 | hero-banner.png
  2    | 1:567    | user-avatar     | 80×80    | user-avatar.png
  3    | 1:890    | product-thumb   | 300×200  | product-thumbnail.png
```

此清单确保可追溯、可复现。

---

## 二、下载流程

### 2.1 收集需要下载的节点

遍历节点树，收集所有含图片的节点：

```
需下载的图片节点列表：
  - nodeId: "1:234", name: "hero-banner", size: 1200x600
  - nodeId: "1:567", name: "user-avatar", size: 80x80
  - nodeId: "1:890", name: "product-thumbnail", size: 300x200
```

### 2.2 资源指纹去重（MD5 校验）

在下载之前，对已收集的节点执行指纹去重，避免重复资源浪费磁盘和带宽。

**流程：**

1. 检查项目中是否存在 `src/assets/assets-manifest.json`（资源指纹清单），不存在则初始化空清单
2. 对每个待下载的节点，先通过 MCP 获取图片二进制数据，计算其 MD5 哈希值
3. 与 `assets-manifest.json` 中已有记录进行比对：
   - **命中**：跳过下载，直接将代码中的引用路径指向已有文件，输出日志 `[SKIP] <filename> (duplicate of <existing-file>)`
   - **未命中**：执行下载，保存到目标目录，并将新记录追加到清单

**清单格式：**

```json
{
  "assets": {
    "hero-banner.png": {
      "md5": "a3f2b8c1d4e5f6a7b8c9d0e1f2a3b4c5",
      "path": "src/assets/images/hero-banner.png",
      "size": "45.3KB",
      "figmaNodeId": "1:234"
    }
  }
}
```

**去重规则：**
- 比较维度为文件内容的 MD5 值，而非文件名（同一张图可能在不同页面有不同命名）
- 当检测到重复时，新组件中的 `import` 路径统一指向已有文件
- 清单随项目提交到 Git，确保团队成员共享去重状态

### 2.3 调用 MCP 下载

```
download_figma_images({
  fileKey: "<fileKey>",
  nodes: [
    { nodeId: "1:234", fileName: "hero-banner.png" },
    { nodeId: "1:567", fileName: "user-avatar.png" },
    { nodeId: "1:890", fileName: "product-thumbnail.png" }
  ],
  localPath: "src/assets/images/",
  pngScale: 2
})
```

> **路径适配说明**：`localPath` 应根据项目已有资源目录设定。常见约定：`src/assets/images/`、`public/images/`、`src/static/`。

### 2.4 文件命名规则

```
原始节点名称 → kebab-case + 后缀
  "Hero Banner"     → hero-banner.png
  "User Avatar"     → user-avatar.png
  "BG_Gradient"     → bg-gradient.png
  "产品图 1"         → product-1.png
```

---

## 三、图片使用规范

### 3.1 静态导入（推荐）

```tsx
import heroBanner from '@/assets/images/hero-banner.png';

<img src={heroBanner} alt="Hero banner" style={{ width: '100%', height: 'auto', objectFit: 'cover' }} />
```

### 3.2 使用组件库 Image 组件（如项目组件库提供）

> 根据技术栈检测结果判断是否有可用的 Image 组件（如 TDesign `Image`、Ant Design `Image`）。无则使用原生 `<img>`。

```tsx
// TDesign 示例
import { Image } from 'tdesign-react';
<Image src={heroBanner} alt="Hero banner" fit="cover" style={{ width: '100%' }} />

// Ant Design 示例
import { Image } from 'antd';
<Image src={heroBanner} alt="Hero banner" style={{ objectFit: 'cover' }} />
```

### 3.3 背景图片

```tsx
<div
  style={{
    width: '100%',
    height: '400px',
    backgroundImage: `url(${heroBanner})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  }}
>
  {/* 内容 */}
</div>
```

---

## 四、占位图处理

当图片下载失败或为动态内容时，使用占位图：

```tsx
{/* 用户头像（动态内容） */}
<img src="https://placehold.co/80x80" alt="用户头像" />

{/* 产品图（动态内容） */}
<img src="https://placehold.co/300x200" alt="产品图" />

{/* 占位图带文字说明 */}
<img src="https://placehold.co/600x400?text=Banner+Image" alt="Banner" />
```

---

## 五、图片优化建议

在代码注释中标注优化建议：

```tsx
{/* TODO: 图片优化建议
  1. hero-banner.png (1200x600) → 考虑使用 WebP 格式，可减少 30% 体积
  2. 建议添加 loading="lazy" 延迟加载
  3. 建议提供 srcSet 适配不同分辨率
*/}
<img
  src={heroBanner}
  alt="Hero banner"
  style={{ width: '100%', height: 'auto', objectFit: 'cover' }}
  loading="lazy"
/>
```

---

## 六、图片处理脚本

项目中提供了图片处理脚本 `scripts/process-images.cjs`，可用于：

- 批量压缩图片
- 转换 WebP 格式
- 生成多分辨率版本
- 上传到 CDN

使用方式：
```bash
node .codebuddy/skills/figma-d2c/scripts/process-images.cjs --dir src/assets/images
```

---

## 七、复合视觉效果节点整体导出（强制规则）

**此节为 v4.0 新增的关键规则**，针对含复杂视觉效果的节点，避免用 CSS 渐变/多层背景反复试错。

### 7.1 触发条件

当 `design-quality-precheck.md` 预检识别出以下节点时，必须整体导出为图片：

| 条件 | 说明 |
|------|------|
| 单节点多 fill 叠加（IMAGE + GRADIENT ≥ 2 层） | CSS 多背景层叠结果可能与 Figma 不一致 |
| 含 `cropTransform` 的 IMAGE fill | Figma 私有裁剪矩阵，CSS 无法精确还原 |
| 非标准混合模式 `blendMode` | CSS `mix-blend-mode` 渲染可能有差异 |
| GROUP 内多个渐变 RECTANGLE 叠加（坐标重叠 > 80%） | 多层叠加效果不可靠 |

### 7.2 导出流程

```
1. 使用 download_figma_images 直接导出该节点为 PNG
   → pngScale: 2（2x 高清）
   → 注意：导出的是整个节点（含所有子节点和 fill 叠加效果）

2. 文件命名：{节点语义名}-composite.png
   → 示例：quiz-bg-composite.png、hero-decor-composite.png

3. 保存到组件就近的 assets 目录
   → 示例：src/pages/{PageName}/assets/

4. 在代码中以 <img> 或 CSS background-image 引用
```

### 7.3 代码使用示例

```tsx
import bgComposite from './assets/quiz-bg-composite.png';

// 场景 1：纯装饰背景 — 用 <img> + aria-hidden
<div className="relative">
  <img
    src={bgComposite}
    alt=""
    aria-hidden="true"
    className="absolute inset-0 w-full h-full rounded-lg"
    style={{ objectFit: 'fill' }}
  />
  {/* 内容层叠加在上方 */}
  <div className="relative z-10">
    {/* 交互内容 */}
  </div>
</div>

// 场景 2：作为容器背景 — 用 CSS background-image
<div
  className="relative rounded-lg"
  style={{
    backgroundImage: `url(${bgComposite})`,
    backgroundSize: '100% 100%',
    backgroundRepeat: 'no-repeat',
  }}
>
  {/* 内容 */}
</div>
```

### 7.4 与毛玻璃/阴影效果的组合

当复合视觉效果节点同时具有 `backdropFilter`（毛玻璃）或 `boxShadow` 时：

```tsx
// 图片作为视觉层，毛玻璃/阴影用 CSS 应用在外层容器上
<div
  className="relative rounded-lg overflow-hidden"
  style={{
    backdropFilter: 'blur(24px)',
    boxShadow: '0px 8px 10px -5px rgba(0,0,0,0.08)',
    border: '1px solid #FFFFFF',
  }}
>
  <img
    src={bgComposite}
    alt=""
    aria-hidden="true"
    className="absolute inset-0 w-full h-full"
    style={{ objectFit: 'fill' }}
  />
  <div className="relative z-10">
    {/* 内容 */}
  </div>
</div>
```

### 7.5 ⚠️ 禁止事项

1. **禁止**对复合视觉效果节点使用 CSS 多层 `background` / `linear-gradient` 模拟
2. **禁止**在 CSS 模拟效果不佳时反复调整渐变参数（每次调整都是猜测，无法收敛）
3. **禁止**将复合节点拆解为多个子层分别导出再叠加（丢失叠加效果的整体性）
4. **禁止**手动修改 `cropTransform` 的裁剪参数（直接导出已包含裁剪结果）

---

## 八、MCP 图片下载工具陷阱与规避策略

> **此节总结了实际 D2C 实践中发现的 `download_figma_images` MCP 工具高频问题，必须在每次下载图片前检查。**

### 8.1 三种下载模式及其差异

MCP `download_figma_images` 工具有三种使用方式，**效果完全不同**：

| 模式 | 参数 | 导出内容 | 适用场景 |
|------|------|---------|---------|
| **模式 A：imageRef + needsCropping=true** | 指定 `imageRef` + `needsCropping: true` + `cropTransform` | 原始素材经 cropTransform 裁剪后的**局部图片** | ❌ **几乎不应使用**，裁剪结果与 Figma 渲染不一致 |
| **模式 B：imageRef + needsCropping=false** | 指定 `imageRef` + `needsCropping: false` | Figma 素材库中的**原始图片**（未经任何处理） | ❌ 仅获取原始素材，不含节点的 fill 模式、缩放、位置调整 |
| **模式 C：仅 nodeId，不指定 imageRef** | 只指定 `nodeId`，不传 `imageRef` | **整个节点渲染为 PNG**，包含所有 fill 叠加、渐变、子节点效果 | ✅ **推荐的默认方式** |

### 8.2 ⚠️ 必须使用模式 C（节点渲染）的场景

以下场景**必须使用模式 C**（不传 imageRef），否则导出结果必然有偏差：

| 场景 | 原因 | 错误表现 |
|------|------|---------|
| 节点 fills 包含 IMAGE + 渐变/颜色叠加 | imageRef 只能获取原始图片素材，不含渐变叠加效果 | 背景图缺少渐变覆盖层 |
| IMAGE fill 含 `cropTransform` | cropTransform 是 Figma 私有矩阵，MCP 裁剪结果与 Figma 渲染不一致 | 图片被错误裁剪，构图偏移 |
| 节点设置了 `clipContent: true` 且图片超出边界 | 模式 C 按节点边界渲染，会裁切溢出内容 | 图片底部/侧边被截断（见 8.3 陷阱） |
| 节点为大尺寸背景（如 Banner、Hero） | 需要获取完整的视觉效果，不是原始素材 | 只拿到部分花纹/纹理 |

### 8.3 ⚠️ 模式 C 的已知陷阱：clipContent 导致渲染裁切

**即使使用模式 C，仍可能存在问题：**

当节点设置了 `clipContent: true`（Figma 中的"裁剪内容"），且子元素或图片 fill 超出了节点边界时，模式 C 渲染导出会**按节点可见边界裁切**，超出部分被丢弃。

**检测方法：**

```
遍历包含 IMAGE fill 的节点，检查以下条件：
1. 节点 clipContent === true
2. IMAGE fill 的 imageRef 原始图片尺寸（宽或高）明显大于节点尺寸
3. IMAGE fill 的 scaleMode === 'FILL' 或 'FIT' 且 cropTransform 存在

满足以上条件 → 标记为 "clipContent 风险节点"
```

**处理策略：**

```
1. 先使用模式 C 导出节点渲染图
2. 验证导出图片的尺寸是否与节点设计尺寸一致
   → 如果一致且视觉完整 → 可以使用
   → 如果视觉不完整（如花纹/图案被截断）→ 执行以下补救
3. 补救方案（按优先级）：
   a. 尝试导出父节点（如果父节点包含完整可见区域）
   b. 标记为"需用户手动从 Figma 导出"，在回归验证中标注
   c. 不要使用 imageRef 模式（模式 A/B），因为会更糟
```

### 8.4 背景图导出后的验证流程（强制步骤）

每张通过 MCP 下载的图片，**必须执行以下验证**：

```
📋 图片导出验证清单：

对每张下载的图片执行：
1. ✅ 文件存在且非空
2. ✅ 图片尺寸与预期一致
   → 模式 C 导出：尺寸应为 节点宽度×pngScale × 节点高度×pngScale
   → 示例：节点 2560×400, pngScale=2 → 预期图片 5120×800
3. ✅ 视觉完整性检查（关键新增）
   → 将导出的图片读取并目视检查（使用 read_file 工具查看图片）
   → 与 Figma 设计稿中的对应区域进行视觉对比
   → 确认图片主体内容完整，没有异常裁切或缺失
4. ⚠️ 如果发现异常：
   → 记录问题（如"底部被截断"、"只有素材局部"）
   → 尝试其他下载模式或补救方案（见 8.3）
   → 在回归验证报告中标注
```

### 8.5 背景图使用方式的选择

根据设计稿中的使用方式选择代码实现：

| 设计稿特征 | 代码实现 | 说明 |
|-----------|---------|------|
| 图片作为容器背景，上方有文字/按钮等内容叠加 | CSS `background-image` | 使用 `backgroundSize: 'cover'` + `backgroundPosition: 'center'` |
| 图片是纯装饰，没有内容叠加 | `<img>` 标签 + `aria-hidden="true"` | 语义化更好 |
| 图片需要与容器精确对齐且不能被 cover 裁切 | CSS `background-image` + `background-size: 100% 100%` | 拉伸填充 |

### 8.6 反模式总结

```
❌ 反模式 1：使用 imageRef 下载背景图
  → 只获取原始素材，不含 Figma 中的 fill 模式和叠加效果
  → 必须使用节点渲染导出（不传 imageRef）

❌ 反模式 2：使用 imageRef + cropTransform 下载
  → MCP 裁剪算法与 Figma 渲染不一致，图片被错误裁切
  → 即使 needsCropping=false 也只是获取原始素材

❌ 反模式 3：下载后不验证图片完整性
  → 直接用在代码中，部署后才发现背景图被截断/缺失
  → 必须在下载后执行视觉验证（8.4 清单）

❌ 反模式 4：用 CSS 多层渐变模拟含图片的复合背景
  → Figma 4 层填充（底色+图片+渐变+遮罩）无法用 CSS 精确还原
  → 直接导出整个节点为图片

✅ 正确做法：
  1. 检测到 IMAGE fill → 使用模式 C（节点渲染导出）
  2. 导出后验证图片尺寸和视觉完整性
  3. 发现 clipContent 问题 → 标记并尝试补救
  4. 在代码中用 background-image 或 <img> 引用
```
