# Skills 使用指南

本仓库共 **25 个** skill，放在 `~/.cursor/skills/`。Cursor 启动时会自动扫描；你也可以在对话里 **@skill 名** 或 **用自然语言描述场景** 触发。

## 怎么触发

```text
# 显式点名（推荐大任务开始时）
@llm-serving-auto-benchmark 帮我在 SGLang 和 vLLM 之间做公平 benchmark

# 自然语言（agent 会根据 description 自动匹配）
用 perf-analysis 分析一下为什么 GPU 利用率只有 60%

# 组合使用
先 @grill-with-docs 把 kvbm study 方案走一遍，再 @model-perf-binary-search 扫 QPS
```

---

## 一、Serving Benchmark & 容量

### `model-perf-binary-search`

**干什么**：在**已知 serve 配置**下，对 LLM 推理服务做 **p50 e2e 延迟 SLO** 约束下的 **最大 QPS 二分搜索**。支持 Mode A（调参）和 Mode B（开/关 feature 后对比）。

**示例**：
```text
@model-perf-binary-search
vLLM 已经起好了，SLO 是 p50 e2e ≤ 200ms，帮我找最大稳定 QPS。
client 用 online_replay.py，结果写到 bench-runs/kvbm_bw_study/phase8_bs/
```

---

### `llm-serving-auto-benchmark`

**干什么**：**跨框架**（SGLang / vLLM / TensorRT-LLM）在相同 workload、GPU、SLA 下公平对比，用 `search_space` 扫 launch 参数；内置 40+ 模型 cookbook YAML。

**示例**：
```text
@llm-serving-auto-benchmark
Qwen3-235B 在 8×H100 上，SGLang vs vLLM vs TRT-LLM 哪个 launch 命令最优？
先用 configs/cookbook-llm/qwen3-235b-a22b.yaml 做 bounded search。
```

```bash
# 仅校验 cookbook 配置（不启动服务）
cd ~/.cursor/skills/llm-serving-auto-benchmark
python scripts/validate_cookbook_configs.py configs/cookbook-llm
```

---

### `llm-serving-capacity-planner`

**干什么**：解析 **SGLang / vLLM 启动 log**，分解 GPU 内存（权重、KV pool、CUDA graph、框架开销），估算 **最大并发** 和 token 容量；适合 KV cache / OOM 排查。

**示例**：
```text
@llm-serving-capacity-planner
这是 SGLang 启动 log，帮我看 KV cache 占了多少、max_running_requests 为什么这么低。
log 路径：/tmp/sglang_startup.log
```

```bash
cd ~/.cursor/skills/llm-serving-capacity-planner
python3 scripts/capacity_analyzer.py --log /tmp/sglang_startup.log
```

---

### `model-compute-simulation`

**干什么**：从 **model config** 构建算子级计算图，估算 **FLOPs、MFU、tensor shape**，支持 TP/EP what-if；写 REPORT 理论部分或 benchmark 前 sanity check。

**示例**：
```text
@model-compute-simulation
Qwen3-235B-A22B，decode B=1 S=1，TP=8 EP=8，bf16，帮我算理论 FLOPs 和 MFU 上限。
```

```bash
cd ~/.cursor/skills/model-compute-simulation
python3 scripts/model_compute_simulator.py "Qwen3-235B-A22B" --tp 8 --ep 8 --batch 1 --seqlen 1
python3 scripts/model_compute_simulator.py --list-models
```

---

## 二、Profiler & 性能分析

### `perf-analysis`

**干什么**：性能分析 **总入口**——分类瓶颈（compute / memory / launch / communication / sync），产出结构化报告，并 **委派** 到 nsys / ncu / binary-search 等子 skill。

**示例**：
```text
@perf-analysis
FlexKV + vLLM serving 比 baseline 慢 30%，帮我分类瓶颈并给出下一步 profiling 计划。
```

---

### `perf-nsight-systems`

**干什么**：**nsys** 系统级 timeline profiling——抓 trace、分析 `.nsys-rep`、看 GPU idle、step gap、NVTX、NCCL overlap。

**示例**：
```text
@perf-nsight-systems
对正在跑的 vLLM serve + online_replay client 抓 60s nsys profile，
分析 GPU 空闲时间和 inter-step gap。
```

---

### `perf-nsight-compute-analysis`

**干什么**：**ncu** kernel 级分析——SOL%、roofline、occupancy、memory hierarchy、`.ncu-rep` 解读；适合单个 CUDA kernel 为什么慢。

**示例**：
```text
@perf-nsight-compute-analysis
这是 flash attention kernel 的 .ncu-rep，帮我看是 memory-bound 还是 compute-bound，
SOL 多少，occupancy 瓶颈在哪。
```

---

### `perf-workload-profiling`

**干什么**：写 **手动 timing harness**（CUDA event、训练 loop 计时）和 **NVTX 标注**；在跑 nsys/ncu 之前先加 instrumentation。

