# 回退机制规则（按需加载）

> **加载时机**: 当用户在"总结确认"步骤选择"回退"时，编排器加载本文件。BUILD_VERIFY 阶段的精细回退另见 `phases/build-verify-rules.md`。

---

## 1. 通用回退规则

- 只能回退到**上一阶段**（不支持跨阶段回退）
- 回退时**必须删除当前阶段及所有后续阶段的产物文件**（BUILD_VERIFY 阶段有特殊规则，见 `phases/build-verify-rules.md`）
- 回退操作记录在 `state.json` 的 `rollbackLog` 中
- 回退后重新从目标阶段的"预览"步骤开始

## 2. 回退执行流程（通用）

```
1. 用户在"总结确认"步骤选择"回退"
2. 确认回退操作（二次确认，因为会删除产物）
3. 记录回退日志到 state.json.rollbackLog
4. 删除当前阶段及后续阶段的所有产物文件
5. 更新 state.json.currentPhase 为上一阶段
6. 更新 phaseHistory 中相关条目的 status 为 "rolled_back"
7. 从目标阶段的"预览"步骤重新开始
```

## 3. 产物删除映射

回退时按阶段删除对应产物：

| 回退目标阶段 | 删除的产物 |
|-------------|-----------|
| ANALYSE_PRODUCT | analysis/ 下所有文件 + architecture/ + implementation/ + testing/ |
| ANALYSE_TECH | analysis/tech-* 文件 + architecture/ + implementation/ + testing/ |
| ARCHITECT_BACKEND | architecture/ + implementation/ + testing/ |
| ARCHITECT_FRONTEND | architecture/ 下前端目录 + implementation/ 下前端目录 + testing/ |
| IMPLEMENT | implementation/ + testing/ |
| BUILD_VERIFY → IMPLEMENT | **仅删除**失败平台的 report 中「编译验证」章节（见 `phases/build-verify-rules.md`）+ testing/；已通过平台的报告保留 |
| E2E_VERIFY | implementation/ 下各 report 的「端到端链路验证」章节 + testing/ |
| TEST | testing/ |
