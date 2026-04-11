# Design Token 提取与应用

从 Figma 设计稿中提取 Design Token（设计令牌），生成可维护的主题变量系统，避免硬编码颜色、间距、字体等值。重点是：**先复用项目 Token，再新增 D2C Token；先锁定命名，再写代码。**

---

## 一、Token 总原则

Token 决策优先级固定为：

1. **Figma Variable 引用**
2. **项目已有 Token**
3. **`token-aliases.json` 别名映射**
4. **新提取的 D2C Token**
5. **原始值兜底**

### 为什么这样排序

- Figma Variable 是设计侧最强语义来源
- 项目已有 Token 是代码侧最稳定约束
- `token-aliases.json` 用来打通设计变量与项目主题
- D2C Token 只作为“项目里还没有”的补位方案
- 原始值只能兜底，不能成为默认行为

---

## 二、Token 提取流程

### 2.1 提取时机

在 `create-workflow.md` 的节点树解析过程中，同步收集所有 Token 信息：

1. 遍历节点树时，收集所有唯一的颜色值、间距值、字体配置
2. 识别 Figma Variables 引用（`boundVariables` 字段）
3. 读取项目已有 Token 配置
4. 读取 `token-aliases.json`
5. 去重合并相同值
6. 按类型分类（`color` / `spacing` / `typography` / `shadow` / `radius`）

### 2.2 收集规则

| 来源 | 提取条件 | Token 类型 |
|------|---------|-----------|
| `fills[0].color` | 出现次数 ≥ 3 或引用了 Figma Variable | color |
| `strokes[0].color` | 出现次数 ≥ 2 或引用了 Figma Variable | color |
| `itemSpacing` | 出现次数 ≥ 3 的相同值 | spacing |
| `padding*` | 出现次数 ≥ 3 的相同值 | spacing |
| `fontSize + fontWeight + lineHeight` 组合 | 出现次数 ≥ 2 | typography |
| `effects[]` | 出现次数 ≥ 2 的相同配置 | shadow |
| `cornerRadius` | 出现次数 ≥ 3 的相同值 | radius |

**注意**：Figma Variables 引用无论出现次数，都必须进入 Token 决策链。

---

## 三、Token 命名与锁定

### 3.1 命名规则

```text
格式：--{类型}-{语义}-{层级}

类型前缀：
  color    → --color-
  spacing  → --spacing-
  font     → --font-
  shadow   → --shadow-
  radius   → --radius-
```

### 3.2 命名原则

- **优先用已有名称**：项目已有 Token 名称优先，不重命名
- **别名只做映射，不做二次发明**：`token-aliases.json` 中的名称视为锁定名称
- **新增 D2C Token 才使用语义命名**：如 `--color-bg-secondary`
- **禁止同值多名**：同一个颜色 / 间距 / 圆角不能因为不同页面反复取新名

### 3.3 Figma Variable 名称转换

```text
brand/primary        → --color-brand-primary
text/secondary       → --color-text-secondary
spacing/page-padding → --spacing-page-padding
radius/card          → --radius-card
```

转换规则：
1. `/` 替换为 `-`
2. 空格替换为 `-`
3. 转为 kebab-case
4. 添加类型前缀

---

## 四、`token-aliases.json` 的使用

在命中项目已有 Token 之前或之后，都必须读取 `token-aliases.json` 进行比对。

### 4.1 支持的映射形式

- Figma Variable → 项目 Token
- 原始值 → 项目 Token
- Figma Variable → Tailwind 类名
- 原始值 → Tailwind 类名

### 4.2 示例

```json
{
  "colorAliases": [
    {
      "figmaVariable": "brand/primary",
      "projectToken": "--color-brand-primary",
      "tailwindClass": "bg-brand-primary",
      "rawValue": "#1677FF"
    }
  ]
}
```

### 4.3 命中规则

1. 先用 `figmaVariable` 精确命中
2. 再用 `rawValue` 精确命中
3. 命中后直接采用 `projectToken` / `tailwindClass`
4. 命中结果写入 Manifest

---

## 五、输出格式

### 5.1 Tailwind CSS 项目

优先复用项目现有 `theme.extend`；只有缺失时才追加：

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: {
          primary: 'var(--color-brand-primary)'
        },
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)'
        }
      },
      borderRadius: {
        card: 'var(--radius-card)'
      }
    }
  }
};
```

同时生成或更新 CSS 变量文件：

```css
:root {
  --color-brand-primary: #1677ff;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #666666;
  --spacing-md: 16px;
  --radius-card: 12px;
}
```

### 5.2 非 Tailwind 项目

直接生成 CSS Variables / SCSS 变量文件：

```scss
$color-brand-primary: #1677ff;
$color-text-primary: #1a1a1a;
$spacing-md: 16px;
$radius-card: 12px;
```

---

## 六、代码生成时的 Token 引用优先级（强制）

```text
优先级 1: Figma Variable 引用 → CSS 变量
  示例: bg-[var(--color-brand-primary)]

优先级 2: 项目已有 Token → 项目现有 token / class
  示例: bg-primary / var(--color-primary)

优先级 3: token-aliases.json → 别名结果
  示例: text-text-primary / var(--color-text-primary)

优先级 4: 新提取的 D2C Token → Token 名称
  示例: bg-brand-primary / var(--color-bg-secondary)

优先级 5: 原始值 → 任意值
  示例: bg-[#F5F7FA]
```

### 严格规则

- **禁止跳过项目已有 Token 直接生成 D2C Token**
- **禁止命中别名后仍新建同值 Token**
- **禁止因为页面不同而改变同值 Token 的命名**

---

## 七、Token 文件更新策略

### 7.1 新建项目

- 首次生成时，创建 `src/styles/design-tokens.css` 或项目指定的 Token 文件
- 在入口文件中自动导入该文件
- 同时生成一份 Token 决策记录到 Manifest

### 7.2 已有项目

- 检查项目是否已有 Token 文件（`variables.css/scss`、`tokens.css`、`theme.ts` 等）
- 已有 → 合并新 Token 到已有文件，不覆盖已有定义
- 没有 → 创建新的 Token 文件

### 7.3 增量更新

- 新页面发现新的 Token 值 → 追加
- 不删除已有 Token
- Token 值变化 → 更新值，不改名
- 若旧名与新别名冲突 → 以项目已有 Token 为准，并在 Manifest 标注冲突

---

## 八、Token 收集报告

在代码生成过程中，输出 Token 收集报告：

```text
🎨 Design Token 收集报告：

  Figma Variables 命中：
    brand/primary → --color-brand-primary

  项目已有 Token 命中：
    #1A1A1A → --color-text-primary

  别名命中：
    spacing/md → --spacing-md

  新增 D2C Token：
    --color-bg-secondary: #F5F7FA

  生成文件：
    ✅ src/styles/design-tokens.css
```

---

## 九、Manifest 记录要求

每次 Token 决策都必须记录来源：

```json
{
  "createdTokens": [
    {
      "nodeId": "1:456",
      "source": "project-token",
      "value": "#1A1A1A",
      "resolvedTo": "--color-text-primary"
    },
    {
      "nodeId": "1:789",
      "source": "token-alias",
      "value": "spacing/md",
      "resolvedTo": "--spacing-md"
    }
  ]
}
```

---

## 十、一致性红线

1. Token 引用优先级必须固定
2. 相同值不得重复命名
3. 别名命中后不得再新增同义 Token
4. D2C Token 只能补位，不能覆盖项目主题体系
5. 同一输入重复执行时，Token 结果必须稳定