**示例**：
```text
@perf-workload-profiling
给 vLLM forward step 加 NVTX range，区分 scheduler / model forward / sampler 耗时。
```

---

### `perf-host-analysis`

**干什么**：检测 **host/CPU overhead** 是否是瓶颈——Phase 1 二分判定（YES/NO），Phase 2 用 NVTX 找 Python 调度、request 管理等根因。

**示例**：
```text
@perf-host-analysis
nsys 显示 GPU 利用率只有 40%，怀疑 host overhead，用 analyze_host_overhead.py 分析一下。
trace：/tmp/serve.nsys-rep
```

---

### `perf-host-optimization`

**干什么**：在 `perf-host-analysis` 判定 host-bound 后，用 **line_profiler** 做 iterative profile → 优化 → 验证 循环。

**示例**：
```text
@perf-host-optimization
host-bound 已确认，vLLM scheduler 是热点，帮我 line_profiler 一轮并提优化 patch。
```

---

### `perf-optimization`

**干什么**：**优化协调 playbook**——决定走 kernel 编写、TileIR、CUDA Graph 还是 profiling 验证；本 repo 内 specialist 已映射到对应 skill。

**示例**：
```text
@perf-optimization
torch-profiler 显示 GEMM 不是瓶颈，attention + allreduce overlap 差，
帮我路由到正确的优化路径并列出优先级。
```

---

### `llm-torch-profiler-analysis`

**干什么**：**torch.profiler** 统一 triage（SGLang / vLLM / TRT-LLM）——输出三张表：kernel 表、overlap 机会表、fusion 模式表；**prefill / decode 分开**。

**示例**：
```text
@llm-torch-profiler-analysis
分析这个 trace.json.gz，输出三表，prefill 和 decode 分开看。
路径：/tmp/TP-0.trace.json.gz，框架 vllm。
```

```bash
cd ~/.cursor/skills/llm-torch-profiler-analysis
python scripts/analyze_llm_torch_profile.py triage --trace /tmp/TP-0.trace.json.gz --framework vllm
```

---

### `llm-pipeline-analysis`

**干什么**：在 torch-profiler trace 里做 **layer / forward pass 级** 拆解——anchor kernel 边界、每层耗时、Perfetto 时间范围；三表太粗时用。

**示例**：
```text
@llm-pipeline-analysis
trace 里 decode 慢，帮我定位是哪些 layer 贡献最大，forward pass 5 layer 3 的 kernel 明细。
trace：/tmp/TP-0.trace.json.gz，config：/models/qwen/config.json
```

```bash
cd ~/.cursor/skills/llm-pipeline-analysis
python3 scripts/layer_timeline_analyzer.py \
  --trace /tmp/TP-0.trace.json.gz --config /models/qwen/config.json --show-all-passes
```

---

## 三、算子开发

### `kernel-triton-writing`

**干什么**：用 **OpenAI Triton** 写 GPU kernel（fused elementwise、softmax、LayerNorm、GEMM、flash attention），带 verify/benchmark 脚本。**只用于 Triton，不是 CUDA C++。**

**示例**：
```text
@kernel-triton-writing
写一个 Triton RMSNorm kernel，支持 non-divisible shape，先 verify 再 benchmark。
参考 vLLM 里现有的 RMSNorm 接口。
```

---

### `kernel-cute-writing`

**干什么**：用 **NVIDIA CuTe DSL（CUTLASS 4.x）** 写 kernel——GEMM、attention、TMA、tensor core pipeline。**只用于 CuTe，不是 Triton。**

**示例**：
```text
@kernel-cute-writing
用 CuTe DSL 实现一个 bf16 GEMM tile，TP=1，先 verify_kernel 再 ncu profile。
```

---

## 四、代码梳理

### `parallel-exploring`

**干什么**：对大型代码仓库 **并行 launch explore subagent**，每个 agent 扫一个区域（scheduler、KV cache、API 等），快速建立心智模型。

**示例**：
```text
@parallel-exploring
我第一次看 FlexKV 源码，并行 explore 一下：core storage、client API、和 vLLM 集成三块。
```

---

### `codebase-onboarding`

**干什么**：并行 explore 后 **合成 onboarding 文档**（架构、数据流、部署、关键模块）；比 `parallel-exploring` 多一步成文。

**示例**：
```text
@codebase-onboarding
给 llm-inference-benchmarking 仓库写一份 onboarding doc，
重点：bench-runs 目录结构、online_replay client、Docker 部署。
```

---

## 五、工程方法论

### `diagnose`

**干什么**：**通用硬 bug / 性能回归** 诊断闭环——建 feedback loop → 复现 → 假设 → 插桩 → 修复 → 回归测试。和 `perf-*` 互补（更偏逻辑 bug、flaky、配置回归）。

**示例**：
```text
@diagnose
phase8 benchmark 结果和 phase7 差 15%，配置一样，帮我建复现 loop 找根因。
```

