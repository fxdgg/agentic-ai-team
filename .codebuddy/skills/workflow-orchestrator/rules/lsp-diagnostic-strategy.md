# LSP 实时诊断策略（通用规则）

> **适用范围**: 所有 IMPLEMENT 阶段开发 Agent 和 BUILD_VERIFY 阶段验证 Agent
> **核心工具**: CodeBuddy IDE 内置的 `read_lints` 工具
> **设计意图**: 通过 IDE 内置的 LSP（Language Server Protocol）诊断能力，在编码过程中实时发现类型错误、编译问题和代码规范违规，避免错误累积到 BUILD_VERIFY 阶段才被发现。

---

## 1. 工具概述

### 1.1 `read_lints` 工具

`read_lints` 是 CodeBuddy IDE 提供的实时诊断工具，底层对接语言服务器（Language Server），能够返回当前工作区中的诊断信息（errors、warnings、hints），**无需手动执行编译命令**。

**支持的诊断类型**:

| 平台 | 语言服务器 | 诊断能力 |
|------|-----------|---------|
| Web 端（TypeScript/React） | TypeScript Language Server | 类型错误、未使用导入、模块解析失败、JSX 类型不匹配 |
| 小程序端（Taro/TypeScript） | TypeScript Language Server | 同上 + Taro 特有的 API 使用检查 |
| 后端（Java） | Java Language Server | 编译错误、类型不匹配、未解析的符号、缺失 import、注解处理错误 |

### 1.2 与终端编译命令的关系

| 维度 | `read_lints`（LSP 诊断） | 终端编译命令 |
|------|--------------------------|-------------|
| 执行速度 | **毫秒级**，增量分析 | 秒~分钟级，全量编译 |
| 调用时机 | 每次文件写入后立即调用 | 阶段性验证（Step 4 自检 / BUILD_VERIFY） |
| 诊断精度 | 高（实时 AST 分析） | 最高（真实编译器） |
| 适用阶段 | IMPLEMENT（编码中） | IMPLEMENT（自检）+ BUILD_VERIFY |
| 互补关系 | 快速捕获 80%+ 的编译错误 | 捕获 LSP 无法发现的构建链问题（资源打包、分包配置、Maven 依赖传递） |

> **核心原则**: `read_lints` 和终端编译命令**互为补充，非互相替代**。`read_lints` 提供编码过程中的即时反馈，终端编译命令提供最终的权威验证。

---

## 2. IMPLEMENT 阶段使用规范

### 2.1 增量诊断策略（每次文件写入后）

**触发时机**: 每次通过 `write_to_file` 或 `replace_in_file` 修改/创建文件后。

**执行流程**:

```
文件写入完成
    ↓
调用 read_lints（指定刚修改的文件路径）
    ↓
检查诊断结果
    ↓
┌─────────────────────────────────────────────┐
│ 无 error 级别诊断                             │
│   → 继续下一个文件的实现                       │
│                                               │
│ 存在 error 级别诊断                           │
│   → 立即修复当前文件的错误                     │
│   → 修复后再次调用 read_lints 确认错误已清除   │
│   → 确认无 error 后继续下一个文件              │
│                                               │
│ 仅有 warning/hint 级别诊断                    │
│   → 记录到工作日志中，不阻断实现流程           │
│   → 在 Step 4 自检时统一评估                   │
└─────────────────────────────────────────────┘
```

### 2.2 批量诊断策略（相关文件组完成后）

**触发时机**: 一组关联文件（如同一模块的 types.ts → api.ts → hooks.ts → index.tsx）全部完成后。

**执行流程**:

```
调用 read_lints（指定模块所在目录路径）
    ↓
检查跨文件的诊断结果（如 import 引用错误、类型不一致）
    ↓
若存在跨文件 error → 逐一修复并重新检查
若仅有 warning → 记录并继续
```

### 2.3 自检阶段增强（Step 4 / 完成验证协议）

在开发 Agent 原有的自检流程（Step 4）和完成验证协议（IDENTIFY → RUN → READ → CLAIM）中，**新增 `read_lints` 作为前置快速检查**：

```
原有流程:
  IDENTIFY → RUN(终端编译命令) → READ → CLAIM

增强后流程:
  IDENTIFY → LSP_SCAN(read_lints 全项目扫描) → RUN(终端编译命令) → READ → CLAIM
                ↓
          若 LSP_SCAN 发现 error:
            → 先修复 LSP 报告的错误
            → 修复后重新 LSP_SCAN 确认
            → 再执行终端编译命令
          
          若 LSP_SCAN 无 error:
            → 直接执行终端编译命令（大概率也会通过）
```

> **价值**: 先用 `read_lints` 快速扫描，可以在终端编译前修复大部分错误，减少编译-修复-重新编译的循环次数。

---

## 3. BUILD_VERIFY 阶段使用规范

### 3.1 前置 LSP 扫描（在终端编译命令之前）

BUILD_VERIFY 阶段的验证 Agent 在执行终端编译命令**之前**，先执行 `read_lints` 全项目扫描：

