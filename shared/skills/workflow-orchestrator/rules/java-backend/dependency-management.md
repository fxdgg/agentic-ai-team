---
description: 第三方依赖引入与版本管理规范。当任务涉及引入新依赖、修改 pom.xml、升级版本、添加第三方 SDK 时加载此规则。
alwaysApply: false
enabled: true
---

# 第三方依赖引入与版本管理规范

> 本规则覆盖：Maven 依赖引入流程、版本验证、版本统一管理、依赖冲突排查、第三方 SDK 引入注意事项。

## 1. 总体原则
- **CRITICAL**: 引入任何外部依赖前，必须先到 Maven 中央仓库（https://repo.maven.apache.org/maven2/ 或 https://mvnrepository.com）验证所指定的 groupId、artifactId 和版本号确实存在。
- **CRITICAL**: 禁止凭印象或猜测填写版本号，必须以 Maven 仓库实际发布版本为准。
- **REQUIRED**: 引入新依赖时必须评估其必要性，避免引入过多不必要的依赖。

## 2. 版本验证流程
- **CRITICAL**: 在 pom.xml 中添加新依赖前，执行以下验证步骤：
  1. 在 Maven 中央仓库确认该 artifactId 存在。
  2. 确认指定版本号已正式发布（非 SNAPSHOT、非撤回版本）。
  3. 确认该版本与当前项目的 Java 版本、Spring Boot 版本兼容。
- **CRITICAL**: 验证 URL 格式：`https://repo.maven.apache.org/maven2/{groupId路径}/{artifactId}/{version}/`，确认页面可访问。

## 3. 同厂商多模块 SDK 版本独立管理
- **CRITICAL**: 同一厂商的不同服务 SDK（如腾讯云的 `tencentcloud-sdk-java-sms`、`tencentcloud-sdk-java-captcha` 等），其版本号**不一定同步发布**，禁止简单地共用同一个版本变量管理。
- **REQUIRED**: 每个 SDK 模块必须独立确认可用版本，分别在 `<properties>` 中定义各自的版本变量。
- 示例：
  ```xml
  <properties>
      <tencentcloud-sdk-captcha.version>3.1.1287</tencentcloud-sdk-captcha.version>
      <tencentcloud-sdk-sms.version>3.1.1230</tencentcloud-sdk-sms.version>
  </properties>
  ```
- **CRITICAL**: 当统一版本变量出现编译错误（如 `程序包不存在`）时，优先排查该版本号在对应 artifactId 下是否真实存在。

## 4. 版本统一管理规范
- **REQUIRED**: 所有第三方依赖版本号必须在父 POM 的 `<properties>` 或 `<dependencyManagement>` 中统一定义。
- **CRITICAL**: 禁止在子模块 pom.xml 中直接硬编码版本号。
- **REQUIRED**: Spring Boot / Spring Cloud / Spring Cloud Alibaba 等框架依赖通过 BOM（Bill of Materials）统一管理。
- **RECOMMENDED**: 对于同一厂商可统一版本的依赖，使用 BOM 方式引入（如果厂商提供了 BOM）。

## 5. 依赖范围（Scope）规范
- **REQUIRED**: 合理使用依赖范围：
  - `compile`（默认）：运行时必需的依赖。
  - `provided`：容器/框架已提供的依赖（如 Lombok、Servlet API）。
  - `runtime`：仅运行时需要（如 MySQL 驱动）。
  - `test`：仅测试使用。
- **CRITICAL**: 禁止将仅测试使用的依赖设为 `compile` 范围。

## 6. 依赖冲突与排除
- **REQUIRED**: 引入新依赖后，执行 `mvn dependency:tree` 检查是否存在版本冲突。
- **REQUIRED**: 发现冲突时，通过 `<exclusions>` 排除低版本或冲突依赖，并在注释中说明原因。
- **CRITICAL**: 禁止忽略依赖冲突警告。

## 7. Maven 本地缓存问题处理
- **REQUIRED**: 当依赖下载失败后修正了版本号，若仍无法下载，需清理本地 Maven 仓库中对应目录下的 `.lastUpdated` 失败标记文件。
- 清理命令示例：
  ```bash
  # 清理指定依赖的失败缓存
  rm -rf ~/.m2/repository/{groupId路径}/{artifactId}/{version}
  
  # 批量清理所有失败标记
  find ~/.m2/repository -name "*.lastUpdated" -delete
  ```
- **REQUIRED**: 清理后重新执行 `mvn clean install -U` 强制更新依赖。

## 8. 安全与合规
- **REQUIRED**: 引入新依赖前，检查是否存在已知安全漏洞（可借助 OWASP Dependency-Check 等工具）。
- **REQUIRED**: 关注依赖的开源许可证，确保与项目许可兼容。
- **RECOMMENDED**: 优先选择活跃维护、社区活跃的依赖库。

## 9. BOM 托管依赖的 API 兼容性检查

- **CRITICAL**: 当使用 Spring Boot BOM 或其他 BOM 托管的第三方库 API 时，禁止直接基于"最新版 API 知识"编写代码。必须先确认项目中该库的实际版本：

  ```bash
  # 确认 BOM 解析出的实际版本
  mvn dependency:tree -Dincludes={groupId}:{artifactId} -pl {module}
  ```

- **CRITICAL**: 确认实际版本后，必须验证所使用的 API 方法在该版本中存在。特别注意以下高风险库（API 跨版本变化大）：
  - `elasticsearch-java`（co.elastic.clients）— 8.x 各小版本间 API 差异显著（如 `RangeQuery.Builder.number()` 仅 8.14+ 存在）
  - `spring-security`（6.x 相对 5.x 有大量废弃/移除 API）
  - `spring-data-*`（接口签名可能跨版本变更）

- **RECOMMENDED**: 对于不确定版本兼容性的 API 调用，优先使用各库长期稳定的通用 API，避免使用仅在最新版本才引入的语法糖或 typed API。

- **REQUIRED**: 项目核心依赖版本参考（以根 `pom.xml` 中 `<properties>` 和 BOM 声明为准）：
  | 组件 | 版本 | 管理方式 |
  |------|------|---------|
  | Spring Boot | 3.3.7 | parent BOM |
  | Spring Cloud | 2023.0.3 | BOM import |
  | Spring Cloud Alibaba | 2023.0.1.2 | BOM import |
  | Java | 21 | properties |
  | MyBatis Plus | 3.5.9 | BOM import |
  | Auth0 JWT | 4.4.0 | dependencyManagement |
  | FastJSON2 | 2.0.47 | dependencyManagement |
  | EasyExcel | 4.0.3 | dependencyManagement |
  | 腾讯云 COS SDK | 5.6.227 | dependencyManagement |
