# My Cursor Agent Skills & Rules

我的 Cursor 配置仓库：[**Saddss/cursor-skills**](https://github.com/Saddss/cursor-skills)

| 文档 | 内容 |
|------|------|
| [SKILLS-GUIDE.md](SKILLS-GUIDE.md) | **38** 个 skill：触发方式、示例、速查表 |
| [RULES-GUIDE.md](RULES-GUIDE.md) | **4** 条 rule：作用、与 skill 区别、速查表 |

---

## 快速开始（新机器）

**1. 安装 gh 并登录**（若尚未安装，见下方 [一次性准备](#一次性准备gh)）。

**2. Clone 并链到 Cursor 目录**

```bash
gh repo clone Saddss/cursor-skills ~/.cursor/cursor-skills
bash ~/.cursor/cursor-skills/scripts/install.sh
```

`install.sh` 会创建两个**同级** symlink（与 Cursor 目录模型一致）：

```text
~/.cursor/skills  →  cursor-skills/skills
~/.cursor/rules   →  cursor-skills/rules
```

**3. 重启 Cursor**（或新开 Agent 对话）。

**4. 验证**

```bash
readlink ~/.cursor/skills ~/.cursor/rules
ls ~/.cursor/cursor-skills/skills | wc -l   # 38
ls ~/.cursor/cursor-skills/rules/*.mdc      # 4
```

- **Settings → Rules**：应看到 4 条全局 rule（自动 `alwaysApply`）。
- 对话里试：`@model-perf-binary-search 简述你能做什么` 或 `@perf-analysis`。

**5. 日常改配置**

```bash
cd ~/.cursor/cursor-skills
# 编辑 skills/<name>/ 或 rules/*.mdc
git add -A && git commit -m "..." && git push
```

其他机器：`git pull` 即可（symlink 指向仓库，无需重复 `install.sh`，除非链接断了）。

---

## 从旧版布局升级（重构前已在用的机器）

旧版：`~/.cursor/skills` **就是 git 根**，skill 目录在仓库顶层。  
新版：git 根为 `~/.cursor/cursor-skills/`，其下 **`skills/` 与 `rules/` 同级**。

**不要**在旧路径上只 `git pull`（会导致 skill 进 `skills/` 子目录，而 Cursor 仍扫 `~/.cursor/skills/*`，路径对不上）。

**推荐：一条迁移脚本**

```bash
# 需已 push 含 skills/ + rules/ 的最新 main 到 GitHub
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Saddss/cursor-skills/main/scripts/migrate-from-legacy-layout.sh)" 2>/dev/null \
  || bash ~/.cursor/cursor-skills/scripts/migrate-from-legacy-layout.sh
```

或本机已有 clone 时：

```bash
bash ~/.cursor/cursor-skills/scripts/migrate-from-legacy-layout.sh
```

脚本会：把旧 `~/.cursor/skills`（若为 git 根）改名为 `cursor-skills` → `git pull` → 运行 `install.sh`。

**手动迁移（无脚本时）**

```bash
# 1) 备份旧仓库（若在 ~/.cursor/skills 且含 .git）
mv ~/.cursor/skills ~/.cursor/cursor-skills

# 2) 拉最新结构
cd ~/.cursor/cursor-skills && git fetch origin && git pull

# 3) 安装 symlink（若 ~/.cursor/skills 已被 mv 走，install 会新建链接）
bash scripts/install.sh

# 4) 重启 Cursor
```

本地有未提交改动时，先在旧目录 `git stash`，迁移后再 `git stash pop`。

---

## 仓库布局

```text
~/.cursor/
├── cursor-skills/          ← git clone 根目录（在这里 commit）
│   ├── skills/             ← 38 个 skill
│   ├── rules/              ← 4 个 .mdc
│   ├── scripts/
│   │   ├── install.sh
│   │   ├── migrate-from-legacy-layout.sh
│   │   ├── validate-skills.sh
│   │   └── validate-rules.sh
│   ├── README.md           ← 本文件
│   ├── SKILLS-GUIDE.md
│   └── RULES-GUIDE.md
├── skills  → cursor-skills/skills
└── rules   → cursor-skills/rules
```

---

## 当前 rules（4 个）

详见 [RULES-GUIDE.md](RULES-GUIDE.md)。

| 文件 | 作用 |
|------|------|
| `rules/no-cursor-in-commits.mdc` | commit/PR 禁止 Cursor 署名与 trailer |
| `rules/git-feature-branch-before-commit.mdc` | 提交前必须先切 feature 分支 |
| `rules/confirm-before-kill-or-cleanup.mdc` | 有容器或磁盘紧张时，kill/清理须先征得同意 |
| `rules/karpathy-guidelines.mdc` | Karpathy 四条：先想清楚、极简、手术式改动、可验证目标 |

---

## 当前 skills（38 个）

详见 [SKILLS-GUIDE.md](SKILLS-GUIDE.md)（含示例与速查表）。

### Serving benchmark & 容量（自有 + BBuf）

- `model-perf-binary-search/` — 已知 serve 配置下，p50 e2e SLO 的最大 QPS 二分搜索（Mode A 调参 / Mode B feature 对比）。**自有实现。**
- `pp-separation-benchmark/` — 对比统一缓存感知基线与截断/未截断请求冷热分池，扫描 GPU 配比并验证 QPS、分池 SLO、命中率和负载均衡。**自有实现。**
- `llm-serving-auto-benchmark/` — 跨框架（SGLang/vLLM/TRT-LLM）公平 benchmark + search_space 扫 launch 参数；带 cookbook YAML。**BBuf vendored。**
- `llm-serving-capacity-planner/` — 解析 serving 启动 log → KV pool / CUDA graph / max concurrency。**BBuf vendored。**
- `model-compute-simulation/` — 从 model config 估 FLOPs/MFU、算子 shape、TP/EP what-if。**BBuf vendored。**

典型链路：`llm-serving-auto-benchmark` → `model-perf-binary-search` → `llm-serving-capacity-planner`；验证冷热分池时使用 `pp-separation-benchmark`。

### Profiler & 性能（NVIDIA + BBuf）

- `perf-analysis/`, `perf-nsight-systems/`, `perf-nsight-compute-analysis/`, `perf-optimization/`, `perf-workload-profiling/`, `perf-host-analysis/`, `perf-host-optimization/`, `llm-torch-profiler-analysis/`, `llm-pipeline-analysis/`

典型链路：慢 → `perf-analysis` → nsys / ncu / torch-profiler → `llm-pipeline-analysis`。

### 算子（NVIDIA）

- `kernel-triton-writing/`, `kernel-cute-writing/`

### 代码梳理（spencerpauly）

- `parallel-exploring/`, `codebase-onboarding/`

### 工程方法论（mattpocock + superpowers/ECC/Every, MIT）

- `search-first/`, `brainstorming/`, `writing-plans/`, `executing-plans/`, `simplify-code/`, `verification-before-completion/`, `diagnose/`, `tdd/`, `handoff/`, `grill-with-docs/`, `improve-codebase-architecture/`, `setup-matt-pocock-skills/`, `to-issues/`, `prototype/`, `review/`, `karpathy-guidelines/`

典型链路：`search-first` → `brainstorming` → `writing-plans` → `executing-plans` + `tdd` → `review` + `simplify-code` → `verification-before-completion`。

> `karpathy-guidelines` 同时有全局 **rule**（自动生效）；skill 用于 `@` 强调，见 [RULES-GUIDE.md](RULES-GUIDE.md)。

### 学习与文档（anthropics）

- `pdf/`, `docx/`, `pptx/`

### 学术作图（自有）

- `academic-figure-workflow/` — 论文 SVG 机理/架构图，包含论证合同、几何门禁、600 dpi 预览、DOCX/WPS 插入验收和已知失败模式。

## 已移除的低价值 / 冗余 skill

| 移除 | 原因 |
|------|------|
| `grill-me` | `grill-with-docs` 的严格子集 |
| `zoom-out` | 已被 `codebase-onboarding` + `parallel-exploring` 覆盖 |

## 许可证

- NVIDIA skills：`LICENSE-Apache-2.0.txt`
- mattpocock：`LICENSE-MIT-Matt-Pocock.txt`
- Superpowers：`LICENSE-MIT-Superpowers.txt`
- ECC：`LICENSE-MIT-ECC.txt`
- EveryInc：`LICENSE-MIT-EveryInc.txt`
- anthropics：各 skill 内 `LICENSE.txt` + `LICENSE-Anthropic-Skills.txt`
- BBuf：上游 [BBuf/AI-Infra-Auto-Driven-SKILLS](https://github.com/BBuf/AI-Infra-Auto-Driven-SKILLS)
- Karpathy guidelines：MIT（[andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)）

## 一次性准备（gh）

```bash
mkdir -p ~/.local/bin && cd /tmp \
  && curl -fsSL -o gh.tgz "https://github.com/cli/cli/releases/download/v2.62.0/gh_2.62.0_linux_amd64.tar.gz" \
  && tar -xzf gh.tgz && cp gh_2.62.0_linux_amd64/bin/gh ~/.local/bin/gh \
  && chmod +x ~/.local/bin/gh && rm -rf gh.tgz gh_2.62.0_linux_amd64 \
  && grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc \
  && export PATH="$HOME/.local/bin:$PATH"

gh auth login
```

## 日常维护

```bash
cd ~/.cursor/cursor-skills
bash scripts/validate-skills.sh
bash scripts/validate-rules.sh
git add -A && git commit -m "describe change" && git push
```

## 新建 skill 骨架

```text
~/.cursor/cursor-skills/skills/<skill-name>/
├── SKILL.md          # frontmatter: name + description
└── scripts/          # 可选
```

参考 `skills/model-perf-binary-search/SKILL.md`。
