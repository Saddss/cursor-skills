---
name: model-perf-binary-search
description: Find the maximum sustainable QPS of an LLM inference service that meets a p50 e2e latency SLO using online_replay.py and a binary search. Use when the user asks to "测最大 QPS"/"二分测性能"/"find max QPS"/"benchmark a model"/"perf test with SLO"/"调参测性能"/"在 X 基础上开启 Y 功能调优" against a local OpenAI-compatible server (e.g. vLLM, SGLang, TRT-LLM) and provides a startup command plus a QPS lower/upper bound. The skill is framework-agnostic, drives the user-supplied serving command, runs replay rounds (8 if no offload / 16 with offload), averages the per-round p50 over the last 4/8 rounds, compares against 6.5s by default, binary-searches QPS to 0.1 precision (extrapolating the upper bound when it still passes), reports progress every 15min (no offload) / 30min (offload), captures prefix-cache hit rate per probe in a framework-agnostic way (scrapes Prometheus /metrics and falls back to engine-specific log scraping or research when the standard endpoint does not expose prefix metrics), and optionally runs additional tuned-parameter sessions in two modes: Mode A (research every existing flag in the user's startup command against the official docs and the local GPU and propose better values), or Mode B (the user names a feature to enable but does not understand it; do a deep multi-stage investigation of that feature, tune the feature's own knobs, and co-adjust user-provided flags whose interactions are documented).
---

# Model Performance Binary Search

Find the maximum QPS at which an LLM inference service still meets a p50 end-to-end latency SLO. This skill drives the `online_replay.py` script from `Saddss/llm-inference-benchmarking@sss-test` (carries the sampler / timeout / round-drain fixes; the upstream `FlowGPT/qq-test` is missing them and will not work against TRT-LLM or any saturated service) against a service that the user provides a startup command for, and binary-searches the QPS axis.

## Dataset selection and bootstrap (must run at session start)

Before every benchmark session, list the regular files under `/mnt/shared/sss/data` and ask the user to choose exactly one dataset. Never reuse the previous session's choice, infer a choice from filenames, or copy every dataset. After the user chooses:

```bash
export LLM_BENCH_DATASET_SRC="/mnt/shared/sss/data/<chosen-file>"
eval "$(bash ~/.cursor/skills/model-perf-binary-search/scripts/bootstrap.sh)"
export LLM_BENCH_DIR="$WORKDIR"
```

What it does (idempotent):

1. **Selection gate** — require one explicit `LLM_BENCH_DATASET_SRC` under `/mnt/shared/sss/data`. Missing mount, missing selection, empty files, and paths outside that directory fail immediately.
2. **Clone or update** `https://github.com/Saddss/llm-inference-benchmarking.git` on branch **`sss-test`** (fetch + checkout + `pull --ff-only` when the repo already exists).
3. **Python env** — install `uv` if missing; create `$WORKDIR/.venv`; run `uv pip install -r requirements.txt` and `uv pip install requests`.
4. **Dataset** — copy only the selected file to `$WORKDIR/datasets/<basename>`. Reuse a non-empty local file with that basename; never bulk-copy the shared directory.
5. Create `$WORKDIR/bench-runs/`.
6. Run `scripts/health_check.py` → `$WORKDIR/.health_check.json`.

Environment overrides (optional):

| Variable | Default |
|----------|---------|
| `LLM_BENCH_DIR` | `$HOME/llm-inference-benchmarking` |
| `LLM_BENCH_REPO_URL` | `https://github.com/Saddss/llm-inference-benchmarking.git` |
| `LLM_BENCH_REPO_BRANCH` | `sss-test` |
| `LLM_BENCH_SHARED_MOUNT` | `/mnt/shared/sss` |
| `LLM_BENCH_DATASET_SRC` | Required selected file under `<mount>/data` |

Bootstrap stdout contains shell-safe `WORKDIR=<absolute path>` and `DATASET=<local selected path>` assignments. Capture both with the command above.

Bootstrap returns exit 0 when setup succeeded (even if health check reports warnings). Read `$LLM_BENCH_DIR/.health_check.json` for `exit` semantics. Bootstrap exits non-zero only on hard failures (no mount, no dataset file, git/uv/import errors).

All later commands assume `$LLM_BENCH_DIR` has `.venv/` and `online_replay.py`, and use `$DATASET` as the replay input.

## Pre-flight health check (gates offload runs)

Right after bootstrap, **always** read `$LLM_BENCH_DIR/.health_check.json` and act on its top-level `exit` field. The check covers:

- GPU presence + driver version
- PCIe link gen (current vs hardware max), with virtualization detection (vfio passthrough often caps the guest at Gen1)
- AER error counts (correctable/fatal/nonfatal) on the GPU's PCIe path
- Other processes already on the GPU (warn if >50% memory is held by someone else)
- **Pinned host↔GPU bandwidth** with `torch` (16 MiB + 64 MiB H2D/D2H, ~2s)
- Free disk space at the workdir

### Exit code semantics + required reaction

| exit | meaning | offload runs | non-offload runs |
|------|---------|--------------|------------------|
| **0** | all green | proceed | proceed |
| **1** | warnings only (e.g. peak BW < 55% of link theoretical, low disk, foreign GPU process) | print the warnings in the agent's reply, then ask user to confirm before starting offload | proceed; mention warnings in the final report |
| **2** | blocker — almost always severely degraded PCIe link or no torch + no link info | **refuse** to run an offload binary search unless the user types an explicit `force=true` override; offer to run non-offload only, or to switch to a different machine | proceed with non-offload, but include the health-check block in the final report |

When `exit >= 1`, **paste the relevant `issues_red` / `issues_warn` strings verbatim** into the agent's reply so the user sees them. Do not paraphrase — these messages already include the action items.

### Re-running the check manually

