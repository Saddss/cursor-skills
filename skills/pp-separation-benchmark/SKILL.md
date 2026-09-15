---
name: pp-separation-benchmark
description: Benchmark an ingress-layer hot/cold pool separation scheme for LLM serving against a unified cache-aware baseline, and (optionally) reproduce it on real Kubernetes via kind. Use when the user asks to "测冷热分离"/"ingress split benchmark"/"分离 vs 统一哪个 QPS 高"/"扫冷热配比"/"pp separation"/"验证 ingress-nginx 冷热分流"/"在 kind 上跑真 vLLM 冷热池". Given a conversation-replay dataset with a known truncation rate, it (1) profiles the workload into hot (non-truncated) vs cold (truncated) request pools by request count AND token load, (2) measures the unified cache-aware baseline (B0) max sustainable QPS under a model SLO via binary search, (3) sweeps hot/cold GPU ratios (2h5c/3h4c/4h3c plus adaptive 1h6c/5h2c/6h1c) where the hot pool runs a cache-aware router + KV offload and the cold pool round-robins truncated requests, requiring each ratio to pass overall+hot+cold SLO and <=15% intra-pool imbalance, and (4) reports best ratio, QPS vs baseline, per-pool latency, internal/external cache hit rate, and imbalance. Includes a two-fidelity design: a "policy fidelity" tier (docker+nginx, zero network noise, answers "is separation worth it") and an "orchestration fidelity" tier (kind + ingress-nginx canary-by-header + NVIDIA device-plugin, answers "does this deploy on real K8s"). Carries hard-won fixes for docker-kill hangs, legitimately-failing ratios aborting the run, kind GPU passthrough via CDI without touching the host docker daemon, and glibc-vs-musl image gotchas.
---

# PP Ingress Hot/Cold Separation Benchmark

Measure whether routing **truncated** (KV-evict) requests to a dedicated **cold pool** and **non-truncated** requests to a cache-aware **hot pool** (with CPU KV offload) beats a single **unified cache-aware** deployment across the same GPUs. The goal is never to prove separation wins — it is to find, per model and workload: is it higher-QPS than unified; what are the per-pool latencies; how does average input length + truncation rate relate to the best hot/cold ratio; and if there is no improvement, the maximum loss or closeness.

The routing signal is a single boolean header (e.g. `X-Flow-KV-Evict: true`) emitted by the replay client per the dataset's truncation flag. **Ingress routes on the header only — it never parses the request body.** This is the production-recommended shape (upstream emits the header; ingress has two rules / two Services).

## Two fidelity tiers — pick before you start

| Tier | Tooling | Answers | Network noise |
|---|---|---|---|
| **Policy fidelity** (default) | docker + nginx `map`, `--gpus device=N` | Is separation worth it? Capacity/latency/cache of the routing policy itself | None (`--network host`, `127.0.0.1`) |
| **Orchestration fidelity** | kind + ingress-nginx canary-by-header + NVIDIA device-plugin | Does it deploy on real K8s? Service/kube-proxy/readiness behavior | Real (kube-proxy/CNI) |

For the science question ("does the split beat unified?"), the docker tier is *cleaner* — it removes network and scheduler noise and isolates the routing policy. Reach for the kind tier only to validate the K8s deployment form; do not use its absolute QPS to compare against the docker tier (kube-proxy/CNI add a hop, and single-node kind has no cross-node latency).

## Portability — nothing here is host-specific

This skill carries no baked-in machine assumptions. Everything is parameterized;
adapt to a new host by setting values, not editing logic:

- **Manifests** use `@@VAR@@` placeholders. Copy `scripts/env.example` → `my.env`,
  fill it in (`VLLM_IMAGE`, `HF_HOST_PATH`, `MODEL_PATH`, `SERVED_MODEL`,
  `DRAFT_PATH`), then `scripts/render-manifests.sh` writes ready-to-apply YAML.
  `manifests/examples-verified/` holds a concrete, already-run copy for reference.
- **kind GPU setup** (`scripts/setup-kind-gpu.sh`) reads `CLUSTER`, `NODE`,
  `CDI_SPEC`, `GPU_ALLOWLIST` from the env — no hardcoded names.
- **GPU count / ratios are free.** Use however many GPUs the host has. The ratios
  (2h5c/3h4c/…) are just "hot count + cold count = total usable GPUs"; the sweep
  logic and probe protocol are independent of the number. There is NO 5-GPU or
  7-GPU assumption — those appear only as worked examples in the references.
