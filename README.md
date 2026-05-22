# My Cursor Agent Skills

我的 Cursor Agent skills 仓库，放在 `~/.cursor/skills/`。

每个子目录是一个 skill，里面必须有 `SKILL.md`。Cursor IDE / Cursor Agent 启动时会自动扫描这个目录加载所有 skills。

## 当前 skills（25 个）

### Serving benchmark & 容量（自有 + BBuf）

- `model-perf-binary-search/` — 已知 serve 配置下，p50 e2e SLO 的最大 QPS 二分搜索（Mode A 调参 / Mode B feature 对比）。**自有实现。**
- `llm-serving-auto-benchmark/` — 跨框架（SGLang/vLLM/TRT-LLM）公平 benchmark + search_space 扫 launch 参数；带 cookbook YAML。**BBuf vendored。**
- `llm-serving-capacity-planner/` — 解析 serving 启动 log → KV pool / CUDA graph / max concurrency。**BBuf vendored。**
- `model-compute-simulation/` — 从 model config 估 FLOPs/MFU、算子 shape、TP/EP what-if。**BBuf vendored。**

典型链路：`llm-serving-auto-benchmark`（选框架+命令）→ `model-perf-binary-search`（SLO 下 QPS）→ `llm-serving-capacity-planner`（解释并发上限）。

### Profiler & 性能（NVIDIA + BBuf）

- `perf-analysis/` — 性能分析总入口（瓶颈分类 + 结构化报告）。NVIDIA Apache-2.0。
- `perf-nsight-systems/` — nsys 系统 timeline + `.nsys-rep`。NVIDIA。
- `perf-nsight-compute-analysis/` — ncu kernel SOL / roofline / `.ncu-rep`。NVIDIA。
- `perf-optimization/` — 优化协调与 specialist 路由（已映射到本 repo 内 skill）。NVIDIA。
- `perf-workload-profiling/` — 手动 timing harness + NVTX。NVIDIA。
- `perf-host-analysis/` — host/CPU overhead 检测（Phase 1/2）。NVIDIA。
- `perf-host-optimization/` — host overhead 治理（line_profiler 迭代）。NVIDIA。
- `llm-torch-profiler-analysis/` — torch.profiler 三表（kernel / overlap / fusion），prefill/decode 分离。**BBuf vendored。**
- `llm-pipeline-analysis/` — trace 层 forward/layer 级 drill-down。**BBuf vendored。**

典型链路：慢 → `perf-analysis` → nsys / ncu / torch-profiler 三选一 → `llm-pipeline-analysis` 细拆 layer。

### 算子（NVIDIA）

- `kernel-triton-writing/` — Triton 写核 + verify/benchmark 脚本。
- `kernel-cute-writing/` — CuTe DSL / CUTLASS 写核。

### 代码梳理（spencerpauly）

- `parallel-exploring/` — 并行 explore subagent 快速扫大仓库。
- `codebase-onboarding/` — 并行 explore 后合成 onboarding 文档（含 zoom-out 场景）。

### 工程方法论（mattpocock, MIT）

- `diagnose/` — 通用 bug/回归诊断闭环（与 perf-* 互补）。
- `tdd/` — 红-绿-重构 TDD。
- `handoff/` — 长 session 交接文档。
- `grill-with-docs/` — 带 CONTEXT.md/ADR 的深度 grilling（**已移除冗余的 `grill-me`**）。
- `improve-codebase-architecture/` — deepening 机会 + HTML architecture review。

### 学习与文档（anthropics）

- `pdf/` `docx/` `pptx/` — 读/写 PDF、Word、PPT。

## 已移除的低价值 / 冗余 skill

| 移除 | 原因 |
|------|------|
| `grill-me` | `grill-with-docs` 的严格子集；infra 大改应带文档 |
| `zoom-out` | 单行指令，已被 `codebase-onboarding` + `parallel-exploring` 覆盖 |

## 许可证

- NVIDIA skills：`LICENSE-Apache-2.0.txt`
- mattpocock：`LICENSE-MIT-Matt-Pocock.txt`
- anthropics：各 skill 内 `LICENSE.txt` + `LICENSE-Anthropic-Skills.txt`
- BBuf：上游 [BBuf/AI-Infra-Auto-Driven-SKILLS](https://github.com/BBuf/AI-Infra-Auto-Driven-SKILLS)（无单独 LICENSE 文件，保留 upstream metadata）

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

然后登录：

```bash
gh auth login
```

### 同步本仓库到 `~/.cursor/skills/`

```bash
[ -d ~/.cursor/skills ] && [ -n "$(ls -A ~/.cursor/skills 2>/dev/null)" ] \
  && mv ~/.cursor/skills ~/.cursor/skills.bak.$(date +%s)

gh repo clone Saddss/cursor-skills ~/.cursor/skills
```

重启 Cursor IDE / Cursor Agent，skills 就被加载了。

## 日常维护

```bash
cd ~/.cursor/skills
bash scripts/validate-skills.sh
git add -A && git commit -m "describe change" && git push
```

在其他机器：`cd ~/.cursor/skills && git pull`

## 新建 skill 骨架

```
~/.cursor/skills/<skill-name>/
├── SKILL.md          # --- YAML front-matter: name + description ---
└── scripts/          # 可选
```

参考 `model-perf-binary-search/SKILL.md` 或 BBuf skill 的脚本化写法。