```bash
"$LLM_BENCH_DIR/.venv/bin/python" \
  ~/.cursor/skills/model-perf-binary-search/scripts/health_check.py --workdir "$LLM_BENCH_DIR"
# or: --no-bandwidth   for a structural-only run (~0.5s, no torch needed)
```

The Python file is portable — invoke it with whichever python has `torch` installed. The script gracefully degrades when torch is missing (skips the BW measurement and warns about it instead of failing).

## Required inputs (ask the user up-front, in one message)

1. **Replay dataset** — list `/mnt/shared/sss/data` and ask the user to choose one, even when only one file exists.
2. **Service startup command** (full shell command, including port). This is opaque to the skill - just run it as given.
3. **Binary search bounds** as `LOW HIGH` (floats, e.g. `3 6`).
4. **Whether offload is enabled** for this run. Ask explicitly every time - do **not** infer it from the startup command. This decides the round counts:
   - `offload = OFF` -> run **8 rounds**, average **last 4** rounds' p50.
   - `offload = ON`  -> run **16 rounds**, average **last 8** rounds' p50.
5. **Model name** to pass to `--model` (the same string the server uses for `served-model-name`).
6. **API base port** (the `localhost` port the server listens on, e.g. `8080`).
7. **Whether to also run a tuning round** after the baseline. If yes, ask whether it is:
   - **Mode A (generic tuning)**: "review my command and propose better values for what is already there"; or
   - **Mode B (feature enablement)**: "在 X 基础上开启 Y 功能, 你去调优性能" — i.e. the user names a specific feature/knob they want enabled but does not necessarily understand it themselves. Mode B triggers a deep, multi-stage investigation (see "Feature-enablement tuning" below) and is more expensive in wall-clock time, so make sure the user knows that.
8. **Optional overrides**: SLO seconds (default `6.5`), precision (default `0.1`). Do **not** ask the user for repo clone, branch, venv, or a path outside the shared-dataset choice unless bootstrap failed.

If any of the above are missing, ask the user before starting.

## Parameter-tuning round (only if the user opted in at input #7)

The goal: produce one or more **extra** complete binary-search sessions with tuned startup commands, so the user can compare baseline vs tuned max QPS. Order of operations: baseline run with the user's original command first, then propose tuning, then run the additional binary search(es). Steps 1–7 below cover **Mode A**; for **Mode B** layer the "Feature-enablement tuning" section on top of them.

**Step 1 - Identify the framework.** Look at the entrypoint of the startup command. Common cases:
- `vllm serve …` / `python -m vllm.entrypoints.openai.api_server` / `vllm/vllm-openai` docker image -> **vLLM**
- `python -m sglang.launch_server` / `sglang …` -> **SGLang**
- `trtllm-serve` / TensorRT-LLM container -> **TensorRT-LLM**
- `lmdeploy serve api_server` -> **LMDeploy**
- Anything else -> ask the user which framework and its repo URL.

**Step 2 - Detect the hardware.** Before researching params, run on the test machine:

```bash
nvidia-smi --query-gpu=index,name,memory.total,driver_version,compute_cap --format=csv
nvidia-smi topo -m 2>/dev/null | head -40
```

Capture: GPU model (e.g. H100-SXM-80GB / A100-80GB / L40S / 4090), per-GPU memory, GPU count, NVLink topology (matters for `--tensor-parallel-size`). If `nvidia-smi` is unavailable, ask the user for the hardware.

**Step 3 - Research every flag in the startup command.** Use the official docs of the identified framework (the latest stable release, not blog posts). Reach for `WebFetch` / `WebSearch` rather than guessing from memory:
- vLLM: <https://docs.vllm.ai/en/latest/serving/engine_args.html> and <https://github.com/vllm-project/vllm>
- SGLang: <https://docs.sglang.ai/> and <https://github.com/sgl-project/sglang>
- TensorRT-LLM: <https://nvidia.github.io/TensorRT-LLM/> and <https://github.com/NVIDIA/TensorRT-LLM>
- LMDeploy: <https://lmdeploy.readthedocs.io/> and <https://github.com/InternLM/lmdeploy>

For **every** flag the user passed, summarise in one sentence what it does and whether it is sensitive on the detected GPU. Do not guess - if a flag is unfamiliar, fetch the doc page.

**Step 4 - Produce a tuning proposal.** Present a short markdown table to the user:

| Flag | Current value | Suggested value | Why (≤1 line, mention GPU/workload) |
|------|---------------|-----------------|--------------------------------------|

Anchor every suggestion in (a) the official doc, (b) the detected GPU's known capabilities, and (c) the workload signal we have (chat replay, p50 e2e SLO 6.5s, max output tokens ≈ 180, prompts up to a few k tokens). Common levers to consider, framework-dependent:

- Throughput vs latency dials: `--max-num-seqs`, `--max-num-batched-tokens`, `--max-running-requests`, `--max-model-len`, `--max-prefill-tokens`.
- Memory: `--gpu-memory-utilization`, `--swap-space`, `--cpu-offload-gb`, `--kv-cache-dtype` (fp8 on Hopper/Ada with FP8 support).
- Compute: `--quantization` (fp8/awq/gptq), `--dtype`, `--enforce-eager` vs CUDA graphs.
- Parallelism / topology: `--tensor-parallel-size`, `--pipeline-parallel-size`, `--data-parallel-size`, NCCL env vars on multi-GPU.
- Scheduling features: `--enable-chunked-prefill`, `--enable-prefix-caching`, `--scheduling-policy`, speculative decoding flags.
- Server plumbing that affects perceived latency: `--disable-log-requests`, `--max-logprobs`, request timeout, `--swap-space`.

If a flag in the user's command is **not** documented in the official docs, flag it as "unknown - verify with user/source" rather than inventing behaviour.

**Step 5 - Ask the user to approve a final tuned command.** Print the proposed command verbatim and ask for confirmation (or ask which suggestions to drop). Do **not** start the tuned service before getting an explicit OK.