```
BUILD_VERIFY 执行流程（增强后）：

1. 前置 LSP 扫描:
   a) 调用 read_lints（指定对应平台的项目目录）
   b) 收集所有 error 级别诊断
   c) 将 LSP 发现的问题记录到验证报告的 "LSP 预扫描" 子章节
   
2. 终端编译命令（原有流程不变）:
   a) 后端: mvn compile -pl {模块列表} -am
   b) Web 端: tsc --noEmit + npm run build
   c) 小程序端: tsc --noEmit + taro build --type weapp

3. 结果交叉验证:
   a) 对比 LSP 诊断和终端编译的结果
   b) 两者共同发现的问题 → 高置信度，直接报告
   c) 仅 LSP 发现的问题 → 标注为 "LSP-only"，可能为误报，建议确认
   d) 仅终端编译发现的问题 → 标注为 "build-only"，通常为构建链特有问题
```

### 3.2 验证报告增强格式

在原有的编译验证章节中新增 LSP 预扫描子章节：

```markdown
### LSP 预扫描

**工具**: read_lints
**扫描范围**: {项目目录}
**结果**: ✅ 无 error / ❌ 发现 {N} 个 error
**warning 数量**: {M}

#### LSP 发现的问题（仅当有 error 时输出）

| # | 文件 | 行号 | 严重度 | 诊断信息 | 与编译结果一致 |
|---|------|------|--------|---------|-------------|
```

---

## 4. 各平台专项指南

### 4.1 TypeScript 平台（Web 端 / 小程序端）

**推荐的 `read_lints` 调用粒度**:

| 时机 | 调用方式 | 说明 |
|------|---------|------|
| 单文件写入后 | `read_lints(文件路径)` | 检查当前文件的类型错误 |
| 模块文件组完成后 | `read_lints(模块目录路径)` | 检查跨文件的导入/类型一致性 |
| Step 4 自检时 | `read_lints(项目根目录)` | 全项目扫描，替代或补充 `tsc --noEmit` |

**常见可即时修复的问题**:
- `TS2322`: Type 'X' is not assignable to type 'Y' → 修复类型声明
- `TS2339`: Property 'x' does not exist on type 'Y' → 补充类型定义或修正属性名
- `TS6133`: 'x' is declared but its value is never read → 移除未使用的导入/变量
- `TS2307`: Cannot find module 'x' → 检查导入路径或安装缺失依赖

### 4.2 Java 平台（后端）

**推荐的 `read_lints` 调用粒度**:

| 时机 | 调用方式 | 说明 |
|------|---------|------|
| 单个类文件写入后 | `read_lints(Java 文件路径)` | 检查编译错误、缺失 import |
| 同一包下多个类完成后 | `read_lints(包目录路径)` | 检查包内依赖关系 |
| 阶段三输出报告前 | `read_lints(模块 src 目录)` | 模块级全量扫描 |

**常见可即时修复的问题**:
- `Cannot resolve symbol 'XXX'` → 添加缺失的 import 语句或依赖
- `Incompatible types` → 修复类型转换或方法签名
- `Method does not override method from its superclass` → 修正 @Override 方法签名
- `Package does not exist` → 检查 pom.xml 依赖声明

### 4.3 修复循环上限

为避免陷入无限修复循环，设置修复次数限制：

| 规则 | 值 | 说明 |
|------|-----|------|
| 单文件最大修复尝试次数 | 3 | 同一文件连续 3 次 `read_lints` 仍有 error → 记录为待排查项，继续其他文件 |
| 模块级最大修复轮次 | 2 | 整个模块的 `read_lints` 修复循环不超过 2 轮 |
| 超限后处理 | 记录 + 继续 | 将未解决的 LSP error 记录到实现报告的风险部分，交由 BUILD_VERIFY 阶段的终端编译进一步确认 |

---

## 5. 诊断结果分级与处理策略

| 严重度 | 处理策略 | 是否阻断 |
|--------|---------|---------|
| **Error** | 立即修复，修复后重新检查确认 | ✅ 阻断当前文件实现 |
| **Warning** | 记录到工作日志/实现报告，Step 4 统一评估 | ❌ 不阻断 |
| **Information** | 仅记录，不需要处理 | ❌ 不阻断 |
| **Hint** | 忽略 | ❌ 不阻断 |

---

## 6. 规则引用声明

本规则文件被以下 Agent 引用：

| Agent | 引用方式 | 使用场景 |
|-------|---------|---------|
| `agents/web-developer.md` | 强制引用 | IMPLEMENT 阶段 Web 端开发中的实时诊断 |
| `agents/miniprogram-developer.md` | 强制引用 | IMPLEMENT 阶段小程序端开发中的实时诊断 |
| `agents/java-domain-developers/_template.md` | 强制引用 | IMPLEMENT 阶段 Java 后端开发中的实时诊断 |
| `agents/java-domain-developers/common-developer.md` | 强制引用 | IMPLEMENT 阶段公共模块开发中的实时诊断 |
| `agents/build-verifier.md` | 条件引用 | BUILD_VERIFY 阶段的前置 LSP 扫描 |
| `agents/build-verifiers/web-build-verifier.md` | 条件引用 | BUILD_VERIFY 阶段 Web 端前置 LSP 扫描 |
| `agents/build-verifiers/backend-build-verifier.md` | 条件引用 | BUILD_VERIFY 阶段后端前置 LSP 扫描 |
| `agents/build-verifiers/miniprogram-build-verifier.md` | 条件引用 | BUILD_VERIFY 阶段小程序端前置 LSP 扫描 |
