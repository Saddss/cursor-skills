# Rules 使用指南

本仓库 **7 条** 全局 Project Rule，源文件在 `~/.cursor/cursor-skills/rules/*.mdc`。安装后 Cursor 从 `~/.cursor/rules/` 加载（目录 symlink 到仓库 `rules/`）。

与 **Skills** 的区别：

| | Rules（`.mdc`） | Skills（`SKILL.md`） |
|--|-----------------|----------------------|
| 加载方式 | `alwaysApply: true`，**每条对话自动生效** | 按 description 匹配，或你 `@skill名` 点名 |
| 适用场景 | 行为约束、安全闸、Git 纪律 | 复杂工作流、脚本、领域 playbook |
| 示例 | 对外产物不添加工具协助归因 | `@perf-analysis` 跑完整 profiling 流程 |

**中文 skill 用法** → [SKILLS-GUIDE.md](SKILLS-GUIDE.md)

---

## 1. `no-ai-attribution`

**干什么**：commit、PR、issue、代码、注释、文档和 release note 不添加工具协助声明、署名、trailer、提示词或生成痕迹；技术内容确有需要时仍可正常使用相关技术名称。

**何时生效**：只要 agent 要 `git commit`、写 PR 描述、amend，都适用。

**你会看到的行为**：
- 不添加 `Co-authored-by`、`Generated-by`、`Assisted-by` 等工具归因
- commit message 和 PR 只写改动本身、技术原因、验证方式与风险
- 使用用户指定或 Git 已配置的真实身份，不使用工具或机器人身份
- 不遗留提示词、聊天记录、内部计划或带工具品牌的模板文本

**无需 @ 触发**（全局 rule）。

---

## 2. `git-feature-branch-before-commit`

**干什么**：默认在语义化 feature 分支提交；用户或仓库流程明确要求当前分支时遵循该要求。

**何时生效**：agent 准备 `git commit` 时。

**你会看到的行为**：
- 默认在 `main` 上有未提交改动 → 先创建 `fix/...` 等语义化分支
- 完成后汇报：分支名、commit hash、是否已 push

**无需 @ 触发**。

---

## 3. `confirm-before-destructive-operations`

**干什么**：可能影响运行中容器、未保存工作、共享资源或非临时数据的破坏性操作，必须确认具体目标和影响。

**覆盖操作**：终止进程、停止容器、删除文件或缓存、清理镜像/volume，以及重写 Git 工作树或历史等。

**你会看到的行为**：目标不明确时先说明现状与计划；已经明确指定对象和操作时不重复询问。

**无需 @ 触发**。

---

## 4. `surgical-coding-guidelines`

**干什么**：合理处理小歧义、极简实现、手术式 diff，并以可验证的成功标准完成任务。

| 原则 | 要点 |
|------|------|
| Think Before Coding | 小且可逆的歧义采用合理假设；实质歧义才询问 |
| Simplicity First | 不做超范围功能/抽象/防御性代码 |
| Surgical Changes | 不顺手改无关代码；只清理自己引入的死代码 |
| Goal-Driven Execution | 把任务写成可验证目标（含测试/check） |

**何时生效**：写代码、review、重构类对话（全局 rule）。

需要显式强调时仍可使用 `@karpathy-guidelines` skill；日常靠本 rule 自动生效。

---

## 5. `minimal-comments`

**干什么**：Inline comment 优先解释非显然的 WHY，删除代码复述并避免跨位置重复；公共 API、协议、单位和边界条件仍可解释必要的 WHAT。

**无需 @ 触发**。

---

## 6. `agent-behavior-and-language`

**干什么**：把本机 Agent 规则中的语言、快速失败、禁止伪测试、文件编辑和验证闭环要求应用到每次对话。

**何时生效**：所有任务自动生效。

**你会看到的行为**：
- 根据可核验材料作出判断，提供链接前先读取页面
- 错误在发生位置报告，不隐藏错误或添加无依据回退
- 不使用模拟对象、虚假数据和仅为通过测试而添加的绕过逻辑
- 不读取或写入 `/tmp`，不使用程序化脚本批量改写代码
- 修改后运行验证命令，说明未运行的检查和剩余风险

## 7. `global-agent-behavior`

**干什么**：读取当前机器的 `$CODEX_HOME/AGENTS.md`，让全局规则随本机配置变化。

**何时生效**：所有任务自动生效。

**无需 @ 触发**。

## 如何确认 Rules 已加载

1. Cursor **Settings → Rules**，应看到上述 7 条（名称来自 `description` frontmatter）。
2. 终端检查 symlink：
   ```bash
   readlink ~/.cursor/rules
   # 应输出：.../cursor-skills/rules
   ls ~/.cursor/cursor-skills/rules/
   ```

未看到时：执行 `bash ~/.cursor/cursor-skills/scripts/install.sh` 并重启 Cursor。

---

## 速查表

| 场景 | 对应 rule |
|------|-----------|
| 要 commit / 开 PR | `no-ai-attribution` + `git-feature-branch-before-commit` |
| 要 kill 进程 / 删容器 / 清磁盘 | `confirm-before-destructive-operations` |
| 避免过度设计、乱改无关代码 | `surgical-coding-guidelines` |
| 控制注释质量 | `minimal-comments` |
| Agent 行为和语言 | `agent-behavior-and-language` + `global-agent-behavior` |
| 想主动强调 Karpathy 原则 | 可额外 `@karpathy-guidelines`（skill） |
