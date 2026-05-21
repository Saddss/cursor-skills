# My Cursor Agent Skills

我的 Cursor Agent skills 仓库，放在 `~/.cursor/skills/`。

每个子目录是一个 skill，里面必须有 `SKILL.md`。Cursor IDE / Cursor Agent 启动时会自动扫描这个目录加载所有 skills。

## 当前 skills

### 性能 / 推理（自有 + NVIDIA vendored）

- `model-perf-binary-search/` — 对 LLM 推理服务做 p50 e2e 延迟 SLO 下的最大 QPS 二分搜索，支持 Mode A（调参）/ Mode B（开启新 feature 后调优）。自有实现。
- `perf-analysis/` — 性能分析协调入口（瓶颈分类 + 结构化报告）。Vendored under Apache-2.0。
- `perf-nsight-systems/` — nsys CLI 系统级 profile + `.nsys-rep` 分析（含 7 个 references）。Vendored under Apache-2.0。
- `perf-nsight-compute-analysis/` — ncu kernel 级分析（SOL%、roofline、occupancy、`.ncu-rep`）。Vendored under Apache-2.0。
- `perf-optimization/` — 优化协调 playbook（specialist 路由、TileIR pipeline）。Vendored under Apache-2.0。
- `perf-workload-profiling/` — 手动 timing harness + NVTX 标注（训练 loop / standalone op）。Vendored under Apache-2.0。
- `perf-host-analysis/` — 检测 host/CPU overhead（Phase 1 二分判定 + Phase 2 NVTX 根因）。Vendored under Apache-2.0；含 `scripts/analyze_host_overhead.py` 帮助脚本。
- `perf-host-optimization/` — host overhead 治理（line_profiler + iterative profile-analyze-optimize-validate）。Vendored under Apache-2.0。
- `kernel-triton-writing/` — Triton kernel 编写 + verify/benchmark 脚本。Vendored under Apache-2.0。
- `kernel-cute-writing/` — CuTe DSL / CUTLASS kernel 编写。Vendored under Apache-2.0。

### 学习与文档（anthropics/skills vendored）

来自 [anthropics/skills](https://github.com/anthropics/skills)，正文 verbatim。Anthropic 专有许可证见各 skill 目录内 `LICENSE.txt` 及仓库根 `LICENSE-Anthropic-Skills.txt`。

- `pdf/` — 读/写/合并 PDF，表格提取，OCR，表单填充。
- `docx/` — Word 文档创建、编辑、tracked changes。
- `pptx/` — PPT 读取（markitdown）、编辑、从零生成。

### 代码梳理（spencerpauly/awesome-cursor-skills vendored）

- `parallel-exploring/` — 并行 launch explore subagent 快速扫大仓库。
- `codebase-onboarding/` — 并行 explore 后合成 onboarding 文档。

### 工程方法论（mattpocock/skills vendored, MIT）

来自 [mattpocock/skills](https://github.com/mattpocock/skills)，正文保持原样，仅做了 Cursor 适配（去掉 Claude 专有字段、补充推理/infra 触发词）。MIT 许可证见 `LICENSE-MIT-Matt-Pocock.txt`。

- `diagnose/` — 硬 bug / 性能回归的诊断闭环：复现 → 最小化 → 假设 → 插桩 → 修复 → 回归测试。与 `perf-analysis` 互补（diagnose 偏通用调试，perf-* 偏 GPU/profile）。
- `tdd/` — 红-绿-重构 TDD，含 `tests.md`、`mocking.md`、`deep-modules.md` 等 reference。
- `zoom-out/` — 拉高一层看模块/调用关系，适合初次进入 vLLM scheduler、KV cache 等陌生代码区。
- `handoff/` — 把长会话压缩成 handoff 文档，方便换 agent 继续 benchmark / profiling 任务。
- `grill-me/` — 轻量 grilling：在动手前把设计决策树走一遍。
- `grill-with-docs/` — 带文档的 grilling：同步更新 `CONTEXT.md` 和 ADR。
- `improve-codebase-architecture/` — 找 deepening 机会，输出 HTML architecture review。

所有 vendored skills 来自 [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM/tree/main/.claude/skills)（PR #12831，2026-04 合并），仅扩展了 front-matter 的 `description` 加入推理场景触发关键词，正文保持原样。上游版权声明保留在仓库根的 `LICENSE-Apache-2.0.txt`。

> TRT-LLM 专有的 references 文件（`perf-host-analysis/references/trtllm-nvtx-ranges.md` 和 `perf-host-optimization/references/hot-path-files.md`）在每个 SKILL.md 顶部都有显式说明，方法论通用，具体文件名 / NVTX label 需要按 vLLM / SGLang 替换。

## 在新机器上一键应用

### 一次性准备（任何新机器都要做一次）

如果新机器还没装 `gh` CLI：

```bash
mkdir -p ~/.local/bin && cd /tmp \
  && curl -fsSL -o gh.tgz "https://github.com/cli/cli/releases/download/v2.62.0/gh_2.62.0_linux_amd64.tar.gz" \
  && tar -xzf gh.tgz && cp gh_2.62.0_linux_amd64/bin/gh ~/.local/bin/gh \
  && chmod +x ~/.local/bin/gh && rm -rf gh.tgz gh_2.62.0_linux_amd64 \
  && grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc \
  && export PATH="$HOME/.local/bin:$PATH"
```

然后登录（按提示选 GitHub.com → HTTPS → Yes → Login with a web browser，浏览器输 device code）：

```bash
gh auth login
```

### 同步本仓库到 `~/.cursor/skills/`

```bash
# 如果 ~/.cursor/skills 已经有东西，先备份
[ -d ~/.cursor/skills ] && [ -n "$(ls -A ~/.cursor/skills 2>/dev/null)" ] \
  && mv ~/.cursor/skills ~/.cursor/skills.bak.$(date +%s)

gh repo clone Saddss/cursor-skills ~/.cursor/skills
```

重启 Cursor IDE / Cursor Agent，skills 就被加载了。

## 日常维护

修改 / 新增 skill 后，先跑校验再提交：

```bash
cd ~/.cursor/skills
bash scripts/validate-skills.sh
git add -A && git commit -m "describe change" && git push
```

在其他机器拉取最新：

```bash
cd ~/.cursor/skills && git pull
```

## 新建 skill 的最低骨架

```
~/.cursor/skills/<skill-name>/
├── SKILL.md          # 必需。开头是 --- YAML front-matter --- 含 name + description
└── scripts/          # 可选，放 helper 脚本
    └── *.py
```

`SKILL.md` 顶部的 YAML front-matter 是 Cursor Agent 判断"什么时候触发这个 skill"的关键，参考现有 `model-perf-binary-search/SKILL.md` 的写法即可。
