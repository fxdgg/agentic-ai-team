# 异常边界处理与自愈策略

D2C 过程中可能遇到的异常及其处理方案。

---

## 一、Figma 数据获取异常

### 1.1 URL 解析失败

**症状**：用户提供的链接无法解析出 `fileKey`

**处理**：
```
向用户提示：
  "无法解析 Figma 链接，请确认链接格式正确。
   支持的格式：
   - https://www.figma.com/file/<fileKey>/<name>
   - https://www.figma.com/design/<fileKey>/<name>
   
   请重新提供链接。"
```

### 1.2 MCP 调用失败

**症状**：`get_figma_data` 返回错误

**处理策略**：
1. **自动重试 1 次**（间隔 2 秒）
2. 仍然失败 → 提示用户：
   ```
   "获取 Figma 数据失败。可能的原因：
    1. Figma 文件需要分享权限（请确认链接是 Public / Anyone with link）
    2. 网络连接问题
    3. Figma 服务暂时不可用
    
    请检查后重试。"
   ```

### 1.3 节点数据为空

**症状**：获取成功但节点树为空或无子节点

**处理**：
```
"获取到的 Figma 节点数据为空。
 可能原因：
 1. node-id 指向了一个空的 Frame
 2. 设计稿内容在其他页面
 
 建议：
 - 在 Figma 中右键点击目标元素 → Copy link
 - 将完整链接（含 node-id）发给我"
```

---

## 二、节点解析异常

### 2.1 未知节点类型

**症状**：遇到未在映射表中的 Figma 节点类型

**处理**：
```tsx
{/* ⚠️ Unknown Figma node type: "BOOLEAN_OPERATION", name: "mask-shape"
    已使用 <div> 兜底，可能需要手动调整 */}
<div style={{ width: '{width}px', height: '{height}px' }}>
  {/* 子节点继续递归渲染 */}
</div>
```

### 2.2 组件无法映射

**症状**：Figma INSTANCE 节点名称无法匹配到项目组件库中的任何组件

**处理**：
1. 使用原生 HTML + CSS 还原视觉效果
2. 在代码注释中标注原始 Figma 组件名
3. 输出建议

```tsx
{/* Figma 组件 "CustomRating" 无法匹配项目组件库，
    已用原生 HTML 还原。如有对应组件请替换。 */}
<div style={{ display: 'flex', gap: '4px' }}>
  {[1, 2, 3, 4, 5].map((star) => (
    <span key={star} style={{ color: '#facc15', fontSize: '18px' }}>★</span>
  ))}
</div>
```

### 2.3 样式溢出

**症状**：嵌套层级过深导致样式代码过长

**处理**：
- 提取为 CSS 类 / CSS Modules / 组件级样式
- 或拆分为子组件

---

## 三、图片/图标处理异常

### 3.1 图片下载失败

**症状**：`download_figma_images` 调用失败

**处理**：
```tsx
{/* ⚠️ 图片 "hero-banner" (nodeId: 1:234) 下载失败
    请手动从 Figma 导出并放置到 src/assets/images/hero-banner.png */}
<img
  src="https://placehold.co/1200x600?text=Hero+Banner"
  alt="Hero banner"
  style={{ width: '100%', height: 'auto', objectFit: 'cover' }}
/>
```

### 3.2 SVG 结构异常

**症状**：下载的 SVG 无法正常渲染

**处理**：
1. 尝试用 `<img>` 标签引入（最兼容）
2. 如需内联，清理 SVG 中的异常属性
3. 注释标注需要手动检查

### 3.3 图标库无匹配

**症状**：项目图标库中无对应图标

**处理**：
1. 下载为 SVG 文件
2. 封装为组件
3. 如下载也失败 → 使用 Unicode/emoji 占位 + 注释

```tsx
{/* ⚠️ 自定义图标 "trophy" 无法匹配，请手动替换 */}
<span style={{ fontSize: '20px' }}>🏆</span>
```

---

## 四、代码生成异常

### 4.1 文件超过 300 行

**触发**：生成的单文件代码超过 300 行

**自愈策略**：
1. 自动识别可独立的 UI 区块
2. 提取为子组件
3. 重新组织 import 和引用

### 4.2 循环依赖

**触发**：拆分的组件之间产生循环引用

**处理**：
1. 共享类型提取到 `types/` 目录
2. 共享常量提取到 `constants/` 目录
3. 调整组件边界

### 4.3 TypeScript 类型推断失败

**触发**：无法从 Figma 数据推断正确类型

**处理**：
```typescript
// 使用明确的类型注释而非 any
interface UnknownData {
  /** TODO: 根据实际 API 返回值定义类型 */
  [key: string]: unknown;
}
```

---

## 五、自愈检查清单

在输出代码前执行自检：

```
□ 所有 import 语句完整且正确
□ 没有使用 any 类型
□ 没有未处理的 TODO（除了标记给用户的）
□ 单文件 ≤ 300 行
□ 所有图片有 alt 属性
□ 交互元素有 cursor-pointer
□ 重复元素使用了 map()
□ 颜色值与设计稿一致
□ 间距值与设计稿一致
□ 所有组件已 export
```
