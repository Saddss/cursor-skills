# Policy-fidelity tier: docker + nginx

The default tier for answering "is the split worth it?". Zero network/scheduler
noise: every worker runs `--network host` on `127.0.0.1`, nginx does header
routing in-process, GPUs are bound with `--gpus device=N`. This isolates the
routing policy from orchestration overhead — which is why it is *cleaner* than
kind for the capacity question.

## Topology

- **B0 (unified)**: one vLLM worker per GPU (ports `8100+gpu`) behind one
  sglang-router with `--policy cache_aware` (port 30000). No external offload.
- **Split ratio `HhCc`**: `H` hot GPUs (ports `8200+gpu`, each with
  `SimpleCPUOffloadConnector` KV offload) behind a `cache_aware` hot router
  (port 30010); `C` cold GPUs (ports `8300+gpu`, no offload) load-balanced
  directly by nginx round-robin. One nginx ingress (port 30020) maps
  `$http_x_flow_kv_evict` → cold backend (`~^true$`) or hot router (default).

## Worker launch (the parts that matter)

vLLM `serve` with: `--max-model-len <len> --max-num-seqs 64
--max-num-batched-tokens 8192 --gpu-memory-utilization 0.94 --language-model-only
--trust-remote-code --kv-cache-dtype fp8 --quantization compressed-tensors
--enable-prefix-caching --speculative-config {"method":"mtp","model":"<draft>",
"num_speculative_tokens":3} --stream-interval 5 -O3`. Env on every worker:
`HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 VLLM_KV_EVICT_TRUNC=1
VLLM_KV_EVICT_TRUNC_MAX_CONVS=8192 VLLM_KV_EVICT_TRUNC_TTL_SEC=1800`. Hot workers
add `VLLM_USE_SIMPLE_KV_OFFLOAD=1` and `--kv-transfer-config {...
cpu_bytes_to_use: <dynamic>}`. Containers: `--init --ipc=host --ulimit
memlock=-1 --ulimit stack=67108864`, single mount `<hf>:/root/.cache/huggingface`.

`--init` is required — without it a child-reaping zombie appears during topology
transitions.

## nginx routing config (generated per ratio)

```
events { worker_connections 4096; }
http {
  upstream hot_backend { server 127.0.0.1:30010; }
  upstream cold_backend { server 127.0.0.1:83<gpu>; ... }   # one per cold GPU
  map $http_x_flow_kv_evict $selected_backend {
    ~^true$ cold_backend;
    default hot_backend;
  }
  server {
    listen 30020;
    location / {
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Flow-KV-Evict $http_x_flow_kv_evict;
      proxy_set_header X-Flow-Conversation-Id $http_x_flow_conversation_id;
      proxy_buffering off;
      proxy_pass http://$selected_backend;
    }
  }
}
```
Mounted read-only at `/etc/nginx/nginx.conf` in an `nginx:1.27-alpine` container.

## Orchestrator / controller design

- **orchestrator**: iterates model profiles (e.g. Kaon then Gemma); per profile
  runs preflight → B0 → ratio sweep (adaptive). Launch under `nohup` so a dropped
  shell/SSH can't SIGHUP it. State is a resumable `state.json`; completed probes
  are skipped on restart (`skip_completed`), `failed_low` ratios are skipped
  (`skip_failed_low`).
- **controller**: per-topology lifecycle — `start-split` (stop owned containers
  idempotently, size offload, launch workers, wait ready, launch router+nginx),
  `run-split` (fixed_qbase probe + capacity binary search), `resume-split`
  (continue from a recorded fixed_qbase). Exit codes: 0 done, 2 `failed_low`
  (valid), other = real error.
- **watch**: low-frequency read-only status panel over `state.json`.

## Replay client

`online_replay.py --forward-kv-evict --replay-mode qps --target-qps <q>
--api-base http://127.0.0.1:30020/v1 --use-chat --round-duration 30
--round-drain-timeout 300 --request-timeout 600 --max-rounds <8|16>
--e2e-slo <slo> --json-output rounds.jsonl`. `--forward-kv-evict` emits the
`X-Flow-KV-Evict` header from the dataset's truncation flag — this is the only
thing that makes the split happen.

## Reference result shape (7-GPU Kaon, p50 E2E < 6.5s)

| ratio | best_pass QPS | vs B0 |
|---|---|---|
| B0 (unified cache-aware) | 31.0 | baseline |
| 2h5c | 31.0 | ~even |
| 1h6c | 18.8 | -39% |
| 3h4c | 5.1 | -84% |
| 4h3c | failed_low (<4.0) | — |

Trend: fewer hot cards / more cold cards is better here; the hot-pool KV offload
is the bottleneck, and it degrades sharply as hot cards increase. Best split only
*matched* unified — no card-count win demonstrated. Report this honestly; the aim
is to quantify improvement OR maximum closeness/loss, not to force a win.