---

### `tdd`

**干什么**：**红-绿-重构** TDD——一次只写一个 test、写最少实现；适合 benchmark harness、解析脚本、自动化工具。

**示例**：
```text
@tdd
给 prefix_cache_hit_rate.py 加测试，先写 failing test 再实现 parse 逻辑。
```

---

### `grill-with-docs`

**干什么**：动手前 **深度 grilling**——逐条走设计决策树，同步维护 `CONTEXT.md` 和 ADR；适合 benchmark study、架构大改。

**示例**：
```text
@grill-with-docs
我要做 kvbm bandwidth study，先 grill 一下实验设计：
workload、baseline、FlexKV 配置、成功标准，并更新 CONTEXT.md。
```

---

### `handoff`

**干什么**：把长 session **压缩成 handoff 文档**，方便换 agent / 明天继续；会建议下一 session 该用哪些 skill。

**示例**：
```text
@handoff
今天 profiling 做到 Phase 2，明天继续 nsys 分析，帮我写 handoff。
```

---

### `improve-codebase-architecture`

**干什么**：找代码库 **deepening 机会**（浅模块变深模块），输出 HTML architecture review；适合 benchmark repo 越堆越大时的定期梳理。

**示例**：
```text
@improve-codebase-architecture
扫一遍 bench-runs/ 和 scripts/，找耦合过紧、难测试的模块，出 HTML review。
```

---

## 六、学习与文档

### `pdf`

**干什么**：读/写/合并 **PDF**——文本提取、表格、OCR、表单填充、拆分旋转。

**示例**：
```text
@pdf
从这篇论文 PDF 提取 Table 2 的数据，转成 markdown 表格。
路径：~/papers/flashattention.pdf
```

---

### `docx`

**干什么**：创建/编辑/解析 **Word (.docx)**——报告、memo、tracked changes。

**示例**：
```text
@docx
把 KV_CACHE_SYSTEMS_SURVEY.md 的核心章节整理成一份格式化的 Word 报告。
```

---

### `pptx`

**干什么**：读/写/编辑 **PowerPoint (.pptx)**——读内容用 markitdown，从零生成或改模板。

**示例**：
```text
@pptx
读取 team_meeting.pptx 里关于 KV cache 的 slides，总结要点。
```

---

## 常见组合（抄作业）

### 新 benchmark study（如 kvbm_bw_study）

```text
1. @grill-with-docs          → 定方案、写 CONTEXT.md
2. @llm-serving-auto-benchmark → 选框架 + launch 命令
3. @model-perf-binary-search   → SLO 下扫最大 QPS
4. @llm-serving-capacity-planner → 解释 KV/并发上限
5. @handoff                  → session 结束交接
```

### Serving 变慢排查

```text
1. @diagnose                 → 先确认能复现
2. @perf-analysis            → 分类瓶颈
3. @perf-nsight-systems      → 或 @llm-torch-profiler-analysis
4. @llm-pipeline-analysis    → layer 细拆（若需要）
5. @perf-host-analysis       → GPU 空转时查 host
```

### 读新框架 + 写 kernel

```text
1. @codebase-onboarding      → 架构 onboarding
2. @kernel-triton-writing    → 写/改 Triton kernel
3. @perf-nsight-compute-analysis → ncu 验证优化效果
```

### 写调研报告

```text
1. @pdf / @pptx              → 读论文/组会 slides
2. @model-compute-simulation → 补理论 FLOPs/MFU 数字
3. @docx                     → 输出 Word 版（可选）
```

---

## 速查表

| 我想… | 用哪个 skill |
|-------|-------------|
| 跨框架选最优 serve 命令 | `llm-serving-auto-benchmark` |
| 已知配置找最大 QPS | `model-perf-binary-search` |
| 看 KV cache / 并发上限 | `llm-serving-capacity-planner` |
| 算理论 FLOPs/MFU | `model-compute-simulation` |
| 不知道慢在哪 | `perf-analysis` |
| 抓 nsys / 看 GPU idle | `perf-nsight-systems` |
| 分析单个 kernel SOL | `perf-nsight-compute-analysis` |
| torch.profiler 三表 | `llm-torch-profiler-analysis` |
| trace 按 layer 细拆 | `llm-pipeline-analysis` |
| GPU 空转 / Python 慢 | `perf-host-analysis` → `perf-host-optimization` |
| 写 Triton kernel | `kernel-triton-writing` |
| 写 CuTe/CUTLASS kernel | `kernel-cute-writing` |
| 第一次进大仓库 | `codebase-onboarding` / `parallel-exploring` |
| 大改前先对齐方案 | `grill-with-docs` |
| bug / 回归 | `diagnose` |
| 写测试/脚本 | `tdd` |
| 换 agent 继续 | `handoff` |
| 读 PDF/PPT/Word | `pdf` / `pptx` / `docx` |