**Step 6 - Service swap for the second session.** Because the skill normally never stops the service it started, switching to the tuned command requires explicit consent. After the baseline binary search finishes, ask: *"I need to stop the current service (PID {pid}) to relaunch with the tuned parameters. OK to kill it?"*. Only on explicit yes, kill it (`kill {pid}` then SIGKILL after a 30s grace period) and start the tuned service via the same lifecycle steps (readiness poll, etc.). If the user says no, stop here and let them swap manually.

**Step 7 - Run the same binary search a second time** with the tuned service, then produce a comparison report:

```
Baseline:  Max QPS = X.X (offload=…, original command)
Tuned:     Max QPS = Y.Y (offload=…, tuned command)
Delta:     +Z.Z QPS (+W%)
```

List per-probe tables for both sessions and note any flags that surprised you (e.g. enabling fp8 KV cache hurt p50 instead of helping). After the tuned session finishes, leave the tuned service running, exactly like the baseline policy.

### Feature-enablement tuning (Mode B)

When the user phrases the request as "在 [base config] 基础上开启 [feature], 你去调优性能" — i.e. they name a specific feature they want enabled and explicitly do **not** understand all the related parameters themselves — extend Mode A as follows. The Mode A baseline still runs first and serves as `cfg_0`. Then:

1. **Deep feature research.** Go beyond a one-line doc lookup. Read, in order:
   - The framework's docs page describing the feature (vLLM/SGLang/TRT-LLM/LMDeploy etc.).
   - Any "design", "architecture", or RFC page if one exists.
   - The actual source code in the framework's repo (the relevant module / the PR that introduced the feature / recent release notes), so you understand defaults, valid ranges, failure modes, and known caveats.
   - Any official benchmark or blog post the framework team published about this feature.
   Quote your sources back to the user (URL + 1-line takeaway each) — the user does not understand the feature, so transparency about where the recommendation comes from is mandatory.

2. **Inventory every knob the feature exposes.** All CLI flags, config options, env vars, and any required model-side settings, with valid range, default, and per-GPU-vs-global scope. Mark which knobs are safe to vary independently and which must move together.

3. **Inventory user-side flags that interact with the feature.** Walk through every flag in the user's existing startup command and label each `independent` or `interacts: <how>` (e.g. enabling prefix caching means `--gpu-memory-utilization` and `--max-num-batched-tokens` matter more; speculative decoding interacts with `--max-num-seqs`; CPU offload interacts with `--swap-space` and `--max-model-len`). Only flags labelled `interacts` are candidates for co-adjustment in the tuning matrix.

