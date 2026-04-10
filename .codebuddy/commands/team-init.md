---
name: team-init
description: 初始化当前项目的 AI Team 配置。连接团队知识仓库，关联业务领域和技术栈，启用跨项目团队知识共享。
---

# 项目 AI Team 初始化

## 指令概述

本指令用于在当前项目中初始化 `.ai-team/project.yaml` 配置文件，建立项目与**团队共享知识仓库**的连接。

**触发方式**：
1. 用户手动执行 `/team-init`
2. `/flow-run` 的 INIT 阶段检测到缺少配置时引导执行

**核心原则**：初始化只创建项目级配置文件和克隆知识仓库，不修改知识仓库中的已有内容。

---

## 执行流程

### Step 1：检查前置条件

```
1. 检查 ~/.ai-team/ 目录是否存在
   - 不存在 → 自动创建个人偏好目录（~/.ai-team/preferences/）
   - 已存在 → 继续

2. 检查 .ai-team/project.yaml 是否已存在
   - 已存在 → 展示当前配置，询问是否重新配置
   - 不存在 → 继续创建
```

### Step 2：连接团队知识仓库

使用 `ask_followup_question` 引导用户配置知识仓库：

```
📚 团队知识仓库配置

ai-team 使用独立 Git 仓库作为团队共享知识库。
所有团队成员通过此仓库共建和消费知识。

请提供团队知识仓库的 Git 地址：
  示例: git@github.com:your-team/team-knowledge.git

如果尚未创建，可选择：
  ➕ 创建新的知识仓库（将在本地初始化并提供推送指引）
  ⏭️ 暂不配置知识仓库（可稍后通过 /team-init 补充）
```

**已有仓库**：
1. 克隆到 `~/.ai-team/team-knowledge`（或用户指定路径）
   ```bash
   git clone {repo_url} ~/.ai-team/team-knowledge
   ```
2. 验证仓库结构（检查 `.knowledge-config.yaml` 是否存在）
3. 读取 `.knowledge-config.yaml` 获取团队信息

**创建新仓库**：
1. 在 `~/.ai-team/team-knowledge` 下初始化目录结构：
   ```
   team-knowledge/
   ├── .knowledge-config.yaml
   ├── KNOWLEDGE.md
   ├── team-conventions/
   │   ├── coding-standards.md
   │   ├── commit-conventions.md
   │   └── log.md
   ├── tech-wiki/
   │   ├── index.md / index.json / log.md
   │   ├── languages/ / frameworks/ / patterns/ / devops/ / anti-patterns/
   ├── biz-wiki/
   │   ├── domains.yaml
   │   └── _cross-domain/cross-domain-graph.md
   └── contributions/
       ├── pending/
       └── conflicts/
   ```
2. 初始化 Git 仓库
   ```bash
   cd ~/.ai-team/team-knowledge
   git init
   git add -A
   git commit -m "init: team knowledge repository"
   ```
3. 提示用户添加远程仓库并推送：
   ```
   💡 本地知识仓库已初始化，请执行以下命令推送到远程：
   cd ~/.ai-team/team-knowledge
   git remote add origin {your-repo-url}
   git push -u origin main
   
   然后将此仓库地址告知团队其他成员，让他们也执行 /team-init 连接。
   ```

### Step 3：仓库绑定（扫描→确认→持久化）

> **核心原则**：扫描只是"建议"，最终哪些目录作为 repo 由用户确认。确认后写入 `project.yaml` 的 `repos[]`，后续工作流直接读取配置，不再重复扫描。

**3a. 自动扫描（仅首次，生成候选列表）**：

> **⚠️ 排除目录**：`.codebuddy/`、`node_modules/`、`.ai-team-install/`、`.ai-team/`、`docs/`、`.git/`、`dist/`、`build/`、`target/`

1. 扫描工作区一级子目录中包含 `.git/` 的目录（排除上述列表）
2. 同时检查工作区根目录是否直接包含 `.git/`
3. 对每个候选目录检测技术栈：
   - `pom.xml` / `build.gradle` → Java
   - `package.json` + 检查 dependencies → React/Vue/Taro/Next.js 等
   - `go.mod` → Go
   - `requirements.txt` / `pyproject.toml` → Python
4. 推断仓库类型：backend / frontend / miniprogram / fullstack / common
5. 推断编译命令：Maven → `mvn clean package -DskipTests`、Node.js → `npm run build` 等

**3b. 用户确认仓库列表**：

使用 `ask_followup_question` 展示扫描结果，**用户逐个确认或排除**：

```
📁 工作区仓库扫描结果

扫描到以下 Git 仓库，请确认哪些是本项目的业务代码仓库：

  ✅ 1. ad-service/           后端 | Java, Spring Boot | mvn clean package
  ✅ 2. creative-service/     后端 | Java, Spring Boot | mvn clean package
  ✅ 3. ad-frontend/          前端 | TypeScript, React | npm run build
  ❓ 4. infra-scripts/        未识别 | Shell | 无编译命令

操作：
  - 输入要排除的序号（如 "排除 4"）
  - 输入要修正的信息（如 "3 类型改为 fullstack"）
  - 输入 "确认" 完成绑定
```

**3c. 持久化到 project.yaml**：

用户确认后，将 repos[] 写入 `.ai-team/project.yaml`（见 Step 4）。**后续 `/flow-run` 的 INIT 阶段直接读取 `project.yaml` 中的 `repos[]`，不再重复扫描。**

