# Rules 使用指南

本仓库 **4 条** 全局 Project Rule，源文件在 `~/.cursor/cursor-skills/rules/*.mdc`。安装后 Cursor 从 `~/.cursor/rules/` 加载（目录 symlink 到仓库 `rules/`）。

与 **Skills** 的区别：

| | Rules（`.mdc`） | Skills（`SKILL.md`） |
|--|-----------------|----------------------|
| 加载方式 | `alwaysApply: true`，**每条对话自动生效** | 按 description 匹配，或你 `@skill名` 点名 |
| 适用场景 | 行为约束、安全闸、Git 纪律 | 复杂工作流、脚本、领域 playbook |
| 示例 | 禁止 commit 带 Cursor 署名 | `@perf-analysis` 跑完整 profiling 流程 |

**中文 skill 用法** → [SKILLS-GUIDE.md](SKILLS-GUIDE.md)

---

## 1. `no-cursor-in-commits`

**干什么**：创建或改写 git commit / PR 时，不得出现 Cursor 相关署名、trailer 或正文里的 cursor 字样。

**何时生效**：只要 agent 要 `git commit`、写 PR 描述、amend，都适用。

**你会看到的行为**：
- 不用 `Co-authored-by: Cursor` 等 trailer
- commit message 只写改动本身；完成后可用 `git log -1 --format=%B` 自检
- 未指定 author 时会先问你，不用占位身份

**无需 @ 触发**（全局 rule）。

---

## 2. `git-feature-branch-before-commit`

**干什么**：在用户仓库里提交前，必须先离开 `main`/`master`，使用有语义的 feature 分支名。

**何时生效**：agent 准备 `git commit` 时。

**你会看到的行为**：
- 在 `main` 上有未提交改动 → 先 `git checkout -b fix/...`
- 完成后汇报：分支名、commit hash、是否已 push

**无需 @ 触发**。

---

## 3. `confirm-before-kill-or-cleanup`

**干什么**：在 **有容器运行** 或 **磁盘空间紧张** 时，任何 kill 进程、停容器、`rm` 释盘必须先征得你同意。

**触发条件（任一）**：
- `docker ps` 等非空 / compose 服务在跑
- 磁盘不足或任务因空间失败

**覆盖操作**：`kill`/`pkill`、`docker stop/rm/compose down`、`rm -rf`、清 cache/镜像/volume 等。

**你会看到的行为**：先说明现状与计划 → 等你明确同意 → 才执行；可建议替代方案但不擅自决定。

**无需 @ 触发**。

---

## 4. `karpathy-guidelines`

**干什么**：[Karpathy 四条原则](https://github.com/multica-ai/andrej-karpathy-skills)——先想清楚、极简实现、手术式 diff、可验证的成功标准。

| 原则 | 要点 |
|------|------|
| Think Before Coding | 说明假设；歧义时列出选项；不清楚就先问 |
| Simplicity First | 不做超范围功能/抽象/防御性代码 |
| Surgical Changes | 不顺手改无关代码；只清理自己引入的死代码 |
| Goal-Driven Execution | 把任务写成可验证目标（含测试/check） |

**何时生效**：写代码、review、重构类对话（全局 rule）。

**与同名 skill 的关系**：`skills/karpathy-guidelines/` 内容相同，可 `@karpathy-guidelines` 在长任务开头**强调**一次；日常靠 rule 自动生效即可。

---

## 如何确认 Rules 已加载

1. Cursor **Settings → Rules**，应看到上述 4 条（名称来自 `description` frontmatter）。
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
| 要 commit / 开 PR | `no-cursor-in-commits` + `git-feature-branch-before-commit` |
| 要 kill 进程 / 删容器 / 清磁盘 | `confirm-before-kill-or-cleanup` |
| 怕 agent 过度设计、乱改无关代码 | `karpathy-guidelines` |
| 想主动强调 Karpathy 原则 | 可额外 `@karpathy-guidelines`（skill） |
