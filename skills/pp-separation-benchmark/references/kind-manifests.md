# Orchestration-fidelity tier: kind + ingress-nginx + real vLLM

All manifests referenced here live in `../manifests/` and were verified end-to-end
on a 7×RTX-5090 host: real vLLM hot/cold pools, GPU passthrough, and exact
header-based routing (proven by per-backend request counts, not response bodies).

## Bring-up order (verified)

```bash
export PATH="$HOME/.local/bin:$PATH"

# 0. Prereqs on host: docker, nvidia-container-toolkit + driver, kind, kubectl.
#    Generate CDI spec once (adds a file, changes nothing else):
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# 1. Create cluster WITH the weights dir mounted (extraMounts) — see kind-config.yaml.
kind create cluster --config manifests/kind-config.yaml   # name: pp-split

# 2. GPU passthrough (idempotent, node-local, no host daemon changes).
bash scripts/setup-kind-gpu.sh                            # -> nvidia.com/gpu = N

# 3. Import the vLLM image into the node's containerd (peak disk ~= uncompressed size).
kind load docker-image <vllm-image> --name pp-split

# 4. Ingress controller, exposed on a NodePort mapped by kind-config extraPortMappings.
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.2/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx patch svc ingress-nginx-controller \
  -p '{"spec":{"type":"NodePort","ports":[{"name":"http","port":80,"targetPort":"http","nodePort":30080,"protocol":"TCP"}]}}'
# WAIT for the admission endpoint before applying any Ingress (see pitfalls.md #5):
until kubectl -n ingress-nginx get endpoints ingress-nginx-controller-admission \
  -o jsonpath='{.subsets[0].addresses[0].ip}' | grep -q .; do sleep 5; done

# 5. Routing rules + pools.
kubectl apply -f manifests/ingress.yaml        # canary-by-header split
kubectl apply -f manifests/vllm-pools.yaml     # real vLLM hot(+offload)/cold pools
```

## The routing rule (manifests/ingress.yaml)

Replicates the docker-tier nginx `map $http_x_flow_kv_evict { ~^true$ cold; default hot; }`
using two Ingress objects that share one host:
- `split-main` — default → `hot-svc`.
- `split-cold-canary` — `canary-by-header: X-Flow-KV-Evict`, `canary-by-header-value: "true"` → `cold-svc`.

canary-by-header is ingress-nginx's native exact-value header router; `"true"`
goes canary (cold), everything else stays on the main rule (hot). Do **not** parse
the body.

## Pools (manifests/vllm-pools.yaml)

- `hot-vllm` (label `app=hot-pool`): vLLM with `--kv-transfer-config
  {"kv_connector":"SimpleCPUOffloadConnector","kv_role":"kv_both",
  "kv_connector_extra_config":{"cpu_bytes_to_use":<bytes>}}`, env
  `VLLM_USE_SIMPLE_KV_OFFLOAD=1`. `runtimeClassName: nvidia`,
  `resources.limits.nvidia.com/gpu: 1`, hostPath mount of the weights dir,
  readinessProbe on `/v1/models`.
- `cold-vllm` (label `app=cold-pool`): identical vLLM **without** the offload
  connector.
- `hot-svc` / `cold-svc` select `app=hot-pool` / `app=cold-pool`.

For a full ratio (e.g. 2h5c) scale `hot-vllm` to 2 and `cold-vllm` to 5, each
pinned to a distinct GPU. For a smoke/single-point check, 1+1 is enough.
`manifests/vllm-smoke.yaml` is a single-pod loader sanity check.

## Verifying routing correctly (do NOT trust response bodies)

Both pools serve the same model, so responses are identical. Prove routing by
counting requests landing on each backend pod:
```bash
HOT=$(kubectl get pod -l app=hot-pool -o name | head -1)
COLD=$(kubectl get pod -l app=cold-pool -o name | head -1)
h0=$(kubectl logs $HOT --tail=2000 | grep -c chat/completions)
c0=$(kubectl logs $COLD --tail=2000 | grep -c chat/completions)
BASE=http://127.0.0.1:<hostPort>/v1/chat/completions
for i in 1 2 3; do curl -s -H 'Content-Type: application/json' -d "$BODY" $BASE >/dev/null; done                         # non-truncated -> hot
for i in 1 2 3; do curl -s -H 'X-Flow-KV-Evict: true' -H 'Content-Type: application/json' -d "$BODY" $BASE >/dev/null; done  # truncated -> cold
# expect hot +3 and cold +3
```

## Load test with the real replay client

Point `online_replay.py --forward-kv-evict --api-base http://127.0.0.1:<hostPort>/v1`
at the ingress; `--forward-kv-evict` makes it emit `X-Flow-KV-Evict` per the
dataset flag, so the split happens exactly as in production. Use the same probe
protocol as the docker tier (16 rounds / tail 8 / 0.1 precision) but remember the
kind numbers carry kube-proxy/CNI overhead and are not directly comparable to the
docker-tier absolute QPS.

## Teardown / rollback

`kind delete cluster --name pp-split` removes everything K8s (one node container)
without touching host docker, neighbor containers, or denylisted GPUs.
