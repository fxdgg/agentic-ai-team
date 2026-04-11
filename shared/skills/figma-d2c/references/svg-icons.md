# SVG / 图标处理（SVG Icons）

处理 Figma 设计稿中的矢量图标资源。

---

## 一、图标识别规则

以下 Figma 节点为图标：

1. **VECTOR 类型节点**
2. **节点名称包含**：`icon`、`Icon`、`ico`
3. **尺寸较小的 FRAME/GROUP**：宽高 ≤ 48px 且仅包含 VECTOR 子节点
4. **INSTANCE 且为 icon 组件**

---

## 二、优先使用项目图标库

> 根据技术栈检测结果（参见 SKILL.md）自动识别项目使用的图标库。在下载 SVG 前，必须先尝试匹配项目图标库中的图标。

### 匹配规则

1. 将 Figma 图标名称 normalize：去除 `icon`、`ic_`、`-`、`_` 前缀/分隔
2. 与项目图标库的图标名做模糊匹配
3. 匹配成功 → 直接使用

### 各图标库使用方式

**tdesign-icons-react / tdesign-icons-vue-next：**

```tsx
import { SearchIcon, CloseIcon, AddIcon } from 'tdesign-icons-react';

<SearchIcon size="20px" />
<CloseIcon className="cursor-pointer" onClick={handleClose} />
```

**@ant-design/icons：**

```tsx
import { SearchOutlined, CloseOutlined, PlusOutlined } from '@ant-design/icons';

<SearchOutlined style={{ fontSize: '20px' }} />
<CloseOutlined className="cursor-pointer" onClick={handleClose} />
```

**lucide-react / lucide-vue-next：**

```tsx
import { Search, X, Plus } from 'lucide-react';

<Search size={20} />
<X className="cursor-pointer" onClick={handleClose} />
```

### 通用图标语义速查

| 语义 | TDesign | Ant Design | Lucide | 尺寸建议 |
|------|---------|-----------|--------|---------|
| 搜索 | `SearchIcon` | `SearchOutlined` | `Search` | 20px |
| 关闭 | `CloseIcon` | `CloseOutlined` | `X` | 20px |
| 添加 | `AddIcon` | `PlusOutlined` | `Plus` | 20px |
| 删除 | `DeleteIcon` | `DeleteOutlined` | `Trash2` | 20px |
| 编辑 | `EditIcon` | `EditOutlined` | `Pencil` | 20px |
| 更多 | `MoreIcon` | `MoreOutlined` | `MoreHorizontal` | 20px |
| 设置 | `SettingIcon` | `SettingOutlined` | `Settings` | 20px |
| 筛选 | `FilterIcon` | `FilterOutlined` | `Filter` | 20px |
| 刷新 | `RefreshIcon` | `ReloadOutlined` | `RefreshCw` | 20px |
| 箭头 | `ChevronRight/Left/Up/DownIcon` | `Right/Left/Up/DownOutlined` | `ChevronRight/Left/Up/Down` | 16px |
| 勾选 | `CheckIcon` | `CheckOutlined` | `Check` | 16px |
| 警告 | `ErrorCircleIcon` | `ExclamationCircleOutlined` | `AlertCircle` | 20px |
| 信息 | `InfoCircleIcon` | `InfoCircleOutlined` | `Info` | 20px |
| 成功 | `CheckCircleIcon` | `CheckCircleOutlined` | `CheckCircle` | 20px |

---

## 三、自定义 SVG 下载

当项目图标库无法匹配时，下载 SVG 资源。

### 3.1 调用 MCP 下载

```
download_figma_images({
  fileKey: "<fileKey>",
  nodes: [
    { nodeId: "1:123", fileName: "custom-chart.svg" },
    { nodeId: "1:456", fileName: "brand-logo.svg" }
  ],
  localPath: "src/assets/icons/"
})
```

### 3.2 SVG 文件命名

```
kebab-case + .svg
  "Chart Icon"   → chart-icon.svg
  "BrandLogo"    → brand-logo.svg
  "ic_star_fill" → star-fill.svg
```

### 3.3 使用方式

#### 方式一：直接 img 引入

```tsx
import chartIcon from '@/assets/icons/chart-icon.svg';

<img src={chartIcon} alt="Chart" width={20} height={20} />
```

#### 方式二：封装为组件（推荐）

对于需要动态变色的图标，封装为组件：

**React：**

```tsx
// src/components/icons/ChartIcon.tsx
interface ChartIconProps {
  size?: string | number;
  color?: string;
  className?: string;
}

const ChartIcon: React.FC<ChartIconProps> = ({
  size = '1em',
  color = 'currentColor',
  className,
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* SVG path 内容 */}
  </svg>
);

export default ChartIcon;
```

**Vue 3：**

```vue
<!-- src/components/icons/ChartIcon.vue -->
<script setup lang="ts">
defineProps<{
  size?: string | number;
  color?: string;
}>();
</script>

<template>
  <svg
    :width="size ?? '1em'"
    :height="size ?? '1em'"
    viewBox="0 0 24 24"
    fill="none"
    :stroke="color ?? 'currentColor'"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- SVG path 内容 -->
  </svg>
</template>
```

---

## 四、SVG 优化

下载的 SVG 文件应进行优化处理：

### 优化规则

1. **移除冗余属性**：`xmlns:xlink`、`xml:space`、编辑器元数据
2. **简化路径**：合并可合并的 path
3. **移除隐藏元素**：`display:none`、`opacity:0` 的元素
4. **统一 viewBox**：确保有正确的 `viewBox` 属性
5. **移除固定尺寸**：删除 `width`/`height`，用 CSS 控制大小

### 优化工具

使用项目内置脚本处理 SVG 文件：

```bash
# 批量优化 SVG
npx svgo --folder src/assets/icons/ --output src/assets/icons/
```

---

## 五、图标统一管理

当项目中自定义图标较多时，创建统一导出：

```tsx
// src/assets/icons/index.ts
export { default as ChartIcon } from './ChartIcon';
export { default as BrandLogo } from './BrandLogo';
export { default as CustomStarIcon } from './CustomStarIcon';
```

使用时：

```tsx
import { ChartIcon, BrandLogo } from '@/assets/icons';
```