4. **Propose a multi-stage experiment plan** (typically 3–5 configurations) and get explicit approval before running anything. A reasonable default plan:
   - `cfg_0`: user's original command, no feature (already the baseline from Step 7 above).
   - `cfg_1`: feature ON with framework defaults; user's other params unchanged. Lets you isolate the feature's pure effect.
   - `cfg_2`: feature ON with **tuned feature-specific params**; user's other params still unchanged.
   - `cfg_3`: feature ON with tuned feature params **and** co-adjusted user params (only those flagged `interacts` in step 3). Each co-adjustment must be justified by the research from step 1.
   - `cfg_4` (optional): a more aggressive variant if `cfg_3` still has SLO headroom (e.g. push the feature's most impactful knob further).

   Show the plan as a markdown table with columns `cfg / startup-command diff vs cfg_0 / hypothesis / expected risk`. Estimate wall-clock cost (`per-probe wall time × ~6 probes × N configurations`, typically several hours) so the user can decide whether to trim the plan.

5. **Run each approved configuration as its own full binary search**, reusing the lifecycle from Step 6 of Mode A: every service swap requires explicit user consent (one consent per swap, do not batch). Honour the same progress-monitoring cadence (15 / 30 min) across all stages — the wall-clock timer is per **session**, not per configuration.

6. **Multi-level tuning loop.** If `cfg_2` or `cfg_3` shows a clear directional signal (e.g. doubling a buffer monotonically helps), you may propose **one** additional refinement configuration without restarting the whole plan — but ask the user before queuing it. Cap the total at ~6 configurations to bound runtime; if more would help, summarise findings and let the user decide whether to extend.

7. **Comparison matrix** at the end:

   | cfg | feature params | user params changed | Max QPS | Δ vs cfg_0 | tail-avg p50 at Max QPS | Notes |
   |-----|----------------|---------------------|---------|------------|--------------------------|-------|

   Pick a winning configuration and recommend it to the user, with rationale tied back to the research from step 1 (e.g. "cfg_3 wins because the feature's prefill buffer requires `--max-num-batched-tokens >= 4096` per the docs, and our chat workload has ~3k-token prompts"). Be honest if no configuration beats `cfg_0` — the right answer can be "the feature does not help this workload on this GPU, here is why".

Mode B never auto-extends into territory the user did not approve. Whenever you want to (a) try a config not in the original plan, (b) co-adjust a flag that was not flagged `interacts`, or (c) change the SLO / round counts to make a probe terminate faster, ask first.

## Working directory and fixed conventions

- Always `cd "$LLM_BENCH_DIR"` before running `online_replay.py`; pass `--input "$DATASET"`.
- Always invoke Python through the workdir venv: `"$LLM_BENCH_DIR/.venv/bin/python" online_replay.py …`.
- Sample range is **always** `0.0 (0.02 * target_qps)`, capped at `1.0`. For `target_qps = 5.1` -> `0.0 0.102`; for `25` -> `0.0 0.5`; for `60` -> `0.0 1.0`.
- `--round-duration 30`, `--replay-mode qps`, `--use-chat`, `--e2e-slo 6.5` (or override).
- Production sampling (dataset has no per-request fields): `--max-tokens 200 --temperature 0.7` (plus `top_p` / penalties via CLI or `online_replay` prod defaults when omitted).
- Use `--json-output` for per-round metrics.
- Pin `--max-rounds` to `8` or `16`.

### Truncation-aware datasets and MTP

- `online_replay.py` always sends `X-Flow-Conversation-Id`; no extra flag is needed.
- A dataset's `body.enable_kv_evict` is ignored by default. Add `--forward-kv-evict` only when the user explicitly requests truncation-eviction testing.
- For MTP runs add `--disable-min-p` and do not pass `--min-p`; the MTP endpoint rejects it. Other runs, including non-MTP speculative decoding, retain production `min_p=0.1`.

## Service lifecycle

The agent owns service start, but **never** stops the service. Per the user's policy:

- Start the service **once** at the beginning by running the user-provided command in the background. Capture the PID and the path of its stdout/stderr log so progress reports can quote the tail.
- Wait for readiness by polling `GET http://localhost:{port}/v1/models` (5xx/connection refused => not ready). Time out after ~10 minutes with a clear error.
- **Do not restart the service between QPS steps** - reuse the same process for every binary-search probe.
- **When the binary search finishes (success, failure, or user interrupt) leave the service running.** Only clean up leftover client processes with `pkill -f "online_replay.py"`. Print the service PID and its log path in the final report so the user can manage it themselves.

Note that some servers (vLLM, SGLang, TRT-LLM) take minutes to load weights. Do not assume readiness from the absence of error output.

### Docker-based services (most common case)

When the user's startup command starts with `docker run …` (vLLM/SGLang/TRT-LLM official images, custom containers), substitute PID-based ops with container-name-based ops. Required tweaks:

- **Launch in detached mode.** The user-provided command is usually foreground; replace `docker run` with `docker run -d --rm --name <bench_name>` so the agent can manage and inspect it. Always carry these flags forward from the user's command: `--gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864` (the last two prevent silent CUDA OOMs on `cudaHostAlloc` paths, e.g. KV offload, pinned KV cache, large prefetch buffers).
- **Mount a HuggingFace cache** so service swap (Mode A / B) does not re-download weights: `-v $HOME/.cache/huggingface:/root/.cache/huggingface`.
- **Capture logs.** PID-based `tail -f service.log` does not work; do `( docker logs -f <bench_name> > bench-runs/service_<ts>.log 2>&1 & )` and report that log path in the final report.
- **Liveness check.** Replace `kill -0 {pid}` with `docker ps --filter name=<bench_name> --format '{{.Names}}'` (empty output = container died, dump `docker logs --tail 100 <bench_name>` immediately).
- **Service swap (Mode A/B).** Replace `kill {pid} && start` with `docker stop <bench_name>` (waits 10s for graceful SIGTERM, then SIGKILL — sufficient for vLLM/TRT-LLM). The `--rm` flag deletes the container automatically once stopped.
- **Cleanup-on-finish policy is identical**: leave the container running. Tell the user to run `docker stop <bench_name>` themselves when done.

Common gotcha: `docker stats <bench_name>` only updates every ~2s and lags real GPU usage; for live GPU pressure use `nvidia-smi` on the host, not docker stats.

## Progress monitoring

Long binary-search sessions need regular wall-clock progress reports so the user does not have to ask. The cadence depends on the offload flag:

- `offload = OFF` -> emit a progress update **every ~15 minutes** of wall-clock time.
- `offload = ON`  -> emit a progress update **every ~30 minutes** of wall-clock time.

Implementation:

- At the start of the session, record `t0 = now()` and set `next_report = t0 + interval`.
- Between probes (and, for long-running probes, also during the wait loop that polls for shard completion) check whether `now() >= next_report`. If so, emit a progress message and advance `next_report += interval`. Multiple intervals can elapse during one long probe; emit one update per interval crossed (do not spam, do not skip silently).
- A progress update is a short markdown block containing:
  - elapsed wall-clock time since session start, plus elapsed since last update;
  - probes completed so far (count + the same per-step table from the "Reporting to the user" section, truncated to last 5 rows if long);
  - the current binary-search bracket `[LOW, HIGH]` and `best_pass`;
  - what is happening **right now** (e.g. "probe 7 at qps=9.4: round 6/8, last per-round p50 = 5.91s") - read it from the most recently appended line of the active shard's `--json-output` file;
  - rough ETA for the current probe (`(total_rounds - rounds_seen) * 30s`) and a coarse ETA for the whole session if the bracket width and average per-probe wall time make it estimable;
  - one line confirming the service PID is still alive (`kill -0 {pid}` works) and the latest few stderr lines if anything looks off.

Do **not** wait for an update window to also surface real failures (server crash, shards exiting non-zero, readiness check breaking). Surface those immediately, regardless of cadence.

## Single QPS probe

Each binary-search step is one probe at a candidate QPS `q` (always rounded to the nearest 0.1). Procedure:

1. Compute `sample_end = min(0.02 * q, 1.0)`.
2. Pick `total_rounds` and `tail_window` from the offload flag (8/4 or 16/8).
3. Choose output paths: `bench-runs/qps_{q}_{timestamp}.jsonl` for client metrics, plus `bench-runs/qps_{q}_{timestamp}.{before,after}.prom` for prefix-cache snapshots.
4. **Snapshot the engine's `/metrics` endpoint** before any traffic is sent (see "Prefix cache hit rate" below). If that step returns `NO_PREFIX_METRICS` or the endpoint is unreachable, follow the fallback flow described there.
5. Run **one** `online_replay.py` process for `q <= 10`. For `q > 10`, shard the load across `n = ceil(q / 10)` parallel processes, each with `--target-qps {q/n}` and a `--sample-range` chunk of width `sample_end / n` (so the union covers `[0, sample_end)`). Each shard writes to its own json file.
6. Wait for **all** shards to exit. Do not early-stop; the user requires the full 8/16 rounds.
7. **Snapshot `/metrics` again** immediately after the last shard exits, then run the prefix-cache diff helper. Cache the resulting `hit_rate` for the per-probe report.
8. Decide PASS/FAIL with the bundled helper. **Always pass `--auto-steady`** unless the user explicitly asks for the legacy tail-only behavior:

```bash
python3 ~/.cursor/skills/model-perf-binary-search/scripts/analyze_rounds.py \
    --json bench-runs/qps_{q}_{ts}_shard*.jsonl \
    --total-rounds {8 or 16} \
    --tail-window {4 or 8} \
    --slo {SLO} \
    --auto-steady
```

The helper prints a single JSON line and exits `0=PASS / 1=FAIL / 2=NOT_ENOUGH_ROUNDS`.

**How `--auto-steady` decides PASS/FAIL.** The fixed tail window is sensitive to cold-start backlog: on real chat workloads the first 5-7 rounds at any QPS can show large p50 while the queue drains, so an 8-round run with a fixed `tail-4` may still include warmup rounds. The auto-steady algorithm walks backward from the last round, including a round in the steady window if its p50 is within `±0.30` of the running median; it stops at the first round that's too far off. If the resulting window has at least 3 rounds, its average becomes the **primary** PASS/FAIL signal. If not (engine never reached steady state, or noisy variance), it falls back to the tail-window average and emits a note. Tunable knobs: `--steady-tolerance 0.30` (default), `--steady-min-window 3` (default).

The helper also always emits a `warmup_dominated` boolean (true when `tail-N / tail-3 > 1.5` or `tail-N / last_round > 2.0`) so the agent can call out runs where the legacy tail metric would have been misleading.

Validated on 12 historical TRT-LLM / vLLM probes against this skill (May 2025): `--auto-steady` flipped 6 cases from FAIL → PASS without any false positives; the 6 cases were ones where rounds 8-12 sat steady well under SLO but rounds 6-7 still had backlog. The flipped runs match the engines' actual sustainable QPS as confirmed by re-runs at adjacent QPS values.

`NOT_ENOUGH_ROUNDS` (e.g. server crashed mid-run, requests timed out) should be treated as **FAIL** for binary-search purposes, but log the JSON output so the user can investigate.

Example shard command (single-process case):

```bash
cd "$LLM_BENCH_DIR" && \
"$LLM_BENCH_DIR/.venv/bin/python" online_replay.py \
    --input "$DATASET" \
    --preload-time 2 \
    --replay-mode qps --target-qps 5.1 \
    --sample-range 0.0 0.102 \
    --api-base http://localhost:8080/v1 \
    --api-key "$(printf 'a%.0s' {1..32})" \
    --model your-model-name \
    --use-chat \
    --max-tokens 200 \
    --temperature 0.7 \
    --top-p 0.85 \
    --top-k 40 \
    --min-p 0.1 \
    --frequency-penalty 0.4 \
    --presence-penalty 0.1 \
    --round-duration 30 \
    --round-drain-timeout 300 \
    --request-timeout 600 \
    --max-rounds 8 \
    --e2e-slo 6.5 \
    --json-output bench-runs/qps_5.1_20260101_120000.jsonl
```

### Prefix cache hit rate (per-probe, framework-agnostic)

Capture this for every probe so the report shows whether the workload is actually benefiting from prefix caching. The signal also helps diagnose why a tuning change moved p50 (e.g. a config that shrinks KV cache may also evict shared prefixes and lower hit rate).

**Default path: Prometheus `/metrics` snapshots around the probe.** Almost every OpenAI-compatible server (vLLM, SGLang, TRT-LLM, LMDeploy, …) exposes a Prometheus endpoint on the same host:port as `/v1`. The bundled helper `scripts/prefix_cache_hit_rate.py` is framework-agnostic — it does *not* hardcode metric names; it scans for any metric whose name contains "prefix" and pairs hit-like with query-like (or fallback hits+misses) names.

```bash
# before the probe
python3 ~/.cursor/skills/model-perf-binary-search/scripts/prefix_cache_hit_rate.py snapshot \
    --url http://localhost:{port}/metrics \
    --out bench-runs/qps_{q}_{ts}.before.prom

# ... probe runs ...

# after the probe
python3 ~/.cursor/skills/model-perf-binary-search/scripts/prefix_cache_hit_rate.py snapshot \
    --url http://localhost:{port}/metrics \
    --out bench-runs/qps_{q}_{ts}.after.prom

# compute hit rate over the probe window
python3 ~/.cursor/skills/model-perf-binary-search/scripts/prefix_cache_hit_rate.py diff \
    --before bench-runs/qps_{q}_{ts}.before.prom \
    --after  bench-runs/qps_{q}_{ts}.after.prom
```

The diff command prints one JSON line with `status`, `hit_rate`, `hits`, `queries`, and the metric names it picked. Exit codes: `0` OK, `2` `NO_PREFIX_METRICS`, `3` error.

**Fallbacks when `/metrics` doesn't expose prefix-cache counters** (in this order, escalating effort):

1. **Engine stdout / log scraping.** Many engines print a periodic line like `Prefix cache hit rate: X.X%`. For Docker, `docker logs --since <probe_start> <container> | grep -iE "prefix.cache|hit.rate"` and average the percentages reported during the probe window. Cite the regex used.
2. **Engine-specific metric names.** If `/metrics` exists but contains zero "prefix"-named metrics, look for engine-specific aliases (e.g. KV-block reuse rate, automatic-prefix-cache hit counter under a non-obvious prefix). Use `WebFetch` / `WebSearch` on the engine's docs / source to identify the right metric, then run the helper diff manually against those names (or `grep -E "<name>" *.prom` to compute by hand).
3. **Ad-hoc instrumentation.** If still nothing, note `hit_rate=unknown` in the per-probe row, log the `/metrics` snapshot for the user, and continue. Do **not** block the binary search on this.

Always include the chosen `hit_metric` / `denom_metric` names in the final report's footer the first time a new engine is encountered, so the next session knows where the rate came from.

## Binary search algorithm

Notation: `LOW`, `HIGH` are floats. `precision = 0.1` by default. `best_pass = None`.

**Always probe LOW before HIGH.** Starting at a too-high QPS (especially with CPU KV offload or a cold engine) commonly creates irreversible queue backlog / ReadTimeout storms that waste the whole probe window and contaminate the service for later steps. Establish a passing floor first, then climb.

1. **Probe LOW first.**
   - If `LOW` FAILs, **extrapolate downward** symmetrically (halve the gap toward 0) until you find a passing QPS or you reach the precision floor. If even a very low QPS fails, report the failure to the user with the per-round p50 values — the service likely has a problem unrelated to capacity; do **not** proceed to HIGH.
   - If `LOW` PASSes, set `best_pass = LOW` and continue.
2. **Probe HIGH.**
   - If `HIGH` PASSes, `best_pass = HIGH`, then **extrapolate upward** (see below) and repeat until the new HIGH FAILs. The user explicitly does not want you to stop at the user-provided HIGH if it still passes.
   - If `HIGH` FAILs, keep `HIGH` as the failing upper bound and continue.
3. **Standard binary search between the latest passing low and failing high.**
   - Loop while `HIGH - LOW > precision`:
     - `mid = round((LOW + HIGH) / 2, 1)` (always step on a 0.1 grid).
     - Skip `mid` if it equals an already-tested value; nudge by `+precision` instead.
     - Probe `mid`. PASS -> `LOW = mid`, update `best_pass`. FAIL -> `HIGH = mid`.
4. **Final answer:** `best_pass` (the largest QPS that satisfied the SLO at 0.1 precision).

### Extrapolating the upper bound when HIGH still passes

You decide the next upper bound based on the SLO margin at the current HIGH. Use this heuristic, not a fixed multiplier:

- Let `p` be the avg-p50 just measured at the current HIGH `H`, and `S` the SLO.
- `slack = (S - p) / S`. Roughly:
  - `slack >= 0.40` (very comfortable, e.g. p ~3.5s vs 6.5s) -> aggressive jump: `new_high = round(H * 1.6, 1)` (cap at `H + 8`).
  - `0.20 <= slack < 0.40` -> moderate: `new_high = round(H * 1.3, 1)`.
  - `0.05 <= slack < 0.20` -> small: `new_high = round(H + max(1.0, 0.15 * H), 1)`.
  - `slack < 0.05` -> the next probe would likely fail; stop extrapolating, keep `H` as the confirmed PASS / search low, and treat the next untested point above as the failing candidate only after an actual FAIL probe (or enter binary search once a FAIL bound exists).

Always set `new_low = H` (the previous HIGH became a confirmed PASS, so the search interval starts there). Then re-probe `new_high`; if it also passes, recompute and extrapolate again.

### Extrapolating the lower bound when LOW fails

Mirror logic: let `p` be the avg-p50 at current LOW `L`. Pick `new_low = round(L / 2, 1)` if `p` is far above SLO (`p > 1.5 * S`), else `new_low = round(L - max(0.5, 0.3 * L), 1)`. Floor at `precision`. If the floor still fails, stop and report.

## Interpretation rules

- "Meets SLO" means the **average of per-round p50 e2e latencies** over the tail window is **strictly less than** the SLO (default `6.5s`). A round whose own p50 is over SLO does **not** by itself fail the QPS - only the tail-window average matters.
- Precision `0.1` means the final answer is reported to one decimal place. If the user says "精确到 0.5" or "整数即可", use that as the precision instead.
- All probes that the binary search needs to make must run to completion (no early stop), per user policy. **Single exception — "obvious-FAIL queue runaway":** kill the probe early (`pkill -f online_replay.py`), write `Result=FAIL`, `hit_rate=n/a`, and proceed with the bisect when **either**:
  1. per-round p50 is monotonically rising (e.g. every round ≥1.3× the prior) **and** the most recent round's p50 is already >10× SLO **and** the engine is in steady saturation (no transient warmup); or
  2. the client is in a ReadTimeout / drain-timeout storm — e.g. ≥2 consecutive rounds that report zero successful requests after drain timeout, or ≥50 ReadTimeouts in the shard stderr while fewer than 3 metric rounds have been written — which typically follows starting too high (another reason LOW is probed first).
  Document the exception in the final report so the user knows which probes were early-stopped.

### Warmup-bias caveat (handled by `--auto-steady`; still disclose in report)

The fixed tail-N window is sensitive to **cold-start backlog**: under realistic chat replay, round 1 can produce 50–100s p50 and it can take ~5–7 rounds for the queue to reach steady state. With the 8-round no-offload policy, `tail-4` can therefore still contain warmup. The auto-steady result and `warmup_dominated` flag must remain visible in the report.

Historical 12-round example from a real vLLM run at q=4.1: per-round p50 `[72, 33, 33, 16, 15, 38, 16, 4.4, 4.8, 5.2, 5.1, 4.9]`. tail-6 = 6.71s → FAIL. But rounds 8–12 are clearly steady at ~4.9s. The legacy tail-only judgement reports a max QPS that **underestimates true sustainable QPS by ~10–20%**.

**`--auto-steady` (recommended default) automatically detects and uses the steady window.** It identified the [4.4, 4.8, 5.2, 5.1, 4.9] tail above as a 5-round steady window at 4.89s, flipping the verdict to PASS — matching the engine's actual sustained capacity.

**Reporting expectations even when auto-steady passes:**

- Show both the primary metric (steady avg, when detected) and the legacy tail-N avg in the per-probe table.
- If `warmup_dominated == true` in the analyzer JSON, paste the helper's `notes[]` string verbatim in the final report. It signals the legacy tail metric would have been misleading.
- If a bisect step PASSes via steady but `warmup_dominated == true`, optionally suggest the user re-run that QPS with `--round-duration 60` or `--max-rounds 16` to confirm. Do **not** silently change those values — they are part of the published methodology.

**When `--auto-steady` falls back to tail-N** (no ≥3-round window within ±30% of running median): the engine genuinely never reached steady state at this QPS. Report the tail-N number and the `notes` line saying "no steady window detected"; this is a legitimate FAIL signal (or, if `tail-N` itself is far above SLO, a clear overload signal).

## Reporting to the user

Track every probe and present the result clearly when done. Use a markdown table:

| Step | QPS | Result | Primary p50 (window) | Tail-N p50 | Prefix cache hit | Notes |
|------|-----|--------|----------------------|------------|------------------|-------|
| 1 | 6.0 | PASS | 4.81s (steady-5) | 5.20s | 31.2% | extrapolating up |
| 2 | 9.0 | PASS | 5.92s (steady-4) | 6.41s | 28.7% | warmup-dominated; extrapolating |
| 3 | 12.0 | FAIL | 7.40s (tail-4, no steady) | 7.40s | 24.1% | engine never reached steady |
| 4 | 10.0 | PASS | 6.11s (steady-5) | 6.30s | 27.4% | |
| 5 | 11.0 | FAIL | 6.84s (steady-3) | 7.10s | 25.8% | thin steady evidence; suggest re-run with --max-rounds 16 |
| ... | ... | ... | ... | ... | ... | converged |

- **Primary p50** is the official PASS/FAIL signal (output of `--auto-steady`). It's either the auto-detected steady-window average (preferred) or the tail-N average (fallback). Always show which window was used in parentheses: `(steady-N)` or `(tail-N, no steady)`.
- **Tail-N p50** is the legacy column kept for transparency / comparison with historic skill runs. If primary == tail (no steady detected), the two columns are equal.
- When `warmup_dominated == true` in the analyzer JSON, paste its `notes[]` string in the per-probe `Notes` cell so the user sees why the two columns may diverge.
- Render `Prefix cache hit` as a percentage with one decimal. If the value is missing for a probe (e.g. `/metrics` unreachable, `NO_PREFIX_METRICS`, or fallback failed), show `n/a` and add a one-line footer explaining why.

Final line: `Max QPS meeting p50 e2e <{SLO}s SLO: {best_pass} (offload={ON|OFF}, rounds={8 or 16}, tail={4 or 8})`.

Also print, in the final report:

- where each shard's `--json-output` file lives so the user can re-inspect;
- the service PID and its stdout/stderr log path, with a reminder that the service is **still running** (the skill never stops it) so the user can decide when to shut it down.

## Failure modes and what to do

- **Service won't start / readiness timeout**: stop, print the last 50 lines of the service stdout/stderr, ask the user how to proceed.
- **First probe at LOW also FAILs after downward extrapolation**: report `Max QPS < {floor}` and the per-round p50 values; do not loop forever.
- **`NOT_ENOUGH_ROUNDS`** from the analyzer: dump the partial json, count it as FAIL for the search, and warn the user that the underlying run did not complete.
- **High variance between rounds in the tail window** (e.g. tail max > 1.5 * tail min): note this in the report; the tail-average answer is still the source of truth, but the user should know.

### CPU KV offload (vLLM `--kv-offloading-size`) gotchas

When the user asks for CPU KV offload (vLLM's `--kv-offloading-size N --kv-offloading-backend native`, or any other engine's equivalent that uses pinned host memory), do **all** of the following before launching the container; missing any one of these will cause a `cudaErrorMemoryAllocation` or `cudaHostAlloc` failure during engine startup with no useful error message above the wrapper traceback.

1. **Pinned-memory permission**: always pass `--ulimit memlock=-1` to `docker run`. The default container ulimit is tiny (8 KB / 64 MB depending on host) and large `cudaHostAlloc` calls will fail with `CUDA error: out of memory` despite plenty of host RAM being free. The symptom is `torch.zeros(...)` failing inside `vllm/v1/kv_offload/cpu/gpu_worker.py`.
2. **Reserve host RAM headroom**: the user-facing `--kv-offloading-size N` is a **lower bound on the actual pinned allocation**, not a hard cap. Empirically on vLLM nightly with Gemma-4 + MTP, the engine pins ~**1.4× N** in practice (extra goes to per-layer/per-attention-type metadata, alignment, and — when speculative decoding is enabled — a separate KV layout for the draft model). Plan for `available_host_ram >= 1.4 * offload_size + 15 GB` (the +15 GB covers vLLM activations + container OS overhead + safety margin). On a 118 GB host this means the practical ceiling is roughly **~60 GB** with MTP-on (uses ~83 GB pinned) and **~75 GB** with MTP-off. The 1.4× multiplier is a rough heuristic — measure once on the actual model with `free -h available` before vs after the "Allocating CPU tensors..." log lines, and refine for that engine/model. When the user requests a size that does not fit, ask them to reduce or free RAM first; do not silently lower it.
3. **Extend the readiness poll budget**: pinning N GB of CPU memory takes ~2.5s/GB on typical hardware (e.g. 50 GB ≈ 130s, 90 GB ≈ 4 min), on top of normal model-load + torch.compile time. The default 10-min readiness budget can be too tight; for offload-on runs use at least 15 min, and monitor `free -h available` dropping toward the offload size as a healthy sign.

Confirm these from the startup logs: the engine prints `[gpu_worker.py:NNN] Allocating M CPU tensors...` lines while pinning. Watch `free -h available` drop by `offload_size / M` per line. If it stalls or the container exits, this is the cause.

## Automation robustness (multi-hour unattended sweeps)

When you script a long unattended sweep (many configs × binary search, hours of wall-clock, no human watching), the binary search itself is the easy part — the orchestration around it is where nights get wasted. These are hard-won rules; each one comes from a real overnight failure that silently burned hours or produced fake data. The overarching principle: **a probe/deployment failure must degrade to a correct verdict, never to fake data or a silent hang.**

1. **Never judge liveness with a single short-timeout health poll.** A saturated-but-alive server is slow to answer `/v1/models` (or `/health`); a 5 s `curl` then times out and you wrongly conclude "server died mid-probe." Retry with a generous timeout (e.g. 20 s × 3) before declaring death, or check the container/process is still up (`docker ps`) as the primary signal. This false-DEAD bites hardest on single-worker tests where one server bears the full load; multi-worker/router setups mask it. If a probe reports a death, confirm the server is actually gone (`docker ps`, direct `curl` with long timeout) before trusting it.

2. **Distinguish "deployment is dead" from "this QPS is too high."** A server that OOM-dies *under load* (GPU VRAM exhausted at high QPS — exit code 137) means *that QPS is too high*, i.e. a **FAIL to bisect below**, not a dead test. If your bisect treats every death as a fatal DIED, retrying the same config just OOMs again and you lose the test. Instead: if the server died mid-probe **and lower QPS have passed**, relaunch it and treat this probe as FAIL (search downward). Only a death **before any PASS** (won't even start) is a true DIED.

3. **`pgrep -f <name>` matches your own observers.** A guard like `while pgrep -f run_x.sh; do sleep; done` will match your monitor scripts, editor, and even the grep — and never exit, hanging the whole run forever. Match container/PID precisely (`ps -eo comm`, exact PID, `docker ps --filter name=^x$`), never `pgrep -f` on a substring that your own tooling also contains.

4. **Globals set inside `$(...)` are lost.** `name=$(launch_and_set_globals)` runs in a subshell; any `LAUNCH_OK=1` it sets is invisible to the caller, so every launch looks failed. Call such functions directly and read globals, or return status via exit code / stdout only.

5. **`n=$(grep -c ... || echo 0)` can hold a newline** ("0\n0"), which then breaks `[ "$n" -ge 10 ]` with `integer expression expected`. Sanitize numeric captures: `n=$(echo "$n" | tr -dc '0-9'); n=${n:-0}`.

6. **Per-test timeout must fit the SLOWEST test, not the median.** Offload runs (2.5 s/GB pinning) with more rounds and upward-extrapolating bounds can take 3-4× a plain run. A cap tuned to the fast case kills the slow ones as false timeouts right when they were converging. Size the hard cap to the worst case (offload + max rounds + full extrapolation), and on timeout recover the partial answer from the probe log (the last PASS/FAIL bracket usually pins it) rather than discarding.

7. **Set the bisect upper bound from the actual deployment, not a habit.** A fixed cap (e.g. 2.0) that's fine for one card is far below a router fronting N cards (ceiling ~N × single-card). Every test then reports "≥2.0" and the sweep is worthless. Always extrapolate the upper bound upward while it still PASSes, with a sane ceiling.

8. **Reuse deployments across tests that share a launch config.** If 3 tests differ only in router policy or a client flag (not the vLLM launch args), start the workers once and run all 3 — don't `stop_all + relaunch` (full recompile) per test. Launch workers in parallel (fire all, then wait-all-ready) so wall time ≈ one compile, not N.

9. **Make the sweep resumable and non-destructive.** Append results to a file; on (re)start, **skip any test that already has a non-DIED result** rather than truncating and re-running everything. A mid-sweep fix or card-count change then costs only the unfinished tests, not the night.

10. **On a shared machine, scan for free resources at launch and never touch others'.** Compute the usable GPU set at runtime (VRAM < threshold, excluding known-bad indices), pin only those, and only ever `docker rm` your own named containers. A co-tenant's job can appear or vanish mid-sweep; a static card list or a blanket `docker rm` will collide.

11. **Verify a `RESULT`/completion signal against the file of record before trusting it.** A monitor tailing a log can read a mid-probe line or a stale value and report a completion that didn't happen. Confirm from the authoritative results file (line count / grep) before acting on "done."

## Helper scripts

- `scripts/analyze_rounds.py` parses one or more JSON-lines files produced by `--json-output`, averages per-round `Latency.p50` (across shards if multiple files are given), and emits PASS/FAIL/NOT_ENOUGH_ROUNDS via exit code. Two metrics are always computed: (a) the legacy tail-N average, (b) an auto-detected steady-window average (backward walk with `±0.30` of running median, minimum 3 rounds). When invoked with `--auto-steady` (recommended default in the probe procedure), the steady metric becomes the primary PASS/FAIL signal with tail-N as fallback. Without the flag, behavior is byte-identical to the v1 tail-only algorithm. Also emits a `warmup_dominated` boolean and human-readable `notes[]` for downstream reporting. Read its top docstring for full details.
- `scripts/prefix_cache_hit_rate.py` snapshots a Prometheus `/metrics` endpoint and computes prefix-cache hit rate between two snapshots. Two subcommands: `snapshot --url … --out …` and `diff --before … --after …`. Framework-agnostic: discovers prefix-cache metric names by heuristic (any name containing "prefix" + hit-like / query-like keywords; falls back to hits+misses pair). Exit codes: `0` OK, `2` NO_PREFIX_METRICS (no prefix metrics on endpoint — caller should fall back to log scraping or engine docs), `3` error. Read its top docstring for full details.
- `scripts/prepare_dataset.sh` validates one explicitly selected shared dataset and atomically stages only that file under `$WORKDIR/datasets/`. It rejects missing, empty, out-of-directory, relative, and unsafe local targets.
- `scripts/smoke.sh` validates round analysis, prefix-cache metrics, and selected-dataset staging (including failure and symlink boundaries). Run it after editing any bundled helper; it needs no network, live engine, or GPU.