- **`GPU_ALLOWLIST` is optional and only for shared hosts.** On a dedicated
  machine leave it empty to expose all GPUs; K8s schedules freely and you can
  skip the denylist/neighbor concerns entirely. Set it only when other tenants
  or reserved cards exist on the box (see pitfalls.md #9).
- Any GPU indices, UUIDs, neighbor container names, or absolute paths in the
  references are **examples from one run**, retained as evidence — not required
  values. Read them as "this is what it looked like when it worked".

## Fixed workload contract (verify at session start, never mutate)

- Lock the dataset by **SHA256 + row count + truncation rate** (within a tolerance band), verify strict timestamp ordering and strict-boolean truncation flags.
- Truncation is both a **request-count** fraction and a **token-load** fraction — they differ (e.g. 52.9% of requests but 59.7% of token load). Allocate cold/hot by token load, not request count. See `scripts/workload_shape.py`.
- On a shared host, fix the GPU allowlist/denylist up front (example from one run: use 0,1,3,4,5,6,7, never touch GPU2 — your host's safe set will differ). On a dedicated host, skip this. Record whether `force_offload_override` is set and the PCIe link gen — a Gen1-downgraded link understates offload benefit (hit rate is unaffected; absolute capacity is).

## Probe protocol

- B0 (unified): 8 rounds, tail window 4. Split ratios: 16 rounds, tail window 8. Precision 0.1 QPS.
- Binary search: run LOW (4.0) then HIGH (9.0); if HIGH passes, extrapolate the ceiling upward to a measured FAIL, then bisect; else bisect within. Every accepted maximum must have an adjacent measured FAIL (no unmeasured ceilings).
- A split ratio passes a QPS only if **all** hold: overall SLO, hot-pool SLO, cold-pool SLO, hot intra-pool imbalance <=15%, cold intra-pool imbalance <=15%.
- Offload sizing is dynamic per hot-worker count: `per_worker = min(CAP, floor((MemAvailable - host_reserve) / (hot_workers * footprint_factor)))`, footprint_factor ~1.4 for the MTP connector, host_reserve ~64 GiB. Abort a topology if MemAvailable falls below a safety floor (~55 GiB) during startup.

## Adaptive ratio sweep

Run 2h5c, 3h4c, 4h3c. Then: if the best is 2h5c, also run 1h6c; if the best is 4h3c, run 5h2c, then 6h1c if 5h2c wins. A ratio that cannot sustain even the QPS floor is a **valid `failed_low` result**, not an error — record it and continue.

## Reporting

Per ratio: best_pass + adjacent FAIL; same-load comparison at the B0 max (hot/cold vs unified latency delta); internal + external cache hit rate computed as `sum(hits)/sum(queries)` across workers (NOT an average of per-worker percentages); intra-pool request counts + imbalance %; and an explicit statement of whether the experiment demonstrates a card-count reduction (if B0 and split use the same cards, it does not).

## Critical fixes baked in (see references/pitfalls.md)

1. **docker-kill hang** — on topology switch, `docker rm -f` intermittently returns "did not receive an exit event" while the container does die. Make teardown idempotent: issue removal, poll `docker ps` until gone, retry N times; only fail if a container is genuinely still alive.
2. **`failed_low` must not abort the run** — a ratio failing the QPS floor exits the controller with code 2; the orchestrator must treat exit-2 from run/resume-split as `skip_failed_low` (not `check=True` fatal), and `best_ratio` must select only among passing ratios (never `float(None)`).
3. **kind GPU passthrough without touching host docker** — the host has `live-restore=false`, so restarting dockerd would restart neighbor containers. Never edit `/etc/docker/daemon.json` or the global `accept-nvidia-visible-devices` switch. Instead use CDI: `nvidia-ctk cdi generate`, copy the toolkit binaries + all driver libs (from the CDI spec's hostPath list) into the kind node, configure the node's own containerd for the nvidia runtime + `enable_cdi`, restart only the node's containerd, and run the device-plugin under a `nvidia` RuntimeClass. See `scripts/setup-kind-gpu.sh`.
4. **glibc vs musl** — vLLM/CUDA images are glibc; `nvidia-smi` and CUDA fail with "not found" (loader error) inside alpine/musl images. Use a glibc base (debian/ubuntu) for any GPU pod.
5. **ingress-nginx admission webhook race** — apply Ingress resources only after the controller's `-admission` Service endpoint is populated, else `connection refused`.
6. **kind is a separate containerd** — the node does not share the host's images; `kind load docker-image` re-imports (peak disk ~= uncompressed image size). Budget disk before importing a large (e.g. 48 GB) vLLM image.

## Shared-host safety (non-negotiable)

Low-frequency monitoring only. Never batch-stop containers, never touch denylisted GPUs or neighbor containers, never run two orchestrators, never delete existing result.json. Before any destructive/system op (delete image, edit global config, create/delete cluster) report first and get approval. If observed reality contradicts a stated assumption (e.g. "qie is idle" but a GPU process started 45s ago), surface it and stop rather than proceed.

## Files

- `scripts/setup-kind-gpu.sh` — idempotent kind GPU passthrough via CDI (no host daemon changes); env-configurable (`CLUSTER`, `NODE`, `CDI_SPEC`, `GPU_ALLOWLIST`).
- `scripts/render-manifests.sh` + `scripts/env.example` — fill the `@@VAR@@` placeholders in the manifests for any host.
- `scripts/workload_shape.py` — split a replay dataset into hot/cold by count and token load.
- `manifests/*.yaml` — templated kind-config, ingress canary-by-header, vLLM smoke pod, hot/cold pools. `manifests/examples-verified/` keeps a concrete already-run copy.
- `references/kind-manifests.md` — bring-up order, routing rule, verification recipe, verified example results.
- `references/pitfalls.md` — the hard-won fixes (docker-kill hang, failed_low, CDI passthrough, glibc/musl, webhook race, disk, extraMounts, comparability, GPU allowlist).
- `references/docker-tier.md` — the docker+nginx policy-fidelity topology and controller/orchestrator design.
- `references/docker-tier.md` — the docker+nginx policy-fidelity topology and controller/orchestrator design.