### Step 4：收集项目信息并创建 project.yaml

基于 Step 3 确认的仓库列表，聚合技术栈信息：

```
🤖 项目信息汇总：

项目名称: {从工作区目录名推断}
绑定仓库: {N} 个
技术栈（从已确认仓库聚合）:
  后端: [Java, Spring Boot]
  前端: [TypeScript, React]

请确认项目名称，或输入修正。

另外，请选择项目关联的业务领域：
```

展示 `{knowledge-repo}/biz-wiki/domains.yaml` 中已有的领域列表，加上"创建新领域"选项：

```
选项:
  - "电商 (ecommerce) — 已有 15 个实体、23 条规则"
  - "支付 (payment) — 已有 8 个实体、12 条规则"
  - "➕ 创建新业务领域"
  - "⏭️ 暂不关联业务领域"
```

### Step 5：创建新领域（如用户选择）

如果用户选择"创建新业务领域"：
1. 询问领域 ID（英文，如 `logistics`）和中文名（如 "物流"）
2. 在 `{knowledge-repo}/biz-wiki/` 下创建领域目录结构：
   ```
   {knowledge-repo}/biz-wiki/{domain}/
   ├── index.md
   ├── index.json
   ├── log.md
   ├── entities/
   ├── relations/
   │   └── entity-graph.md
   ├── rules/
   ├── flows/
   └── pitfalls/
   ```
3. 在 `{knowledge-repo}/biz-wiki/domains.yaml` 中注册新领域
4. 提交到知识仓库：
   ```bash
   cd {knowledge-repo}
   git add biz-wiki/{domain}/
   git commit -m "domain: create {domain} ({中文名})"
   git push origin main
   ```

### Step 6：个人身份确认（注册前置条件）

> **必须在注册前完成**——成员注册依赖姓名，archiver 阶段七的贡献分支和追踪也依赖姓名。

1. 检查 `~/.ai-team/preferences/` 目录是否存在
   - 不存在 → 自动创建
2. 检查 `~/.ai-team/preferences/profile.yaml` 的 `name` 字段：
   - 如果为空或文件不存在 → 使用 `ask_followup_question` 引导填写：
     ```
     👤 首次使用 ai-team，请提供个人信息（用于知识贡献追踪）：
     
     姓名（将显示在知识条目的贡献者中）: ___
     角色（如 Full-Stack Developer）: ___
     ```
   - 写入 `~/.ai-team/preferences/profile.yaml`：
     ```yaml
     name: "{用户输入}"
     role: "{用户输入}"
     updated_at: "{ISO-8601}"
     ```
   - 如果 `name` 已有值 → 跳过，直接使用已有值

> 个人偏好始终保存在本地 `~/.ai-team/preferences/`，不上传到团队知识仓库。

### Step 7：注册团队成员

使用 Step 6 确认的 `name` 作为成员标识，在知识仓库中注册：

1. **读取** `{knowledge-repo}/.knowledge-config.yaml` 的 `members` 列表

2. **判断角色**：
   - 如果 `members` 列表为空（首个成员 = 仓库创建者）→ 角色设为 `maintainer`
   - 如果 `members` 列表非空且当前 `name` 不在列表中 → 角色设为 `contributor`
   - 如果当前 `name` 已在列表中 → 跳过注册，使用已有角色

3. **写入成员信息**（追加到 `members` 列表）：
   ```yaml
   members:
     # ... 已有成员 ...
     - name: "{profile.yaml 中的 name}"
       role: "maintainer"  # 或 "contributor"
       joined: "{ISO-8601}"
       registered_from_project: "{project_name}"
   ```

4. **提交并推送**：
   ```bash
   cd {knowledge-repo}
   git add .knowledge-config.yaml
   git commit -m "member: {name} joined as {role}"
   git push origin main
   ```

5. **确认**：
   ```
   👥 团队注册完成！
   角色: {maintainer/contributor}
   团队成员数: {members.length}
   ```

> **注意**：如果 git push 因并发冲突失败（另一个成员同时注册），自动 `git pull --rebase` 后重试。members 列表是追加式的，不会产生内容冲突。

### Step 8：完成确认

```
✅ AI Team 初始化完成！

📁 项目配置: .ai-team/project.yaml
📚 团队知识仓库: {knowledge_repo.url}（本地: {knowledge_repo.local_path}）
🧠 业务领域: {domain 中文名}（{entity_count} 个实体、{rule_count} 条规则）
🔧 技术栈: {tech_stack 摘要}
👤 个人偏好: {已配置/待配置}
👥 团队角色: {maintainer/contributor}

接下来你可以：
  - /flow-run — 启动需求开发工作流（知识会自动注入）
  - /flow-import — 导入历史项目知识到团队知识库
```

---

## 注意事项

1. `/team-init` **不修改知识仓库中的已有内容**（除非创建新领域或注册成员）
2. 新创建的业务领域是空的，需要通过 `/flow-import` 或工作流 ARCHIVE 沉淀知识
3. 一个项目可以关联到多个业务领域（高级场景，通过手动编辑 project.yaml 的 domain 字段为数组实现）
4. `/team-init` 可以多次执行（重新配置）
5. 团队知识仓库默认克隆到 `~/.ai-team/team-knowledge`，可通过 `knowledge_repo.local_path` 自定义
6. 个人偏好（`~/.ai-team/preferences/`）始终为本地私有，不会被推送到团队知识仓库
